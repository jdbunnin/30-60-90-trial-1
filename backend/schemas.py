# backend/schemas.py — All Pydantic Schemas (Part 1 of 2)

from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import date, datetime
from enum import Enum


# ---------------------------------------------------------------------------
# ENUMS (mirror SQLAlchemy enums for Pydantic)
# ---------------------------------------------------------------------------
class VehicleStatusEnum(str, Enum):
    active = "active"
    sold = "sold"
    wholesale = "wholesale"
    traded = "traded"


class AgingClassEnum(str, Enum):
    healthy = "healthy"
    at_risk = "at_risk"
    danger = "danger"


class CompSourceEnum(str, Enum):
    auto = "auto"
    manual = "manual"


class ExitPathEnum(str, Enum):
    retail = "retail"
    wholesale_auction = "wholesale_auction"
    dealer_trade = "dealer_trade"


class PriceActionEnum(str, Enum):
    hold = "hold"
    reduce = "reduce"
    increase = "increase"


class ElasticityEnum(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class ConfidenceEnum(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


# ---------------------------------------------------------------------------
# DEALERSHIP
# ---------------------------------------------------------------------------
class DealershipCreate(BaseModel):
    name: str
    timezone: str = "America/Chicago"


class DealershipOut(BaseModel):
    id: int
    name: str
    timezone: str
    created_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# USER
# ---------------------------------------------------------------------------
class UserCreate(BaseModel):
    email: str
    name: str
    role: str = "manager"


class UserOut(BaseModel):
    id: int
    dealership_id: int
    email: str
    name: str
    role: str

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# VEHICLE
# ---------------------------------------------------------------------------
class VinAddRequest(BaseModel):
    vin: str = Field(..., min_length=17, max_length=17)
    # Optional overrides at creation time
    acquisition_cost: Optional[float] = None
    recon_cost: Optional[float] = None
    list_price: Optional[float] = None
    floorplan_rate_apr: Optional[float] = None
    wholesale_exit_price: Optional[float] = None
    min_acceptable_margin: Optional[float] = None
    mileage: Optional[int] = None
    date_acquired: Optional[date] = None


class VehicleUpdate(BaseModel):
    year: Optional[int] = None
    make: Optional[str] = None
    model: Optional[str] = None
    trim: Optional[str] = None
    body_style: Optional[str] = None
    engine: Optional[str] = None
    acquisition_cost: Optional[float] = None
    recon_cost: Optional[float] = None
    list_price: Optional[float] = None
    floorplan_rate_apr: Optional[float] = None
    wholesale_exit_price: Optional[float] = None
    min_acceptable_margin: Optional[float] = None
    mileage: Optional[int] = None
    status: Optional[VehicleStatusEnum] = None
    date_sold: Optional[date] = None
    sold_price: Optional[float] = None


class VehicleOut(BaseModel):
    id: int
    dealership_id: int
    vin: str
    status: VehicleStatusEnum
    year: Optional[int]
    make: Optional[str]
    model: Optional[str]
    trim: Optional[str]
    body_style: Optional[str]
    engine: Optional[str]
    acquisition_cost: float
    recon_cost: float
    list_price: float
    floorplan_rate_apr: float
    wholesale_exit_price: float
    min_acceptable_margin: float
    mileage: int
    date_acquired: Optional[date]
    days_in_inventory: int
    date_sold: Optional[date]
    sold_price: Optional[float]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# VEHICLE SIGNALS
# ---------------------------------------------------------------------------
class SignalsUpdate(BaseModel):
    views_total: Optional[int] = None
    views_last_7: Optional[int] = None
    leads_total: Optional[int] = None
    leads_last_7: Optional[int] = None
    test_drives: Optional[int] = None
    notes: Optional[str] = None


class SignalsOut(BaseModel):
    id: int
    vehicle_id: int
    views_total: int
    views_last_7: int
    leads_total: int
    leads_last_7: int
    test_drives: int
    notes: str
    updated_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# COMPS
# ---------------------------------------------------------------------------
class CompManualAdd(BaseModel):
    year: Optional[int] = None
    make: Optional[str] = None
    model: Optional[str] = None
    trim: Optional[str] = None
    mileage: Optional[int] = None
    price: Optional[float] = None
    sold_price: Optional[float] = None
    days_on_market: Optional[int] = None
    distance_miles: Optional[float] = None
    dealer_name: Optional[str] = None
    listing_status: str = "active"


class CompOut(BaseModel):
    id: int
    vehicle_id: int
    source: CompSourceEnum
    vin: Optional[str]
    year: Optional[int]
    make: Optional[str]
    model: Optional[str]
    trim: Optional[str]
    mileage: Optional[int]
    price: Optional[float]
    sold_price: Optional[float]
    days_on_market: Optional[int]
    distance_miles: Optional[float]
    dealer_name: Optional[str]
    listing_status: str
    found_at: datetime

    class Config:
        from_attributes = True


class CompSummaryOut(BaseModel):
    id: int
    vehicle_id: int
    auto_count: int
    manual_count: int
    median_price: Optional[float]
    mean_price: Optional[float]
    low_price: Optional[float]
    high_price: Optional[float]
    median_days_to_sale: Optional[float]
    supply_count: int
    demand_score: float
    supply_vs_demand: Optional[str]
    discrepancy_flag: bool
    discrepancy_note: Optional[str]
    weighted_source: Optional[str]
    weight_reason: Optional[str]
    computed_at: datetime

    class Config:
        from_attributes = True
      # ---------------------------------------------------------------------------
# ANALYSIS — Daily Curve Point
# ---------------------------------------------------------------------------
class DailyCurvePoint(BaseModel):
    day: int
    daily_sell_probability: float
    cumulative_sell_probability: float
    floorplan_cost_to_date: float
    gross_erosion_to_date: float


# ---------------------------------------------------------------------------
# ANALYSIS — Full Report
# ---------------------------------------------------------------------------
class AnalysisReportOut(BaseModel):
    id: int
    vehicle_id: int

    # Probabilities
    p30: float
    p60: float
    p90: float

    # Aging
    aging_class: AgingClassEnum
    daily_carry_cost: float
    carry_cost_30: float
    carry_cost_60: float
    carry_cost_90: float
    margin_erosion_30: float
    margin_erosion_60: float
    margin_erosion_90: float
    inflection_day: int

    # Pricing strategy
    price_action: PriceActionEnum
    price_change_amount: float
    price_action_lift_p: float
    price_action_gross_impact: float
    price_elasticity: ElasticityEnum
    elasticity_reason: str

    # Exit path
    optimal_exit: ExitPathEnum
    exit_expected_gross: float
    exit_expected_days: float
    exit_reason: str

    # Actions + Risk
    action_plan: List[str]
    risks: List[str]
    change_triggers: List[str]
    confidence: ConfidenceEnum

    # Curve
    daily_curve: List[DailyCurvePoint]

    computed_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# ANALYSIS — Lightweight Insight (list view)
# ---------------------------------------------------------------------------
class VehicleInsight(BaseModel):
    vehicle_id: int
    vin: str
    year: Optional[int]
    make: Optional[str]
    model: Optional[str]
    trim: Optional[str]
    status: VehicleStatusEnum
    days_in_inventory: int
    list_price: float
    acquisition_cost: float
    recon_cost: float

    p30: Optional[float] = None
    p60: Optional[float] = None
    p90: Optional[float] = None
    aging_class: Optional[AgingClassEnum] = None
    daily_carry_cost: Optional[float] = None
    inflection_day: Optional[int] = None
    price_action: Optional[PriceActionEnum] = None
    one_line_action: Optional[str] = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# FLOORPLAN ALARM
# ---------------------------------------------------------------------------
class AlarmOut(BaseModel):
    id: int
    dealership_id: int
    alarm_date: date
    total_active_units: int
    total_daily_burn: float
    projected_burn_30: float
    projected_burn_60: float
    top_burners: List[Any]
    threshold_crossings: Any
    underwater_vehicles: List[Any]
    executive_summary: str
    created_at: datetime

    class Config:
        from_attributes = True


class AlarmConfigUpdate(BaseModel):
    thresholds: Optional[List[int]] = None
    enabled: Optional[bool] = None
    email_targets: Optional[List[str]] = None
    alarm_hour: Optional[int] = None


class AlarmConfigOut(BaseModel):
    id: int
    dealership_id: int
    thresholds: List[int]
    enabled: bool
    email_targets: List[str]
    alarm_hour: int

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# PRICING WATERFALL
# ---------------------------------------------------------------------------
class WaterfallRule(BaseModel):
    trigger_day: int
    reduction_pct: float
    min_margin_floor: float


class WaterfallSettingsUpdate(BaseModel):
    rules: Optional[List[WaterfallRule]] = None
    price_floor_policy: Optional[str] = None
    auto_mode: Optional[bool] = None


class WaterfallSettingsOut(BaseModel):
    id: int
    dealership_id: int
    rules: List[Any]
    price_floor_policy: str
    auto_mode: bool
    updated_at: datetime

    class Config:
        from_attributes = True


class WaterfallStepOut(BaseModel):
    step: int
    trigger_day: int
    trigger_condition: str
    current_price: float
    new_price: float
    dollar_change: float
    expected_probability_lift: float
    expected_days_saved: float
    price_floor: float
    stop_condition: str


class WaterfallPlanOut(BaseModel):
    vehicle_id: int
    current_price: float
    total_cost: float
    wholesale_exit_price: float
    steps: List[WaterfallStepOut]
    recommendation: str


# ---------------------------------------------------------------------------
# PRICE EVENT LOG
# ---------------------------------------------------------------------------
class PriceEventOut(BaseModel):
    id: int
    vehicle_id: int
    dealership_id: int
    event_type: str
    old_price: float
    new_price: float
    reason: str
    triggered_by: str
    created_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# GENERIC RESPONSES
# ---------------------------------------------------------------------------
class MessageResponse(BaseModel):
    message: str
    detail: Optional[Any] = None
