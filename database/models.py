from sqlalchemy import Column, String, Float, DateTime
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