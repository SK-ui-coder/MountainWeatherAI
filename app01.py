import os
import math
from datetime import datetime, timedelta

import requests
import streamlit as st
import pydeck as pdk
import gpxpy

# =========================
# 設定（APIキー直書き済み）
# =========================
API_KEY = "da865c8f1e19541afd9d604af0c3899"
BASE_URL_CURRENT = "https://api.openweathermap.org/data/2.5/weather"
BASE_URL_FORECAST = "https://api.openweathermap.org/data/2.5/forecast"
UNITS = "metric"
LANG = "ja"

# =========================
# 天気関連
# =========================
def fetch_current_weather(lat: float, lon: float) -> dict:
    params = {
        "lat": lat,
        "lon": lon,
        "appid": API_KEY,
        "units": UNITS,
        "lang": LANG,
    }
    r = requests.get(BASE_URL_CURRENT, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()
    if data.get("cod") != 200:
        raise ValueError(f"API error: {data.get('message', 'unknown')}")
    return data


def fetch_hourly_forecast(lat: float, lon: float) -> list:
    params = {
        "lat": lat,
        "lon": lon,
        "appid": API_KEY,
        "units": UNITS,
        "lang": LANG,
    }
    r = requests.get(BASE_URL_FORECAST, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()
    if data.get("cod") != "200":
        raise ValueError(f"API error: {data.get('message', 'unknown')}")
    return data.get("list", [])


def interpret_weather_for_hiking(current: dict, forecast_list: list) -> str:
    main = current.get("main", {})
    weather = current.get("weather", [{}])[0]
    wind = current.get("wind", {})

    temp = main.get("temp", 0)
    humidity = main.get("humidity", 0)
    wind_speed = wind.get("speed", 0)
    description = weather.get("description", "")
    wid = weather.get("id", 800)

    rain_flag = False
    strong_rain_flag = False
    for item in forecast_list[:8]:
        rain = item.get("rain", {})
        snow = item.get("snow", {})
        if rain.get("3h", 0) > 0 or snow.get("3h", 0) > 0:
            rain_flag = True
        if rain.get("3h", 0) >= 5:
            strong_rain_flag = True

    score = 0
    comment_parts = []

    if 5 <= temp <= 22:
        score += 2
        comment_parts.append("気温は登山に適した範囲です。")
    elif temp < 0:
        score -= 2
        comment_parts.append("気温が氷点下でかなり寒く、低体温症に注意が必要です。")
    elif temp > 28:
        score -= 2
        comment_parts.append("気温が高く、熱中症のリスクがあります。")

    if wind_speed < 5:
        score += 1
        comment_parts.append("風は弱めで歩きやすそうです。")
    elif 5 <= wind_speed < 10:
        comment_parts.append("やや風が強めですが、注意していれば問題ないレベルです。")
    else:
        score -= 2
        comment_parts.append("風がかなり強く、稜線歩きや露出した場所では危険です。")

    if strong_rain_flag:
        score -= 3
        comment_parts.append("今後強い雨が予想されており、登山は控えた方が安全です。")
    elif rain_flag:
        score -= 1
        comment_parts.append("今後雨の可能性があり、レインウェアや防水対策が必要です。")
    else:
        score += 1
        comment_parts.append("降水の予測は少なく、視界も比較的良さそうです。")

    if 200 <= wid < 300:
        score -= 4
        comment_parts.append("雷を伴う天候が予想されており、登山は非常に危険です。")
    elif 600 <= wid < 700:
        comment_parts.append("雪の可能性があり、足元と視界に注意が必要です。")

    if score >= 3:
        summary = "総合的に見て、条件は比較的良好で、計画通りの登山がしやすい天候です。"
        level = "◎ 登山日和"
    elif 0 <= score < 3:
        summary = "一部注意点はありますが、装備と計画を整えれば登山は可能なコンディションです。"
        level = "○ 注意しながら登山可能"
    elif -2 <= score < 0:
        summary = "リスク要因がいくつかあり、ルート短縮や時間帯の調整を検討した方が良さそうです。"
        level = "△ 条件やルートを慎重に選ぶべき状況"
    else:
        summary = "天候条件が悪く、無理な登山は避けるべき状況です。"
        level = "× 登山は推奨されない"

    return f"{level}\n\n" + "\n".join(comment_parts) + "\n\n" + summary


def draw_wind_compass(wind_deg: float):
    dirs = [
        (0, "北"),
        (45, "北東"),
        (90, "東"),
        (135, "南東"),
        (180, "南"),
        (225, "南西"),
        (270, "西"),
        (315, "北西"),
        (360, "北"),
    ]
    closest = min(dirs, key=lambda d: abs(wind_deg - d[0]))
    return closest[1]


# =========================
# 難易度判定
# =========================
def evaluate_mountain_difficulty(distance_km, elevation_gain_m, max_altitude_m, current_weather):
    main = current_weather.get("main", {})
    wind = current_weather.get("wind", {})
    temp = main.get("temp", 10)
    wind_speed = wind.get("speed", 3)

    score = 0
    comment = []

    if distance_km < 5:
        score += 1
        comment.append("歩行距離は短めで負荷は軽めです。")
    elif distance_km > 12:
        score -= 1
        comment.append("歩行距離が長く、持久力が求められます。")

    if elevation_gain_m < 500:
        score += 1
        comment.append("累積標高は控えめです。")
    elif elevation_gain_m > 1200:
        score -= 1
        comment.append("累積標高が大きく、負荷が高いです。")

    if max_altitude_m > 2500:
        score -= 1
        comment.append("高標高域での行動となり、気象変化に注意が必要です。")

    if wind_speed > 10:
        score -= 1
        comment.append("風が強く、難易度が上がります。")

    if temp < 0 or temp > 28:
        score -= 1
        comment.append("気温条件が厳しいです。")

    if score >= 2:
        level = "初級（初心者向け）"
    elif 0 <= score < 2:
        level = "中級（一般登山者向け）"
    else:
        level = "上級（経験者向け）"

    return f"{level}\n\n" + "\n".join(comment)


# =========================
# 装備提案
# =========================
def suggest_equipment(temp, wind_speed, rain_expected, snow_expected, season):
    items = [
        "地図・コンパス（またはGPS）",
        "ヘッドランプ",
        "ファーストエイドキット",
        "非常食・行動食",
        "レインウェア（上下）",
    ]

    if temp < 5:
        items += ["フリース", "ダウンジャケット", "厚手の手袋"]
    if temp > 25:
        items += ["速乾ウェア", "帽子", "多めの水分"]

    if wind_speed > 8:
        items.append("防風シェル")

    if rain_expected:
        items += ["防水登山靴", "ザックカバー"]
    if snow_expected:
        items += ["防寒グローブ", "ゲイター"]

    if season == "夏":
        items.append("虫除け・日焼け止め")
    if season == "冬":
        items.append("アイゼン（必要なら）")

    return list(dict.fromkeys(items))


# =========================
# GPX
# =========================
def parse_gpx(file):
    gpx = gpxpy.parse(file)
    points = []
    for track in gpx.tracks:
        for segment in track.segments:
            for p in segment.points:
                points.append((p.latitude, p.longitude))
    return points


# =========================
# Streamlit UI
# =========================
def main():
    st.set_page_config(page_title="登山計画アプリ", page_icon="🏔", layout="wide")
    st.title("🏔 登山計画アプリ（完全版）")

    st.sidebar.header("山の情報")
    mountain_name = st.sidebar.text_input("山の名前", "テスト山")
    lat = st.sidebar.number_input("緯度", value=35.0)
    lon = st.sidebar.number_input("経度", value=135.0)
    distance_km = st.sidebar.number_input("歩行距離 (km)", value=8.0)
    elevation_gain_m = st.sidebar.number_input("累積標高 (m)", value=800.0)
    max_altitude_m = st.sidebar.number_input("最高標高 (m)", value=1500.0)
    season = st.sidebar.selectbox("季節", ["春", "夏", "秋", "冬"])

    gpx_file = st.sidebar.file_uploader("GPXファイル", type=["gpx"])

    st.markdown("### 1. 天気情報")

    try:
        current = fetch_current_weather(lat, lon)
        forecast_list = fetch_hourly_forecast(lat, lon)
    except Exception as e:
        st.error(f"天気情報の取得に失敗しました: {e}")
        return

    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("現在の天気")
        weather = current["weather"][0]
        main = current["main"]
        wind = current["wind"]

        st.write(f"天気: {weather['description']}")
        st.write(f"気温: {main['temp']} ℃")
        st.write(f"体感温度: {main['feels_like']} ℃")
        st.write(f"湿度: {main['humidity']} %")
        st.write(f"風速: {wind['speed']} m/s")

    with col2:
        st.subheader("風向き")
        wind_deg = current["wind"].get("deg", 0)
        st.write(f"{draw_wind_compass(wind_deg)}（{wind_deg}°）")

    with col3:
        st.subheader("AIコメント")
        st.write(interpret_weather_for_hiking(current, forecast_list))

    st.markdown("---")
    st.markdown("### 2. 難易度判定")
    st.write(
        evaluate_mountain_difficulty(
            distance_km, elevation_gain_m, max_altitude_m, current
        )
    )

    st.markdown("---")
    st.markdown("### 3. 装備提案")

    rain_expected = any(item.get("rain", {}).get("3h", 0) > 0 for item in forecast_list[:8])
    snow_expected = any(item.get("snow", {}).get("3h", 0) > 0 for item in forecast_list[:8])

    temp = current["main"]["temp"]
    wind_speed = current["wind"]["speed"]

    for item in suggest_equipment(temp, wind_speed, rain_expected, snow_expected, season):
        st.write(f"- {item}")

    st.markdown("---")
    st.markdown("### 4. GPXルート表示")

    if gpx_file:
        try:
            points = parse_gpx(gpx_file)
            if points:
                mid_lat = sum(p[0] for p in points) / len(points)
                mid_lon = sum(p[1] for p in points) / len(points)

                layer = pdk.Layer(
                    "PathLayer",
                    data=[{"path": [[lon, lat] for lat, lon in points]}],
                    get_color=[0, 100, 255],
                    width_scale=10,
                    width_min_pixels=3,
                )

                view_state = pdk.ViewState(
                    latitude=mid_lat,
                    longitude=mid_lon,
                    zoom=12,
                    pitch=45,
                )

                st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view_state))
            else:
                st.info("GPXからルートが取得できませんでした。")
        except Exception as e:
            st.error(f"GPX解析に失敗しました: {e}")
    else:
        st.info("GPXファイルをアップロードするとルートが表示されます。")


if __name__ == "__main__":
    main()
