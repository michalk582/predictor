# scripts/02_backfill.py
import os
import sys
import time
from datetime import datetime, timedelta

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

    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d")

    current_date = start_date
    session = SessionLocal()

    print(f"Rozpoczynam pełny backfill (prąd + pogoda) od {start_date_str} do {end_date_str}...")

    try:
        while current_date <= end_date:

            date_str = current_date.strftime("%Y-%m-%d")
            print(f"\n--- Przetwarzanie daty: {date_str} ---")
            try:
                # 1. Pobieranie danych energetycznych z PSE
                df_pse = pse_client.get_kse_load(date_str)

                # 2. Pobieranie i skalowanie danych pogodowych z Open-Meteo
                df_weather = weather_client.get_weather_for_date(date_str)

                # 3. Czyszczenie starych danych dla tego dnia w obu tabelach (idempotentność)
                session.query(KseLoad).filter(KseLoad.business_date == date_str).delete()
                session.query(WeatherLoad).filter(WeatherLoad.business_date == date_str).delete()
                session.commit()

                # 4. Zapis danych energetycznych do tabeli kse_load
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
                    print(f"-> Zapisano {len(pse_objects)} rekordów KSE.")

                # 5. Zapis danych pogodowych do tabeli weather_db
                if not df_weather.empty:
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
                    print(f"-> Zapisano {len(weather_objects)} rekordów pogodowych.")

                # Zatwierdzenie transakcji dla bieżącego dnia
                session.commit()
            except Exception as e:
                print(f"Wystąpił błąd dla daty {date_str}: {e}.")

            finally:
                current_date += timedelta(days=1)
                time.sleep(0.5)

        print("\nZakończono pomyślnie cały backfill!")

    except Exception as e:
        session.rollback()
        print(f"\n[BŁĄD] Wystąpił problem podczas backfillu: {e}")
    finally:
        session.close()
        time.sleep(1)


if __name__ == "__main__":
    # Możesz tutaj zmienić zakres dat, który chcesz pobrać
    run_backfill("2026-03-03", "2026-09-30")