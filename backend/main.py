# backend/main.py — FastAPI App + All Routes (Part 1 of 3)

import httpx
import csv
import io
from datetime import date, datetime
from typing import Optional, List

from fastapi import FastAPI, Depends, HTTPException, Header, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from models import (
    init_db, get_db, ALLOWED_ORIGINS, NHTSA_API_URL,
    Dealership, User, Vehicle, VehicleSignals, Comp, CompSummary,
    AnalysisReport, FloorplanAlarm, AlarmConfig, PricingWaterfallSettings,
    PriceEventLog, VehicleStatus, CompSource,
)
from schemas import (
    DealershipCreate, DealershipOut, UserCreate, UserOut,
    VinAddRequest, VehicleUpdate, VehicleOut,
    SignalsUpdate, SignalsOut,
    CompManualAdd, CompOut, CompSummaryOut, CompSourceEnum,
    AnalysisReportOut, VehicleInsight,
    AlarmOut, AlarmConfigUpdate, AlarmConfigOut,
    WaterfallSettingsUpdate, WaterfallSettingsOut,
    WaterfallPlanOut, WaterfallStepOut,
    PriceEventOut, MessageResponse,
)
import engine

# ---------------------------------------------------------------------------
# APP INIT
# ---------------------------------------------------------------------------
app = FastAPI(title="30-60-90 Inventory Intelligence", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()
    # Seed a default dealership for dev convenience
    from models import SessionLocal
    db = SessionLocal()
    if not db.query(Dealership).first():
        demo = Dealership(name="Demo Dealership", timezone="America/Chicago")
        db.add(demo)
        db.commit()
        db.refresh(demo)
        # Default alarm config
        db.add(AlarmConfig(dealership_id=demo.id, thresholds=[30, 45, 60, 75]))
        # Default waterfall settings
        db.add(PricingWaterfallSettings(
            dealership_id=demo.id,
            rules=[
                {"trigger_day": 15, "reduction_pct": 3, "min_margin_floor": 1500},
                {"trigger_day": 30, "reduction_pct": 5, "min_margin_floor": 1000},
                {"trigger_day": 45, "reduction_pct": 8, "min_margin_floor": 500},
                {"trigger_day": 60, "reduction_pct": 12, "min_margin_floor": 0},
            ],
            price_floor_policy="total_cost",
        ))
        db.commit()
    db.close()


# ---------------------------------------------------------------------------
# HELPER: Get dealership_id from header
# ---------------------------------------------------------------------------
def get_dealership_id(x_dealership_id: int = Header(default=1)) -> int:
    return x_dealership_id


# ---------------------------------------------------------------------------
# HEALTH
# ---------------------------------------------------------------------------
@app.get("/api/vehicles/{vehicle_id}", response_model=VehicleOut)
def health():
    return {"status": "ok", "app": "30-60-90", "version": "1.0.0"}


# ---------------------------------------------------------------------------
# DEALERSHIP ROUTES
# ---------------------------------------------------------------------------
@app.post("/api/dealerships", response_model=DealershipOut)
def create_dealership(payload: DealershipCreate, db: Session = Depends(get_db)):
    d = Dealership(name=payload.name, timezone=payload.timezone)
    db.add(d)
    db.commit()
    db.refresh(d)
    # Create default configs
    db.add(AlarmConfig(dealership_id=d.id, thresholds=[30, 45, 60, 75]))
    db.add(PricingWaterfallSettings(
        dealership_id=d.id,
        rules=[
            {"trigger_day": 15, "reduction_pct": 3, "min_margin_floor": 1500},
            {"trigger_day": 30, "reduction_pct": 5, "min_margin_floor": 1000},
            {"trigger_day": 45, "reduction_pct": 8, "min_margin_floor": 500},
            {"trigger_day": 60, "reduction_pct": 12, "min_margin_floor": 0},
        ],
    ))
    db.commit()
    return d


@app.get("/api/dealerships", response_model=List[DealershipOut])
def list_dealerships(db: Session = Depends(get_db)):
    return db.query(Dealership).all()


# ---------------------------------------------------------------------------
# USER ROUTES
# ---------------------------------------------------------------------------
@app.post("/api/users", response_model=UserOut)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    dealership_id: int = Depends(get_dealership_id),
):
    u = User(dealership_id=dealership_id, email=payload.email, name=payload.name, role=payload.role)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


