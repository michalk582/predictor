import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
from datetime import datetime, timedelta
import pandas as pd
from sqlalchemy.dialects.postgresql import insert
from api.weather_client import WeatherApiClient
from database.connection import engine
from database.loader import DataLoader
from database.models import Predictions
from training.xgb_trainer import XGBTrainer, MODEL_PATH, META_PATH

HORIZON_DAYS = 1


def load_model_version() -> str:
    with open(META_PATH, encoding="utf-8") as f:
        return json.load(f)["model_version"]


def save_predictions(df: pd.DataFrame, forecast_made_at: datetime, model_version: str) -> None:
    rows = [
        {
            "forecast_made_at": forecast_made_at,
            "dtime": r.dtime.to_pydatetime(),
            "business_date": r.dtime.strftime("%Y-%m-%d"),
            "temperature": float(r.temperature),
            "wind_speed": float(r.wind_speed),
            "radiation": float(r.radiation),
            "load_model_prediction": float(r.load_model_prediction),
            "model_version": model_version,
        }
        for r in df.itertuples()
    ]
    if not rows:
        print("Brak prognoz do zapisania.")
        return

    stmt = insert(Predictions).values(rows).on_conflict_do_nothing(constraint="uq_pred_run_dtime")
    with engine.begin() as conn:
        conn.execute(stmt)
    print(f"Zapisano {len(rows)} prognoz (forecast_made_at={forecast_made_at}, model={model_version})")


def run_prediction() -> pd.DataFrame:
    forecast_made_at = datetime.now().replace(minute=0, second=0, microsecond=0)
    start = forecast_made_at.date() + timedelta(days=1)
    end = start + timedelta(days=HORIZON_DAYS - 1)

    print(f"Prognoza na: {start} – {end}")

    # 1. Prognoza pogody
    wc = WeatherApiClient(base_url="https://api.open-meteo.com/v1/forecast")
    df_weather = wc.get_weather_for_date(start.isoformat(), end.isoformat())
    df_weather["dtime"] = pd.to_datetime(df_weather["dtime"])

    # 2. Cechy (ta sama funkcja co w treningu)
    dl = DataLoader()
    X = dl.prepare_to_prediction(df_weather)

    # 3. Model
    trainer = XGBTrainer()
    trainer.load_model(str(MODEL_PATH))
    model_version = load_model_version()

    # 4. Wynik: pogoda + prognoza w jednej tabeli
    result = df_weather[["dtime", "temperature", "wind_speed", "radiation"]].copy()
    result["load_model_prediction"] = trainer.predict(X)
    result = result[result["dtime"] > forecast_made_at]

    print(result.to_string(index=False))

    # 5. Zapis do bazy
    save_predictions(result, forecast_made_at, model_version)
    return result



if __name__ == "__main__":
    run_prediction()


