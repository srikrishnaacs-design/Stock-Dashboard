import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import yfinance as yf
import ta

st.title("📊 Stock Dashboard")

# --- Screener Data ---
def get_screener_data(symbol):
    url = f"https://www.screener.in/company/{symbol}/"
    r = requests.get(url)
    soup = BeautifulSoup(r.text, "html.parser")

    def extract(label):
        try:
            return soup.find("td", string=label).find_next_sibling("td").text.strip()
        except:
            return None

    return {
        "PE": extract("Stock P/E"),
        "PB": extract("Price to book value"),
        "ROE": extract("Return on equity"),
        "ROCE": extract("Return on capital employed"),
        "OPM": extract("Operating profit margin"),
        "MarketCap": extract("Market Cap"),
        "Promoter": extract("Promoter holding"),
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
uploaded = st.file_uploader("Upload Excel", type=["xlsx"])

if uploaded:
    df = pd.read_excel(uploaded)

    results = []

    for symbol in df["Symbol"]:
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
        except:
            st.warning(f"Error fetching {symbol}")

    final = pd.DataFrame(results)

    st.dataframe(final)
