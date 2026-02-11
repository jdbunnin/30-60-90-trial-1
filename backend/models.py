# backend/models.py — Config + Database + All Models

import os
from datetime import datetime, date
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Text, Boolean,
    Date, DateTime, ForeignKey, JSON, Enum as SAEnum
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
import enum

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./dev.db")

# Render Postgres URLs start with postgres:// but SQLAlchemy needs postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

NHTSA_API_URL = os.getenv("NHTSA_API_URL", "https://vpic.nhtsa.dot.gov/api/vehicles")
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "https://thirty-sixty-ninety.onrender.com",
    "https://three0-60-90-trial-1.onrender.com",
]
# ---------------------------------------------------------------------------
# DATABASE ENGINE + SESSION
# ---------------------------------------------------------------------------
connect_args = {}
if "sqlite" in DATABASE_URL:
    connect_args = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, connect_args=connect_args, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency — yields a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# ENUMS
# ---------------------------------------------------------------------------
class VehicleStatus(str, enum.Enum):
    active = "active"
    sold = "sold"
    wholesale = "wholesale"
    traded = "traded"


class AgingClass(str, enum.Enum):
    healthy = "healthy"
    at_risk = "at_risk"
    danger = "danger"


class CompSource(str, enum.Enum):
    auto = "auto"
    manual = "manual"


class ExitPath(str, enum.Enum):
    retail = "retail"
    wholesale_auction = "wholesale_auction"
    dealer_trade = "dealer_trade"


class PriceAction(str, enum.Enum):
    hold = "hold"
    reduce = "reduce"
    increase = "increase"


class Elasticity(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"


class Confidence(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"


# ---------------------------------------------------------------------------
# MODELS
# ---------------------------------------------------------------------------

class Dealership(Base):
    __tablename__ = "dealerships"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    timezone = Column(String(50), default="America/Chicago")
    created_at = Column(DateTime, default=datetime.utcnow)

    users = relationship("User", back_populates="dealership")
    vehicles = relationship("Vehicle", back_populates="dealership")
    waterfall_settings = relationship("PricingWaterfallSettings", back_populates="dealership", uselist=False)
    alarm_config = relationship("AlarmConfig", back_populates="dealership", uselist=False)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    dealership_id = Column(Integer, ForeignKey("dealerships.id"), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    role = Column(String(50), default="manager")  # principal, gm, manager
    created_at = Column(DateTime, default=datetime.utcnow)

    dealership = relationship("Dealership", back_populates="users")


class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True)
    dealership_id = Column(Integer, ForeignKey("dealerships.id"), nullable=False)
    vin = Column(String(17), nullable=False, index=True)
    status = Column(SAEnum(VehicleStatus), default=VehicleStatus.active)

    # VIN-decoded identity
    year = Column(Integer)
    make = Column(String(100))
    model = Column(String(100))
    trim = Column(String(100))
    body_style = Column(String(100))
    engine = Column(String(200))

    # Dealer financials (user-input)
    acquisition_cost = Column(Float, default=0)
    recon_cost = Column(Float, default=0)
    list_price = Column(Float, default=0)
    floorplan_rate_apr = Column(Float, default=6.5)  # percent
    wholesale_exit_price = Column(Float, default=0)
    min_acceptable_margin = Column(Float, default=500)
    mileage = Column(Integer, default=0)

    # Tracking
    date_acquired = Column(Date, default=date.today)
    days_in_inventory = Column(Integer, default=0)
    date_sold = Column(Date, nullable=True)
    sold_price = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    dealership = relationship("Dealership", back_populates="vehicles")
    signals = relationship("VehicleSignals", back_populates="vehicle", uselist=False)
    comps = relationship("Comp", back_populates="vehicle")
    comp_summary = relationship("CompSummary", back_populates="vehicle", uselist=False)
    analysis_reports = relationship("AnalysisReport", back_populates="vehicle")
    price_events = relationship("PriceEventLog", back_populates="vehicle")

    @property
    def total_cost(self):
        return (self.acquisition_cost or 0) + (self.recon_cost or 0)

    @property
    def daily_floorplan_cost(self):
        return self.total_cost * ((self.floorplan_rate_apr or 6.5) / 100) / 365


class VehicleSignals(Base):
    __tablename__ = "vehicle_signals"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)

    views_total = Column(Integer, default=0)
    views_last_7 = Column(Integer, default=0)
    leads_total = Column(Integer, default=0)
    leads_last_7 = Column(Integer, default=0)
    test_drives = Column(Integer, default=0)
    notes = Column(Text, default="")

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    vehicle = relationship("Vehicle", back_populates="signals")


class Comp(Base):
    __tablename__ = "comps"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    source = Column(SAEnum(CompSource), default=CompSource.auto)

    vin = Column(String(17), nullable=True)
    year = Column(Integer)
    make = Column(String(100))
    model = Column(String(100))
    trim = Column(String(100))
    mileage = Column(Integer)
    price = Column(Float)
    sold_price = Column(Float, nullable=True)
    days_on_market = Column(Integer, nullable=True)
    distance_miles = Column(Float, nullable=True)
    dealer_name = Column(String(255), nullable=True)
    listing_status = Column(String(50), default="active")  # active, sold, delisted
    found_at = Column(DateTime, default=datetime.utcnow)

    vehicle = relationship("Vehicle", back_populates="comps")


class CompSummary(Base):
    __tablename__ = "comp_summaries"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False, unique=True)

    auto_count = Column(Integer, default=0)
    manual_count = Column(Integer, default=0)
    median_price = Column(Float)
    mean_price = Column(Float)
    low_price = Column(Float)
    high_price = Column(Float)
    median_days_to_sale = Column(Float)
    supply_count = Column(Integer, default=0)
    demand_score = Column(Float, default=0)  # 0-100
    supply_vs_demand = Column(String(50))  # oversupplied / balanced / undersupplied

    discrepancy_flag = Column(Boolean, default=False)
    discrepancy_note = Column(Text, nullable=True)
    weighted_source = Column(String(20), nullable=True)  # auto or manual — which is weighted more
    weight_reason = Column(Text, nullable=True)

    computed_at = Column(DateTime, default=datetime.utcnow)

    vehicle = relationship("Vehicle", back_populates="comp_summary")


