import streamlit as st
import plotly.express as px
import folium
from streamlit_folium import st_folium
import pandas as pd

from mountains import mountains
from weather import get_weather
from danger import judge, recommend
from equipment import equipment
from mountain import summit_temp

st.set_page_config(page_title="Mountain Weather AI", page_icon="🏔", layout="wide")
st.title("🏔 Mountain Weather AI Pro")
st.caption("登山専用AI天気アプリ｜風速3指標対応")
st.divider()

def number_or_none(value):
    try:
        value = float(value)
        return value if pd.notna(value) else None
    except (TypeError, ValueError):
        return None

def fmt_speed(value):
    value = number_or_none(value)
    return f"{value:.1f} m/s" if value is not None else "データなし"

def wind_risk(avg_wind=None, max_wind=None, gust_wind=None):
    """アプリ用の安全側の目安。公的な統一基準ではありません。"""
    avg, maximum, gust = map(number_or_none, (avg_wind, max_wind, gust_wind))
    # 風速データが欠損している場合、穏やかと誤判定しない
    available = [v for v in (avg, maximum, gust) if v is not None]
    if not available:
        return "判定不能", 0, "風速データが取得できません。予報を確認できるまで登山判断を保留してください。"
    if (avg is not None and avg >= 20) or (maximum is not None and maximum >= 20) or (gust is not None and gust >= 30):
        return "極めて危険", 1, "🔴 強風予報です。登山中止を強く推奨します。"
    if (avg is not None and avg >= 15) or (maximum is not None and maximum >= 15) or (gust is not None and gust >= 25):
        return "非常に高い", 1, "🔴 強風予報です。登山中止を推奨します。"
    if (avg is not None and avg >= 10) or (maximum is not None and maximum >= 10) or (gust is not None and gust >= 20):
        return "高い", 2, "🟠 強風に警戒し、登山計画の再検討を推奨します。"
    if (avg is not None and avg >= 5) or (maximum is not None and maximum >= 5) or (gust is not None and gust >= 10):
        return "注意", 3, "🟡 風の状況に注意してください。山頂の最新予報も確認してください。"
    return "比較的低い", 5, "風速以外に、降水・雷・気温・登山道情報も確認してください。"

def combined_recommendation(wind_score, rain, high_temp, weather_code=None):
    rain = number_or_none(rain)
    high_temp = number_or_none(high_temp)
    if wind_score <= 1:
        return "★☆☆☆☆"
    if rain is not None and rain >= 80:
        return "★☆☆☆☆"
    if wind_score == 2 or (rain is not None and rain >= 50):
        return "★★☆☆☆"
    if high_temp is not None and high_temp >= 30:
        return "★★☆☆☆"
    if rain is not None and rain < 30 and wind_score >= 4:
        return "★★★★★"
    return "★★★☆☆"

mountain = st.selectbox("山を選択", list(mountains.keys()))
data = mountains[mountain]
base = {"lat": data["lat"], "lon": data["lon"], "height": data["height"], "name": mountain, "type": "山頂"}
locations = data.get("locations") or []
points = []
if locations:
    for p in locations:
        if "lat" in p and "lon" in p:
            points.append({"name": p.get("name", "名称不明"), "type": p.get("type", "地点"),
                           "lat": p["lat"], "lon": p["lon"], "height": p.get("height")})
elif data.get("points"):
    for p in data["points"]:
        points.append({"name": p.get("name", "名称不明"), "type": p.get("type", "予報地点"),
                       "lat": p["lat"], "lon": p["lon"], "height": p.get("height")})
else:
    points = [base]

seen, forecast_points = set(), []
for p in points:
    key = (p["name"], round(p["lat"], 6), round(p["lon"], 6))
    if key not in seen:
        seen.add(key)
        forecast_points.append(p)

labels = [f"{p['type']}｜{p['name']}" for p in forecast_points]
selected_label = st.selectbox("📍 予報地点を選択", labels)
selected = forecast_points[labels.index(selected_label)]
lat, lon = selected["lat"], selected["lon"]
height = selected.get("height") or data["height"]
st.info(f"📍 {selected['name']} ｜ {selected['type']} ｜ 標高 {height} m ｜ {lat:.5f}, {lon:.5f}")

