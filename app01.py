import textwrap

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import folium
from streamlit_folium import st_folium

from mountains import mountains
from weather import (
    get_weather,
    get_hourly,
    get_90days,
    get_14day_weather_change,
)
from mountain import summit_temp

try:
    from danger import judge, recommend
except Exception:
    judge = None
    recommend = None

try:
    from equipment import equipment
except Exception:
    equipment = {}


# =========================================================
# ページ設定
# =========================================================
st.set_page_config(
    page_title="Mountain Weather AI Pro",
    page_icon="⛰️",
    layout="wide",
)


# =========================================================
# HTML描画ヘルパー
# 重要：indent付きHTMLをそのままst.markdownへ渡すと
# Markdownのコードブロックとして表示されるためdedentする。
# =========================================================
def html_block(value):
    st.markdown(
        textwrap.dedent(value).strip(),
        unsafe_allow_html=True,
    )


# =========================================================
# CSS
# =========================================================
html_block("""
<style>
.weather-window {
    background: linear-gradient(145deg, #171a20, #30363f);
    color: white;
    border-radius: 26px;
    padding: 24px;
    margin: 10px 0 22px 0;
    box-shadow: 0 12px 32px rgba(0,0,0,.20);
}

.weather-top {
    display:flex;
    justify-content:space-between;
    align-items:flex-start;
    gap:12px;
}

.weather-place {
    font-size:18px;
    font-weight:700;
}

.weather-height {
    font-size:12px;
    color:#b9c0c8;
    margin-top:4px;
}

.weather-now {
    display:flex;
    align-items:center;
    gap:16px;
    margin:20px 0 12px 0;
}

.weather-icon-big {
    font-size:58px;
    line-height:1;
}

.weather-temp-big {
    font-size:58px;
    font-weight:800;
    line-height:1;
}

.weather-text-big {
    font-size:18px;
    margin-top:8px;
    color:#eef1f4;
}

.weather-detail-line {
    font-size:13px;
    color:#d4d9de;
    margin-top:8px;
}

.hourly-title {
    font-size:14px;
    font-weight:700;
    margin:18px 0 8px 0;
}

.hourly-scroll {
    display:flex;
    gap:9px;
    overflow-x:auto;
    padding:4px 2px 10px 2px;
    -webkit-overflow-scrolling:touch;
}

.hour-card {
    flex:0 0 91px;
    background:rgba(255,255,255,.09);
    border:1px solid rgba(255,255,255,.13);
    border-radius:15px;
    padding:10px 8px;
    text-align:center;
}

.hour-card.current {
    background:rgba(255,255,255,.18);
    border-color:rgba(255,255,255,.30);
}

.hour-time {font-size:12px;font-weight:700;}
.hour-icon {font-size:28px;margin:7px 0;white-space:nowrap;}
.hour-temp {font-size:17px;font-weight:800;}
.hour-rain {font-size:11px;color:#d8dde2;margin-top:5px;}
.hour-wind {font-size:10px;color:#bfc6cc;margin-top:4px;}

.judge-box, .gear-box, .long-box {
    background:white;
    border:1px solid #e1e5e9;
    border-radius:19px;
    padding:18px;
    margin:10px 0 18px 0;
    box-shadow:0 4px 14px rgba(0,0,0,.06);
}

.judge-main {font-size:25px;font-weight:800;margin-top:5px;}
.judge-reason {font-size:13px;color:#666;margin-top:7px;}
.gear-item {padding:7px 0;font-size:15px;}

.day-scroll {
    display:flex;
    gap:10px;
    overflow-x:auto;
    padding:4px 2px 14px 2px;
    -webkit-overflow-scrolling:touch;
}

.day-card {
    flex:0 0 125px;
    background:white;
    border:1px solid #e0e4e8;
    border-radius:16px;
    padding:12px;
    text-align:center;
    box-shadow:0 3px 10px rgba(0,0,0,.06);
}

.day-card.today {
    border:2px solid #555;
    background:#f5f6f7;
}

.day-date {font-size:12px;font-weight:700;}
.day-icon {font-size:31px;margin:7px 0;white-space:nowrap;}
.day-weather {font-size:12px;font-weight:700;min-height:34px;}
.day-high {font-size:18px;font-weight:800;margin-top:7px;}
.day-low {font-size:12px;color:#777;}
.day-rain {font-size:11px;color:#555;margin-top:5px;}

@media (max-width: 768px) {
    .weather-window {padding:18px;border-radius:21px;}
    .weather-temp-big {font-size:48px;}
    .weather-icon-big {font-size:48px;}
    .weather-now {gap:12px;}
}
</style>
""")


