# backend/engine.py — The 30-60-90 Brain (Part 1 of 2)
# All math: probability curves, floorplan calcs, aging classification,
# pricing elasticity, exit path scoring, waterfall generation, alarm generation.

import math
import statistics
from datetime import date, timedelta
from typing import List, Optional, Dict, Any


# ---------------------------------------------------------------------------
# CONSTANTS & DEFAULTS
# ---------------------------------------------------------------------------
DEFAULT_MEDIAN_DAYS_TO_SALE = 45.0
DEFAULT_DEMAND_SCORE = 50.0
DEFAULT_FLOORPLAN_APR = 6.5

# Logistic curve steepness parameters (tuned to industry benchmarks)
BASE_LAMBDA = 0.035  # base daily hazard rate
DEMAND_MULTIPLIER_RANGE = (0.5, 2.0)  # low demand = slow, high demand = fast
PRICE_SENSITIVITY = 0.0015  # per dollar below market, probability boost


# ---------------------------------------------------------------------------
# HELPER: Clamp
# ---------------------------------------------------------------------------
def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


# ---------------------------------------------------------------------------
# 1) SALE PROBABILITY MODEL
#    Uses a modified exponential CDF calibrated by comp data + signals
# ---------------------------------------------------------------------------
def compute_lambda(
    median_days_to_sale: float = DEFAULT_MEDIAN_DAYS_TO_SALE,
    demand_score: float = DEFAULT_DEMAND_SCORE,
    price_vs_market: float = 0.0,  # negative = priced below market
    days_already_held: int = 0,
    views_last_7: int = 0,
    leads_last_7: int = 0,
) -> float:
    """
    Compute the daily hazard rate (lambda) for sale probability.
    Higher lambda = faster expected sale.
    """
    # Base lambda from median days to sale
    if median_days_to_sale > 0:
        base = math.log(2) / median_days_to_sale
    else:
        base = BASE_LAMBDA

    # Demand adjustment: score 0-100 maps to multiplier range
    demand_factor = DEMAND_MULTIPLIER_RANGE[0] + (
        (demand_score / 100) * (DEMAND_MULTIPLIER_RANGE[1] - DEMAND_MULTIPLIER_RANGE[0])
    )

    # Price adjustment: below market boosts, above market penalizes
    price_factor = 1.0 + (price_vs_market * PRICE_SENSITIVITY * -1)
    price_factor = clamp(price_factor, 0.3, 2.5)

    # Engagement signal boost
    signal_boost = 1.0
    if views_last_7 > 50:
        signal_boost += 0.1
    if views_last_7 > 100:
        signal_boost += 0.1
    if leads_last_7 > 3:
        signal_boost += 0.15
    if leads_last_7 > 8:
        signal_boost += 0.15

    # Aging penalty: vehicles get stale
    aging_penalty = 1.0
    if days_already_held > 30:
        aging_penalty -= 0.05 * ((days_already_held - 30) / 30)
    aging_penalty = clamp(aging_penalty, 0.4, 1.0)

    lam = base * demand_factor * price_factor * signal_boost * aging_penalty
    return clamp(lam, 0.001, 0.15)


def cumulative_sell_probability(lam: float, day: int) -> float:
    """P(sold by day T) = 1 - e^(-lambda * T)"""
    return 1.0 - math.exp(-lam * day)


def daily_sell_probability(lam: float, day: int) -> float:
    """P(sold on exactly day T) = lambda * e^(-lambda * T)"""
    return lam * math.exp(-lam * day)


def compute_probabilities(lam: float) -> Dict[str, float]:
    return {
        "p30": round(cumulative_sell_probability(lam, 30), 4),
        "p60": round(cumulative_sell_probability(lam, 60), 4),
        "p90": round(cumulative_sell_probability(lam, 90), 4),
    }


