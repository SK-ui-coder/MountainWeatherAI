import os
import math
from datetime import datetime, timedelta

import requests
import streamlit as st
import pydeck as pdk
import gpxpy

# =========================
# 設定
# =========================
API_KEY = os.getenv("OPENWEATHER_API_KEY", "YOUR_API_KEY_HERE")  # ←必要なら直書き
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
    """
    登山向けの簡易AIコメント
    気温・降水・風速・天気コードなどから総合コメントを生成
    """
    main = current.get("main", {})
    weather = current.get("weather", [{}])[0]
    wind = current.get("wind", {})

    temp = main.get("temp", 0)
    humidity = main.get("humidity", 0)
    wind_speed = wind.get("speed", 0)
    description = weather.get("description", "")
    wid = weather.get("id", 800)

    # 降水の有無（直近数時間）
    rain_flag = False
    strong_rain_flag = False
    for item in forecast_list[:8]:  # 約24時間分
        rain = item.get("rain", {})
        snow = item.get("snow", {})
        if rain.get("3h", 0) > 0 or snow.get("3h", 0) > 0:
            rain_flag = True
        if rain.get("3h", 0) >= 5:
            strong_rain_flag = True

    score = 0
    comment_parts = []

    # 気温評価
    if 5 <= temp <= 22:
        score += 2
        comment_parts.append("気温は登山に適した範囲です。")
    elif temp < 0:
        score -= 2
        comment_parts.append("気温が氷点下でかなり寒く、低体温症に注意が必要です。")
    elif temp > 28:
        score -= 2
        comment_parts.append("気温が高く、熱中症のリスクがあります。")

    # 風速評価
    if wind_speed < 5:
        score += 1
        comment_parts.append("風は弱めで歩きやすそうです。")
    elif 5 <= wind_speed < 10:
        comment_parts.append("やや風が強めですが、注意していれば問題ないレベルです。")
    else:
        score -= 2
        comment_parts.append("風がかなり強く、稜線歩きや露出した場所では危険です。")

    # 降水評価
    if strong_rain_flag:
        score -= 3
        comment_parts.append("今後強い雨が予想されており、登山は控えた方が安全です。")
    elif rain_flag:
        score -= 1
        comment_parts.append("今後雨の可能性があり、レインウェアや防水対策が必要です。")
    else:
        score += 1
        comment_parts.append("降水の予測は少なく、視界も比較的良さそうです。")

    # 天気コード評価（雷・嵐など）
    if 200 <= wid < 300:
        score -= 4
        comment_parts.append("雷を伴う天候が予想されており、登山は非常に危険です。")
    elif 600 <= wid < 700:
        comment_parts.append("雪の可能性があり、足元と視界に注意が必要です。")

    # 総合評価
    if score >= 3:
        summary = "総合的に見て、条件は比較的良好で、計画通りの登山がしやすい天候です。"
        level = "◎ 登山日和（ただし基本的な安全対策は必須）"
    elif 0 <= score < 3:
        summary = "一部注意点はありますが、装備と計画を整えれば登山は可能なコンディションです。"
        level = "○ 注意しながら登山可能"
    elif -2 <= score < 0:
        summary = "リスク要因がいくつかあり、ルート短縮や時間帯の調整を検討した方が良さそうです。"
        level = "△ 条件やルートを慎重に選ぶべき状況"
    else:
        summary = "天候条件が悪く、無理な登山は避けるべき状況です。別日に変更することを強く推奨します。"
        level = "× 登山は推奨されないコンディション"

    return f"{level}\n\n" + "\n".join(comment_parts) + "\n\n" + summary


def draw_wind_compass(wind_deg: float):
    """
    風向きを円形コンパスで表示するための簡易図形データを返す。
    Streamlit では pydeck ではなく、単純にテキスト＋絵で代用する。
    ここでは方位文字列だけ返す。
    """
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
    # 最も近い方位を選ぶ
    closest = min(dirs, key=lambda d: abs(wind_deg - d[0]))
    return closest[1]