# ---------------------------------------------------------------------------
# VIN DECODE HELPER
# ---------------------------------------------------------------------------
async def decode_vin(vin: str) -> dict:
    """Call NHTSA vPIC API to decode VIN."""
    url = f"{NHTSA_API_URL}/DecodeVinValues/{vin}?format=json"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            results = data.get("Results", [{}])[0]
            return {
                "year": int(results.get("ModelYear") or 0) or None,
                "make": results.get("Make") or None,
                "model": results.get("Model") or None,
                "trim": results.get("Trim") or None,
                "body_style": results.get("BodyClass") or None,
                "engine": " ".join(filter(None, [
                    results.get("EngineConfiguration"),
                    results.get("DisplacementL"),
                    results.get("FuelTypePrimary"),
                ])) or None,
            }
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# VEHICLE ROUTES
# ---------------------------------------------------------------------------
@app.post("/api/vehicles/from-vin", response_model=VehicleOut)
async def add_vehicle_from_vin(
    payload: VinAddRequest,
    db: Session = Depends(get_db),
    dealership_id: int = Depends(get_dealership_id),
):
    # Check for duplicate VIN at this dealership
    existing = db.query(Vehicle).filter(
        Vehicle.dealership_id == dealership_id,
        Vehicle.vin == payload.vin.upper(),
        Vehicle.status == VehicleStatus.active,
    ).first()
    if existing:
        raise HTTPException(400, f"Active vehicle with VIN {payload.vin} already exists (id={existing.id}).")

    # Decode VIN
    decoded = await decode_vin(payload.vin.upper())

    v = Vehicle(
        dealership_id=dealership_id,
        vin=payload.vin.upper(),
        year=decoded.get("year"),
        make=decoded.get("make"),
        model=decoded.get("model"),
        trim=decoded.get("trim"),
        body_style=decoded.get("body_style"),
        engine=decoded.get("engine"),
        acquisition_cost=payload.acquisition_cost or 0,
        recon_cost=payload.recon_cost or 0,
        list_price=payload.list_price or 0,
        floorplan_rate_apr=payload.floorplan_rate_apr or 6.5,
        wholesale_exit_price=payload.wholesale_exit_price or 0,
        min_acceptable_margin=payload.min_acceptable_margin or 500,
        mileage=payload.mileage or 0,
        date_acquired=payload.date_acquired or date.today(),
        days_in_inventory=0,
    )

    # Calculate days if date_acquired provided
    if payload.date_acquired:
        v.days_in_inventory = (date.today() - payload.date_acquired).days

    db.add(v)
    db.commit()
    db.refresh(v)

    # Create empty signals record
    db.add(VehicleSignals(vehicle_id=v.id))
    db.commit()

    return v


@app.get("/api/vehicles", response_model=List[VehicleOut])
def list_vehicles(
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    dealership_id: int = Depends(get_dealership_id),
):
    q = db.query(Vehicle).filter(Vehicle.dealership_id == dealership_id)
    if status:
        q = q.filter(Vehicle.status == status)
    vehicles = q.order_by(Vehicle.days_in_inventory.desc()).all()

    # Refresh days_in_inventory
    for v in vehicles:
        if v.date_acquired and v.status == VehicleStatus.active:
            v.days_in_inventory = (date.today() - v.date_acquired).days
    db.commit()

    return vehicles


@app.get("/api/vehicles/{vehicle_id}", response_model=VehicleOut)
def get_vehicle(
    vehicle_id: int,
    db: Session = Depends(get_db),
    dealership_id: int = Depends(get_dealership_id),
):
    v = db.query(Vehicle).filter(
        Vehicle.id == vehicle_id,
        Vehicle.dealership_id == dealership_id,
    ).first()
    if not v:
        raise HTTPException(404, "Vehicle not found.")

    if v.date_acquired and v.status == VehicleStatus.active:
        v.days_in_inventory = (date.today() - v.date_acquired).days
        db.commit()

    return v