class AnalysisReport(Base):
    __tablename__ = "analysis_reports"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)

    # Probabilities
    p30 = Column(Float)
    p60 = Column(Float)
    p90 = Column(Float)

    # Classification
    aging_class = Column(SAEnum(AgingClass))
    daily_carry_cost = Column(Float)
    carry_cost_30 = Column(Float)
    carry_cost_60 = Column(Float)
    carry_cost_90 = Column(Float)
    margin_erosion_30 = Column(Float)
    margin_erosion_60 = Column(Float)
    margin_erosion_90 = Column(Float)
    inflection_day = Column(Integer)  # day when holding becomes irrational

    # Pricing strategy
    price_action = Column(SAEnum(PriceAction))
    price_change_amount = Column(Float, default=0)
    price_action_lift_p = Column(Float, default=0)  # expected probability lift
    price_action_gross_impact = Column(Float, default=0)
    price_elasticity = Column(SAEnum(Elasticity))
    elasticity_reason = Column(Text)

    # Exit path
    optimal_exit = Column(SAEnum(ExitPath))
    exit_expected_gross = Column(Float)
    exit_expected_days = Column(Float)
    exit_reason = Column(Text)

    # Actions
    action_plan = Column(JSON)  # list of 3-5 strings

    # Risk
    risks = Column(JSON)  # list of strings
    change_triggers = Column(JSON)  # list of strings
    confidence = Column(SAEnum(Confidence))

    # Day-by-day curve (90 items)
    daily_curve = Column(JSON)

    computed_at = Column(DateTime, default=datetime.utcnow)

    vehicle = relationship("Vehicle", back_populates="analysis_reports")


class FloorplanAlarm(Base):
    __tablename__ = "floorplan_alarms"

    id = Column(Integer, primary_key=True, index=True)
    dealership_id = Column(Integer, ForeignKey("dealerships.id"), nullable=False)

    alarm_date = Column(Date, default=date.today)
    total_active_units = Column(Integer)
    total_daily_burn = Column(Float)
    projected_burn_30 = Column(Float)
    projected_burn_60 = Column(Float)
    top_burners = Column(JSON)  # list of {vehicle_id, vin, daily_cost, days}
    threshold_crossings = Column(JSON)  # {30: [...], 45: [...], 60: [...], 75: [...]}
    underwater_vehicles = Column(JSON)  # list of {vehicle_id, vin, net_gross}
    executive_summary = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)


class AlarmConfig(Base):
    __tablename__ = "alarm_configs"

    id = Column(Integer, primary_key=True, index=True)
    dealership_id = Column(Integer, ForeignKey("dealerships.id"), nullable=False, unique=True)

    thresholds = Column(JSON, default=[30, 45, 60, 75])
    enabled = Column(Boolean, default=True)
    email_targets = Column(JSON, default=[])  # list of email strings
    alarm_hour = Column(Integer, default=6)  # local time hour

    dealership = relationship("Dealership", back_populates="alarm_config")


class PricingWaterfallSettings(Base):
    __tablename__ = "pricing_waterfall_settings"

    id = Column(Integer, primary_key=True, index=True)
    dealership_id = Column(Integer, ForeignKey("dealerships.id"), nullable=False, unique=True)

    # Default waterfall rules as JSON array
    # Each rule: {trigger_day, price_reduction_pct, min_margin_floor, stop_at_wholesale: bool}
    rules = Column(JSON, default=[
        {"trigger_day": 15, "reduction_pct": 3, "min_margin_floor": 1500},
        {"trigger_day": 30, "reduction_pct": 5, "min_margin_floor": 1000},
        {"trigger_day": 45, "reduction_pct": 8, "min_margin_floor": 500},
        {"trigger_day": 60, "reduction_pct": 12, "min_margin_floor": 0},
    ])
    price_floor_policy = Column(String(50), default="total_cost")  # total_cost or wholesale
    auto_mode = Column(Boolean, default=False)  # future: auto-apply

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    dealership = relationship("Dealership", back_populates="waterfall_settings")


class PriceEventLog(Base):
    __tablename__ = "price_event_log"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    dealership_id = Column(Integer, ForeignKey("dealerships.id"), nullable=False)

    event_type = Column(String(50))  # waterfall_reduction, manual_override, status_change
    old_price = Column(Float)
    new_price = Column(Float)
    reason = Column(Text)
    triggered_by = Column(String(50))  # system, user email, etc.
    created_at = Column(DateTime, default=datetime.utcnow)

    vehicle = relationship("Vehicle", back_populates="price_events")


# ---------------------------------------------------------------------------
# CREATE ALL TABLES
# ---------------------------------------------------------------------------
def init_db():
    Base.metadata.create_all(bind=engine)
