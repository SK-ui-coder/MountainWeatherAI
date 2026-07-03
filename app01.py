import streamlit as st
import plotly.express as px

from mountains import mountains
from weather import get_weather, get_hourly, get_current_weather
from danger import judge, recommend
from equipment import equipment
from mountain import summit_temp

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
# 14日予報（Open-Meteo）
# ---------------------------------------------------------
df = get_weather(lat, lon)

# ---------------------------------------------------------
# おすすめ度計算
# ---------------------------------------------------------
df["おすすめ"] = ""
for i in range(len(df)):
    rain = float(df.loc[i, "降水確率"])
    wind = float(df.loc[i, "風速"])

    if rain < 30 and wind < 8:
        df.loc[i, "おすすめ"] = "★★★★★"
    elif rain < 50:
        df.loc[i, "おすすめ"] = "★★★★☆"
    else:
        df.loc[i, "おすすめ"] = "★★☆☆☆"

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
# 危険度判定・山頂気温・装備
# ---------------------------------------------------------
danger, score = judge(today["風速"], today["降水確率"])
star = recommend(score)
summit = summit_temp(today["最高気温"], height)
gear = equipment(summit, today["風速"], today["降水確率"])

# ---------------------------------------------------------
# メトリクス表示
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

sunrise = today["日の出"]
sunset = today["日の入り"]

if hasattr(sunrise, "strftime"):
    c1.info(sunrise.strftime("%H:%M"))
    c2.info(sunset.strftime("%H:%M"))
else:
    c1.info(sunrise[11:16])
    c2.info(sunset[11:16])

# ---------------------------------------------------------
# 装備提案（前半）
# ---------------------------------------------------------
st.subheader("🥾 AI装備提案")
for g in gear:
    st.success(g)

st.divider()

# ---------------------------------------------------------
# ここから Part3（後半）で追加
# ・24時間予報
# ・グラフ
# ・詳細装備
# ---------------------------------------------------------
st.markdown("### ⏳ この先は Part3 で追加します")
# ---------------------------------------------------------
# 24時間予報（Open-Meteo）
# ---------------------------------------------------------
st.subheader("🕒 24時間予報")

hourly = get_hourly(lat, lon)

# 表示用に時刻だけ抽出
hourly["時刻表示"] = hourly["時刻"].dt.strftime("%H:%M")

st.dataframe(
    hourly[["時刻表示", "天気", "気温", "湿度", "雨量", "風速", "風向"]],
    use_container_width=True,
    hide_index=True
)

st.divider()

# ---------------------------------------------------------
# グラフ切り替え
# ---------------------------------------------------------
st.subheader("📊 グラフ表示")

graph_type = st.selectbox(
    "グラフを選択してください",
    ["気温", "風速", "降水量", "湿度"]
)

if graph_type == "気温":
    fig = px.line(hourly, x="時刻表示", y="気温", markers=True)
    fig.update_layout(yaxis_title="気温 (℃)")
    st.plotly_chart(fig, use_container_width=True)

elif graph_type == "風速":
    fig = px.line(hourly, x="時刻表示", y="風速", markers=True)
    fig.update_layout(yaxis_title="風速 (m/s)")
    st.plotly_chart(fig, use_container_width=True)

elif graph_type == "降水量":
    fig = px.bar(hourly, x="時刻表示", y="雨量")
    fig.update_layout(yaxis_title="降水量 (mm)")
    st.plotly_chart(fig, use_container_width=True)

elif graph_type == "湿度":
    fig = px.line(hourly, x="時刻表示", y="湿度", markers=True)
    fig.update_layout(yaxis_title="湿度 (%)")
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ---------------------------------------------------------
# 山頂気温の詳細
# ---------------------------------------------------------
st.subheader("🧊 山頂の体感温度")

summit_temp_now = summit_temp(current["現在気温"], height)

c1, c2 = st.columns(2)
c1.metric("現在の山頂気温", f"{summit_temp_now}℃")
c2.metric("予報の山頂気温", f"{summit}℃")

st.info("標高差に応じて気温を自動計算しています（100m につき約 -0.6℃）")

st.divider()

# ---------------------------------------------------------
# 装備の詳細
# ---------------------------------------------------------
st.subheader("🎒 装備の詳細アドバイス")

for g in gear:
    st.success(f"✔ {g}")

st.info("気温・風速・降水確率から AI が自動判定しています。")

st.divider()

# ---------------------------------------------------------
# 14日予報（再掲）
# ---------------------------------------------------------
st.subheader("📅 14日予報（一覧）")
st.dataframe(df, use_container_width=True, hide_index=True)

st.markdown("### ✅ Part3 完了しました")
st.caption("次は Part4（CSS / デザイン統一）を追加できます。")

# ---------------------------------------------------------
# CSS（デザイン統一）
# ---------------------------------------------------------
st.markdown("""
<style>

/* 全体の背景色 */
body {
    background-color: #e9f2ff;
}

/* Streamlit 全体の背景 */
.main {
    background-color: #e9f2ff;
}

/* タイトル */
h1 {
    color: #0a4da8;
    font-weight: 800;
}

/* セクションタイトル */
h2, h3, h4 {
    color: #0a4da8;
    font-weight: 700;
}

/* カード風のボックス */
div[data-testid="stMetric"] {
    background-color: #ffffff;
    padding: 15px;
    border-radius: 12px;
    border: 1px solid #d0e3ff;
    box-shadow: 0px 2px 4px rgba(0,0,0,0.05);
}

/* info / success / warning のカード */
.stAlert {
    border-radius: 12px;
}

/* データフレームの背景 */
.dataframe {
    background-color: white;
}

/* スマホ対応：余白調整 */
@media (max-width: 768px) {
    .block-container {
        padding-left: 1rem;
        padding-right: 1rem;
    }
}

/* セレクトボックスのデザイン */
.stSelectbox > div > div {
    background-color: #ffffff;
    border-radius: 10px;
    border: 1px solid #bcd4ff;
}

/* グラフの背景 */
.js-plotly-plot {
    background-color: #ffffff !important;
    border-radius: 12px;
    padding: 10px;
}

/* テーブルの文字色 */
table {
    color: #003366;
}

/* テーブルヘッダー */
thead th {
    background-color: #d8e7ff !important;
    color: #003366 !important;
}

/* ボタン */
.stButton>button {
    background-color: #0a4da8;
    color: white;
    border-radius: 10px;
    padding: 10px 20px;
    font-weight: 600;
}

</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 90日予報（Open-Meteo / 簡易版）
# ---------------------------------------------------------
def get_90days(lat, lon):

    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": [
            "weather_code",
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_probability_max",
            "wind_speed_10m_max",
        ],
        "forecast_days": 90,
        "timezone": "Asia/Tokyo"
    }

    res = requests.get(BASE_URL, params=params)
    res.raise_for_status()
    data = res.json()

    daily = data["daily"]

    df = pd.DataFrame({
        "日付": daily["time"],
        "天気": [weather_icon(i) for i in daily["weather_code"]],
        "最高気温": daily["temperature_2m_max"],
        "最低気温": daily["temperature_2m_min"],
        "降水確率": daily["precipitation_probability_max"],
        "風速": daily["wind_speed_10m_max"],
    })

    return df

from weather import get_weather, get_hourly, get_current_weather, get_90days