@app.put("/api/vehicles/{vehicle_id}", response_model=VehicleOut)
def update_vehicle(
    vehicle_id: int,
    payload: VehicleUpdate,
    db: Session = Depends(get_db),
    dealership_id: int = Depends(get_dealership_id),
):
    v = db.query(Vehicle).filter(
        Vehicle.id == vehicle_id,
        Vehicle.dealership_id == dealership_id,
    ).first()
    if not v:
        raise HTTPException(404, "Vehicle not found.")

    old_price = v.list_price
    old_status = v.status

    update_data = payload.dict(exclude_unset=True)
    for key, val in update_data.items():
        setattr(v, key, val)

    v.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(v)

    # Log price changes
    if payload.list_price is not None and payload.list_price != old_price:
        db.add(PriceEventLog(
            vehicle_id=v.id,
            dealership_id=dealership_id,
            event_type="manual_override",
            old_price=old_price,
            new_price=payload.list_price,
            reason="Manual price update by dealer.",
            triggered_by="user",
        ))
        db.commit()

    # Log status changes
    if payload.status is not None and payload.status != old_status:
        db.add(PriceEventLog(
            vehicle_id=v.id,
            dealership_id=dealership_id,
            event_type="status_change",
            old_price=old_price,
            new_price=v.list_price,
            reason=f"Status changed from {old_status} to {payload.status}.",
            triggered_by="user",
        ))
        db.commit()

    return v


# ---------------------------------------------------------------------------
# SIGNALS ROUTES
# ---------------------------------------------------------------------------
@app.put("/api/vehicles/{vehicle_id}/signals", response_model=SignalsOut)
def update_signals(
    vehicle_id: int,
    payload: SignalsUpdate,
    db: Session = Depends(get_db),
    dealership_id: int = Depends(get_dealership_id),
):
    v = db.query(Vehicle).filter(Vehicle.id == vehicle_id, Vehicle.dealership_id == dealership_id).first()
    if not v:
        raise HTTPException(404, "Vehicle not found.")

    sig = db.query(VehicleSignals).filter(VehicleSignals.vehicle_id == vehicle_id).first()
    if not sig:
        sig = VehicleSignals(vehicle_id=vehicle_id)
        db.add(sig)
        db.commit()
        db.refresh(sig)

    update_data = payload.dict(exclude_unset=True)
    for key, val in update_data.items():
        setattr(sig, key, val)

    sig.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(sig)
    return sig


@app.get("/api/vehicles/{vehicle_id}/signals", response_model=SignalsOut)
def get_signals(
    vehicle_id: int,
    db: Session = Depends(get_db),
    dealership_id: int = Depends(get_dealership_id),
):
    sig = db.query(VehicleSignals).filter(VehicleSignals.vehicle_id == vehicle_id).first()
    if not sig:
        raise HTTPException(404, "No signals found.")
    return sig
  # ---------------------------------------------------------------------------
# COMPS ROUTES
# ---------------------------------------------------------------------------

def _get_vehicle_or_404(vehicle_id: int, dealership_id: int, db: Session) -> Vehicle:
    v = db.query(Vehicle).filter(
        Vehicle.id == vehicle_id,
        Vehicle.dealership_id == dealership_id,
    ).first()
    if not v:
        raise HTTPException(404, "Vehicle not found.")
    return v


def _generate_mock_comps(vehicle: Vehicle) -> List[dict]:
    """
    Mock comp generator — produces realistic synthetic comps.
    PLUGGABLE: Replace this with Marketcheck, CarGurus, Manheim API calls.
    """
    import random
    random.seed(hash(vehicle.vin))

    base_price = vehicle.list_price if vehicle.list_price else 25000
    base_mileage = vehicle.mileage if vehicle.mileage else 40000
    comps = []

    for i in range(random.randint(8, 18)):
        price_variance = random.uniform(-0.12, 0.08)
        mileage_variance = random.randint(-15000, 20000)
        dom = random.randint(5, 75)
        is_sold = random.random() < 0.4

        comp_price = round(base_price * (1 + price_variance), 0)
        comp_mileage = max(1000, base_mileage + mileage_variance)

        comps.append({
            "year": vehicle.year or 2022,
            "make": vehicle.make or "Unknown",
            "model": vehicle.model or "Unknown",
            "trim": vehicle.trim,
            "mileage": comp_mileage,
            "price": comp_price,
            "sold_price": round(comp_price * random.uniform(0.94, 1.0), 0) if is_sold else None,
            "days_on_market": dom,
            "distance_miles": round(random.uniform(5, 150), 1),
            "dealer_name": f"Dealer #{random.randint(100, 999)}",
            "listing_status": "sold" if is_sold else random.choice(["active", "active", "delisted"]),
        })

    return comps


