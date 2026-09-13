import streamlit as st
import plotly.express as px
import folium
from streamlit_folium import st_folium

from mountains import mountains
from weather import get_weather
from danger import judge, recommend
from equipment import equipment
from mountain import summit_temp

st.set_page_config(page_title='Mountain Weather AI', page_icon='🏔', layout='wide')
st.title('🏔 Mountain Weather AI Pro')
st.caption('登山専用AI天気アプリ')
st.divider()

mountain = st.selectbox('山を選択', list(mountains.keys()))
data = mountains[mountain]

base = {'lat': data['lat'], 'lon': data['lon'], 'height': data['height'], 'name': mountain, 'type': '山頂'}
locations = data.get('locations') or []
points = []
if locations:
    for p in locations:
        if 'lat' in p and 'lon' in p:
            points.append({
                'name': p.get('name', '名称不明'), 'type': p.get('type', '地点'),
                'lat': p['lat'], 'lon': p['lon'], 'height': p.get('height')
            })
elif data.get('points'):
    for p in data['points']:
        points.append({
            'name': p.get('name', '名称不明'), 'type': p.get('type', '予報地点'),
            'lat': p['lat'], 'lon': p['lon'], 'height': p.get('height')
        })
else:
    points = [base]

# 同一地点の重複を除去
seen = set()
forecast_points = []
for p in points:
    key = (p['name'], round(p['lat'], 6), round(p['lon'], 6))
    if key not in seen:
        seen.add(key)
        forecast_points.append(p)

labels = [f"{p['type']}｜{p['name']}" for p in forecast_points]
selected_label = st.selectbox('📍 予報地点を選択', labels)
selected = forecast_points[labels.index(selected_label)]
lat, lon = selected['lat'], selected['lon']
height = selected.get('height') or data['height']

st.info(f"📍 {selected['name']}　｜ {selected['type']}　｜ 標高 {height} m　｜ {lat:.5f}, {lon:.5f}")

st.subheader('🗺️ 登山マップ')
map_locations = locations or forecast_points
location_types = ['山頂', '山小屋', '登山口', 'テント場', '避難小屋']
available = [t for t in location_types if any(p.get('type') == t for p in map_locations)]
selected_types = st.multiselect('表示する地点', location_types, default=available or location_types)

m = folium.Map(location=[lat, lon], zoom_start=13, control_scale=True)
icons = {
    '山頂': ('flag', 'fa', 'red'),
    '山小屋': ('home', 'fa', 'green'),
    '登山口': ('sign-in', 'fa', 'blue'),
    'テント場': ('cloud', 'fa', 'orange'),
    '避難小屋': ('warning-sign', 'glyphicon', 'purple'),
}

for p in map_locations:
    typ = p.get('type', '山頂')
    if typ not in selected_types or 'lat' not in p or 'lon' not in p:
        continue
    icon, prefix, color = icons.get(typ, ('info-sign', 'glyphicon', 'gray'))
    h = p.get('height')
    htxt = f'{h} m' if h is not None else '標高不明'
    selected_here = (p.get('name') == selected['name'] and abs(p['lat']-lat) < 1e-5 and abs(p['lon']-lon) < 1e-5)
    popup = f'''<div style="min-width:220px;background:#fff;color:#111;padding:8px;font-family:Arial,sans-serif"><b style="color:#111">{'⭐ 現在の予報地点' if selected_here else typ}</b><br><span style="color:#222">{p.get('name','名称不明')}<br>標高：{htxt}<br>緯度：{p['lat']:.5f}<br>経度：{p['lon']:.5f}</span></div>'''
    folium.Marker([p['lat'], p['lon']], popup=folium.Popup(popup, max_width=320), tooltip=f'{typ}｜{p.get("name","名称不明")}', icon=folium.Icon(color=color, icon=icon, prefix=prefix)).add_to(m)