# =========================
# 難易度・危険度関連
# =========================
def evaluate_mountain_difficulty(
    distance_km: float,
    elevation_gain_m: float,
    max_altitude_m: float,
    current_weather: dict,
) -> str:
    """
    山の難易度をざっくりAI風に判定する。
    距離・累積標高・最高標高・天候から「初級 / 中級 / 上級」を返す。
    """
    main = current_weather.get("main", {})
    wind = current_weather.get("wind", {})
    temp = main.get("temp", 10)
    wind_speed = wind.get("speed", 3)

    score = 0
    comment = []

    # 距離
    if distance_km < 5:
        score += 1
        comment.append("歩行距離は短めで、体力的な負荷は比較的軽めです。")
    elif 5 <= distance_km <= 12:
        score += 0
        comment.append("歩行距離は一般的な日帰り登山レベルです。")
    else:
        score -= 1
        comment.append("歩行距離が長く、持久力と計画性が求められます。")

    # 累積標高
    if elevation_gain_m < 500:
        score += 1
        comment.append("累積標高は控えめで、登りの負荷はそれほど大きくありません。")
    elif 500 <= elevation_gain_m <= 1200:
        score += 0
        comment.append("累積標高は一般的な登山レベルで、適度な負荷があります。")
    else:
        score -= 1
        comment.append("累積標高が大きく、登り下りともにハードな行程です。")

    # 最高標高
    if max_altitude_m < 1500:
        comment.append("標高はそれほど高くなく、高山病のリスクは低めです。")
    elif 1500 <= max_altitude_m <= 2500:
        comment.append("中程度の標高で、気温低下や天候変化に注意が必要です。")
    else:
        score -= 1
        comment.append("高標高域での行動となり、気象の急変や低体温症リスクが高まります。")

    # 天候（風・気温）
    if wind_speed > 10:
        score -= 1
        comment.append("風が強く、稜線や露出した場所では難易度が一段階上がります。")
    if temp < 0 or temp > 28:
        score -= 1
        comment.append("気温条件が厳しく、体温管理や水分補給に注意が必要です。")

    # 難易度判定
    if score >= 2:
        level = "初級（初心者〜初中級者向け）"
        summary = "全体として負荷は比較的軽く、基本的な登山経験があれば楽しめる難易度です。"
    elif 0 <= score < 2:
        level = "中級（一般登山者向け）"
        summary = "体力と装備が整っていれば問題なく歩けますが、油断は禁物の難易度です。"
    else:
        level = "上級（経験者向け）"
        summary = "体力・技術・装備が揃った登山者向けで、慎重な計画と判断が求められます。"

    return f"{level}\n\n" + "\n".join(comment) + "\n\n" + summary


# =========================
# 装備提案
# =========================
def suggest_equipment(
    temp: float,
    wind_speed: float,
    rain_expected: bool,
    snow_expected: bool,
    season: str,
) -> list:
    """
    登山装備のAI風提案。
    """
    items = []

    # 基本セット
    items.extend([
        "地図・コンパス（または信頼できるGPS）",
        "ヘッドランプ（予備電池含む）",
        "ファーストエイドキット",
        "非常食・行動食",
        "レインウェア（上下）",
    ])

    # 気温
    if temp < 5:
        items.extend([
            "保温性の高いミッドレイヤー（フリースなど）",
            "ダウンジャケットまたはインサレーション",
            "厚手の手袋・ニット帽",
        ])
    elif temp > 25:
        items.extend([
            "通気性の良い速乾ウェア",
            "帽子・サングラス",
            "多めの水分（1.5〜2L以上）",
        ])

    # 風
    if wind_speed > 8:
        items.append("防風性の高いシェルジャケット")

    # 雨・雪
    if rain_expected:
        items.extend([
            "防水性の高い登山靴",
            "ザックカバー",
        ])
    if snow_expected:
        items.extend([
            "防寒性の高いグローブ",
            "ゲイター（スパッツ）",
            "防水・防寒ブーツ",
        ])

    # 季節
    if season in ["春", "秋"]:
        items.append("薄手のレイヤーを重ねて温度調整できる服装")
    elif season == "夏":
        items.append("虫除けスプレー・日焼け止め")
    elif season == "冬":
        items.extend([
            "アイゼン（必要なルートの場合）",
            "バラクラバやネックウォーマー",
        ])

    # 重複削除
    unique_items = []
    for it in items:
        if it not in unique_items:
            unique_items.append(it)

    return unique_items


# =========================
# GPX関連
# =========================
def parse_gpx(file) -> list:
    """
    GPXファイルから緯度経度のリストを抽出
    """
    gpx = gpxpy.parse(file)
    points = []
    for track in gpx.tracks:
        for segment in track.segments:
            for p in segment.points:
                points.append((p.latitude, p.longitude))
    return points


def create_route_layer(points: list):
    """
    pydeck用のルートレイヤーを作成
    """
    if not points:
        return None

    data = [{"lat": lat, "lon": lon} for lat, lon in points]

    layer = pdk.Layer(
        "PathLayer",
        data=data,
        get_path="[[lon, lat]]",
        get_color=[0, 100, 255],
        width_scale=10,
        width_min_pixels=3,
    )
    return layer


