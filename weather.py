import requests
import pandas as pd

BASE_URL = "https://api.open-meteo.com/v1/forecast"

WEATHER_INFO = {
    0: ("☀️", "快晴"),
    1: ("🌤️", "晴れ"),
    2: ("⛅", "晴れ時々曇り"),
    3: ("☁️", "曇り"),
    45: ("🌫️", "霧"),
    48: ("🌫️", "霧"),
    51: ("🌦️", "弱い霧雨"),
    53: ("🌦️", "霧雨"),
    55: ("🌦️", "強い霧雨"),
    56: ("🌧️", "弱い着氷性霧雨"),
    57: ("🌧️", "強い着氷性霧雨"),
    61: ("🌧️", "弱い雨"),
    63: ("🌧️", "雨"),
    65: ("🌧️", "強い雨"),
    66: ("🌧️", "弱い着氷性の雨"),
    67: ("🌧️", "強い着氷性の雨"),
    71: ("❄️", "弱い雪"),
    73: ("❄️", "雪"),
    75: ("❄️", "強い雪"),
    77: ("🌨️", "雪あられ"),
    80: ("🌦️", "弱いにわか雨"),
    81: ("🌦️", "にわか雨"),
    82: ("🌧️", "強いにわか雨"),
    85: ("🌨️", "弱いにわか雪"),
    86: ("🌨️", "強いにわか雪"),
    95: ("⛈️", "雷雨"),
    96: ("⛈️", "雷雨＋ひょう"),
    99: ("⛈️", "強い雷雨＋ひょう"),
}

def weather_info(code):
    try:
        code = int(code)
    except (TypeError, ValueError):
        return "🌥️", "天気不明"
    return WEATHER_INFO.get(code, ("🌥️", "天気不明"))

def weather_icon(code):
    return weather_info(code)[0]

def weather_text(code):
    return weather_info(code)[1]

def weather_category(code):
    try:
        code = int(code)
    except (TypeError, ValueError):
        return "不明"
    if code in [0, 1, 2]:
        return "晴れ"
    if code == 3:
        return "曇り"
    if code in [45, 48]:
        return "霧"
    if code in [51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82]:
        return "雨"
    if code in [71, 73, 75, 77, 85, 86]:
        return "雪"
    if code in [95, 96, 99]:
        return "雷雨"
    return "不明"

def _representative_codes(times, codes):
    records = []
    for t, c in zip(times, codes):
        try:
            records.append((pd.to_datetime(t), c))
        except Exception:
            pass
    if not records:
        return []
    periods = [(5, 10), (10, 14), (14, 18), (18, 24)]
    result = []
    for start, end in periods:
        candidates = [(ts, c) for ts, c in records if start <= ts.hour < end]
        if candidates:
            result.append(candidates[-1][1])
    return result

def daily_weather_summary(times, codes):
    reps = _representative_codes(times, codes)
    if not reps:
        return "天気不明"
    cats = [weather_category(c) for c in reps]
    valid = [c for c in cats if c != "不明"]
    if not valid:
        return "天気不明"
    changed = []
    for cat in valid:
        if not changed or changed[-1] != cat:
            changed.append(cat)
    if len(changed) == 1:
        return weather_text(reps[0])
    return f"{changed[0]}のち{changed[-1]}"

def daily_weather_icon(times, codes):
    reps = _representative_codes(times, codes)
    icons = []
    cats = []
    for code in reps:
        cat = weather_category(code)
        if cat == "不明":
            continue
        if not cats or cats[-1] != cat:
            cats.append(cat)
            icons.append(weather_icon(code))
    return "→".join(icons[:3]) if icons else "🌥️"

def get_weather(lat, lon):
    params = {
        "latitude": lat, "longitude": lon,
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,wind_speed_10m_max,sunrise,sunset",
        "forecast_days": 14, "timezone": "Asia/Tokyo"
    }
    response = requests.get(BASE_URL, params=params, timeout=20)
    response.raise_for_status()
    daily = response.json()["daily"]
    return pd.DataFrame({
        "日付": daily["time"],
        "天気": [weather_icon(i) for i in daily["weather_code"]],
        "天気詳細": [weather_text(i) for i in daily["weather_code"]],
        "最高気温": daily["temperature_2m_max"],
        "最低気温": daily["temperature_2m_min"],
        "降水確率": daily["precipitation_probability_max"],
        "風速": daily["wind_speed_10m_max"],
        "日の出": daily["sunrise"],
        "日の入り": daily["sunset"]
    })

