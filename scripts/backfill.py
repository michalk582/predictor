# scripts/02_backfill.py
import os
import sys
import time
from datetime import datetime, timedelta
import pandas as pd

# Dodanie ścieżki do głównego katalogu projektu, aby Python widział paczki 'api' i 'database'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.pse_client import PseApiClient
from api.weather_client import WeatherApiClient
from database.connection import SessionLocal
from database.models import KseLoad, WeatherLoad
from database.connection import engine
from database.models import Base

# <<< DOPISZ TO TUTAJ (zaraz pod importami) >>>
# To polecenie sprawdza bazę i automatycznie tworzy brakujące tabele
Base.metadata.create_all(bind=engine)

def run_backfill(start_date_str: str, end_date_str: str):
    pse_client = PseApiClient()
    weather_client = WeatherApiClient()
    session = SessionLocal()

    print(f"Rozpoczynam pełny backfill od {start_date_str} do {end_date_str}...")

    try:
        print("--- Pobieranie danych pogodowych ---")
        df_weather = weather_client.get_weather_for_date(start_date_str, end_date_str)

        if not df_weather.empty:
            session.query(WeatherLoad).filter(
                WeatherLoad.business_date >= start_date_str,
                WeatherLoad.business_date <= end_date_str
            ).delete()
            session.commit()

            weather_objects = [
                WeatherLoad(
                    dtime=row['dtime'],
                    business_date=row['business_date'],
                    temperature=row['temperature'],
                    wind_speed=row['wind_speed'],
                    radiation=row['radiation']
                )
                for _, row in df_weather.iterrows()
            ]
            session.bulk_save_objects(weather_objects)
            session.commit()
            print(f"-> Zapisano {len(weather_objects)} rekordów pogodowych za jednym zamachem!\n")

        else:
            print("-> Brak danych pogodowych z API.\n")

        # ===============================
        # KSE
        # ===============================

        print("--- Rozpoczynam pobieranie danych PSE ---")
        months = pd.date_range(start=start_date_str, end=end_date_str, freq='MS')
        if not len(months):
            months = [pd.to_datetime(start_date_str).replace(day=1)]

        for month_start in months:
            # Ustalamy początek i koniec paczki (żeby nie wyjść poza ostateczny end_date_str)
            chunk_start = max(month_start.strftime("%Y-%m-%d"), start_date_str)
            # Ostatni dzień danego miesiąca:
            month_end = month_start + pd.offsets.MonthEnd(0)
            chunk_end = min(month_end.strftime("%Y-%m-%d"), end_date_str)

            print(f"Pobieranie KSE: {chunk_start} - {chunk_end}...")

            try:
                df_pse = pse_client.get_kse_load(chunk_start, chunk_end)

                # Usuwamy stare dane z tego okresu
                session.query(KseLoad).filter(
                    KseLoad.business_date >= chunk_start,
                    KseLoad.business_date <= chunk_end
                ).delete()

                if not df_pse.empty:
                    pse_objects = [
                        KseLoad(
                            dtime=row['dtime'],
                            business_date=row['business_date'],
                            period=row['period'],
                            load_actual=row['load_actual'],
                            load_fcst=row.get('load_fcst')
                        )
                        for _, row in df_pse.iterrows()
                    ]
                    session.bulk_save_objects(pse_objects)
                    session.commit()
                    print(f"-> Zapisano {len(pse_objects)} rekordów KSE dla tego okresu.")
                else:
                    session.commit()

            except Exception as e:
                print(f"[BŁĄD PSE] {chunk_start} - {chunk_end}: {e}")
                session.rollback()
            finally:
                time.sleep(1)
    except Exception as e:
        print(f"\n[BŁĄD KRYTYCZNY] Cały proces został przerwany: {e}")
        session.rollback()
    finally:
        session.close()
        print("\nZakończono działanie skryptu backfill.")




if __name__ == "__main__":
    run_backfill("2026-01-01", "2026-10-10")