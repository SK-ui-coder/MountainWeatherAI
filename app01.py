import streamlit as st
import plotly.express as px

from mountains import mountains
from weather import get_weather, get_hourly, get_current_weather, get_90days
from danger import judge, recommend
from equipment import equipment
from mountain import summit_temp

# ---------------------------------------------------------
# CSS（安全版）
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

# ---------------------------------------------------------
# Streamlit 基本設定
# ---------------------------------------------------------
st.set_page_config(
    page_title="Mountain Weather AI Pro",
    page_icon="🏔",
    layout="wide"
)

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
# 現在の天気（OpenWeatherMap）
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

# おすすめ度
df["おすすめ"] = df.apply(
    lambda row: "★★★★★" if row["降水確率"] < 30 and row["風速"] < 8
    else "★★★★☆" if row["降水確率"] < 50
    else "★★☆☆☆",
    axis=1
)

# ---------------------------------------------------------
# 日付選択
# ---------------------------------------------------------
selected_date = st.selectbox("📅 日付を選択", df["日付"])
today = df[df["日付"] == selected_date].iloc[0]

# ---------------------------------------------------------
# 今日の天気サマリー
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
# AI コメント
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
# 危険度判定
# ---------------------------------------------------------
danger, score = judge(today["風速"], today["降水確率"])
star = recommend(score)
summit = summit_temp(today["最高気温"], height)
gear = equipment(summit, today["風速"], today["降水確率"])

# ---------------------------------------------------------
# メトリクス
# ---------------------------------------------------------
col1, col2, col3, col4 = st.columns(4)
col1.metric("天気", today["天気"])
col2.metric("最高", f"{today['最高気温']}℃")
col3.metric("降水", f"{today['降水確率']}%")
col4.metric("風", f"{today['風速']} m/s")

col5, col6, col7, col8 = st.columns(4)
col5.metric("危険度", danger)
col6.metric("AIスコア", f"{score}点")
col7.metric("山頂気温", f"{summit}℃")
col8.metric("おすすめ度", star)

st.divider()

# ---------------------------------------------------------
# 日の出・日の入り
# ---------------------------------------------------------
st.subheader("🌅 日の出・日の入り")

c1, c2 = st.columns(2)
c1.info(today["日の出"][11:16])
c2.info(today["日の入り"][11:16])

# ---------------------------------------------------------
# 装備提案
# ---------------------------------------------------------
st.subheader("🥾 AI装備提案")
for g in gear:
    st.success(g)

st.divider()

# ---------------------------------------------------------
# 24時間予報（コンパス対応）
# ---------------------------------------------------------
st.subheader("🕒 24時間予報")

hourly = get_hourly(lat, lon)
hourly["時刻表示"] = hourly["時刻"].dt.strftime("%H:%M")

st.dataframe(
    hourly[["時刻表示", "天気", "気温", "湿度", "雨量", "風速", "コンパス"]],
    use_container_width=True,
    hide_index=True
)

st.divider()

# ---------------------------------------------------------
# 風向きコンパス（円形）
# ---------------------------------------------------------
st.subheader("🧭 風向きコンパス")

# 風向き（度数）を取得するために weather.py を少し拡張している前提なら：
# hourly に "風向度" カラムを追加しておくと楽です

# ここでは仮に hourly に "風向度" があるとする
if "風向度" in hourly.columns:
    fig_compass = px.scatter_polar(
        hourly,
        r=["1"] * len(hourly),          # 半径は固定
        theta="風向度",                # 角度（度）
        color="風速",                  # 風速で色分け
        hover_name="時刻表示",
        color_continuous_scale="Blues"
    )
    fig_compass.update_layout(
        showlegend=False,
        polar=dict(
            radialaxis=dict(visible=False),
            angularaxis=dict(direction="clockwise", rotation=90)
        ),
        title="24時間の風向き（コンパス表示）"
    )
    st.plotly_chart(fig_compass, use_container_width=True)
else:
    st.info("風向きコンパス表示には '風向度' カラムが必要です。weather.py に追加できます。")


# ---------------------------------------------------------
# グラフ
# ---------------------------------------------------------
st.subheader("📊 グラフ表示")

graph_type = st.selectbox(
    "グラフを選択してください",
    ["気温", "風速", "降水量", "湿度"]
)

if graph_type == "気温":
    fig = px.line(hourly, x="時刻表示", y="気温", markers=True)
elif graph_type == "風速":
    fig = px.line(hourly, x="時刻表示", y="風速", markers=True)
elif graph_type == "降水量":
    fig = px.bar(hourly, x="時刻表示", y="雨量")
else:
    fig = px.line(hourly, x="時刻表示", y="湿度", markers=True)

st.plotly_chart(fig, use_container_width=True)

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

# グラフ共通レイアウト
def blue_layout(fig, y_title):
    fig.update_layout(
        template="plotly_white",
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        font=dict(color="#0a4da8"),
        yaxis_title=y_title,
        xaxis_title="時刻",
        margin=dict(l=40, r=20, t=40, b=40)
    )
    return fig

# 気温などのグラフ部分
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

# ---------------------------------------------------------
# 山の難易度判定
# ---------------------------------------------------------
def mountain_difficulty(mountain_name, info):
    height = info.get("height", 0)
    distance = info.get("distance", 0)      # km
    up = info.get("up", 0)                  # 累積標高

    score = 0
    score += height / 100      # 標高
    score += distance * 2      # 距離
    score += up / 200          # 累積標高

    if score < 20:
        level = "★ 初心者向け"
        comment = "体力に自信がなくても楽しめるコースです。天気が良ければ安心して計画できます。"
    elif score < 40:
        level = "★★ 初級〜中級"
        comment = "ある程度の体力が必要ですが、計画を立てれば安全に楽しめます。"
    elif score < 60:
        level = "★★★ 中級"
        comment = "登りが長く、天候悪化時は負荷が高くなります。装備と計画をしっかりと。"
    else:
        level = "★★★★ 上級者向け"
        comment = "急登や長距離があり、悪天候時は危険度が高まります。経験者向けの山です。"

    return round(score), level, comment

# 山選択の後に追加
diff_score, diff_level, diff_comment = mountain_difficulty(mountain, mountains[mountain])

st.subheader("⛰ 山の難易度（AI判定）")
c1, c2 = st.columns(2)
c1.metric("難易度スコア", f"{diff_score}点")
c2.metric("レベル", diff_level)
st.caption(diff_comment)

import gpxpy
import gpxpy.gpx
import pandas as pd
import pydeck as pdk

# ---------------------------------------------------------
# GPX ルート表示
# ---------------------------------------------------------
st.subheader("🗺 GPX ルート表示")

uploaded_gpx = st.file_uploader("GPXファイルをアップロードしてください", type=["gpx"])

if uploaded_gpx is not None:
    gpx = gpxpy.parse(uploaded_gpx.read().decode("utf-8"))
    points = []
    for track in gpx.tracks:
        for segment in track.segments:
            for p in segment.points:
                points.append([p.latitude, p.longitude])

    if points:
        df_route = pd.DataFrame(points, columns=["lat", "lon"])

        st.map(df_route)

        # もう少しリッチに表示したい場合（pydeck）
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
    else:
        st.warning("GPXからルートポイントを取得できませんでした。")
else:
    st.info("GPXファイルをアップロードすると、登山ルートを地図上に表示できます。")

