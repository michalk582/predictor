from sqlalchemy import Column, String, Float, DateTime, Integer, UniqueConstraint
from sqlalchemy.orm import declarative_base


Base = declarative_base()

class KseLoad(Base):
    __tablename__ = 'kse_load'
    dtime = Column(DateTime, primary_key=True)
    business_date = Column(String)
    period = Column(String)
    load_actual = Column(Float, nullable=True) # Rzeczywiste zapotrzebowanie
    load_fcst = Column(Float, nullable=True) # Oficjalna prognoza

class WeatherLoad(Base):
    __tablename__ = "weather_load"
    dtime = Column(DateTime, primary_key=True)
    business_date = Column(String(10), index=True)  # Data (np. '2026-10-01')
    temperature = Column(Float)  # Temperatura 2m (°C)
    wind_speed = Column(Float)  # Prędkość wiatru (m/s)
    radiation = Column(Float)

class Predictions(Base):
    __tablename__ = "predictions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    forecast_made_at = Column(DateTime, nullable=False, index=True)

    dtime = Column(DateTime, nullable=False, index=True)  # godzina, której dotyczy prognoza
    business_date = Column(String(10), index=True)
    temperature = Column(Float)
    wind_speed = Column(Float)
    radiation = Column(Float)

    load_model_prediction = Column(Float, nullable=False)
    model_version = Column(String)
    __table_args__ = (UniqueConstraint("forecast_made_at", "dtime", name="uq_pred_run_dtime"),)

class ModelMetrics(Base):
    __tablename__ = "model_metrics"
    id = Column(Integer, primary_key=True, autoincrement=True)
    eval_date = Column(String(10), nullable=False, index=True)  # oceniany dzień, np. '2026-10-21'
    horizon_day = Column(Integer, nullable=False)               # 1 = prognoza zrobiona dzień wcześniej
    model_version = Column(String, nullable=False)
    n_hours = Column(Integer)                                   # ile godzin miało rzeczywiste dane
    mae = Column(Float)                                         # MW
    mape = Column(Float)
    computed_at = Column(DateTime)

    __table_args__ = (
        UniqueConstraint("eval_date", "horizon_day", "model_version", name="uq_metrics_day"),
    )