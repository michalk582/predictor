import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from datetime import date, timedelta

from sqlalchemy import text

from database.connection import engine
from scripts.run_backfill import run_backfill
from scripts.evaluate import run_evaluation
from scripts.predict_future import run_prediction

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("daily_update")

MAX_CATCHUP_DAYS = 60  # bezpiecznik: nie pobieraj więcej naraz


def get_last_date(table: str) -> date | None:
    with engine.connect() as conn:
        last = conn.execute(text(f"SELECT MAX(dtime) FROM {table}")).scalar()
    return last.date() if last else None


def update_data() -> None:
    yesterday = date.today() - timedelta(days=1)

    last_dates = [get_last_date(t) for t in ("kse_load", "weather_load")]
    last_dates = [d for d in last_dates if d is not None]
    if not last_dates:
        raise RuntimeError("Baza jest pusta. Najpierw uruchom run_backfill dla pełnego zakresu.")

    # od najstarszej z ostatnich dat (ten dzień mógł być niepełny)
    start = min(last_dates)
    start = max(start, yesterday - timedelta(days=MAX_CATCHUP_DAYS))

    if start > yesterday:
        log.info("Dane są aktualne.")
        return

    log.info(f"Pobieram dane: {start} – {yesterday}")
    run_backfill(start.strftime("%Y-%m-%d"), yesterday.strftime("%Y-%m-%d"))


def main() -> None:
    steps = [
        ("Aktualizacja danych", update_data),
        ("Ocena prognoz", run_evaluation),
        ("Nowa prognoza", run_prediction),
    ]
    for name, step in steps:
        log.info(f"Start: {name}")
        try:
            step()
            log.info(f"OK: {name}")
        except Exception:
            log.exception(f"Błąd: {name}")
            if name == "Aktualizacja danych":
                continue  # bez nowych danych nadal robimy ocenę i prognozę
            raise


if __name__ == "__main__":
    main()