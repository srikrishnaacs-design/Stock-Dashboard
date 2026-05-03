import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import yfinance as yf
import ta
import time
import random

st.set_page_config(layout="wide")
st.title("📊 Stock Intelligence Dashboard")

# --- Screener Data ---
def get_screener_data(symbol):
    url = f"https://www.screener.in/company/{symbol}/"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")

        data = {}

        # Extract ALL ratios safely
        for li in soup.select("ul#top-ratios li"):
            try:
                name = li.select_one("span.name").text.strip()
                value = li.select_one("span.number").text.strip()
                data[name] = value
            except:
                continue

        return {
            "PE": data.get("Stock P/E"),
            "PB": data.get("Price to book value"),
            "ROE": data.get("Return on equity"),
            "ROCE": data.get("Return on capital employed"),
            "OPM": data.get("Operating profit margin"),
            "MarketCap": data.get("Market Cap"),
            "Promoter": data.get("Promoter holding"),
        }

    except:
        return {
            "PE": None,
            "PB": None,
            "ROE": None,
            "ROCE": None,
            "OPM": None,
            "MarketCap": None,
            "Promoter": None,
        }
# --- Yahoo Data ---
def get_yahoo_data(symbol):
    ticker = yf.Ticker(symbol + ".NS")
    info = ticker.info
    hist = ticker.history(period="6mo")

    return {
        "CMP": info.get("currentPrice"),
        "52High": info.get("fiftyTwoWeekHigh"),
        "52Low": info.get("fiftyTwoWeekLow"),
        "Recommendation": info.get("recommendationKey"),
        "Close": hist["Close"],
        "Volume": hist["Volume"]
    }

# --- Trend ---
def compute_trend(close, volume):
    df = pd.DataFrame({"close": close, "volume": volume})

    df["ema50"] = ta.trend.ema_indicator(df["close"], 50)
    df["ema200"] = ta.trend.ema_indicator(df["close"], 200)
    df["rsi"] = ta.momentum.rsi(df["close"], 14)
    df["vol_avg"] = df["volume"].rolling(20).mean()

    latest = df.iloc[-1]
    score = 0

    if latest["close"] > latest["ema50"] > latest["ema200"]:
        score += 40

    if 50 < latest["rsi"] < 70:
        score += 30

    if latest["volume"] > latest["vol_avg"]:
        score += 30

    if score > 70:
        return "Strong Uptrend", score
    elif score > 55:
        return "Weak Uptrend", score
    elif score > 40:
        return "Sideways", score
    else:
        return "Downtrend", score

# --- Upload ---
uploaded = st.file_uploader("Upload Excel (Column name must be 'Symbol')", type=["xlsx"])

if uploaded:
    df = pd.read_excel(uploaded)

    results = []

    for symbol in df["Symbol"]:
        import time,random
        time.sleep(random.uniform(1, 2))
    
    try:
        s = get_screener_data(symbol)
        y = get_yahoo_data(symbol)
    
        trend, trend_score = compute_trend(y["Close"], y["Volume"])
    
        results.append({
            "Symbol": symbol,
            "CMP": y["CMP"],
            "52W High": y["52High"],
            "52W Low": y["52Low"],
            "PE": s["PE"],
            "PB": s["PB"],
            "ROE": s["ROE"],
            "ROCE": s["ROCE"],
            "OPM": s["OPM"],
            "Market Cap": s["MarketCap"],
            "Promoter %": s["Promoter"],
            "Trend": trend,
            "Trend Score": trend_score,
            "Recommendation": y["Recommendation"]
        })
    
    except Exception as e:
        st.warning(f"{symbol} failed")

    final = pd.DataFrame(results)

    # --- Scoring ---
    def compute_score(row):
        score = 0

        try:
            score += (row["Trend Score"] / 100) * 15
        except:
            pass

        try:
            if row["ROE"]:
                score += min(float(str(row["ROE"]).replace('%','')), 25) / 25 * 10
        except:
            pass

        try:
            if row["ROCE"]:
                score += min(float(str(row["ROCE"]).replace('%','')), 30) / 30 * 20
        except:
            pass

        try:
            if row["PE"] and row["Industry PE"] and row["PE"] < row["Industry PE"]:
                score += 15
        except:
            pass

        return round(score, 2)

    final["Score"] = final.apply(compute_score, axis=1)

    # --- Alerts ---
    def generate_alerts(row):
        alerts = []

        try:
            if row["PE"] < row["Industry PE"]:
                alerts.append("Undervalued")
            else:
                alerts.append("Overvalued")
        except:
            pass

        try:
            if row["CMP"] > 0.9 * row["52W High"]:
                alerts.append("Near High")

            if row["CMP"] < 0.5 * row["52W High"]:
                alerts.append("Deep Value")
        except:
            pass

        if "Uptrend" in row["Trend"]:
            alerts.append("Bullish")

        if "Downtrend" in row["Trend"]:
            alerts.append("Bearish")

        try:
            if float(str(row["ROCE"]).replace('%','')) > 20:
                alerts.append("High ROCE")

            if float(str(row["ROE"]).replace('%','')) > 15:
                alerts.append("Strong ROE")
        except:
            pass

        return ", ".join(alerts)

    final["Alerts"] = final.apply(generate_alerts, axis=1)

    # --- Filter ---
    min_score = st.slider("Minimum Score", 0, 100, 0)
    filtered = final[final["Score"] >= min_score]

    st.write(f"Showing {len(filtered)} stocks")

    # --- Top 5 ---
    st.subheader("🏆 Top Stocks")
    st.dataframe(filtered.sort_values("Score", ascending=False).head(5))

    # --- Full Table ---
    st.subheader("📊 Full Dashboard")
    st.dataframe(filtered.sort_values("Score", ascending=False))
