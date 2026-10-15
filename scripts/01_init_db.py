import os
import sys

# Najpierw dodajemy ścieżkę (to uczy Pythona, gdzie jest główny folder)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import engine
from database.models import Base

def init_db():
    print("Connecting with PostgreSQL...")
    Base.metadata.create_all(engine)
    print("Done.")

if __name__ == "__main__":
    init_db()