@app.post("/api/vehicles/{vehicle_id}/comps/refresh", response_model=MessageResponse)
def refresh_comps(
    vehicle_id: int,
    db: Session = Depends(get_db),
    dealership_id: int = Depends(get_dealership_id),
):
    """
    Fetch automated comps. Currently uses mock generator.
    Replace _generate_mock_comps() with real API calls.
    """
    v = _get_vehicle_or_404(vehicle_id, dealership_id, db)

    # Remove old auto comps
    db.query(Comp).filter(
        Comp.vehicle_id == vehicle_id,
        Comp.source == CompSource.auto,
    ).delete()
    db.commit()

    # Generate new comps
    mock_comps = _generate_mock_comps(v)
    for c in mock_comps:
        db.add(Comp(
            vehicle_id=vehicle_id,
            source=CompSource.auto,
            year=c["year"],
            make=c["make"],
            model=c["model"],
            trim=c.get("trim"),
            mileage=c["mileage"],
            price=c["price"],
            sold_price=c.get("sold_price"),
            days_on_market=c.get("days_on_market"),
            distance_miles=c.get("distance_miles"),
            dealer_name=c.get("dealer_name"),
            listing_status=c.get("listing_status", "active"),
        ))
    db.commit()

    # Rebuild summary
    _rebuild_comp_summary(vehicle_id, db)

    return MessageResponse(message=f"Refreshed {len(mock_comps)} automated comps.", detail={"count": len(mock_comps)})


@app.post("/api/vehicles/{vehicle_id}/comps/manual", response_model=CompOut)
def add_manual_comp(
    vehicle_id: int,
    payload: CompManualAdd,
    db: Session = Depends(get_db),
    dealership_id: int = Depends(get_dealership_id),
):
    _get_vehicle_or_404(vehicle_id, dealership_id, db)

    c = Comp(
        vehicle_id=vehicle_id,
        source=CompSource.manual,
        year=payload.year,
        make=payload.make,
        model=payload.model,
        trim=payload.trim,
        mileage=payload.mileage,
        price=payload.price,
        sold_price=payload.sold_price,
        days_on_market=payload.days_on_market,
        distance_miles=payload.distance_miles,
        dealer_name=payload.dealer_name,
        listing_status=payload.listing_status,
    )
    db.add(c)
    db.commit()
    db.refresh(c)

    _rebuild_comp_summary(vehicle_id, db)

    return c


@app.post("/api/vehicles/{vehicle_id}/comps/upload", response_model=MessageResponse)
async def upload_comps(
    vehicle_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    dealership_id: int = Depends(get_dealership_id),
):
    """
    Upload CSV with columns: year,make,model,trim,mileage,price,sold_price,days_on_market,distance_miles,dealer_name,listing_status
    """
    _get_vehicle_or_404(vehicle_id, dealership_id, db)

    content = await file.read()
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))

    count = 0
    for row in reader:
        try:
            c = Comp(
                vehicle_id=vehicle_id,
                source=CompSource.manual,
                year=int(row.get("year", 0)) or None,
                make=row.get("make"),
                model=row.get("model"),
                trim=row.get("trim"),
                mileage=int(row.get("mileage", 0)) if row.get("mileage") else None,
                price=float(row.get("price", 0)) if row.get("price") else None,
                sold_price=float(row.get("sold_price", 0)) if row.get("sold_price") else None,
                days_on_market=int(row.get("days_on_market", 0)) if row.get("days_on_market") else None,
                distance_miles=float(row.get("distance_miles", 0)) if row.get("distance_miles") else None,
                dealer_name=row.get("dealer_name"),
                listing_status=row.get("listing_status", "active"),
            )
            db.add(c)
            count += 1
        except (ValueError, KeyError):
            continue

    db.commit()
    _rebuild_comp_summary(vehicle_id, db)

    return MessageResponse(message=f"Uploaded {count} manual comps from CSV.", detail={"count": count})


@app.get("/api/vehicles/{vehicle_id}/comps", response_model=List[CompOut])
def list_comps(
    vehicle_id: int,
    source: Optional[str] = Query(None, description="auto|manual|all"),
    db: Session = Depends(get_db),
    dealership_id: int = Depends(get_dealership_id),
):
    _get_vehicle_or_404(vehicle_id, dealership_id, db)

    q = db.query(Comp).filter(Comp.vehicle_id == vehicle_id)
    if source == "auto":
        q = q.filter(Comp.source == CompSource.auto)
    elif source == "manual":
        q = q.filter(Comp.source == CompSource.manual)

    return q.order_by(Comp.found_at.desc()).all()


