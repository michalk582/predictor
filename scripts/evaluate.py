import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime

import pandas as pd
from sqlalchemy.dialects.postgresql import insert

from database.connection import engine
from database.models import ModelMetrics

MIN_HOURS = 20  # oceniaj tylko dni z prawie kompletnymi danymi z PSE

QUERY = """
    SELECT p.forecast_made_at, p.dtime, p.business_date, p.model_version,
           p.load_model_prediction, k.load_actual
    FROM predictions p
    JOIN kse_load k ON k.dtime = p.dtime
    WHERE k.load_actual IS NOT NULL
"""


def compute_metrics() -> pd.DataFrame:
    df = pd.read_sql(QUERY, engine, parse_dates=["forecast_made_at", "dtime"])
    if df.empty:
        print("Brak prognoz z rzeczywistymi danymi do oceny.")
        return df

    # horyzont w dniach: o ile dni wcześniej zrobiono prognozę
    df["horizon_day"] = (df["dtime"].dt.normalize() - df["forecast_made_at"].dt.normalize()).dt.days

    # jeśli jednego dnia było kilka uruchomień, bierzemy najnowszą prognozę
    df = (df.sort_values("forecast_made_at")
            .groupby(["dtime", "horizon_day", "model_version"], as_index=False)
            .last())

    df["abs_err"] = (df["load_model_prediction"] - df["load_actual"]).abs()
    df["ape"] = df["abs_err"] / df["load_actual"] * 100

    metrics = (df.groupby(["business_date", "horizon_day", "model_version"])
                 .agg(n_hours=("dtime", "count"), mae=("abs_err", "mean"), mape=("ape", "mean"))
                 .reset_index()
                 .rename(columns={"business_date": "eval_date"}))

    return metrics[metrics["n_hours"] >= MIN_HOURS]


def save_metrics(metrics: pd.DataFrame) -> None:
    if metrics.empty:
        return
    now = datetime.now()
    rows = [
        {
            "eval_date": r.eval_date,
            "horizon_day": int(r.horizon_day),
            "model_version": r.model_version,
            "n_hours": int(r.n_hours),
            "mae": float(r.mae),
            "mape": float(r.mape),
            "computed_at": now,
        }
        for r in metrics.itertuples()
    ]
    stmt = insert(ModelMetrics).values(rows)
    # jeśli PSE poprawi dane, ponowna ocena nadpisze stary wynik
    stmt = stmt.on_conflict_do_update(
        constraint="uq_metrics_day",
        set_={c: stmt.excluded[c] for c in ["n_hours", "mae", "mape", "computed_at"]},
    )
    with engine.begin() as conn:
        conn.execute(stmt)
    print(f"Zapisano metryki dla {len(rows)} dni.")


def run_evaluation() -> pd.DataFrame:
    metrics = compute_metrics()
    if not metrics.empty:
        print(metrics.to_string(index=False))
    save_metrics(metrics)
    return metrics


if __name__ == "__main__":
    run_evaluation()