st.subheader("🗺️ 登山マップ")
map_locations = locations or forecast_points
location_types = ["山頂", "山小屋", "登山口", "テント場", "避難小屋"]
available = [t for t in location_types if any(p.get("type") == t for p in map_locations)]
selected_types = st.multiselect("表示する地点", location_types, default=available or location_types)
m = folium.Map(location=[lat, lon], zoom_start=13, control_scale=True)
icons = {"山頂": ("flag", "fa", "red"), "山小屋": ("home", "fa", "green"),
         "登山口": ("sign-in", "fa", "blue"), "テント場": ("cloud", "fa", "orange"),
         "避難小屋": ("warning-sign", "glyphicon", "purple")}
for p in map_locations:
    typ = p.get("type", "山頂")
    if typ not in selected_types or "lat" not in p or "lon" not in p:
        continue
    icon, prefix, color = icons.get(typ, ("info-sign", "glyphicon", "gray"))
    h = p.get("height")
    htxt = f"{h} m" if h is not None else "標高不明"
    selected_here = p.get("name") == selected["name"] and abs(p["lat"]-lat) < 1e-5 and abs(p["lon"]-lon) < 1e-5
    popup = f"""<div style="min-width:220px;background:#fff;color:#111;padding:8px;font-family:Arial,sans-serif"><b>{'⭐ 現在の予報地点' if selected_here else typ}</b><br>{p.get('name','名称不明')}<br>標高：{htxt}<br>緯度：{p['lat']:.5f}<br>経度：{p['lon']:.5f}</div>"""
    folium.Marker([p["lat"], p["lon"]], popup=folium.Popup(popup, max_width=320),
                  tooltip=f"{typ}｜{p.get('name','名称不明')}",
                  icon=folium.Icon(color=color, icon=icon, prefix=prefix)).add_to(m)
folium.CircleMarker([lat, lon], radius=9, color="black", weight=3, fill=False,
                    tooltip="⭐ 現在の予報地点").add_to(m)
legend = """<div style="position:fixed;bottom:20px;left:20px;z-index:9999;background:#fff;color:#111;padding:12px 16px;border:2px solid #555;border-radius:10px;font:14px/1.9 Arial,sans-serif"><b>🏔️ 登山マップ</b><br>🔴 山頂<br>🟢 山小屋<br>🔵 登山口<br>🟠 テント場<br>🟣 避難小屋</div>"""
m.get_root().html.add_child(folium.Element(legend))
st_folium(m, use_container_width=True, height=500, returned_objects=[])

st.subheader("🌦️ 予報データ")
try:
    df = get_weather(lat, lon)
except Exception as exc:
    st.error(f"天気予報を取得できませんでした: {exc}")
    st.stop()

# 互換性: 旧weather.pyが「風速」列を返しても動作する
if "最大風速" not in df.columns and "風速" in df.columns:
    df["最大風速"] = df["風速"]
if "最大風速" not in df.columns:
    df["最大風速"] = None
if "最大瞬間風速" not in df.columns:
    df["最大瞬間風速"] = None

# 旧コード/既存の下流処理との互換列
df["風速"] = df["最大風速"]

recommendations, risk_names, wind_scores, comments = [], [], [], []
for _, row in df.iterrows():
    wind_label, wind_score, wind_comment = wind_risk(
        avg_wind=None, max_wind=row.get("最大風速"), gust_wind=row.get("最大瞬間風速")
    )
    rain = number_or_none(row.get("降水確率"))
    high = number_or_none(row.get("最高気温"))
    if wind_score <= 1:
        comment = wind_comment
    elif rain is not None and rain >= 80:
        comment = "🌧️ 降水確率が高いため、登山中止を含めて再検討してください。"
    elif rain is not None and rain >= 50:
        comment = "☔ 雨具が必要です。降水の時間帯と雷予報も確認してください。"
    elif high is not None and high >= 30:
        comment = "🥵 熱中症対策として十分な水分を持参しましょう。"
    else:
        comment = wind_comment
    recommendations.append(combined_recommendation(wind_score, rain, high))
    risk_names.append(wind_label)
    wind_scores.append(wind_score)
    comments.append(comment)

