import pandas as pd
import holidays
from database.connection import engine
import numpy as np

TARGET = "load_actual"
FEATURES = [
    "temperature", "wind_speed", "radiation",
    "day_of_week", "is_holiday",
    "hour_sin", "hour_cos", "month_sin", "month_cos",
]
PL_HOLIDAYS = holidays.Poland(years=range(2020, 2031))

class DataLoader:
    def __init__(self):
        self.engine = engine

    def get_data(self) -> pd.DataFrame:
        query = """
                SELECT k.dtime, k.load_actual, w.temperature, w.wind_speed, w.radiation
                FROM kse_load k
                         JOIN weather_load w ON k.dtime = w.dtime
                WHERE k.load_actual IS NOT NULL
                ORDER BY k.dtime
                """
        return pd.read_sql(query, con=self.engine, parse_dates=['dtime'])

    @staticmethod
    def make_features(df: pd.DataFrame) -> pd.DataFrame:
        """Jedna funkcja do cech, używana i w treningu, i w prognozie."""
        out = df.copy()
        dt = out["dtime"]
        hour, month = dt.dt.hour, dt.dt.month

        out["day_of_week"] = dt.dt.dayofweek
        out["is_holiday"] = dt.dt.date.map(lambda d: d in PL_HOLIDAYS).astype(int)
        out["hour_sin"] = np.sin(2 * np.pi * hour / 24)
        out["hour_cos"] = np.cos(2 * np.pi * hour / 24)
        out["month_sin"] = np.sin(2 * np.pi * (month - 1) / 12)
        out["month_cos"] = np.cos(2 * np.pi * (month - 1) / 12)
        return out

    def prepare_data_to_training(self, df: pd.DataFrame, test_days: int = 60):
        """Podział czasowy: ostatnie `test_days` dni jako test."""
        data = self.make_features(df).sort_values("dtime")
        cutoff = data["dtime"].max() - pd.Timedelta(days=test_days)
        train, test = data[data["dtime"] <= cutoff], data[data["dtime"] > cutoff]
        return train[FEATURES], test[FEATURES], train[TARGET], test[TARGET]

    def prepare_to_prediction(self, df: pd.DataFrame) -> pd.DataFrame:
        return self.make_features(df)[FEATURES]


