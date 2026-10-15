import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import SessionLocal
from database.models import KseLoad, WeatherLoad

def clean_database():
    print("Czyszczenie tabeli...")
    session = SessionLocal()
    try:
        session.query(WeatherLoad).delete()
        session.query(KseLoad).delete()

        session.commit()
        print("Usunięto pomyślnie")
    except Exception as e:
        session.rollback()
        print(f"Wystąpił błąd: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    confirm = input("Are you sure you want to delete all records from database?")
    if confirm.lower() == 'yes' or confirm.lower() == 'tak':
        clean_database()
    else:
        print("Operation cancelled")


