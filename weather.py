import requests
import pandas as pd

BASE_URL = "https://api.open-meteo.com/v1/forecast"


def weather_icon(code):

    if code == 0:
        return "☀️"

    elif code in [1,2]:
        return "🌤"

    elif code == 3:
        return "☁️"

    elif code in [45,48]:
        return "🌫"

    elif code in [51,53,55]:
        return "🌦"

    elif code in [61,63,65]:
        return "🌧"

    elif code in [71,73,75]:
        return "❄️"

    elif code in [95,96,99]:
        return "⛈"

    return "❓"


def get_weather(lat,lon):

    params={

        "latitude":lat,
        "longitude":lon,

        "daily":[

    "weather_code",
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_probability_max",
    "wind_speed_10m_max",
    "sunrise",
    "sunset"

],

        "forecast_days":14,

        "timezone":"Asia/Tokyo"

    }

    response=requests.get(BASE_URL,params=params)

    response.raise_for_status()

    data=response.json()

    daily=data["daily"]

    df = pd.DataFrame({

    "日付": daily["time"],

    "天気": [weather_icon(i) for i in daily["weather_code"]],

    "最高気温": daily["temperature_2m_max"],

    "最低気温": daily["temperature_2m_min"],

    "降水確率": daily["precipitation_probability_max"],

    "風速": daily["wind_speed_10m_max"],

    "日の出": daily["sunrise"],

    "日の入り": daily["sunset"]

})

    return df