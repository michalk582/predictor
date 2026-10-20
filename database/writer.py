import pandas as pd
from sqlalchemy.dialects.postgresql import insert
from database.connection import engine

BATCH_SIZE = 5000  # Postgres ma limit ~65k parametrów na jedno zapytanie


def upsert_df(model, df: pd.DataFrame, key: str = "dtime") -> int:
    """Zapisuje DataFrame do tabeli. Wiersze o istniejącym kluczu są aktualizowane."""
    if df.empty:
        return 0

    table_cols = [c.name for c in model.__table__.columns]
    data = df[[c for c in table_cols if c in df.columns]]
    data = data.astype(object).where(data.notna(), None)   # NaN -> NULL
    rows = data.to_dict(orient="records")

    with engine.begin() as conn:
        for i in range(0, len(rows), BATCH_SIZE):
            batch = rows[i:i + BATCH_SIZE]
            stmt = insert(model).values(batch)
            update_cols = {c: stmt.excluded[c] for c in batch[0] if c != key}
            stmt = stmt.on_conflict_do_update(index_elements=[key], set_=update_cols)
            conn.execute(stmt)
    return len(rows)