import requests
import pandas as pd
from datetime import datetime

BASE = "https://api.open-meteo.com/v1/forecast"

# 天気アイコン
def icon(code):
    table = {
        0:"☀️", 1:"🌤", 2:"🌤", 3:"☁️",
        45:"🌫", 48:"🌫",
        51:"🌦", 53:"🌦", 55:"🌦",
        61:"🌧", 63:"🌧", 65:"🌧",
        71:"❄️", 73:"❄️", 75:"❄️",
        95:"⛈", 96:"⛈", 99:"⛈"
    }
    return table.get(code, "❓")

# 風向き（文字）
def wind_dir(deg):
    dirs = ["北","北北東","北東","東北東","東","東南東","南東","南南東",
            "南","南南西","南西","西南西","西","西北西","北西","北北西"]
    return dirs[int((deg+11.25)/22.5)%16]

# 風向き（コンパス矢印）
def wind_arrow(deg):
    arrows = {
        "北":"⬆️", "北北東":"↗️", "北東":"↗️", "東北東":"↗️",
        "東":"➡️", "東南東":"↘️", "南東":"↘️", "南南東":"↘️",
        "南":"⬇️", "南南西":"↙️", "南西":"↙️", "西南西":"↙️",
        "西":"⬅️", "西北西":"↖️", "北西":"↖️", "北北西":"↖️"
    }
    return arrows.get(wind_dir(deg), "❓")

# 14日予報
def get_weather(lat, lon):
    p = {
        "latitude": lat, "longitude": lon,
        "daily": [
            "weather_code","temperature_2m_max","temperature_2m_min",
            "precipitation_probability_max","wind_speed_10m_max",
            "sunrise","sunset"
        ],
        "forecast_days": 14, "timezone": "Asia/Tokyo"
    }
    d = requests.get(BASE, params=p).json()["daily"]
    return pd.DataFrame({
        "日付": d["time"],
        "天気": [icon(i) for i in d["weather_code"]],
        "最高気温": d["temperature_2m_max"],
        "最低気温": d["temperature_2m_min"],
        "降水確率": d["precipitation_probability_max"],
        "風速": d["wind_speed_10m_max"],
        "日の出": d["sunrise"],
        "日の入り": d["sunset"]
    })

# 24時間予報
def get_hourly(lat, lon):
    p = {
        "latitude": lat, "longitude": lon,
        "hourly": [
            "temperature_2m","relative_humidity_2m","precipitation",
            "weather_code","wind_speed_10m","wind_direction_10m"
        ],
        "forecast_days": 2, "timezone": "Asia/Tokyo"
    }
    h = requests.get(BASE, params=p).json()["hourly"]
    df = pd.DataFrame({
        "時刻": pd.to_datetime(h["time"]),
        "気温": h["temperature_2m"],
        "湿度": h["relative_humidity_2m"],
        "雨量": h["precipitation"],
        "天気": [icon(i) for i in h["weather_code"]],
        "風速": h["wind_speed_10m"],
        "風向": [wind_dir(d) for d in h["wind_direction_10m"]],
        "コンパス": [wind_arrow(d) for d in h["wind_direction_10m"]],
    })
    return df[df["時刻"] >= datetime.now()].head(24)

# 現在の天気
def get_current_weather(lat, lon, key):
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={key}&units=metric&lang=ja"
    d = requests.get(url).json()
    return {
        "現在気温": d["main"]["temp"],
        "体感温度": d["main"]["feels_like"],
        "現在天気": d["weather"][0]["description"],
        "湿度": d["main"]["humidity"],
        "風速": d["wind"]["speed"],
        "風向": wind_dir(d["wind"]["deg"]) if "deg" in d["wind"] else "不明",
        "コンパス": wind_arrow(d["wind"]["deg"]) if "deg" in d["wind"] else "❓"
    }

# 90日予報
def get_90days(lat, lon):
    p = {
        "latitude": lat, "longitude": lon,
        "daily": [
            "weather_code","temperature_2m_max","temperature_2m_min",
            "precipitation_probability_max","wind_speed_10m_max"
        ],
        "forecast_days": 90, "timezone": "Asia/Tokyo"
    }
    d = requests.get(BASE, params=p).json()["daily"]
    return pd.DataFrame({
        "日付": d["time"],
        "天気": [icon(i) for i in d["weather_code"]],
        "最高気温": d["temperature_2m_max"],
        "最低気温": d["temperature_2m_min"],
        "降水確率": d["precipitation_probability_max"],
        "風速": d["wind_speed_10m_max"],
    })

# ---------------------------------------------------------
# CSS（白い表示の不具合を完全修正）
# ---------------------------------------------------------
css = """
<style>

.main, body {
    background-color: #e9f2ff;
}

/* metric カード */
div[data-testid="metric-container"] {
    background-color: #ffffff;
    padding: 15px;
    border-radius: 12px;
    border: 1px solid #d0e3ff;
    box-shadow: 0px 2px 4px rgba(0,0,0,0.05);
}

/* info / success */
.stAlert {
    border-radius: 12px;
}

/* グラフ背景 */
.js-plotly-plot {
    background-color: #ffffff !important;
    border-radius: 12px;
    padding: 10px;
}

/* テーブル */
thead th {
    background-color: #d8e7ff !important;
    color: #003366 !important;
}

/* スマホ対応 */
@media (max-width: 768px) {
    .block-container {
        padding-left: 1rem;
        padding-right: 1rem;
    }
}

</style>
"""

st.markdown(css, unsafe_allow_html=True)