# ---------------------------------------------------------------------------
# 2) DAILY CURVE (90 data points for hover UI)
# ---------------------------------------------------------------------------
def generate_daily_curve(
    lam: float,
    total_cost: float,
    list_price: float,
    daily_floorplan: float,
    days_already_held: int = 0,
) -> List[Dict[str, Any]]:
    """
    Returns 90 objects: day 1-90 from TODAY (not from acquisition).
    Each point includes:
      - daily_sell_probability
      - cumulative_sell_probability
      - floorplan_cost_to_date (from acquisition, so includes days_already_held)
      - gross_erosion_to_date (how much gross has shrunk since acquisition)
    """
    curve = []
    for d in range(1, 91):
        total_day = days_already_held + d
        cum_p = cumulative_sell_probability(lam, d)
        daily_p = daily_sell_probability(lam, d)
        floorplan_to_date = daily_floorplan * total_day
        potential_gross = list_price - total_cost
        gross_erosion = floorplan_to_date  # erosion = accumulated carry cost

        curve.append({
            "day": d,
            "daily_sell_probability": round(daily_p, 5),
            "cumulative_sell_probability": round(cum_p, 4),
            "floorplan_cost_to_date": round(floorplan_to_date, 2),
            "gross_erosion_to_date": round(gross_erosion, 2),
        })
    return curve


# ---------------------------------------------------------------------------
# 3) AGING CLASSIFICATION
# ---------------------------------------------------------------------------
def classify_aging(days_in_inventory: int, p30: float) -> str:
    if days_in_inventory <= 30 and p30 >= 0.35:
        return "healthy"
    elif days_in_inventory <= 60 or p30 >= 0.20:
        return "at_risk"
    else:
        return "danger"


# ---------------------------------------------------------------------------
# 4) INFLECTION POINT
#    The day where expected marginal gain from holding < marginal carry cost
# ---------------------------------------------------------------------------
def compute_inflection_day(
    lam: float,
    list_price: float,
    total_cost: float,
    daily_floorplan: float,
    wholesale_exit_price: float,
    days_already_held: int = 0,
) -> int:
    """
    Find the day (from today) where holding one more day costs more
    than the expected marginal revenue gain.
    """
    potential_retail_gross = list_price - total_cost

    for d in range(1, 181):
        total_day = days_already_held + d
        floorplan_accumulated = daily_floorplan * total_day
        net_retail_gross = potential_retail_gross - floorplan_accumulated

        # Expected value of holding = P(sell on day d) * net_retail_gross
        p_sell_today = daily_sell_probability(lam, d)
        ev_hold = p_sell_today * net_retail_gross

        # Cost of holding one more day
        marginal_cost = daily_floorplan

        # Wholesale alternative (available anytime)
        wholesale_gross = wholesale_exit_price - total_cost - floorplan_accumulated

        # Inflection: EV of holding < marginal cost OR wholesale beats retail EV
        if ev_hold < marginal_cost or net_retail_gross < wholesale_gross:
            return d

    return 180  # never found — very unlikely


# ---------------------------------------------------------------------------
# 5) CARRY COST PROJECTIONS
# ---------------------------------------------------------------------------
def compute_carry_costs(daily_floorplan: float, days_already_held: int) -> Dict[str, float]:
    return {
        "daily_carry_cost": round(daily_floorplan, 2),
        "carry_cost_30": round(daily_floorplan * (days_already_held + 30), 2),
        "carry_cost_60": round(daily_floorplan * (days_already_held + 60), 2),
        "carry_cost_90": round(daily_floorplan * (days_already_held + 90), 2),
    }


def compute_margin_erosion(
    list_price: float, total_cost: float, daily_floorplan: float, days_already_held: int
) -> Dict[str, float]:
    current_gross = list_price - total_cost - (daily_floorplan * days_already_held)
    return {
        "margin_erosion_30": round(current_gross - daily_floorplan * 30, 2),
        "margin_erosion_60": round(current_gross - daily_floorplan * 60, 2),
        "margin_erosion_90": round(current_gross - daily_floorplan * 90, 2),
    }
  # ---------------------------------------------------------------------------
