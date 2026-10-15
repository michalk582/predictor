import pandas as pd
from database.connection import engine


class DataLoader:
    def __init__(self):
        self.engine = engine

    def get_training_data(self) -> pd.DataFrame:
        df = pd.read_sql(f"SELECT k.dtime, k.load_actual, w.temperature, w.wind_speed, w.radiation FROM kse_load k JOIN weather_load w ON k.dtime = w.dtime;", con=self.engine)
        return df



