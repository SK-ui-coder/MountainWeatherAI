import streamlit as st
import plotly.express as px
import pandas as pd
import gpxpy
import pydeck as pdk

from mountains import mountains
from weather import get_weather, get_hourly, get_current_weather, get_90days
from danger import judge, recommend
from equipment import equipment
from mountain import summit_temp

# ---------------------------------------------------------
# CSS（絶対に壊れない安全版）
# ---------------------------------------------------------
css = """
<style>
.main, body { background-color: #e9f2ff; }

div[data-testid="metric-container"] {
    background-color: #ffffff;
    padding: 15px;
    border-radius: 12px;
    border: 1px solid #d0e3ff;
    box-shadow: 0px 2px 4px rgba(0,0,0,0.05);
}

.js-plotly-plot {
    background-color: #ffffff !important;
    border-radius: 12px;
    padding: 10px;
}

thead th {
    background-color: #d8e7ff !important;
    color: #003366 !important;
}
</style>
"""
st.markdown(css, unsafe_allow_html=True)

# ---------------------------------------------------------
# ページ設定
# ---------------------------------------------------------
st.set_page_config(page_title="Mountain Weather AI Pro", page_icon="🏔", layout="wide")
st.title("🏔 Mountain Weather AI Pro")
st.caption("登山専用AI天気アプリ")
st.divider()

# ---------------------------------------------------------
# 山選択
# ---------------------------------------------------------
mountain = st.selectbox("山を選択してください", mountains.keys())
lat = mountains[mountain]["lat"]
lon = mountains[mountain]["lon"]
height = mountains[mountain]["height"]

st.info(f"標高：{height} m")

# ---------------------------------------------------------
# 現在の天気
# ---------------------------------------------------------
api_key = st.secrets["OPENWEATHER_KEY"]
current = get_current_weather(lat, lon, api_key)

st.subheader("⛅ 現在の天気")

c1, c2, c3 = st.columns(3)
c1.metric("気温", f"{current['現在気温']}℃")
c2.metric("体感温度", f"{current['体感温度']}℃")
c3.metric("湿度", f"{current['湿度']}%")

c4, c5 = st.columns(2)
c4.metric("天気", current["現在天気"])
c5.metric("風速", f"{current['風速']} m/s")

st.divider()

# ---------------------------------------------------------
# 14日予報
# ---------------------------------------------------------
df = get_weather(lat, lon)

df["おすすめ"] = df.apply(
    lambda row: "★★★★★" if row["降水確率"] < 30 and row["風速"] < 8
    else "★★★★☆" if row["降水確率"] < 50
    else "★★☆☆☆",
    axis=1
)

selected_date = st.selectbox("📅 日付を選択", df["日付"])
today = df[df["日付"] == selected_date].iloc[0]

# ---------------------------------------------------------
# Today's Topics（重複なし）
# ---------------------------------------------------------
st.markdown("## 📢 Today's Topics")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(f"# {today['天気']}")
    st.metric("最高気温", f"{today['最高気温']}℃")
    st.metric("最低気温", f"{today['最低気温']}℃")

with col2:
    st.metric("風速", f"{today['風速']} m/s")
    st.metric("降水確率", f"{today['降水確率']} %")

with col3:
    st.metric("おすすめ", today["おすすめ"])

# ---------------------------------------------------------
# AIコメント
# ---------------------------------------------------------
st.markdown("### 🤖 AIコメント")

weather = today["天気"]

if today["風速"] >= 15:
    comment = "🔴 強風です。登山は危険なので延期をおすすめします。"
elif weather in ["🌧", "🌦", "⛈"]:
    comment = "🌧 雨の可能性があります。防水対策をしっかり行いましょう。"
elif today["降水確率"] >= 50:
    comment = "☔ 雨具を必ず持参してください。"
elif today["最高気温"] >= 30:
    comment = "🥵 気温が高いので熱中症対策を万全に。"
elif weather == "❄️":
    comment = "❄️ 雪の可能性があります。防寒装備を強化してください。"
else:
    comment = "☀️ 登山に適したコンディションです。"

st.info(comment)

# ---------------------------------------------------------
# 危険度・山頂気温・おすすめ度
# ---------------------------------------------------------
danger, score = judge(today["風速"], today["降水確率"])
star = recommend(score)
summit = summit_temp(today["最高気温"], height)

col5, col6, col7, col8 = st.columns(4)
col5.metric("危険度", danger)
col6.metric("AIスコア", f"{score}点")
col7.metric("山頂気温", f"{summit}℃")
col8.metric("おすすめ度", star)

st.divider()