@app.get("/api/vehicles/{vehicle_id}/comps/summary", response_model=CompSummaryOut)
def get_comp_summary(
    vehicle_id: int,
    db: Session = Depends(get_db),
    dealership_id: int = Depends(get_dealership_id),
):
    _get_vehicle_or_404(vehicle_id, dealership_id, db)

    summary = db.query(CompSummary).filter(CompSummary.vehicle_id == vehicle_id).first()
    if not summary:
        raise HTTPException(404, "No comp summary. Run comp refresh first.")
    return summary


def _rebuild_comp_summary(vehicle_id: int, db: Session):
    """Rebuild the CompSummary for a vehicle using engine."""
    auto_comps = db.query(Comp).filter(
        Comp.vehicle_id == vehicle_id,
        Comp.source == CompSource.auto,
    ).all()
    manual_comps = db.query(Comp).filter(
        Comp.vehicle_id == vehicle_id,
        Comp.source == CompSource.manual,
    ).all()

    summary_data = engine.build_comp_summary(auto_comps, manual_comps)

    existing = db.query(CompSummary).filter(CompSummary.vehicle_id == vehicle_id).first()
    if existing:
        for key, val in summary_data.items():
            setattr(existing, key, val)
        existing.computed_at = datetime.utcnow()
    else:
        existing = CompSummary(vehicle_id=vehicle_id, **summary_data)
        db.add(existing)

    db.commit()


# ---------------------------------------------------------------------------
# ANALYSIS ROUTES
# ---------------------------------------------------------------------------

@app.post("/api/vehicles/{vehicle_id}/analyze", response_model=AnalysisReportOut)
def analyze_vehicle(
    vehicle_id: int,
    db: Session = Depends(get_db),
    dealership_id: int = Depends(get_dealership_id),
):
    """Full analysis — returns complete report including 90-day curve."""
    v = _get_vehicle_or_404(vehicle_id, dealership_id, db)

    # Refresh days
    if v.date_acquired and v.status == VehicleStatus.active:
        v.days_in_inventory = (date.today() - v.date_acquired).days
        db.commit()

    comp_summary = db.query(CompSummary).filter(CompSummary.vehicle_id == vehicle_id).first()
    signals = db.query(VehicleSignals).filter(VehicleSignals.vehicle_id == vehicle_id).first()

    result = engine.run_full_analysis(v, comp_summary, signals)

    # Store report
    report = AnalysisReport(vehicle_id=vehicle_id, **result)
    db.add(report)
    db.commit()
    db.refresh(report)

    return report


@app.get("/api/vehicles/{vehicle_id}/curve")
def get_curve(
    vehicle_id: int,
    days: int = Query(90, ge=1, le=180),
    db: Session = Depends(get_db),
    dealership_id: int = Depends(get_dealership_id),
):
    """Return just the daily curve from the latest analysis."""
    report = db.query(AnalysisReport).filter(
        AnalysisReport.vehicle_id == vehicle_id,
    ).order_by(AnalysisReport.computed_at.desc()).first()

    if not report or not report.daily_curve:
        raise HTTPException(404, "No analysis found. Run analyze first.")

    curve = report.daily_curve[:days]
    return {"vehicle_id": vehicle_id, "days": len(curve), "curve": curve}


@app.get("/api/vehicles/insights", response_model=List[VehicleInsight])
@app.get("/api/vehicles/insights", response_model=List[VehicleInsight])
def get_insights(
    status: str = Query("active"),
    db: Session = Depends(get_db),
    dealership_id: int = Depends(get_dealership_id),
):
    vehicles = db.query(Vehicle).filter(
        Vehicle.dealership_id == dealership_id,
        Vehicle.status == status,
    ).order_by(Vehicle.days_in_inventory.desc()).all()

    insights = []
    for v in vehicles:
        if v.date_acquired and v.status == VehicleStatus.active:
            v.days_in_inventory = (date.today() - v.date_acquired).days

        report = db.query(AnalysisReport).filter(
            AnalysisReport.vehicle_id == v.id,
        ).order_by(AnalysisReport.computed_at.desc()).first()

        one_line = None
        if report and report.action_plan:
            actions = report.action_plan
            if isinstance(actions, list) and len(actions) > 0:
                one_line = actions[0]

        insights.append({
            "vehicle_id": v.id,
            "vin": v.vin,
            "year": v.year,
            "make": v.make,
            "model": v.model,
            "trim": v.trim,
            "status": v.status,
            "days_in_inventory": v.days_in_inventory or 0,
            "list_price": v.list_price or 0,
            "acquisition_cost": v.acquisition_cost or 0,
            "recon_cost": v.recon_cost or 0,
            "p30": report.p30 if report else None,
            "p60": report.p60 if report else None,
            "p90": report.p90 if report else None,
            "aging_class": report.aging_class if report else None,
            "daily_carry_cost": report.daily_carry_cost if report else None,
            "inflection_day": report.inflection_day if report else None,
            "price_action": report.price_action if report else None,
            "one_line_action": one_line,
        })

    db.commit()
    return insights
  # ---------------------------------------------------------------------------