# =========================================================
# ユーティリティ
# =========================================================
def safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def weather_icon_from_text(text):
    text = str(text)
    if "雷" in text:
        return "⛈️"
    if "雪" in text:
        return "❄️"
    if "雨" in text:
        if "晴" in text or "曇" in text:
            return "🌦️"
        return "🌧️"
    if "霧" in text:
        return "🌫️"
    if "曇" in text:
        return "☁️"
    if "晴" in text:
        return "☀️"
    return "🌤️"


def format_num(value, digits=1):
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return "-"


def hiking_judgement(df):
    """短期予報から登山コンディションを4段階判定。"""
    if df is None or len(df) == 0:
        return "🟡 判定不能", "予報データがありません。", 0

    rain = safe_float(df["降水確率"].max()) if "降水確率" in df else 0
    wind = safe_float(df["風速"].max()) if "風速" in df else 0
    low = safe_float(df["最低気温"].min()) if "最低気温" in df else 10

    score = 0
    reasons = []

    if rain >= 80:
        score += 3
        reasons.append(f"降水確率{rain:.0f}%")
    elif rain >= 50:
        score += 2
        reasons.append(f"降水確率{rain:.0f}%")
    elif rain >= 30:
        score += 1
        reasons.append(f"降水確率{rain:.0f}%")

    if wind >= 50:
        score += 3
        reasons.append(f"最大風速{wind:.1f}km/h")
    elif wind >= 35:
        score += 2
        reasons.append(f"最大風速{wind:.1f}km/h")
    elif wind >= 25:
        score += 1
        reasons.append(f"最大風速{wind:.1f}km/h")

    if low <= 0:
        score += 3
        reasons.append(f"最低気温{low:.1f}℃")
    elif low <= 5:
        score += 2
        reasons.append(f"最低気温{low:.1f}℃")
    elif low <= 10:
        score += 1
        reasons.append(f"最低気温{low:.1f}℃")

    if score >= 6:
        result = "🔴 登山非推奨"
    elif score >= 4:
        result = "🟠 注意して登山"
    elif score >= 2:
        result = "🟡 条件付きで登山可能"
    else:
        result = "🟢 登山おすすめ"

    reason = " / ".join(reasons) if reasons else "大きな気象リスクは比較的少ない予報です。"
    return result, reason, score


def gear_from_weather(mountain_name, df, height):
    """既存の装備リスト＋天候条件から装備を追加。"""
    result = []

    # 既存equipment.pyのデータを尊重
    if isinstance(equipment, dict):
        base = equipment.get(mountain_name, equipment.get("default", []))
        if isinstance(base, (list, tuple, set)):
            result.extend([str(x) for x in base])

    rain = safe_float(df["降水確率"].max()) if "降水確率" in df else 0
    wind = safe_float(df["風速"].max()) if "風速" in df else 0
    low = safe_float(df["最低気温"].min()) if "最低気温" in df else 10

    if rain >= 30:
        result += ["レインウェア", "ザックカバー"]
    if wind >= 25:
        result += ["ウインドシェル"]
    if low <= 10:
        result += ["防寒着"]
    if low <= 5:
        result += ["手袋"]
    if low <= 0:
        result += ["防寒手袋", "ニット帽"]
    if height >= 1500:
        result += ["防寒着", "ヘッドライト"]

    # 順序維持で重複削除
    seen = set()
    return [x for x in result if not (x in seen or seen.add(x))]


# =========================================================
# タイトル
# =========================================================
st.title("⛰️ Mountain Weather AI Pro")
st.caption("1日の天気の流れ・登山判定・装備判定をひとつの画面で確認")


# =========================================================
# 山・地点
# =========================================================
mountain = st.selectbox("🏔️ 山を選択", list(mountains.keys()))
data = mountains[mountain]

forecast_points = data.get("locations", [])
if not forecast_points:
    forecast_points = [{
        "name": mountain,
        "type": "山頂",
        "lat": data["lat"],
        "lon": data["lon"],
        "height": data["height"],
    }]

