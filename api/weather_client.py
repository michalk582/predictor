# api/weather_client.py
import requests
import pandas as pd


class WeatherApiClient:
    """
    Klasa odpowiedzialna za pobieranie i dopasowywanie historycznych danych pogodowych z Open-Meteo.
    """

    def __init__(self):
        self.base_url = "https://archive-api.open-meteo.com/v1/archive"

    def get_weather_for_date(self, date_str: str) -> pd.DataFrame:
        latitude = 52.23
        longitude = 21.01

        params = {
            "latitude": latitude,
            "longitude": longitude,
            "start_date": date_str,
            "end_date": date_str,
            "hourly": "temperature_2m,wind_speed_10m,shortwave_radiation",
            "timezone": "UTC"
        }

        try:
            response = requests.get(self.base_url, params=params, timeout=10)
        except requests.exceptions.RequestException as e:
            print(f"-> Błąd połączenia z API pogody dla {date_str}: {e}")
            return pd.DataFrame()

        if response.status_code == 200:
            data = response.json()

            if "hourly" in data and "time" in data["hourly"]:
                df = pd.DataFrame(data["hourly"])

                col_mapping = {
                    "time": "dtime",
                    "temperature_2m": "temperature",
                    "wind_speed_10m": "wind_speed",
                    "shortwave_radiation": "radiation"
                }
                df = df.rename(columns=col_mapping)

                # prarsowanie
                df['dtime'] = pd.to_datetime(df['dtime'])
                if df['dtime'].dt.tz is not None:
                    df['dtime'] = df['dtime'].dt.tz_localize(None)


                df['business_date'] = date_str

                final_columns = ['dtime', 'business_date', 'temperature', 'wind_speed', 'radiation']
                print(f"-> Pobrano pogodę; {len(df)} rekordów dla {date_str}.")
                return df[final_columns]
            else:
                print(f"-> API pogody nie zwróciło danych dla {date_str}.")
                return pd.DataFrame()
        else:
            print(f"-> Błąd API pogody! Kod: {response.status_code} - {response.text}")
            return pd.DataFrame()