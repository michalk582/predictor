# api/pse_client.py
import requests
import pandas as pd


class PseApiClient:
    """
    Klasa odpowiedzialna za komunikację z API Polskich Sieci Elektroenergetycznych.
    """

    def __init__(self):
        self.base_url = "https://api.raporty.pse.pl/api"

    def get_kse_load(self, date_str: str) -> pd.DataFrame:
        endpoint = f"{self.base_url}/his-wlk-cal"
        params = {"$filter": f"business_date eq '{date_str}'"}

        try:
            response = requests.get(endpoint, params=params, timeout=10)
        except requests.exceptions.RequestException as e:
            print(f"Błąd z API PSE dla {date_str}: {e}")
            return pd.DataFrame()

        if response.status_code == 200:
            data = response.json()

            if 'value' in data and len(data['value']) > 0:
                df = pd.DataFrame(data['value'])
                df.columns = [col.lower() for col in df.columns]

                # Jawne i pewne mapowanie nazw kolumn z API PSE na naszą bazę
                col_mapping = {
                    'demand': 'load_actual',  # Nowa nazwa z API PSE
                    'zapotrzebowanie': 'load_actual',  # Alternatywna nazwa
                    'udtczas': 'dtime',
                    'data_time': 'dtime',
                    'ts': 'dtime',
                    'tc': 'period',
                    'okres': 'period'
                }
                df = df.rename(columns=col_mapping)

                # Bezpieczne parsowanie czasu
                if 'dtime' in df.columns:
                    df['dtime'] = pd.to_datetime(df['dtime'])
                    if df['dtime'].dt.tz is not None:
                        df['dtime'] = df['dtime'].dt.tz_localize(None)

                # Uzupełnienie brakujących kolumn
                if 'load_fcst' not in df.columns:
                    df['load_fcst'] = None
                if 'period' not in df.columns:
                    df['period'] = 'unknown'

                final_columns = ['dtime', 'business_date', 'period', 'load_actual', 'load_fcst']

                for col in final_columns:
                    if col not in df.columns:
                        df[col] = None

                df['period'] = df['period'].astype(str)

                df = df.set_index('dtime')

                df = df.resample('1h').agg({
                    'business_date' : 'first',
                    'period' : 'first',
                    'load_actual' : 'mean',
                    'load_fcst' : 'mean'
                }).reset_index()

                df = df[df['dtime'].dt.strftime('%Y-%m-%d') == date_str]
                df['period'] = df['dtime'].dt.strftime('%H:00') + ' - ' + (
                            df['dtime'] + pd.Timedelta(hours=1)).dt.strftime('%H:00')

                print(f"-> Pobrano i uśredniono do godzin: {len(df)} rekordów dla daty {date_str}.")
                return df[final_columns]
            else:
                print(f"-> API nie zwróciło żadnych danych dla {date_str}.")
                return pd.DataFrame()
        else:
            print(f"-> Błąd API! Kod: {response.status_code} - {response.text}")
            return pd.DataFrame()