folium.CircleMarker([lat, lon], radius=9, color='black', weight=3, fill=False, tooltip='⭐ 現在の予報地点').add_to(m)
legend = '''<div style="position:fixed;bottom:20px;left:20px;z-index:9999;background:#fff!important;color:#111!important;padding:12px 16px;border:2px solid #555;border-radius:10px;font:14px/1.9 Arial,sans-serif;box-shadow:0 3px 10px rgba(0,0,0,.35)"><b style="color:#111!important">🏔️ 登山マップ</b><br><span style="color:#e53935!important">●</span> 山頂<br><span style="color:#43a047!important">●</span> 山小屋<br><span style="color:#1e88e5!important">●</span> 登山口<br><span style="color:#fb8c00!important">●</span> テント場<br><span style="color:#8e24aa!important">●</span> 避難小屋</div>'''
m.get_root().html.add_child(folium.Element(legend))
st_folium(m, use_container_width=True, height=500, returned_objects=[])

# 選択した地点の座標で天気を取得
df = get_weather(lat, lon)
df['おすすめ'] = ''
for i in range(len(df)):
    rain, wind = df.loc[i, '降水確率'], df.loc[i, '風速']
    df.loc[i, 'おすすめ'] = '★★★★★' if rain < 30 and wind < 8 else ('★★★★☆' if rain < 50 else '★★☆☆☆')

selected_date = st.selectbox('📅 日付を選択してください', df['日付'])
today = df[df['日付'] == selected_date].iloc[0]

st.markdown('## 📢 Today\'s Topics')
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(f"# {today['天気']}")
    st.metric('最高気温', f"{today['最高気温']}℃")
    st.metric('最低気温', f"{today['最低気温']}℃")
with c2:
    st.metric('風速', f"{today['風速']} m/s")
    st.metric('降水確率', f"{today['降水確率']} %")
with c3:
    st.metric('おすすめ', today['おすすめ'])

st.markdown('### 🤖 AIコメント')
if today['風速'] >= 15:
    comment = '🔴 強風予報です。登山は延期をおすすめします。'
elif today['降水確率'] >= 80:
    comment = '🌧️ 雨の可能性が非常に高いため、防水対策が必要です。'
elif today['降水確率'] >= 50:
    comment = '☔ 雨具を必ず持参してください。'
elif today['最高気温'] >= 30:
    comment = '🥵 熱中症対策として十分な水分を持参しましょう。'
else:
    comment = '☀️ 登山に適したコンディションです。'
st.info(comment)

danger, score = judge(today['風速'], today['降水確率'])
star = recommend(score)
summit = summit_temp(today['最高気温'], height)
gear = equipment(summit, today['風速'], today['降水確率'])

cols = st.columns(4)
cols[0].metric('天気', today['天気']); cols[1].metric('最高', f"{today['最高気温']}℃"); cols[2].metric('降水', f"{today['降水確率']}%"); cols[3].metric('風', f"{today['風速']} m/s")
cols = st.columns(4)
cols[0].metric('危険度', danger); cols[1].metric('AIスコア', f'{score}点'); cols[2].metric('山頂気温', f'{summit}℃'); cols[3].metric('おすすめ度', star)
st.divider()

st.subheader('🌅 日の出・日の入り')
c1, c2 = st.columns(2)
sunrise, sunset = today['日の出'], today['日の入り']
if hasattr(sunrise, 'strftime'):
    c1.info(sunrise.strftime('%H:%M')); c2.info(sunset.strftime('%H:%M'))
else:
    c1.info(str(sunrise)[11:16]); c2.info(str(sunset)[11:16])

st.subheader('🥾 AI装備提案')
for g in gear: st.success(g)
st.subheader('14日予報')
st.dataframe(df, use_container_width=True, hide_index=True)
for title, kind, y in [('最高気温','line','最高気温'), ('風速','bar','風速'), ('降水確率','bar','降水確率')]:
    st.subheader(title)
    fig = px.line(df, x='日付', y=y, markers=True) if kind == 'line' else px.bar(df, x='日付', y=y)
    st.plotly_chart(fig, use_container_width=True)