df["おすすめ"] = recommendations
df["風の危険度"] = risk_names
df["風判定スコア"] = wind_scores
df["AIコメント"] = comments

selected_date = st.selectbox("📅 日付を選択してください", df["日付"].astype(str).tolist())
today = df[df["日付"].astype(str) == selected_date].iloc[0]

st.markdown("## 📢 Today's Topics")
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(f"# {today['天気']}")
    st.metric("最高気温", f"{today['最高気温']}℃")
    st.metric("最低気温", f"{today['最低気温']}℃")
with c2:
    st.metric("最大風速（10m高度）", fmt_speed(today["最大風速"]))
    st.metric("最大瞬間風速（10m高度）", fmt_speed(today["最大瞬間風速"]))
    st.metric("降水確率", f"{today['降水確率']}%")
with c3:
    st.metric("おすすめ", today["おすすめ"])
    st.metric("風の危険度", today["風の危険度"])

st.caption("風速はOpen-Meteoの10m高度の予報値です。山頂の実測値ではなく、地形による増速・突風を完全には表現しません。")

st.markdown("### 🤖 AIコメント")
st.info(today["AIコメント"])

# 既存の危険度モジュールが例外を起こしても、風判定を優先して表示する
try:
    danger_label, score = judge(
        number_or_none(today["最大風速"]) if number_or_none(today["最大風速"]) is not None else 0,
        number_or_none(today["降水確率"]) if number_or_none(today["降水確率"]) is not None else 0
    )
except Exception:
    danger_label, score = today["風の危険度"], int(today["風判定スコア"] * 20)

# 風の判定が厳しい場合、既存judgeの甘い判定で上書きしない
wind_score = int(today["風判定スコア"])
if wind_score <= 1:
    danger_label, score, star = today["風の危険度"], min(int(score), 30), "★☆☆☆☆"
elif wind_score == 2:
    danger_label, score, star = today["風の危険度"], min(int(score), 50), "★★☆☆☆"
else:
    star = today["おすすめ"]

summit = summit_temp(number_or_none(today["最高気温"]) or 0, height)
gear = equipment(summit, number_or_none(today["最大風速"]) or 0,
                 number_or_none(today["降水確率"]) if number_or_none(today["降水確率"]) is not None else 0)

cols = st.columns(4)
cols[0].metric("天気", today["天気"])
cols[1].metric("最高気温", f"{today['最高気温']}℃")
cols[2].metric("降水確率", f"{today['降水確率']}%")
cols[3].metric("最大風速", fmt_speed(today["最大風速"]))
cols = st.columns(4)
cols[0].metric("危険度", danger_label)
cols[1].metric("AIスコア", f"{score}点")
cols[2].metric("山頂気温（推定）", f"{summit}℃")
cols[3].metric("おすすめ度", star)
st.divider()

st.subheader("🌅 日の出・日の入り")
c1, c2 = st.columns(2)
sunrise, sunset = today["日の出"], today["日の入り"]
if hasattr(sunrise, "strftime"):
    c1.info(sunrise.strftime("%H:%M")); c2.info(sunset.strftime("%H:%M"))
else:
    c1.info(str(sunrise)[11:16]); c2.info(str(sunset)[11:16])

st.subheader("🥾 AI装備提案")
for g in gear:
    st.success(g)

st.subheader("14日予報")
display_cols = ["日付", "天気詳細", "最高気温", "最低気温", "降水確率", "最大風速", "最大瞬間風速", "おすすめ", "風の危険度"]
st.dataframe(df[display_cols], use_container_width=True, hide_index=True)

for title, kind, y in [
    ("最高気温", "line", "最高気温"),
    ("最大風速（10m高度）", "bar", "最大風速"),
    ("最大瞬間風速（10m高度）", "bar", "最大瞬間風速"),
    ("降水確率", "bar", "降水確率"),
]:
    st.subheader(title)
    fig = px.line(df, x="日付", y=y, markers=True) if kind == "line" else px.bar(df, x="日付", y=y)
    st.plotly_chart(fig, use_container_width=True)
