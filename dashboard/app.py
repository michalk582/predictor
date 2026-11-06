import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import streamlit as st

from database.connection import engine

st.set_page_config(page_title="KSE Predictor", page_icon="⚡", layout="wide")


@st.cache_data(ttl=600)
def query(sql: str) -> pd.DataFrame:
    return pd.read_sql(sql, engine)

# --- Dane -------------------------------------------------------------------
latest = query("""
    SELECT dtime, load_model_prediction, temperature, model_version, forecast_made_at
    FROM predictions
    WHERE forecast_made_at = (SELECT MAX(forecast_made_at) FROM predictions)
    ORDER BY dtime
""")

history = query("""
    SELECT DISTINCT ON (p.dtime) p.dtime, p.load_model_prediction, k.load_actual
    FROM predictions p
    JOIN kse_load k ON k.dtime = p.dtime
    WHERE k.load_actual IS NOT NULL
      AND p.dtime >= NOW() - INTERVAL '14 days'
    ORDER BY p.dtime, p.forecast_made_at DESC
""")

metrics = query("""
    SELECT eval_date, model_version, mae, mape
    FROM model_metrics
    WHERE horizon_day = 1
    ORDER BY eval_date
""")

# --- Nagłówek i KPI ---------------------------------------------------------
st.title("⚡ Prognoza zapotrzebowania KSE")
st.caption("Automatyczny pipeline: dane PSE + prognoza pogody Open-Meteo → XGBoost → ocena dzień po dniu")

if latest.empty:
    st.warning("Brak prognoz w bazie.")
    st.stop()

last7 = metrics.tail(7)
prev7 = metrics.iloc[-14:-7]
mape7 = last7["mape"].mean() if not last7.empty else None
delta = (mape7 - prev7["mape"].mean()) if mape7 is not None and not prev7.empty else None

c1, c2, c3, c4 = st.columns(4)
c1.metric("Szczyt jutro", f"{latest['load_model_prediction'].max():,.0f} MW".replace(",", " "))
c2.metric(
    "MAPE (ostatnie 7 dni)",
    f"{mape7:.2f}%" if mape7 is not None else "–",
    f"{delta:+.2f} pp" if delta is not None else None,
    delta_color="inverse",
)
c3.metric("MAE (ostatnie 7 dni)", f"{last7['mae'].mean():,.0f} MW".replace(",", " ") if not last7.empty else "–")
c4.metric("Model", latest["model_version"].iloc[0])
st.caption(f"Ostatnia prognoza: {latest['forecast_made_at'].iloc[0]:%Y-%m-%d %H:%M}")

# --- Prognoza na jutro ------------------------------------------------------
target_day = latest["dtime"].iloc[0].date()
st.subheader(f"Prognoza na {target_day:%d.%m.%Y}")
st.line_chart(
    latest.set_index("dtime")[["load_model_prediction"]].rename(columns={"load_model_prediction": "Prognoza [MW]"})
)

# --- Prognoza vs rzeczywistość ---------------------------------------------
st.subheader("Prognoza vs rzeczywistość (ostatnie 14 dni)")
if history.empty:
    st.info("Brak ocenionych prognoz z ostatnich 14 dni.")
else:
    st.line_chart(
        history.set_index("dtime").rename(columns={
            "load_model_prediction": "Prognoza [MW]",
            "load_actual": "Rzeczywistość [MW]",
        })
    )

# --- Błąd w czasie ----------------------------------------------------------
st.subheader("Dzienny błąd prognozy (MAPE)")
if metrics.empty:
    st.info("Brak ocen modelu.")
else:
    st.bar_chart(metrics.set_index("eval_date")[["mape"]].rename(columns={"mape": "MAPE [%]"}))
    with st.expander("Szczegóły ocen"):
        st.dataframe(
            metrics.rename(columns={
                "eval_date": "Dzień", "model_version": "Model", "mae": "MAE [MW]", "mape": "MAPE [%]",
            }).round(2),
            hide_index=True,
            use_container_width=True,
        )