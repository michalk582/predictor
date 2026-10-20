import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import pandas as pd

from api.pse_client import PseApiClient
from api.weather_client import WeatherApiClient
from database.models import KseLoad, WeatherLoad
from database.writer import upsert_df


def month_chunks(start: str, end: str):
    """Dzieli zakres dat na kawałki miesięczne (PSE nie lubi dużych zapytań)."""
    current = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)
    while current <= end_ts:
        chunk_end = min(current + pd.offsets.MonthEnd(0), end_ts)
        yield current.strftime("%Y-%m-%d"), chunk_end.strftime("%Y-%m-%d")
        current = chunk_end + pd.Timedelta(days=1)


def backfill_weather(start: str, end: str) -> None:
    print("--- Pobieranie danych pogodowych ---")
    df = WeatherApiClient().get_weather_for_date(start, end)
    if df.empty:
        raise RuntimeError(f"Brak danych pogodowych z API dla {start} – {end}")
    n = upsert_df(WeatherLoad, df)
    print(f"-> Zapisano/zaktualizowano {n} rekordów pogodowych.\n")


def backfill_kse(start: str, end: str) -> list[str]:
    print("--- Pobieranie danych PSE ---")
    client = PseApiClient()
    errors = []
    for chunk_start, chunk_end in month_chunks(start, end):
        print(f"Pobieranie KSE: {chunk_start} – {chunk_end}...")
        try:
            df = client.get_kse_load(chunk_start, chunk_end)
            if df.empty:
                errors.append(f"{chunk_start} – {chunk_end}: brak danych z PSE")
                continue
            n = upsert_df(KseLoad, df)
            print(f"-> Zapisano/zaktualizowano {n} rekordów KSE.")
        except Exception as e:
            print(f"[BŁĄD PSE] {chunk_start} – {chunk_end}: {e}")
            errors.append(f"{chunk_start} – {chunk_end}: {e}")
        finally:
            time.sleep(1)
    return errors


def run_backfill(start_date_str: str, end_date_str: str) -> None:
    print(f"Backfill: {start_date_str} – {end_date_str}")
    errors = []

    try:
        backfill_weather(start_date_str, end_date_str)
    except Exception as e:
        print(f"[BŁĄD POGODA] {e}")
        errors.append(f"pogoda: {e}")

    errors += backfill_kse(start_date_str, end_date_str)

    if errors:
        # zgłaszamy wyżej, żeby daily_update zalogował błąd zamiast "OK"
        raise RuntimeError("Backfill zakończony z błędami:\n" + "\n".join(errors))
    print("Backfill zakończony bez błędów.")


if __name__ == "__main__":
    run_backfill("2026-01-01", "2026-10-10")