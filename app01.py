import requests
import pandas as pd

api_key = st.secrets["OPENWEATHER_KEY"]
current = get_current_weather(lat, lon, api_key)

st.subheader("⛅ 現在の天気（OpenWeatherMap）")

c1, c2, c3 = st.columns(3)

c1.metric("現在の気温", f"{current['現在気温']}℃")
c2.metric("体感温度", f"{current['体感温度']}℃")
c3.metric("湿度", f"{current['湿度']}%")

c4, c5 = st.columns(2)
c4.metric("現在の天気", current["現在天気"])
c5.metric("風速（現在）", f"{current['風速']} m/s")


# ---------------------------------------------------------
# ① Open-Meteo（14日予報）
# ---------------------------------------------------------
def get_weather(lat, lon):
    url = (
        "https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}"
        "&daily=temperature_2m_max,temperature_2m_min,"
        "precipitation_probability_max,windspeed_10m_max,"
        "sunrise,sunset,weathercode"
        "&timezone=Asia/Tokyo"
    )

    res = requests.get(url)
    data = res.json()

    df = pd.DataFrame({
        "日付": data["daily"]["time"],
        "最高気温": data["daily"]["temperature_2m_max"],
        "最低気温": data["daily"]["temperature_2m_min"],
        "降水確率": data["daily"]["precipitation_probability_max"],
        "風速": data["daily"]["windspeed_10m_max"],
        "日の出": data["daily"]["sunrise"],
        "日の入り": data["daily"]["sunset"],
        "天気コード": data["daily"]["weathercode"],
    })

    df["天気"] = df["天気コード"].apply(weather_code_to_text)

    return df


def weather_code_to_text(code):
    mapping = {
        0: "快晴",
        1: "晴れ",
        2: "薄曇り",
        3: "曇り",
        45: "霧",
        48: "霧（着氷）",
        51: "霧雨（弱）",
        53: "霧雨（中）",
        55: "霧雨（強）",
        61: "雨（弱）",
        63: "雨（中）",
        65: "雨（強）",
        71: "雪（弱）",
        73: "雪（中）",
        75: "雪（強）",
        80: "にわか雨（弱）",
        81: "にわか雨（中）",
        82: "にわか雨（強）",
    }
    return mapping.get(code, "不明")


# ---------------------------------------------------------
# ② OpenWeatherMap（現在の天気）
# ---------------------------------------------------------
def get_current_weather(lat, lon, api_key):
    url = (
        f"https://api.openweathermap.org/data/2.5/weather"
        f"?lat={lat}&lon={lon}&appid={api_key}&units=metric&lang=ja"
    )

    res = requests.get(url)
    data = res.json()

    current = {
        "現在気温": data["main"]["temp"],
        "体感温度": data["main"]["feels_like"],
        "現在天気": data["weather"][0]["description"],
        "湿度": data["main"]["humidity"],
        "風速": data["wind"]["speed"],
    }

    return current

