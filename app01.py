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
    weather_icon,
    weather_text,
)
from danger import judge, recommend
from equipment import equipment
from mountain import summit_temp


# =========================================================
# ページ設定
# =========================================================
st.set_page_config(
    page_title="Mountain Weather AI Pro",
    page_icon="⛰️",
    layout="wide",
)

st.markdown("""
<style>
/* 横スクロールできる14日カード */
.forecast-scroll {
    display: flex;
    gap: 10px;
    overflow-x: auto;
    padding: 8px 4px 16px 4px;
    scroll-snap-type: x proximity;
    -webkit-overflow-scrolling: touch;
}

.forecast-card {
    flex: 0 0 175px;
    min-height: 185px;
    border: 1px solid #d8dee9;
    border-radius: 14px;
    padding: 13px;
    background: #ffffff;
    box-shadow: 0 2px 8px rgba(0,0,0,.08);
    scroll-snap-align: start;
}

.forecast-card .date {
    font-size: 14px;
    font-weight: 700;
    color: #333;
}

.forecast-card .icon {
    font-size: 34px;
    margin: 5px 0;
    white-space: nowrap;
}

.forecast-card .weather {
    font-size: 15px;
    font-weight: 700;
    min-height: 40px;
    color: #222;
}

.forecast-card .temp {
    font-size: 14px;
    margin-top: 7px;
}

.forecast-card .rain {
    font-size: 13px;
    margin-top: 5px;
    color: #444;
}

.forecast-scroll::-webkit-scrollbar {
    height: 9px;
}
.forecast-scroll::-webkit-scrollbar-thumb {
    background: #aaa;
    border-radius: 10px;
}
.forecast-scroll::-webkit-scrollbar-track {
    background: #eee;
    border-radius: 10px;
}

/* 地図凡例 */
.map-legend {
    background: white;
    color: #111 !important;
    padding: 10px 12px;
    border: 1px solid #aaa;
    border-radius: 8px;
    font-size: 13px;
    line-height: 1.7;
    box-shadow: 0 1px 5px rgba(0,0,0,.25);
}
.map-legend * {
    color: #111 !important;
}

/* モバイルでも表を横スクロール */
[data-testid="stDataFrame"] {
    overflow-x: auto;
}
</style>
""", unsafe_allow_html=True)


# =========================================================
# タイトル
# =========================================================
st.title("⛰️ Mountain Weather AI Pro")
st.caption("登山地点ごとの14日予報・24時間予報・天気変化・危険度をまとめて確認")


# =========================================================
# 山を選択
# =========================================================
mountain = st.selectbox("🏔️ 山を選択", list(mountains.keys()))
data = mountains[mountain]

if data.get("ship_origin"):
    st.caption(f"⚓ 軍艦名由来：{data['ship_origin']}")

# ---------------------------------------------------------
# 予報地点を選択
# ---------------------------------------------------------
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

selected_label = st.selectbox("📍 予報地点を選択", labels)
selected = forecast_points[labels.index(selected_label)]

lat = float(selected["lat"])
lon = float(selected["lon"])
height = float(selected.get("height") or data["height"])

st.caption(
    f"📍 {selected['name']}　"
    f"緯度 {lat:.4f} / 経度 {lon:.4f} / 標高 {height:.0f}m"
)


# =========================================================
# 予報取得
# =========================================================
try:
    df = get_weather(lat, lon)
    hourly = get_hourly(lat, lon)
    change_df = get_14day_weather_change(lat, lon)
except Exception as e:
    st.error(f"天気予報の取得に失敗しました：{e}")
    st.stop()


# =========================================================
# 今日の天気
# =========================================================
st.subheader("🌤️ 今日の予報")

if len(change_df) > 0:
    today = change_df.iloc[0]
    st.markdown(
        f"### {today['天気']}　{today['天気詳細']}"
    )

if len(df) > 0:
    today_df = df.iloc[0]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("最高気温", f"{today_df['最高気温']}℃")
    c2.metric("最低気温", f"{today_df['最低気温']}℃")
    c3.metric("降水確率", f"{today_df['降水確率']}%")
    c4.metric("最大風速", f"{today_df['風速']} km/h")


# =========================================================
# 14日予報：横スクロールカード
# =========================================================
st.subheader("📅 14日予報")

cards = []

for i, row in df.iterrows():
    date = row["日付"]
    detail = row["天気詳細"]

    # 時間別天気変化を対応する日付から取得
    match = change_df[change_df["日付"] == str(date)]

    if len(match):
        change = match.iloc[0]
        icon = change["天気"]
        summary = change["天気詳細"]
    else:
        icon = row["天気"]
        summary = detail

    cards.append(f"""
    <div class="forecast-card">
        <div class="date">{date}</div>
        <div class="icon">{icon}</div>
        <div class="weather">{summary}</div>
        <div class="temp">
            🌡️ {row['最高気温']}℃ / {row['最低気温']}℃
        </div>
        <div class="rain">☔ 降水 {row['降水確率']}%</div>
        <div class="rain">💨 風 {row['風速']} km/h</div>
    </div>
    """)