labels = [f"{p.get('type', '予報地点')}｜{p['name']}" for p in forecast_points]
selected_label = st.selectbox("📍 予報地点", labels)
selected = forecast_points[labels.index(selected_label)]

lat = float(selected["lat"])
lon = float(selected["lon"])
height = float(selected.get("height") or data["height"])


# =========================================================
# データ取得
# =========================================================
try:
    df = get_weather(lat, lon)
    hourly = get_hourly(lat, lon)
    change_df = get_14day_weather_change(lat, lon)
except Exception as e:
    st.error(f"天気予報の取得に失敗しました：{e}")
    st.stop()


# =========================================================
# 今日・現在
# =========================================================
today = df.iloc[0] if len(df) else {}

if len(hourly):
    current = hourly.iloc[0]
    current_temp = current.get("気温", today.get("最高気温", "-"))
    current_weather = current.get("天気詳細", "天気不明")
else:
    current_temp = today.get("最高気温", "-")
    current_weather = today.get("天気詳細", "天気不明")

high = today.get("最高気温", "-")
low = today.get("最低気温", "-")
rain = today.get("降水確率", "-")
wind = today.get("風速", "-")


# =========================================================
# 🌦️ メインの「天気アプリ窓」
# =========================================================
icon = weather_icon_from_text(current_weather)

html_block(f"""
<div class="weather-window">
    <div class="weather-top">
        <div>
            <div class="weather-place">⛰️ {mountain}</div>
            <div class="weather-height">📍 {selected['name']}　標高 {height:.0f}m</div>
        </div>
    </div>

    <div class="weather-now">
        <div class="weather-icon-big">{icon}</div>
        <div>
            <div class="weather-temp-big">{format_num(current_temp, 1)}℃</div>
            <div class="weather-text-big">{current_weather}</div>
        </div>
    </div>

    <div class="weather-detail-line">
        🌡️ 最高 {format_num(high, 1)}℃　最低 {format_num(low, 1)}℃
    </div>
    <div class="weather-detail-line">
        ☔ 降水 {format_num(rain, 0)}%　💨 最大風速 {format_num(wind, 1)} km/h
    </div>

    <div class="hourly-title">🕐 これから24時間の天気</div>
""")


# =========================================================
# 🕐 1日の天気の流れ
# =========================================================
if len(hourly):
    cards = []
    for i, (_, row) in enumerate(hourly.iterrows()):
        time = pd.to_datetime(row["時刻"]).strftime("%H:%M")
        weather = row.get("天気詳細", "")
        icon = weather_icon_from_text(weather)
        temp = row.get("気温", "-")
        rain_mm = row.get("雨量", "-")
        wind_h = row.get("風速", "-")
        cls = "hour-card current" if i == 0 else "hour-card"

        cards.append(f"""
        <div class="{cls}">
            <div class="hour-time">{time}</div>
            <div class="hour-icon">{icon}</div>
            <div class="hour-temp">{format_num(temp, 1)}℃</div>
            <div class="hour-rain">☔ {format_num(rain_mm, 1)}mm</div>
            <div class="hour-wind">💨 {format_num(wind_h, 1)}km/h</div>
        </div>
        """)

    html_block('<div class="hourly-scroll">' + "".join(cards) + "</div>")
else:
    st.info("時間別予報が取得できませんでした。")

html_block("</div>")


# =========================================================
# 🥾 登山判定
# =========================================================
judge_text, judge_reason, judge_score = hiking_judgement(df)

st.subheader("🥾 登山判定")
html_block(f"""
<div class="judge-box">
    <div style="font-size:13px;color:#777;">本日の総合コンディション</div>
    <div class="judge-main">{judge_text}</div>
    <div class="judge-reason">{judge_reason}</div>
    <div style="font-size:12px;color:#999;margin-top:8px;">判定スコア：{judge_score}</div>
</div>
""")


# =========================================================
# 🎒 装備判定
# =========================================================
st.subheader("🎒 装備判定")
gear = gear_from_weather(mountain, df, height)

if gear:
    html_block('<div class="gear-box">')
    for item in gear:
        st.checkbox(item, key=f"gear_{mountain}_{selected['name']}_{item}")
    html_block("</div>")
else:
    st.info("この山の基本装備データが登録されていません。")


# =========================================================
# 📅 14日予報
# =========================================================
st.subheader("📅 14日予報")