# =========================
# Streamlit UI
# =========================
def main():
    st.set_page_config(page_title="登山計画アプリ", page_icon="🏔", layout="wide")

    st.title("🏔 登山計画サポートアプリ Ver1.2（全部入り）")

    st.sidebar.header("山の情報入力")

    # 山の基本情報
    mountain_name = st.sidebar.text_input("山の名前", value="テスト山")
    lat = st.sidebar.number_input("緯度", value=35.0, format="%.6f")
    lon = st.sidebar.number_input("経度", value=135.0, format="%.6f")

    distance_km = st.sidebar.number_input("想定歩行距離 (km)", value=8.0, min_value=0.0, step=0.5)
    elevation_gain_m = st.sidebar.number_input("累積標高 (m)", value=800.0, min_value=0.0, step=50.0)
    max_altitude_m = st.sidebar.number_input("最高標高 (m)", value=1500.0, min_value=0.0, step=50.0)

    season = st.sidebar.selectbox("季節", ["春", "夏", "秋", "冬"], index=0)

    st.sidebar.markdown("---")
    st.sidebar.header("GPXルート（任意）")
    gpx_file = st.sidebar.file_uploader("GPXファイルをアップロード", type=["gpx"])

    st.markdown("### 1. 現在の天気と1時間予報")

    try:
        current = fetch_current_weather(lat, lon)
        forecast_list = fetch_hourly_forecast(lat, lon)
    except Exception as e:
        st.error(f"天気情報の取得に失敗しました: {e}")
        return

    # 現在の天気表示
    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("現在の天気")
        weather = current.get("weather", [{}])[0]
        main = current.get("main", {})
        wind = current.get("wind", {})

        st.write(f"**地点:** {current.get('name', mountain_name)}")
        st.write(f"**天気:** {weather.get('description', '不明')}")
        st.write(f"**気温:** {main.get('temp', '不明')} ℃")
        st.write(f"**体感温度:** {main.get('feels_like', '不明')} ℃")
        st.write(f"**湿度:** {main.get('humidity', '不明')} %")
        st.write(f"**風速:** {wind.get('speed', '不明')} m/s")

    with col2:
        st.subheader("風向き")
        wind_deg = current.get("wind", {}).get("deg", 0)
        direction_text = draw_wind_compass(wind_deg)
        st.write(f"**風向:** {direction_text}（{wind_deg}°）")

    with col3:
        st.subheader("登山向けAIコメント")
        ai_comment = interpret_weather_for_hiking(current, forecast_list)
        st.write(ai_comment)

    st.markdown("---")
    st.markdown("### 2. 山の難易度・危険度評価")

    difficulty_text = evaluate_mountain_difficulty(
        distance_km=distance_km,
        elevation_gain_m=elevation_gain_m,
        max_altitude_m=max_altitude_m,
        current_weather=current,
    )
    st.write(difficulty_text)

    st.markdown("---")
    st.markdown("### 3. 装備提案")

    # 雨・雪の簡易判定（直近24h）
    rain_expected = False
    snow_expected = False
    for item in forecast_list[:8]:
        rain = item.get("rain", {})
        snow = item.get("snow", {})
        if rain.get("3h", 0) > 0:
            rain_expected = True
        if snow.get("3h", 0) > 0:
            snow_expected = True

    temp = current.get("main", {}).get("temp", 10)
    wind_speed = current.get("wind", {}).get("speed", 3)

    equipment_list = suggest_equipment(
        temp=temp,
        wind_speed=wind_speed,
        rain_expected=rain_expected,
        snow_expected=snow_expected,
        season=season,
    )

    for item in equipment_list:
        st.write(f"- {item}")

    st.markdown("---")
    st.markdown("### 4. GPXルート表示（任意）")

    if gpx_file is not None:
        try:
            points = parse_gpx(gpx_file)
            if points:
                mid_lat = sum(p[0] for p in points) / len(points)
                mid_lon = sum(p[1] for p in points) / len(points)

                route_layer = pdk.Layer(
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

                st.pydeck_chart(pdk.Deck(
                    layers=[route_layer],
                    initial_view_state=view_state,
                    tooltip={"text": "登山ルート"},
                ))
            else:
                st.info("GPXからルートポイントが取得できませんでした。")
        except Exception as e:
            st.error(f"GPXの解析に失敗しました: {e}")
    else:
        st.info("GPXファイルをアップロードすると、ここにルートが表示されます。")

    st.markdown("---")
    st.caption("※ このアプリは登山計画の補助ツールであり、最終的な安全判断は必ず自身で行ってください。")


if __name__ == "__main__":
    main()
