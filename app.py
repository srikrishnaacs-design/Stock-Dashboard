# app.py
import streamlit as st
import pandas as pd

from data_fetch.screener import get_screener_data
from data_fetch.yahoo import get_yahoo_data
from indicators.technicals import compute_trend
from scoring.model import compute_score
from alerts.engine import generate_alerts
from db.database import save_data, load_old

st.title("📊 Stock Intelligence Dashboard")

uploaded = st.file_uploader("Upload Excel", type=["xlsx"])

if uploaded:
    df = pd.read_excel(uploaded)

    results = []

    for symbol in df["Symbol"]:
        s = get_screener_data(symbol)
        y = get_yahoo_data(symbol)

        trend, trend_score = compute_trend(y["Close"], y["Volume"])

        row = {
            "Symbol": symbol,
            "CMP": y["CMP"],
            "52High": y["52High"],
            "52Low": y["52Low"],
            "PE": float(s["PE"] or 0),
            "PB": float(s["PB"] or 0),
            "ROE": float(s["ROE"] or 0),
            "ROCE": float(s["ROCE"] or 0),
            "OPM": float(s["OPM"] or 0),
            "MarketCap": float(s["MarketCap"] or 0),
            "Promoter": float(s["Promoter"] or 0),
            "Trend": trend,
            "TrendScore": trend_score,
            "Recommendation": y["Recommendation"]
        }

        results.append(row)

    final = pd.DataFrame(results)

    final["Score"] = final.apply(compute_score, axis=1)
    final["Alerts"] = final.apply(generate_alerts, axis=1)

    st.dataframe(final.sort_values("Score", ascending=False))

    save_data(final)