# FLOORPLAN ALARM ROUTES
# ---------------------------------------------------------------------------

@app.post("/api/alarms/run", response_model=AlarmOut)
def run_alarm(
    db: Session = Depends(get_db),
    dealership_id: int = Depends(get_dealership_id),
):
    """Manual trigger — generates alarm for today."""
    # Get config
    config = db.query(AlarmConfig).filter(AlarmConfig.dealership_id == dealership_id).first()
    thresholds = config.thresholds if config else [30, 45, 60, 75]

    # Get active vehicles
    vehicles = db.query(Vehicle).filter(
        Vehicle.dealership_id == dealership_id,
        Vehicle.status == VehicleStatus.active,
    ).all()

    # Refresh days
    for v in vehicles:
        if v.date_acquired:
            v.days_in_inventory = (date.today() - v.date_acquired).days
    db.commit()

    # Generate alarm
    alarm_data = engine.generate_alarm(vehicles, thresholds, dealership_id)

    alarm = FloorplanAlarm(
        dealership_id=dealership_id,
        alarm_date=date.today(),
        total_active_units=alarm_data["total_active_units"],
        total_daily_burn=alarm_data["total_daily_burn"],
        projected_burn_30=alarm_data["projected_burn_30"],
        projected_burn_60=alarm_data["projected_burn_60"],
        top_burners=alarm_data["top_burners"],
        threshold_crossings=alarm_data["threshold_crossings"],
        underwater_vehicles=alarm_data["underwater_vehicles"],
        executive_summary=alarm_data["executive_summary"],
    )
    db.add(alarm)
    db.commit()
    db.refresh(alarm)

    # --- EMAIL STUB ---
    # In production, send alarm_data via SMTP/SendGrid/SES here.
    # email_payload = {
    #     "to": config.email_targets if config else [],
    #     "subject": f"30-60-90 Daily Alarm — {alarm.alarm_date}",
    #     "body": alarm.executive_summary,
    #     "data": alarm_data,
    # }
    # send_email(email_payload)

    return alarm


@app.get("/api/alarms/latest", response_model=AlarmOut)
def get_latest_alarm(
    db: Session = Depends(get_db),
    dealership_id: int = Depends(get_dealership_id),
):
    alarm = db.query(FloorplanAlarm).filter(
        FloorplanAlarm.dealership_id == dealership_id,
    ).order_by(FloorplanAlarm.created_at.desc()).first()

    if not alarm:
        raise HTTPException(404, "No alarms found. Run an alarm first.")
    return alarm


@app.get("/api/alarms/history", response_model=List[AlarmOut])
def get_alarm_history(
    limit: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    dealership_id: int = Depends(get_dealership_id),
):
    return db.query(FloorplanAlarm).filter(
        FloorplanAlarm.dealership_id == dealership_id,
    ).order_by(FloorplanAlarm.created_at.desc()).limit(limit).all()


@app.put("/api/alarms/config", response_model=AlarmConfigOut)
def update_alarm_config(
    payload: AlarmConfigUpdate,
    db: Session = Depends(get_db),
    dealership_id: int = Depends(get_dealership_id),
):
    config = db.query(AlarmConfig).filter(AlarmConfig.dealership_id == dealership_id).first()
    if not config:
        config = AlarmConfig(dealership_id=dealership_id)
        db.add(config)
        db.commit()
        db.refresh(config)

    update_data = payload.dict(exclude_unset=True)
    for key, val in update_data.items():
        setattr(config, key, val)

    db.commit()
    db.refresh(config)
    return config


