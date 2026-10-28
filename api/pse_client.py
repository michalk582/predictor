# api/pse_client.py
import requests
import pandas as pd


class PseApiClient:
    """
    Klasa odpowiedzialna za komunikację z API Polskich Sieci Elektroenergetycznych.
    """

    def __init__(self):
        self.base_url = "https://api.raporty.pse.pl/api"

    def get_kse_load(self, start_date: str, end_date: str):
        url = f"{self.base_url}/his-wlk-cal"
        all_records = []

        # Generujemy listę pojedynczych dni w zadanym zakresie (np. cały styczeń)
        days = pd.date_range(start=start_date, end=end_date)

        # Pętla ukryta wewnątrz klienta API - szybkie zapytania dzień po dniu
        for single_date in days:
            day_str = single_date.strftime('%Y-%m-%d')
            params = {
                # Pytamy tylko o jeden dzień (96 rekordów = omijamy limit 100!)
                "$filter": f"business_date eq '{day_str}'"
            }

            try:
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if "value" in data and len(data["value"]) > 0:
                        all_records.extend(data["value"])
            except Exception as e:
                print(f"-> Błąd połączenia z PSE dla {day_str}: {e}")

        # Jeśli po sprawdzeniu wszystkich dni z miesiąca nic nie mamy
        if not all_records:
            return pd.DataFrame()

        # Przekształcamy zebrane wiersze z całego miesiąca na DataFrame
        df = pd.DataFrame(all_records)

        df = df.rename(columns={'demand': 'load_actual'})
        df['load_fcst'] = None

        # 25.10 / zmiana czasu: PSE oznacza powtórzoną godzinę jako "02a" — pomijamy ją
        df = df[~df['dtime'].astype(str).str.contains(r'\d{2}a:', regex=True)]

        df['dtime'] = pd.to_datetime(df['dtime'])
        if df['dtime'].dt.tz is not None:
            df['dtime'] = df['dtime'].dt.tz_localize(None)

        df = df.set_index('dtime')

        # Uśredniamy 2800+ rekordów kwadransowych do ~744 godzinowych
        df = df.resample('1h').agg({
            'business_date': 'first',
            'load_actual': 'mean',
            'load_fcst': 'mean'
        }).reset_index()

        df = df.dropna(subset=['load_actual'])

        df['period'] = df['dtime'].dt.strftime('%H:00') + ' - ' + (df['dtime'] + pd.Timedelta(hours=1)).dt.strftime(
            '%H:00')
        df['business_date'] = df['dtime'].dt.strftime('%Y-%m-%d')

        final_columns = ['dtime', 'business_date', 'period', 'load_actual', 'load_fcst']
        return df[final_columns]