st.markdown(
    '<div class="forecast-scroll">' + "".join(cards) + '</div>',
    unsafe_allow_html=True
)

st.caption("👆 横にスクロールして14日分を確認できます")


# =========================================================
# 14日気温グラフ
# =========================================================
st.subheader("🌡️ 14日間の気温推移")

fig = go.Figure()

fig.add_trace(go.Scatter(
    x=df["日付"],
    y=df["最高気温"],
    mode="lines+markers",
    name="最高気温",
))

fig.add_trace(go.Scatter(
    x=df["日付"],
    y=df["最低気温"],
    mode="lines+markers",
    name="最低気温",
))

fig.update_layout(
    height=360,
    margin=dict(l=20, r=20, t=20, b=20),
    hovermode="x unified",
    xaxis_title="日付",
    yaxis_title="気温（℃）",
)

st.plotly_chart(fig, use_container_width=True)


# =========================================================
# 24時間予報
# =========================================================
st.subheader("🕐 これから24時間")

if len(hourly) > 0:
    h = hourly.copy()
    h["表示時刻"] = h["時刻"].dt.strftime("%m/%d %H:%M")

    st.dataframe(
        h[
            ["表示時刻", "天気", "天気詳細", "気温",
             "湿度", "雨量", "風速", "風向"]
        ].rename(columns={
            "表示時刻": "時刻",
            "天気詳細": "天気詳細",
            "気温": "気温℃",
            "湿度": "湿度%",
            "雨量": "雨量mm",
            "風速": "風速km/h",
        }),
        use_container_width=True,
        hide_index=True,
    )


# =========================================================
# 危険度
# =========================================================
st.subheader("⚠️ 登山危険度")

try:
    danger_score = judge(df)
    st.metric("危険度", danger_score)
    st.write(recommend(danger_score))
except Exception:
    st.info("危険度判定は現在のデータ形式に合わせて表示できませんでした。")


# =========================================================
# 山頂気温
# =========================================================
st.subheader("🏔️ 山頂気温の目安")

try:
    ground_temp = float(df.iloc[0]["最高気温"])
    summit = summit_temp(ground_temp, data["height"])
    st.metric("山頂予想気温", f"{summit:.1f}℃")
except Exception:
    st.info("山頂気温を計算できませんでした。")


# =========================================================
# 装備
# =========================================================
st.subheader("🎒 装備チェック")

try:
    items = equipment.get(mountain, equipment.get("default", []))
    if items:
        for item in items:
            st.checkbox(str(item), key=f"equipment_{mountain}_{item}")
except Exception:
    st.info("装備情報は現在のデータ形式に合わせて表示できませんでした。")


# =========================================================
# 登山地点マップ
# =========================================================
st.subheader("🗺️ 登山地点マップ")

m = folium.Map(
    location=[lat, lon],
    zoom_start=11,
    control_scale=True,
)

colors = {
    "山頂": ("red", "flag"),
    "山小屋": ("green", "home"),
    "登山口": ("blue", "sign-in"),
    "テント場": ("orange", "cloud"),
    "避難小屋": ("purple", "warning-sign"),
}

for p in forecast_points:
    ptype = p.get("type", "その他")
    color, icon = colors.get(ptype, ("gray", "info-sign"))

    folium.Marker(
        [p["lat"], p["lon"]],
        popup=folium.Popup(
            f"<b>{p['name']}</b><br>"
            f"種類：{ptype}<br>"
            f"標高：{p.get('height', '-')}m",
            max_width=250,
        ),
        icon=folium.Icon(color=color, icon=icon),
    ).add_to(m)

# 選択中の予報地点
folium.CircleMarker(
    [lat, lon],
    radius=9,
    color="black",
    fill=True,
    fill_opacity=0.15,
    popup=f"現在の予報地点：{selected['name']}",
).add_to(m)

legend_html = """
<div class="map-legend"
     style="position: fixed; bottom: 25px; right: 25px; z-index:9999;">
<b>📍 地図凡例</b><br>
<span style="color:#d00 !important;">●</span> 山頂<br>
<span style="color:#008000 !important;">●</span> 山小屋<br>
<span style="color:#06c !important;">●</span> 登山口<br>
<span style="color:#f90 !important;">●</span> テント場<br>
<span style="color:#800080 !important;">●</span> 避難小屋
</div>
"""

m.get_root().html.add_child(folium.Element(legend_html))

st_folium(
    m,
    width=None,
    height=560,
    returned_objects=[],
)


# =========================================================
# 90日予報
# =========================================================
with st.expander("📆 90日予報を表示"):
    try:
        df90 = get_90days(lat, lon)
        st.dataframe(
            df90,
            use_container_width=True,
            hide_index=True,
        )
    except Exception as e:
        st.error(f"90日予報の取得に失敗しました：{e}")