@app.get("/api/alarms/config", response_model=AlarmConfigOut)
def get_alarm_config(
    db: Session = Depends(get_db),
    dealership_id: int = Depends(get_dealership_id),
):
    config = db.query(AlarmConfig).filter(AlarmConfig.dealership_id == dealership_id).first()
    if not config:
        raise HTTPException(404, "No alarm config found.")
    return config


# ---------------------------------------------------------------------------
# PRICING WATERFALL ROUTES
# ---------------------------------------------------------------------------

@app.get("/api/settings/pricing-waterfall", response_model=WaterfallSettingsOut)
def get_waterfall_settings(
    db: Session = Depends(get_db),
    dealership_id: int = Depends(get_dealership_id),
):
    settings = db.query(PricingWaterfallSettings).filter(
        PricingWaterfallSettings.dealership_id == dealership_id,
    ).first()
    if not settings:
        raise HTTPException(404, "No waterfall settings found.")
    return settings


@app.put("/api/settings/pricing-waterfall", response_model=WaterfallSettingsOut)
def update_waterfall_settings(
    payload: WaterfallSettingsUpdate,
    db: Session = Depends(get_db),
    dealership_id: int = Depends(get_dealership_id),
):
    settings = db.query(PricingWaterfallSettings).filter(
        PricingWaterfallSettings.dealership_id == dealership_id,
    ).first()
    if not settings:
        settings = PricingWaterfallSettings(dealership_id=dealership_id)
        db.add(settings)
        db.commit()
        db.refresh(settings)

    update_data = payload.dict(exclude_unset=True)

    # Convert rules from Pydantic models to dicts for JSON storage
    if "rules" in update_data and update_data["rules"] is not None:
        update_data["rules"] = [
            r.dict() if hasattr(r, "dict") else r for r in update_data["rules"]
        ]

    for key, val in update_data.items():
        setattr(settings, key, val)

    settings.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(settings)
    return settings


@app.post("/api/vehicles/{vehicle_id}/pricing-waterfall/plan", response_model=WaterfallPlanOut)
def generate_waterfall_plan(
    vehicle_id: int,
    db: Session = Depends(get_db),
    dealership_id: int = Depends(get_dealership_id),
):
    v = _get_vehicle_or_404(vehicle_id, dealership_id, db)

    # Refresh days
    if v.date_acquired and v.status == VehicleStatus.active:
        v.days_in_inventory = (date.today() - v.date_acquired).days
        db.commit()

    settings = db.query(PricingWaterfallSettings).filter(
        PricingWaterfallSettings.dealership_id == dealership_id,
    ).first()

    if not settings:
        raise HTTPException(404, "No waterfall settings configured.")

    plan_data = engine.generate_waterfall_plan(
        vehicle=v,
        rules=settings.rules,
        price_floor_policy=settings.price_floor_policy,
    )

    return WaterfallPlanOut(
        vehicle_id=plan_data["vehicle_id"],
        current_price=plan_data["current_price"],
        total_cost=plan_data["total_cost"],
        wholesale_exit_price=plan_data["wholesale_exit_price"],
        steps=[WaterfallStepOut(**s) for s in plan_data["steps"]],
        recommendation=plan_data["recommendation"],
    )


@app.post("/api/vehicles/{vehicle_id}/pricing-waterfall/apply", response_model=VehicleOut)
def apply_waterfall_step(
    vehicle_id: int,
    step: int = Query(1, ge=1, description="Which step number to apply"),
    db: Session = Depends(get_db),
    dealership_id: int = Depends(get_dealership_id),
):
    """
    Manually approve and apply a waterfall step.
    Applies the price change and logs it.
    """
    v = _get_vehicle_or_404(vehicle_id, dealership_id, db)

    # Generate the plan to get the step
    settings = db.query(PricingWaterfallSettings).filter(
        PricingWaterfallSettings.dealership_id == dealership_id,
    ).first()
    if not settings:
        raise HTTPException(404, "No waterfall settings configured.")

    plan_data = engine.generate_waterfall_plan(v, settings.rules, settings.price_floor_policy)

    # Find the requested step
    target_step = None
    for s in plan_data["steps"]:
        if s["step"] == step:
            target_step = s
            break

    if not target_step:
        raise HTTPException(404, f"Step {step} not found in waterfall plan.")

    old_price = v.list_price
    new_price = target_step["new_price"]

    # Apply
    v.list_price = new_price
    v.updated_at = datetime.utcnow()

    # Log
    db.add(PriceEventLog(
        vehicle_id=v.id,
        dealership_id=dealership_id,
        event_type="waterfall_reduction",
        old_price=old_price,
        new_price=new_price,
        reason=(
            f"Waterfall step {step} applied. "
            f"Trigger: {target_step['trigger_condition']}. "
            f"Expected probability lift: {target_step['expected_probability_lift']:.1%}."
        ),
        triggered_by="user_approved",
    ))

    db.commit()
    db.refresh(v)
    return v