# 6) PRICING STRATEGY RECOMMENDATION
# ---------------------------------------------------------------------------
def compute_price_elasticity(
    comp_median_price: Optional[float],
    list_price: float,
    demand_score: float,
    supply_count: int,
) -> Dict[str, Any]:
    """
    Assess how sensitive this vehicle's sell probability is to price changes.
    Returns elasticity level + reason.
    """
    if comp_median_price is None or comp_median_price == 0:
        return {"elasticity": "medium", "reason": "Insufficient comp data to assess elasticity precisely."}

    price_ratio = list_price / comp_median_price
    reasons = []

    # High supply + priced above market = very elastic
    if supply_count > 15 and price_ratio > 1.03:
        reasons.append(f"High supply ({supply_count} comps) with price {round((price_ratio-1)*100,1)}% above median.")
        elasticity = "high"
    elif supply_count > 10 and price_ratio > 1.0:
        reasons.append(f"Moderate supply ({supply_count} comps), priced above median.")
        elasticity = "high"
    # Low supply = price insensitive
    elif supply_count <= 5 and demand_score > 60:
        reasons.append(f"Low supply ({supply_count} comps) with strong demand (score {demand_score}).")
        elasticity = "low"
    elif demand_score > 70 and price_ratio < 1.02:
        reasons.append(f"Strong demand (score {demand_score}), competitively priced.")
        elasticity = "low"
    else:
        reasons.append(f"Moderate market conditions. Supply: {supply_count}, demand score: {demand_score}.")
        elasticity = "medium"

    return {"elasticity": elasticity, "reason": " ".join(reasons)}


def recommend_pricing(
    list_price: float,
    total_cost: float,
    comp_median_price: Optional[float],
    days_in_inventory: int,
    p30: float,
    demand_score: float,
    supply_count: int,
    min_acceptable_margin: float,
    daily_floorplan: float,
) -> Dict[str, Any]:
    """
    Returns: action (hold/reduce/increase), dollar amount, expected lift, gross impact.
    """
    if comp_median_price is None or comp_median_price == 0:
        return {
            "price_action": "hold",
            "price_change_amount": 0,
            "price_action_lift_p": 0,
            "price_action_gross_impact": 0,
        }

    price_vs_market = list_price - comp_median_price
    price_floor = total_cost + min_acceptable_margin

    # REDUCE logic
    if (price_vs_market > 0 and days_in_inventory > 15) or (days_in_inventory > 30 and p30 < 0.30):
        # How much to reduce
        if days_in_inventory > 60:
            target = min(comp_median_price * 0.97, comp_median_price - 500)
        elif days_in_inventory > 30:
            target = comp_median_price
        else:
            target = comp_median_price + (price_vs_market * 0.5)

        target = max(target, price_floor)
        change = round(list_price - target, 0)

        if change < 100:
            return {
                "price_action": "hold",
                "price_change_amount": 0,
                "price_action_lift_p": 0,
                "price_action_gross_impact": 0,
            }

        # Estimate probability lift from price reduction
        lift = clamp(change * PRICE_SENSITIVITY * 0.5, 0.01, 0.25)
        # Gross impact: lose the reduction but save carry days
        estimated_days_saved = lift * 30
        carry_saved = estimated_days_saved * daily_floorplan
        gross_impact = round(carry_saved - change, 2)

        return {
            "price_action": "reduce",
            "price_change_amount": round(change, 2),
            "price_action_lift_p": round(lift, 4),
            "price_action_gross_impact": gross_impact,
        }

    # INCREASE logic
    if price_vs_market < -1000 and demand_score > 65 and days_in_inventory < 20:
        increase = round(min(abs(price_vs_market) * 0.5, 2000), 0)
        lift = -0.02  # slight probability decrease
        gross_impact = round(increase + (lift * 30 * daily_floorplan), 2)

        return {
            "price_action": "increase",
            "price_change_amount": round(increase, 2),
            "price_action_lift_p": round(lift, 4),
            "price_action_gross_impact": gross_impact,
        }

    # HOLD
    return {
        "price_action": "hold",
        "price_change_amount": 0,
        "price_action_lift_p": 0,
        "price_action_gross_impact": 0,
    }


