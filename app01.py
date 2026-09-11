import streamlit as st
import plotly.express as px
import folium
from streamlit_folium import st_folium

from mountains import mountains
from weather import get_weather

from danger import judge, recommend
from equipment import equipment
from mountain import summit_temp
legend_html = """
<div style="
    position: fixed;
    bottom: 20px;
    left: 20px;
    z-index: 9999;
    background-color: #ffffff !important;
    color: #222222 !important;
    padding: 12px 16px;
    border: 2px solid #555555;
    border-radius: 10px;
    font-size: 14px;
    line-height: 1.9;
    box-shadow: 0 3px 10px rgba(0,0,0,0.35);
">

<div style="
    color: #111111 !important;
    font-weight: bold;
    margin-bottom: 5px;
">
🏔️ 山マップ
</div>

<div style="color:#111111 !important;">
<span style="color:#e53935 !important; font-size:18px;">●</span>
山頂
</div>

<div style="color:#111111 !important;">
<span style="color:#43a047 !important; font-size:18px;">●</span>
山小屋
</div>

<div style="color:#111111 !important;">
<span style="color:#1e88e5 !important; font-size:18px;">●</span>
登山口
</div>

<div style="color:#111111 !important;">
<span style="color:#fb8c00 !important; font-size:18px;">●</span>
テント場
</div>

<div style="color:#111111 !important;">
<span style="color:#8e24aa !important; font-size:18px;">●</span>
避難小屋
</div>

</div>
"""

m.get_root().html.add_child(folium.Element(legend_html))


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
# 山選択・予報地点
# ---------------------------------------------------------
mountain = st.selectbox("山を選択", mountains.keys())

mountain_data = mountains[mountain]
lat = mountain_data["lat"]
lon = mountain_data["lon"]
height = mountain_data["height"]

# 複数予報地点に対応
# mountains.py に "points" があれば、それを使用。
# なければ従来の lat/lon/height を1地点として使用します。
if "points" in mountain_data:
    forecast_points = mountain_data["points"]
else:
    forecast_points = [{
        "name": mountain,
        "lat": lat,
        "lon": lon,
        "height": height
    }]

point_names = [p["name"] for p in forecast_points]
selected_point_name = st.selectbox("📍 予報地点", point_names)

selected_point = next(
    p for p in forecast_points if p["name"] == selected_point_name
)

lat = selected_point["lat"]
lon = selected_point["lon"]
height = selected_point["height"]

st.info(
    f"📍 {selected_point['name']}　"
    f"標高 {height} m　"
    f"（{lat:.5f}, {lon:.5f}）"
)

# ---------------------------------------------------------
# 登山スポット・予報地点マップ
# ---------------------------------------------------------
st.subheader("🗺️ 登山マップ")

# mountains.py に "locations" があれば、
# 山頂・山小屋・登山口・テント場をまとめて表示します。
# なければ従来の予報地点だけを表示します。
if "locations" in mountain_data:
    map_locations = mountain_data["locations"]
else:
    map_locations = [{
        "name": selected_point["name"],
        "lat": selected_point["lat"],
        "lon": selected_point["lon"],
        "height": selected_point["height"],
        "type": "山頂",
    }]

# 表示対象の種類
location_types = ["山頂", "山小屋", "登山口", "テント場"]
selected_types = st.multiselect(
    "表示する地点",
    location_types,
    default=location_types,
)

# 地図中心
m = folium.Map(
    location=[lat, lon],
    zoom_start=13,
    control_scale=True,
)

# 種類ごとのアイコン
icon_settings = {
    "山頂": {"icon": "flag", "prefix": "fa", "color": "red"},
    "山小屋": {"icon": "home", "prefix": "fa", "color": "green"},
    "登山口": {"icon": "sign-in", "prefix": "fa", "color": "blue"},
    "テント場": {"icon": "cloud", "prefix": "fa", "color": "orange"},
}

for point in map_locations:
    point_type = point.get("type", "山頂")

    if point_type not in selected_types:
        continue

    settings = icon_settings.get(
        point_type,
        {"icon": "info-sign", "prefix": "glyphicon", "color": "gray"},
    )

    height_text = (
        f"{point['height']} m"
        if point.get("height") is not None
        else "標高不明"
    )

    popup_html = f"""
    <div style="min-width:180px">
        <b>{point_type}：{point['name']}</b><br>
        標高：{height_text}<br>
        緯度：{point['lat']:.5f}<br>
        経度：{point['lon']:.5f}
    </div>
    """

    folium.Marker(
        location=[point["lat"], point["lon"]],
        popup=folium.Popup(popup_html, max_width=300),
        tooltip=f"{point_type}｜{point['name']}",
        icon=folium.Icon(
            color=settings["color"],
            icon=settings["icon"],
            prefix=settings["prefix"],
        ),
    ).add_to(m)

# 地図上に凡例を追加
legend_html = """
<div style="
position: fixed;
bottom: 20px;
left: 20px;
z-index: 9999;
background: white;
padding: 10px 12px;
border: 1px solid #999;
border-radius: 8px;
font-size: 13px;
line-height: 1.8;
">
<b>登山マップ</b><br>
🔴 山頂　🟢 山小屋<br>
🔵 登山口　🟠 テント場
</div>
"""

m.get_root().html.add_child(folium.Element(legend_html))

st_folium(
    m,
    use_container_width=True,
    height=500,
    returned_objects=[],
)

# ---------------------------------------------------------
# 天気データ取得
# ---------------------------------------------------------
df = get_weather(lat, lon)

# ---------------------------------------------------------
# おすすめ度を先に計算（UI に反映されるように）
# ---------------------------------------------------------
df["おすすめ"] = ""
for i in range(len(df)):
    rain = df.loc[i, "降水確率"]
    wind = df.loc[i, "風速"]

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

if today["風速"] >= 15:
    comment = "🔴 強風予報です。登山は延期をおすすめします。"
elif today["降水確率"] >= 80:
    comment = "🌧️ 雨の可能性が非常に高いため、防水対策が必要です。"
elif today["降水確率"] >= 50:
    comment = "☔ 雨具を必ず持参してください。"
elif today["最高気温"] >= 30:
    comment = "🥵 熱中症対策として十分な水分を持参しましょう。"
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

# 文字列なら安全にスライス、datetimeならフォーマット
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