def get_hourly(lat, lon):
    params = {
        "latitude": lat, "longitude": lon,
        "hourly": "temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m,wind_direction_10m",
        "forecast_days": 2, "timezone": "Asia/Tokyo"
    }
    res = requests.get(BASE_URL, params=params, timeout=20)
    res.raise_for_status()
    hourly = res.json()["hourly"]
    df = pd.DataFrame({
        "時刻": pd.to_datetime(hourly["time"]),
        "気温": hourly["temperature_2m"],
        "湿度": hourly["relative_humidity_2m"],
        "雨量": hourly["precipitation"],
        "天気": [weather_icon(i) for i in hourly["weather_code"]],
        "天気詳細": [weather_text(i) for i in hourly["weather_code"]],
        "天気分類": [weather_category(i) for i in hourly["weather_code"]],
        "風速": hourly["wind_speed_10m"],
        "風向": [wind_direction(d) for d in hourly["wind_direction_10m"]],
        "風向度": hourly["wind_direction_10m"],
    })
    now = pd.Timestamp.now(tz="Asia/Tokyo").tz_localize(None)
    return df[df["時刻"] >= now].head(24).reset_index(drop=True)

def get_today_weather_summary(lat, lon):
    params = {
        "latitude": lat, "longitude": lon,
        "hourly": "weather_code", "forecast_days": 1,
        "timezone": "Asia/Tokyo"
    }
    res = requests.get(BASE_URL, params=params, timeout=20)
    res.raise_for_status()
    hourly = res.json()["hourly"]
    return {
        "天気": daily_weather_summary(hourly["time"], hourly["weather_code"]),
        "アイコン": daily_weather_icon(hourly["time"], hourly["weather_code"]),
    }

def wind_direction(deg):
    dirs = ["北", "北北東", "北東", "東北東", "東", "東南東", "南東", "南南東",
            "南", "南南西", "南西", "西南西", "西", "西北西", "北西", "北北西"]
    try:
        return dirs[int((float(deg) + 11.25) / 22.5) % 16]
    except (TypeError, ValueError):
        return "不明"

def get_current_weather(lat, lon, api_key):
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric&lang=ja"
    res = requests.get(url, timeout=20)
    res.raise_for_status()
    data = res.json()
    return {
        "現在気温": data["main"]["temp"],
        "体感温度": data["main"]["feels_like"],
        "現在天気": data["weather"][0]["description"],
        "湿度": data["main"]["humidity"],
        "風速": data["wind"]["speed"],
        "風向": wind_direction(data["wind"]["deg"]) if "deg" in data["wind"] else "不明",
    }

def get_90days(lat, lon):
    params = {
        "latitude": lat, "longitude": lon,
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,wind_speed_10m_max",
        "forecast_days": 90, "timezone": "Asia/Tokyo"
    }
    res = requests.get(BASE_URL, params=params, timeout=20)
    res.raise_for_status()
    daily = res.json()["daily"]
    return pd.DataFrame({
        "日付": daily["time"],
        "天気": [weather_icon(i) for i in daily["weather_code"]],
        "天気詳細": [weather_text(i) for i in daily["weather_code"]],
        "最高気温": daily["temperature_2m_max"],
        "最低気温": daily["temperature_2m_min"],
        "降水確率": daily["precipitation_probability_max"],
        "風速": daily["wind_speed_10m_max"],
    })


# =========================================================
# 14日予報：時間別データから「晴れのち曇り」等を作成
# =========================================================
def get_14day_weather_change(lat, lon):
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "weather_code",
        "forecast_days": 14,
        "timezone": "Asia/Tokyo"
    }

    res = requests.get(BASE_URL, params=params, timeout=20)
    res.raise_for_status()
    hourly = res.json()["hourly"]

    df = pd.DataFrame({
        "日時": pd.to_datetime(hourly["time"]),
        "weather_code": hourly["weather_code"]
    })

    df["日付"] = df["日時"].dt.strftime("%Y-%m-%d")

    rows = []
    for date, group in df.groupby("日付", sort=True):
        times = group["日時"].dt.strftime("%Y-%m-%dT%H:%M").tolist()
        codes = group["weather_code"].tolist()

        reps = _representative_codes(times, codes)
        summary = daily_weather_summary(times, codes)
        icons = daily_weather_icon(times, codes)

        # 代表コードから、その日の「メイン天気」を取得
        valid_codes = [c for c in reps if weather_category(c) != "不明"]
        main_code = valid_codes[0] if valid_codes else 3

        rows.append({
            "日付": date,
            "天気": icons,
            "天気詳細": summary,
            "天気コード": main_code,
        })

    return pd.DataFrame(rows)