# ---------------------------------------------------------------------------
# 7) OPTIMAL EXIT PATH
# ---------------------------------------------------------------------------
def recommend_exit_path(
    list_price: float,
    total_cost: float,
    wholesale_exit_price: float,
    daily_floorplan: float,
    days_in_inventory: int,
    p30: float,
    p60: float,
    lam: float,
    comp_median_price: Optional[float],
) -> Dict[str, Any]:
    """
    Compare retail vs wholesale-auction vs dealer trade.
    Pick the risk-adjusted best path.
    """
    current_carry = daily_floorplan * days_in_inventory

    # RETAIL path
    retail_gross = list_price - total_cost - current_carry
    if lam > 0:
        expected_days_retail = min(1.0 / lam, 120)
    else:
        expected_days_retail = 90
    future_carry_retail = daily_floorplan * expected_days_retail
    retail_net = retail_gross - future_carry_retail
    retail_risk_adjusted = retail_net * p60  # weight by probability of actually selling

    # WHOLESALE path
    wholesale_gross = wholesale_exit_price - total_cost - current_carry
    wholesale_days = 7  # typically quick
    wholesale_carry = daily_floorplan * wholesale_days
    wholesale_net = wholesale_gross - wholesale_carry
    wholesale_risk_adjusted = wholesale_net * 0.95  # high certainty

    # DEALER TRADE path
    trade_gross = wholesale_exit_price * 1.03 - total_cost - current_carry  # slight premium over wholesale
    trade_days = 14
    trade_carry = daily_floorplan * trade_days
    trade_net = trade_gross - trade_carry
    trade_risk_adjusted = trade_net * 0.70  # moderate certainty

    options = {
        "retail": {
            "gross": round(retail_risk_adjusted, 2),
            "days": round(expected_days_retail, 0),
            "net": round(retail_net, 2),
            "risk_adjusted": round(retail_risk_adjusted, 2),
        },
        "wholesale_auction": {
            "gross": round(wholesale_net, 2),
            "days": wholesale_days,
            "net": round(wholesale_net, 2),
            "risk_adjusted": round(wholesale_risk_adjusted, 2),
        },
        "dealer_trade": {
            "gross": round(trade_net, 2),
            "days": trade_days,
            "net": round(trade_net, 2),
            "risk_adjusted": round(trade_risk_adjusted, 2),
        },
    }

    # Pick highest risk-adjusted
    best = max(options, key=lambda k: options[k]["risk_adjusted"])
    chosen = options[best]

    # Explain why
    reasons = []
    if best == "retail":
        reasons.append(f"Retail yields highest risk-adjusted return (${chosen['risk_adjusted']:,.0f}).")
        reasons.append(f"Expected {chosen['days']:.0f} days to sale with {p60:.0%} probability by day 60.")
        if retail_risk_adjusted > wholesale_risk_adjusted * 1.3:
            reasons.append("Retail significantly outperforms wholesale on expected value.")
    elif best == "wholesale_auction":
        reasons.append(f"Wholesale is the strongest exit at ${chosen['risk_adjusted']:,.0f} risk-adjusted.")
        reasons.append(f"Retail probability too low (p30={p30:.0%}) to justify continued holding cost.")
        reasons.append(f"Exit in ~{wholesale_days} days eliminates further floorplan bleed.")
    else:
        reasons.append(f"Dealer trade offers a slight premium over wholesale (${chosen['risk_adjusted']:,.0f}).")
        reasons.append("Retail risk is elevated but wholesale feels premature.")

    return {
        "optimal_exit": best,
        "exit_expected_gross": chosen["risk_adjusted"],
        "exit_expected_days": chosen["days"],
        "exit_reason": " ".join(reasons),
    }


