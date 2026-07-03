import streamlit as st
import plotly.express as px

from mountains import mountains
from weather import get_weather, get_current_weather
from danger import judge, recommend
from equipment import equipment
from mountain import summit_temp

# ---------------------------------------------------------
# Streamlit 基本設定
# ---------------------------------------------------------
st.set_page_config(
    page_title="Mountain Weather AI",
    page_icon="🏔",
    layout="wide"
)

st.title("🏔 Mountain Weather AI Pro")
st.caption("登山専用AI天気アプリ")
st.divider()

# ---------------------------------------------------------
# 山選択
# ---------------------------------------------------------
mountain = st.selectbox("山を選択", mountains.keys())

lat = mountains[mountain]["lat"]
lon = mountains[mountain]["lon"]
height = mountains[mountain]["height"]

st.info(f"標高 {height} m")

# ---------------------------------------------------------
# OpenWeatherMap 現在の天気
# ---------------------------------------------------------
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

st.divider()

# ---------------------------------------------------------
# Open-Meteo 14日予報
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

st.markdown("---")

# ---------------------------------------------------------
# 日付選択
# ---------------------------------------------------------
selected_date = st.selectbox("📅 日付を選択してください", df["日付"])
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

weather = today["天気"]  # ☀️ 🌤 ☁️ 🌧 ❄️ など

if today["風速"] >= 15:
    comment = "🔴 強風です。登山は危険なので延期をおすすめします。"

elif weather in ["🌧", "🌦", "⛈"]:
    comment = "🌧 雨の可能性があります。防水対策をしっかり行いましょう。"

elif today["降水確率"] >= 50:
    comment = "☔ 雨具を必ず持参してください。"

elif today["最高気温"] >= 30:
    comment = "🥵 気温が高いので熱中症対策を万全に。"

elif weather in ["❄️"]:
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
# 装備提案
# ---------------------------------------------------------
st.subheader("🥾 AI装備提案")
for g in gear:
    st.success(g)

# ---------------------------------------------------------
# 14日予報
# ---------------------------------------------------------
st.subheader("14日予報")
st.dataframe(df, use_container_width=True, hide_index=True)

# ---------------------------------------------------------
# グラフ
# ---------------------------------------------------------
st.subheader("最高気温")
fig = px.line(df, x="日付", y="最高気温", markers=True)
st.plotly_chart(fig, use_container_width=True)

st.subheader("風速")
fig = px.bar(df, x="日付", y="風速")
st.plotly_chart(fig, use_container_width=True)

st.subheader("降水確率")
fig = px.bar(df, x="日付", y="降水確率")
st.plotly_chart(fig, use_container_width=True)