# ---------------------------------------------------------------------------
# PRICE EVENT LOG ROUTES
# ---------------------------------------------------------------------------

@app.get("/api/vehicles/{vehicle_id}/price-events", response_model=List[PriceEventOut])
def get_price_events(
    vehicle_id: int,
    db: Session = Depends(get_db),
    dealership_id: int = Depends(get_dealership_id),
):
    _get_vehicle_or_404(vehicle_id, dealership_id, db)

    events = db.query(PriceEventLog).filter(
        PriceEventLog.vehicle_id == vehicle_id,
        PriceEventLog.dealership_id == dealership_id,
    ).order_by(PriceEventLog.created_at.desc()).all()

    return events


@app.get("/api/price-events", response_model=List[PriceEventOut])
def get_all_price_events(
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    dealership_id: int = Depends(get_dealership_id),
):
    return db.query(PriceEventLog).filter(
        PriceEventLog.dealership_id == dealership_id,
    ).order_by(PriceEventLog.created_at.desc()).limit(limit).all()


# ---------------------------------------------------------------------------
# BATCH OPERATIONS
# ---------------------------------------------------------------------------

@app.post("/api/vehicles/analyze-all", response_model=MessageResponse)
def analyze_all_vehicles(
    db: Session = Depends(get_db),
    dealership_id: int = Depends(get_dealership_id),
):
    """Run analysis on all active vehicles. Useful for daily batch."""
    vehicles = db.query(Vehicle).filter(
        Vehicle.dealership_id == dealership_id,
        Vehicle.status == VehicleStatus.active,
    ).all()

    count = 0
    for v in vehicles:
        if v.date_acquired:
            v.days_in_inventory = (date.today() - v.date_acquired).days

        comp_summary = db.query(CompSummary).filter(CompSummary.vehicle_id == v.id).first()
        signals = db.query(VehicleSignals).filter(VehicleSignals.vehicle_id == v.id).first()

        result = engine.run_full_analysis(v, comp_summary, signals)
        report = AnalysisReport(vehicle_id=v.id, **result)
        db.add(report)
        count += 1

    db.commit()
    return MessageResponse(
        message=f"Analyzed {count} active vehicles.",
        detail={"count": count},
    )


@app.post("/api/vehicles/refresh-all-comps", response_model=MessageResponse)
def refresh_all_comps(
    db: Session = Depends(get_db),
    dealership_id: int = Depends(get_dealership_id),
):
    """Refresh comps for all active vehicles. Useful for daily batch."""
    vehicles = db.query(Vehicle).filter(
        Vehicle.dealership_id == dealership_id,
        Vehicle.status == VehicleStatus.active,
    ).all()

    count = 0
    for v in vehicles:
        # Remove old auto comps
        db.query(Comp).filter(
            Comp.vehicle_id == v.id,
            Comp.source == CompSource.auto,
        ).delete()

        # Generate new
        mock_comps = _generate_mock_comps(v)
        for c in mock_comps:
            db.add(Comp(
                vehicle_id=v.id,
                source=CompSource.auto,
                year=c["year"],
                make=c["make"],
                model=c["model"],
                trim=c.get("trim"),
                mileage=c["mileage"],
                price=c["price"],
                sold_price=c.get("sold_price"),
                days_on_market=c.get("days_on_market"),
                distance_miles=c.get("distance_miles"),
                dealer_name=c.get("dealer_name"),
                listing_status=c.get("listing_status", "active"),
            ))
        count += 1

    db.commit()

    # Rebuild summaries
    for v in vehicles:
        _rebuild_comp_summary(v.id, db)

    return MessageResponse(
        message=f"Refreshed comps for {count} vehicles.",
        detail={"count": count},
    )