# ---------------------------------------------------------------------------
# 8) ACTION PLAN GENERATOR
# ---------------------------------------------------------------------------
def generate_action_plan(
    days_in_inventory: int,
    aging_class: str,
    price_action: str,
    price_change_amount: float,
    optimal_exit: str,
    p30: float,
    views_last_7: int = 0,
    leads_last_7: int = 0,
    list_price: float = 0,
    comp_median_price: Optional[float] = None,
) -> List[str]:
    actions = []

    # Price action
    if price_action == "reduce":
        actions.append(f"Reduce price by ${price_change_amount:,.0f} this week to align with market and boost sell probability.")
    elif price_action == "increase":
        actions.append(f"Increase price by ${price_change_amount:,.0f} — demand supports a stronger position.")

    # Engagement actions
    if views_last_7 < 20:
        actions.append("Boost online visibility: refresh photos, update description, feature on homepage.")
    if leads_last_7 == 0 and days_in_inventory > 14:
        actions.append("Zero leads in 7 days — consider targeted promotion or social media push.")
    if leads_last_7 > 0 and leads_last_7 < 3:
        actions.append("Follow up aggressively on existing leads — each one matters at this stage.")

    # Aging-specific
    if aging_class == "danger":
        actions.append("URGENT: This unit is bleeding cash daily. Make an exit decision within 48 hours.")
        if optimal_exit != "retail":
            actions.append(f"Prepare {optimal_exit.replace('_', ' ')} exit — retail window is closing.")
    elif aging_class == "at_risk":
        actions.append("Set a hard deadline: if no serious buyer interest in 10 days, escalate exit strategy.")

    # Comp awareness
    if comp_median_price and list_price > comp_median_price * 1.05:
        actions.append(f"You are {round((list_price/comp_median_price - 1)*100, 1)}% above market median — buyers see this.")

    # Always ensure we have 3-5
    if len(actions) < 3:
        actions.append("Review this vehicle in your next morning meeting — assign one person to own the exit.")
    if len(actions) < 3:
        actions.append("Verify vehicle is listed on all active channels with current pricing.")

    return actions[:5]


# ---------------------------------------------------------------------------
# 9) RISK & CONFIDENCE
# ---------------------------------------------------------------------------
def assess_risk_and_confidence(
    days_in_inventory: int,
    comp_count: int,
    demand_score: float,
    p30: float,
    aging_class: str,
    price_action: str,
) -> Dict[str, Any]:
    risks = []
    triggers = []

    if comp_count < 5:
        risks.append("Low comp volume — market pricing estimates may be unreliable.")
        triggers.append("If 5+ new comps appear, re-run analysis for sharper pricing.")
    if days_in_inventory > 60:
        risks.append(f"Unit has aged {days_in_inventory} days — buyer perception of staleness is real.")
    if demand_score < 30:
        risks.append("Demand score is weak — this segment may be softening.")
        triggers.append("If demand score drops below 20, pivot to wholesale immediately.")
    if p30 < 0.15:
        risks.append("Very low 30-day sell probability — holding cost is likely exceeding expected return.")
    if price_action == "reduce":
        risks.append("Price reduction recommended — if dealer resists, probability will continue declining.")
        triggers.append("If no offers within 7 days of reduction, cut again or wholesale.")

    # Always add a macro risk
    risks.append("Market-wide inventory shifts or rate changes could alter this analysis.")
    triggers.append("Re-run analysis weekly or after any comp refresh.")

    # Confidence level
    if comp_count >= 10 and demand_score > 40:
        confidence = "high"
    elif comp_count >= 5:
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "risks": risks[:4],
        "change_triggers": triggers[:3],
        "confidence": confidence,
    }