day_cards = []
for i, (_, row) in enumerate(df.iterrows()):
    date = str(row.get("日付", ""))
    match = change_df[change_df["日付"].astype(str) == date] if len(change_df) else pd.DataFrame()

    if len(match):
        change = match.iloc[0]
        icon = change.get("天気", row.get("天気", "🌤️"))
        summary = change.get("天気詳細", row.get("天気詳細", ""))
    else:
        icon = row.get("天気", "🌤️")
        summary = row.get("天気詳細", "")

    cls = "day-card today" if i == 0 else "day-card"
    day_cards.append(f"""
    <div class="{cls}">
        <div class="day-date">{date}</div>
        <div class="day-icon">{icon}</div>
        <div class="day-weather">{summary}</div>
        <div class="day-high">{format_num(row.get('最高気温'), 1)}℃</div>
        <div class="day-low">最低 {format_num(row.get('最低気温'), 1)}℃</div>
        <div class="day-rain">☔ {format_num(row.get('降水確率'), 0)}%</div>
    </div>
    """)

html_block('<div class="day-scroll">' + "".join(day_cards) + "</div>")
st.caption("👆 横にスワイプして14日分を確認できます")


# =========================================================
# 🌡️ 24時間気温グラフ
# =========================================================
st.subheader("🌡️ 24時間の気温変化")
if len(hourly):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=hourly["時刻"],
        y=hourly["気温"],
        mode="lines+markers",
        name="気温",
        line=dict(width=3),
        marker=dict(size=6),
    ))
    fig.update_layout(
        height=300,
        margin=dict(l=10, r=10, t=15, b=10),
        hovermode="x unified",
        xaxis_title="",
        yaxis_title="℃",
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)


# =========================================================
# 🏔️ 山頂気温
# =========================================================
st.subheader("🏔️ 山頂気温の目安")
try:
    summit = summit_temp(float(high), height)
    st.metric("山頂予想気温", f"{summit:.1f}℃")
except Exception:
    st.info("山頂気温を計算できませんでした。")


# =========================================================
# 🗺️ マップ
# =========================================================
st.subheader("🗺️ 登山地点マップ")
m = folium.Map(location=[lat, lon], zoom_start=11, control_scale=True)
colors = {
    "山頂": ("red", "flag"),
    "山小屋": ("green", "home"),
    "登山口": ("blue", "sign-in"),
    "テント場": ("orange", "cloud"),
    "避難小屋": ("purple", "warning-sign"),
}

for p in forecast_points:
    ptype = p.get("type", "その他")
    color, icon_name = colors.get(ptype, ("gray", "info-sign"))
    folium.Marker(
        [p["lat"], p["lon"]],
        popup=folium.Popup(
            f"<b>{p['name']}</b><br>種類：{ptype}<br>標高：{p.get('height', '-')}m",
            max_width=250,
        ),
        icon=folium.Icon(color=color, icon=icon_name),
    ).add_to(m)

folium.CircleMarker(
    [lat, lon],
    radius=9,
    color="black",
    fill=True,
    fill_opacity=0.15,
    popup=f"現在の予報地点：{selected['name']}",
).add_to(m)

st_folium(m, width=None, height=520, returned_objects=[])


# =========================================================
# 📆 90日長期予報
# =========================================================
st.subheader("📆 90日長期予報")
st.caption("※ 90日先は短期予報ではなく、ECMWFの季節予報による長期傾向です。")

with st.expander("90日長期予報を表示"):
    try:
        df90 = get_90days(lat, lon)
        if df90 is None or len(df90) == 0:
            st.warning("90日長期予報のデータが取得できませんでした。")
        else:
            st.dataframe(
                df90,
                use_container_width=True,
                hide_index=True,
            )

            if "平均気温" in df90.columns:
                fig90 = go.Figure()
                fig90.add_trace(go.Scatter(
                    x=df90["日付"],
                    y=df90["平均気温"],
                    mode="lines",
                    name="平均気温",
                ))
                fig90.update_layout(
                    height=300,
                    margin=dict(l=10, r=10, t=15, b=10),
                    xaxis_title="",
                    yaxis_title="℃",
                )
                st.plotly_chart(fig90, use_container_width=True)
    except Exception as e:
        st.warning("90日長期予報は現在取得できません。短期予報は正常に表示できます。")
        st.caption(f"詳細: {e}")