# ---------------------------------------------------------
# 山の難易度（AI判定）
# ---------------------------------------------------------
def mountain_difficulty(info):
    height = info.get("height", 0)
    distance = info.get("distance", 5)
    up = info.get("up", height)

    score = height/100 + distance*2 + up/200

    if score < 20:
        level = "★ 初心者向け"
    elif score < 40:
        level = "★★ 初級〜中級"
    elif score < 60:
        level = "★★★ 中級"
    else:
        level = "★★★★ 上級者向け"

    return round(score), level

score_d, level_d = mountain_difficulty(mountains[mountain])

st.subheader("⛰ 山の難易度（AI判定）")
st.metric("難易度スコア", f"{score_d}点")
st.metric("レベル", level_d)

st.divider()

# ---------------------------------------------------------
# 24時間予報
# ---------------------------------------------------------
st.subheader("🕒 24時間予報")

hourly = get_hourly(lat, lon)
hourly["時刻表示"] = hourly["時刻"].dt.strftime("%H:%M")

st.dataframe(
    hourly[["時刻表示", "天気", "気温", "湿度", "雨量", "風速", "コンパス"]],
    use_container_width=True,
    hide_index=True
)

# ---------------------------------------------------------
# 円形コンパス
# ---------------------------------------------------------
st.subheader("🧭 風向きコンパス（円形）")

fig_compass = px.scatter_polar(
    hourly,
    r=[1] * len(hourly),
    theta="風向度",
    color="風速",
    hover_name="時刻表示",
    color_continuous_scale="Blues"
)

fig_compass.update_layout(
    showlegend=False,
    polar=dict(
        radialaxis=dict(visible=False),
        angularaxis=dict(direction="clockwise", rotation=90)
    )
)

st.plotly_chart(fig_compass, use_container_width=True)

st.divider()

# ---------------------------------------------------------
# グラフ青テーマ
# ---------------------------------------------------------
def blue_layout(fig, y_title):
    fig.update_layout(
        template="plotly_white",
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        font=dict(color="#0a4da8"),
        yaxis_title=y_title,
        xaxis_title="時刻",
    )
    return fig

st.subheader("📊 グラフ表示")

graph_type = st.selectbox("グラフを選択してください", ["気温", "風速", "降水量", "湿度"])

if graph_type == "気温":
    fig = px.line(hourly, x="時刻表示", y="気温", markers=True, color_discrete_sequence=["#1f77b4"])
    fig = blue_layout(fig, "気温 (℃)")
elif graph_type == "風速":
    fig = px.line(hourly, x="時刻表示", y="風速", markers=True, color_discrete_sequence=["#1f77b4"])
    fig = blue_layout(fig, "風速 (m/s)")
elif graph_type == "降水量":
    fig = px.bar(hourly, x="時刻表示", y="雨量", color_discrete_sequence=["#1f77b4"])
    fig = blue_layout(fig, "降水量 (mm)")
else:
    fig = px.line(hourly, x="時刻表示", y="湿度", markers=True, color_discrete_sequence=["#1f77b4"])
    fig = blue_layout(fig, "湿度 (%)")

st.plotly_chart(fig, use_container_width=True)

st.divider()

# ---------------------------------------------------------
# GPX ルート表示
# ---------------------------------------------------------
st.subheader("🗺 GPX ルート表示")

uploaded_gpx = st.file_uploader("GPXファイルをアップロード", type=["gpx"])

if uploaded_gpx:
    gpx = gpxpy.parse(uploaded_gpx.read().decode("utf-8"))
    points = []
    for track in gpx.tracks:
        for segment in track.segments:
            for p in segment.points:
                points.append([p.latitude, p.longitude])

    df_route = pd.DataFrame(points, columns=["lat", "lon"])
    st.map(df_route)

    layer = pdk.Layer(
        "PathLayer",
        data=df_route,
        get_path="[[lon, lat]]",
        get_color=[10, 100, 200],
        width_scale=10,
        width_min_pixels=2,
    )
    view_state = pdk.ViewState(
        latitude=df_route["lat"].mean(),
        longitude=df_route["lon"].mean(),
        zoom=12,
        pitch=45,
    )
    st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view_state))

st.divider()

# ---------------------------------------------------------
# 90日予報
# ---------------------------------------------------------
st.subheader("📆 90日予報")

long_df = get_90days(lat, lon)

fig1 = px.line(long_df, x="日付", y="最高気温", title="最高気温の推移")
fig2 = px.line(long_df, x="日付", y="降水確率", title="降水確率の推移")

st.plotly_chart(fig1, use_container_width=True)
st.plotly_chart(fig2, use_container_width=True)

st.markdown("### ✅ 完成版 Mountain Weather AI Pro")