# ---------------------------------------------------------------------------
# 10) FULL ANALYSIS — Orchestrator
# ---------------------------------------------------------------------------
def run_full_analysis(
    vehicle: Any,
    comp_summary: Optional[Any] = None,
    signals: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Master function. Takes a Vehicle ORM object + optional CompSummary + Signals.
    Returns the complete analysis dict ready to store in AnalysisReport.
    """
    total_cost = (vehicle.acquisition_cost or 0) + (vehicle.recon_cost or 0)
    daily_fp = total_cost * ((vehicle.floorplan_rate_apr or DEFAULT_FLOORPLAN_APR) / 100) / 365
    days = vehicle.days_in_inventory or 0

    # Extract comp data
    median_price = comp_summary.median_price if comp_summary and comp_summary.median_price else None
    median_days = comp_summary.median_days_to_sale if comp_summary and comp_summary.median_days_to_sale else DEFAULT_MEDIAN_DAYS_TO_SALE
    demand_score = comp_summary.demand_score if comp_summary else DEFAULT_DEMAND_SCORE
    supply_count = comp_summary.supply_count if comp_summary else 0
    comp_count = (comp_summary.auto_count or 0) + (comp_summary.manual_count or 0) if comp_summary else 0

    # Extract signals
    v7 = signals.views_last_7 if signals else 0
    l7 = signals.leads_last_7 if signals else 0

    price_vs_market = (vehicle.list_price - median_price) if median_price else 0

    # 1) Lambda
    lam = compute_lambda(
        median_days_to_sale=median_days,
        demand_score=demand_score,
        price_vs_market=price_vs_market,
        days_already_held=days,
        views_last_7=v7,
        leads_last_7=l7,
    )

    # 2) Probabilities
    probs = compute_probabilities(lam)

    # 3) Curve
    curve = generate_daily_curve(lam, total_cost, vehicle.list_price, daily_fp, days)

    # 4) Classification
    aging_class = classify_aging(days, probs["p30"])

    # 5) Inflection
    inflection = compute_inflection_day(
        lam, vehicle.list_price, total_cost, daily_fp,
        vehicle.wholesale_exit_price or 0, days
    )

    # 6) Carry costs + erosion
    carry = compute_carry_costs(daily_fp, days)
    erosion = compute_margin_erosion(vehicle.list_price, total_cost, daily_fp, days)

    # 7) Pricing
    pricing = recommend_pricing(
        vehicle.list_price, total_cost, median_price, days,
        probs["p30"], demand_score, supply_count,
        vehicle.min_acceptable_margin or 500, daily_fp,
    )

    # 8) Elasticity
    elast = compute_price_elasticity(median_price, vehicle.list_price, demand_score, supply_count)

    # 9) Exit path
    exit_rec = recommend_exit_path(
        vehicle.list_price, total_cost, vehicle.wholesale_exit_price or 0,
        daily_fp, days, probs["p30"], probs["p60"], lam, median_price,
    )

    # 10) Action plan
    actions = generate_action_plan(
        days, aging_class, pricing["price_action"], pricing["price_change_amount"],
        exit_rec["optimal_exit"], probs["p30"], v7, l7,
        vehicle.list_price, median_price,
    )

    # 11) Risk
    risk = assess_risk_and_confidence(
        days, comp_count, demand_score, probs["p30"], aging_class, pricing["price_action"],
    )

    return {
        **probs,
        "aging_class": aging_class,
        "inflection_day": inflection,
        **carry,
        **erosion,
        **pricing,
        "price_elasticity": elast["elasticity"],
        "elasticity_reason": elast["reason"],
        **exit_rec,
        "action_plan": actions,
        **risk,
        "daily_curve": curve,
    }


# ---------------------------------------------------------------------------
# 11) COMP SUMMARY BUILDER
# ---------------------------------------------------------------------------
def build_comp_summary(
    auto_comps: List[Any],
    manual_comps: List[Any],
) -> Dict[str, Any]:
    """
    Takes lists of Comp ORM objects, builds summary stats.
    Handles discrepancy detection between auto and manual sources.
    """
    all_comps = auto_comps + manual_comps

    if not all_comps:
        return {
            "auto_count": 0, "manual_count": 0,
            "median_price": None, "mean_price": None,
            "low_price": None, "high_price": None,
            "median_days_to_sale": None,
            "supply_count": 0, "demand_score": 50,
            "supply_vs_demand": "unknown",
            "discrepancy_flag": False, "discrepancy_note": None,
            "weighted_source": None, "weight_reason": None,
        }

    # Prices
    auto_prices = [c.price for c in auto_comps if c.price]
    manual_prices = [c.price for c in manual_comps if c.price]
    all_prices = [c.price for c in all_comps if c.price]

    # Days on market
    all_dom = [c.days_on_market for c in all_comps if c.days_on_market is not None]

    median_price = statistics.median(all_prices) if all_prices else None
    mean_price = statistics.mean(all_prices) if all_prices else None
    low_price = min(all_prices) if all_prices else None
    high_price = max(all_prices) if all_prices else None
    median_dom = statistics.median(all_dom) if all_dom else None

    # Supply vs demand heuristic
    supply_count = len(all_comps)
    sold_count = len([c for c in all_comps if c.listing_status == "sold"])
    if supply_count > 0:
        sold_ratio = sold_count / supply_count
    else:
        sold_ratio = 0

    if sold_ratio > 0.5 and supply_count < 15:
        demand_score = 75
        svd = "undersupplied"
    elif sold_ratio < 0.2 or supply_count > 25:
        demand_score = 25
        svd = "oversupplied"
    else:
        demand_score = 50
        svd = "balanced"

    # Discrepancy detection
    discrepancy_flag = False
    discrepancy_note = None
    weighted_source = None
    weight_reason = None

    if auto_prices and manual_prices:
        auto_median = statistics.median(auto_prices)
        manual_median = statistics.median(manual_prices)
        diff_pct = abs(auto_median - manual_median) / auto_median * 100 if auto_median else 0

        if diff_pct > 8:
            discrepancy_flag = True
            discrepancy_note = (
                f"Auto comps median ${auto_median:,.0f} vs manual comps median ${manual_median:,.0f} "
                f"({diff_pct:.1f}% difference)."
            )
            # Weight decision
            if len(auto_comps) >= 8:
                weighted_source = "auto"
                weight_reason = (
                    f"Auto data weighted more: {len(auto_comps)} comps vs {len(manual_comps)} manual. "
                    f"Larger sample with broader market coverage."
                )
            elif len(manual_comps) >= 5 and len(auto_comps) < 5:
                weighted_source = "manual"
                weight_reason = (
                    f"Manual data weighted more: {len(manual_comps)} dealer-sourced comps "
                    f"vs only {len(auto_comps)} auto comps. Local knowledge prioritized."
                )
            else:
                weighted_source = "auto"
                weight_reason = "Default to automated comps for consistency. Verify manual comps are current."

    return {
        "auto_count": len(auto_comps),
        "manual_count": len(manual_comps),
        "median_price": round(median_price, 2) if median_price else None,
        "mean_price": round(mean_price, 2) if mean_price else None,
        "low_price": round(low_price, 2) if low_price else None,
        "high_price": round(high_price, 2) if high_price else None,
        "median_days_to_sale": round(median_dom, 1) if median_dom else None,
        "supply_count": supply_count,
        "demand_score": demand_score,
        "supply_vs_demand": svd,
        "discrepancy_flag": discrepancy_flag,
        "discrepancy_note": discrepancy_note,
        "weighted_source": weighted_source,
        "weight_reason": weight_reason,
    }


# ---------------------------------------------------------------------------
# 12) WATERFALL PLAN GENERATOR
# ---------------------------------------------------------------------------
def generate_waterfall_plan(
    vehicle: Any,
    rules: List[Dict],
    price_floor_policy: str = "total_cost",
) -> Dict[str, Any]:
    """
    Given waterfall rules and vehicle data, produce step-by-step plan.
    """
    total_cost = (vehicle.acquisition_cost or 0) + (vehicle.recon_cost or 0)
    daily_fp = total_cost * ((vehicle.floorplan_rate_apr or DEFAULT_FLOORPLAN_APR) / 100) / 365
    current_price = vehicle.list_price
    wholesale = vehicle.wholesale_exit_price or 0

    if price_floor_policy == "wholesale":
        floor = wholesale
    else:
        floor = total_cost

    steps = []
    running_price = current_price

    for i, rule in enumerate(sorted(rules, key=lambda r: r.get("trigger_day", 0))):
        trigger_day = rule.get("trigger_day", 30)
        reduction_pct = rule.get("reduction_pct", 5)
        margin_floor = rule.get("min_margin_floor", 0)

        reduction_amount = round(current_price * (reduction_pct / 100), 0)
        new_price = running_price - reduction_amount

        # Enforce floors
        effective_floor = max(floor, total_cost + margin_floor)
        if new_price < effective_floor:
            new_price = effective_floor
            reduction_amount = running_price - new_price

        if reduction_amount <= 0:
            continue

        # Estimate probability lift
        lift = clamp(reduction_amount * PRICE_SENSITIVITY * 0.4, 0.01, 0.20)
        days_saved = round(lift * 25, 1)

        # Stop condition
        future_carry = daily_fp * trigger_day
        net_at_new_price = new_price - total_cost - future_carry
        stop = "Wholesale exit superior" if net_at_new_price < (wholesale - total_cost) else "Continue retail"

        steps.append({
            "step": i + 1,
            "trigger_day": trigger_day,
            "trigger_condition": f"Day {trigger_day} in inventory reached",
            "current_price": round(running_price, 2),
            "new_price": round(new_price, 2),
            "dollar_change": round(-reduction_amount, 2),
            "expected_probability_lift": round(lift, 4),
            "expected_days_saved": days_saved,
            "price_floor": round(effective_floor, 2),
            "stop_condition": stop,
        })

        running_price = new_price

    recommendation = (
        f"Plan has {len(steps)} price steps from ${current_price:,.0f} "
        f"down to ${running_price:,.0f}. Floor: ${floor:,.0f}."
    )

    return {
        "vehicle_id": vehicle.id,
        "current_price": current_price,
        "total_cost": total_cost,
        "wholesale_exit_price": wholesale,
        "steps": steps,
        "recommendation": recommendation,
    }


# ---------------------------------------------------------------------------
# 13) ALARM GENERATOR
# ---------------------------------------------------------------------------
def generate_alarm(
    vehicles: List[Any],
    thresholds: List[int],
    dealership_id: int,
) -> Dict[str, Any]:
    """
    Takes all active vehicles, produces daily alarm payload.
    """
    if not thresholds:
        thresholds = [30, 45, 60, 75]

    thresholds = sorted(thresholds)
    total_burn = 0
    burner_list = []
    threshold_crossings = {str(t): [] for t in thresholds}
    underwater = []

    for v in vehicles:
        tc = (v.acquisition_cost or 0) + (v.recon_cost or 0)
        daily = tc * ((v.floorplan_rate_apr or DEFAULT_FLOORPLAN_APR) / 100) / 365
        days = v.days_in_inventory or 0
        total_carry = daily * days
        net_gross = (v.list_price or 0) - tc - total_carry

        total_burn += daily

        burner_list.append({
            "vehicle_id": v.id,
            "vin": v.vin,
            "year": v.year,
            "make": v.make,
            "model": v.model,
            "daily_cost": round(daily, 2),
            "days": days,
            "total_carry": round(total_carry, 2),
            "net_gross": round(net_gross, 2),
        })

        # Threshold crossings (newly crossing = days equals threshold)
        for t in thresholds:
            if days == t or (days > t and days <= t + 1):
                threshold_crossings[str(t)].append({
                    "vehicle_id": v.id,
                    "vin": v.vin,
                    "days": days,
                })
            elif days > t:
                # Currently beyond — we track separately in the payload
                pass

        if net_gross < 0:
            underwater.append({
                "vehicle_id": v.id,
                "vin": v.vin,
                "year": v.year,
                "make": v.make,
                "model": v.model,
                "net_gross": round(net_gross, 2),
                "days": days,
            })

    # Sort burners
    burner_list.sort(key=lambda x: x["daily_cost"], reverse=True)
    top_3 = burner_list[:3]

    # Projections
    projected_30 = round(total_burn * 30, 2)
    projected_60 = round(total_burn * 60, 2)

    # Executive summary
    total_units = len(vehicles)
    uw_count = len(underwater)
    summary_parts = [
        f"{total_units} active units. Total daily floorplan burn: ${total_burn:,.2f}.",
        f"Projected 30-day burn: ${projected_30:,.0f}. 60-day burn: ${projected_60:,.0f}.",
    ]
    if uw_count > 0:
        summary_parts.append(f"⚠ {uw_count} vehicle(s) are underwater (negative net gross after carry).")
    if top_3:
        summary_parts.append(
            f"Top burner: {top_3[0]['year']} {top_3[0]['make']} {top_3[0]['model']} "
            f"(${top_3[0]['daily_cost']}/day, {top_3[0]['days']} days)."
        )

    for t in thresholds:
        crossings = threshold_crossings[str(t)]
        if crossings:
            summary_parts.append(f"{len(crossings)} vehicle(s) just crossed the {t}-day threshold.")

    return {
        "dealership_id": dealership_id,
        "total_active_units": total_units,
        "total_daily_burn": round(total_burn, 2),
        "projected_burn_30": projected_30,
        "projected_burn_60": projected_60,
        "top_burners": top_3,
        "threshold_crossings": threshold_crossings,
        "underwater_vehicles": underwater,
        "executive_summary": " ".join(summary_parts),
    }
