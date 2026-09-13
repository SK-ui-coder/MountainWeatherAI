import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import folium
from streamlit_folium import st_folium


# =========================================================
# 山データ
# =========================================================
try:
    from mountains import mountains
except ImportError:
    try:
        from mountains import MOUNTAINS as mountains
    except ImportError as e:
        st.error("❌ mountains.py を読み込めません。")
        st.info(
            "mountains.py の中に "
            "mountains = {...} または MOUNTAINS = {...} "
            "があるか確認してください。"
        )
        st.exception(e)
        st.stop()


from weather import (
    get_weather,
    get_hourly,
    get_90days,
    get_14day_weather_change,
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


# =========================================================
# CSS
# =========================================================
st.markdown("""
<style>

body {
    background-color: #f5f7fa;
}

/* ===============================
   天気メインウィンドウ
================================ */

.weather-window {
    background: linear-gradient(
        145deg,
        #20252b,
        #343b43
    );

    color: white;

    border-radius: 24px;

    padding: 25px;

    margin-top: 10px;
    margin-bottom: 22px;

    box-shadow:
        0 10px 30px rgba(0,0,0,0.18);
}

.weather-location {
    font-size: 18px;
    font-weight: 700;
}

.weather-temp {
    font-size: 64px;
    font-weight: 700;
    line-height: 1;
    margin-top: 12px;
}

.weather-description {
    font-size: 20px;
    margin-top: 10px;
}

.weather-sub {
    font-size: 13px;
    color: #d5d9dd;
    margin-top: 8px;
}


/* ===============================
   時間別天気
================================ */

.hourly-window {

    display: flex;

    gap: 10px;

    overflow-x: auto;

    padding:
        15px
        2px
        12px
        2px;

    margin-top: 20px;

    -webkit-overflow-scrolling: touch;
}

.hour-card {

    flex: 0 0 105px;

    background:
        rgba(255,255,255,0.10);

    border:
        1px solid rgba(255,255,255,0.15);

    border-radius: 15px;

    padding: 12px;

    text-align: center;

    min-height: 145px;
}

.hour-time {
    font-size: 13px;
    font-weight: 700;
}

.hour-icon {
    font-size: 31px;
    margin: 8px 0;
}

.hour-temp {
    font-size: 19px;
    font-weight: 700;
}

.hour-rain {
    font-size: 12px;
    color: #d9dde1;
    margin-top: 7px;
}

.hour-wind {
    font-size: 11px;
    color: #c9ced3;
}


/* ===============================
   日別予報
================================ */

.day-scroll {

    display: flex;

    gap: 10px;

    overflow-x: auto;

    padding:
        8px
        2px
        16px
        2px;

    -webkit-overflow-scrolling: touch;
}

.day-card {

    flex:
        0 0 125px;

    background: white;

    border:
        1px solid #e0e4e8;

    border-radius: 17px;

    padding: 13px;

    text-align: center;

    box-shadow:
        0 3px 10px rgba(0,0,0,0.06);
}

.day-card.today {

    border:
        2px solid #555;

    background:
        #f1f4f7;
}

.day-date {
    font-size: 13px;
    font-weight: 700;
}

.day-icon {
    font-size: 36px;
    margin: 7px 0;
}

.day-weather {
    font-size: 13px;
    font-weight: 700;
    min-height: 38px;
}

.day-high {
    font-size: 19px;
    font-weight: 700;
}

.day-low {
    color: #777;
    font-size: 13px;
}

.day-rain {
    color: #555;
    font-size: 12px;
    margin-top: 7px;
}


/* ===============================
   判定ウィンドウ
================================ */

.judgement-window {

    background: white;

    border-radius: 18px;

    padding: 20px;

    border:
        1px solid #e1e4e8;

    box-shadow:
        0 3px 12px rgba(0,0,0,0.07);

    margin-bottom: 18px;
}

.judgement-title {
    font-size: 18px;
    font-weight: 700;
}

.judgement-main {
    font-size: 25px;
    font-weight: 800;
    margin-top: 8px;
}

.judgement-reason {
    color: #666;
    font-size: 14px;
    margin-top: 7px;
}


/* ===============================
   装備
================================ */

.equipment-window {

    background: white;

    border-radius: 18px;

    padding: 20px;

    border:
        1px solid #e1e4e8;

    box-shadow:
        0 3px 12px rgba(0,0,0,0.07);

    margin-bottom: 20px;
}


/* ===============================
   スクロールバー
================================ */

.hourly-window::-webkit-scrollbar,
.day-scroll::-webkit-scrollbar {
    height: 7px;
}

.hourly-window::-webkit-scrollbar-thumb,
.day-scroll::-webkit-scrollbar-thumb {
    background: #aaa;
    border-radius: 10px;
}

.hourly-window::-webkit-scrollbar-track,
.day-scroll::-webkit-scrollbar-track {
    background: #eee;
    border-radius: 10px;
}


/* ===============================
   スマホ
================================ */

@media (max-width: 768px) {

    .weather-temp {
        font-size: 52px;
    }

    .weather-window {
        padding: 20px;
        border-radius: 20px;
    }

    .hour-card {
        flex: 0 0 95px;
    }

    .day-card {
        flex: 0 0 115px;
    }

}

</style>
""", unsafe_allow_html=True)


# =========================================================
# 関数
# =========================================================

def get_weather_icon(text):
    """天気文字列からアイコンを決定"""

    text = str(text)

    if "雷" in text:
        return "⛈️"

    if "雪" in text:
        return "❄️"

    if "雨" in text:
        if "晴" in text or "曇" in text:
            return "🌦️"
        return "🌧️"

    if "曇" in text:
        if "晴" in text:
            return "🌤️"
        return "☁️"

    if "晴" in text:
        return "☀️"

    return "🌤️"


def number_value(value, default=0):
    """数値変換"""

    try:
        return float(value)
    except:
        return default


def hiking_judgement(df):
    """天気から登山判定"""

    if len(df) == 0:
        return (
            "🟡 判定不能",
            "天気データがありません。",
            0
        )

    rain = number_value(
        df["降水確率"].max()
    )

    wind = number_value(
        df["風速"].max()
    )

    low = number_value(
        df.iloc[0]["最低気温"],
        20
    )

    score = 0

    if rain >= 70:
        score += 3
    elif rain >= 50:
        score += 2
    elif rain >= 30:
        score += 1

    if wind >= 50:
        score += 3
    elif wind >= 35:
        score += 2
    elif wind >= 25:
        score += 1

    if low <= 0:
        score += 3
    elif low <= 5:
        score += 2
    elif low <= 10:
        score += 1

    if score >= 6:
        return (
            "🔴 登山非推奨",
            "雨・強風・低温などの悪条件が重なっています。",
            score
        )

    if score >= 4:
        return (
            "🟠 注意して登山",
            "気象条件が厳しいため、慎重な行動が必要です。",
            score
        )

    if score >= 2:
        return (
            "🟡 条件付きで登山可能",
            "天候の変化に注意してください。",
            score
        )

    return (
        "🟢 登山おすすめ",
        "大きな気象リスクは比較的少ない予報です。",
        score
    )


def equipment_judgement(df):
    """天気から必要装備を判定"""

    if len(df) == 0:
        return [], []

    rain = number_value(
        df["降水確率"].max()
    )

    wind = number_value(
        df["風速"].max()
    )

    low = number_value(
        df.iloc[0]["最低気温"],
        20
    )

    items = [
        "登山靴",
        "レインウェア",
        "ヘッドライト",
    ]

    reasons = []

    if rain >= 30:
        items.append("防水スタッフバッグ")
        reasons.append(
            f"☔ 降水確率 {rain:.0f}%"
        )

    if wind >= 25:
        items.append("ウインドシェル")
        reasons.append(
            f"💨 最大風速 {wind:.0f} km/h"
        )

    if low <= 10:
        items.append("防寒着")
        reasons.append(
            f"🌡️ 最低気温 {low:.0f}℃"
        )

    if low <= 5:
        items.append("手袋")
        items.append("ニット帽")

    return items, reasons


# =========================================================
# タイトル
# =========================================================

st.title("⛰️ Mountain Weather AI Pro")

st.caption(
    "山の天気を見て、登山できるか・何を持っていくかまで判定"
)


# =========================================================
# 山選択
# =========================================================

mountain = st.selectbox(
    "🏔️ 山を選択",
    list(mountains.keys())
)

data = mountains[mountain]


# =========================================================
# 予報地点
# =========================================================

forecast_points = data.get(
    "locations",
    []
)

if not forecast_points:

    forecast_points = [{
        "name": mountain,
        "type": "山頂",
        "lat": data["lat"],
        "lon": data["lon"],
        "height": data["height"],
    }]


labels = [
    f"{p.get('type', '予報地点')}｜{p['name']}"
    for p in forecast_points
]


selected_label = st.selectbox(
    "📍 予報地点",
    labels
)

selected = forecast_points[
    labels.index(selected_label)
]


lat = float(selected["lat"])
lon = float(selected["lon"])

height = float(
    selected.get(
        "height",
        data["height"]
    )
)


st.caption(
    f"📍 {selected['name']}　"
    f"標高 {height:.0f}m"
)


# =========================================================
# 天気取得
# =========================================================

try:

    df = get_weather(
        lat,
        lon
    )

    hourly = get_hourly(
        lat,
        lon
    )

    change_df = get_14day_weather_change(
        lat,
        lon
    )

except Exception as e:

    st.error(
        f"天気予報の取得に失敗しました：{e}"
    )

    st.stop()


# =========================================================
# 今日の情報
# =========================================================

if len(df) > 0:

    today = df.iloc[0]

    high = today.get(
        "最高気温",
        "-"
    )

    low = today.get(
        "最低気温",
        "-"
    )

    rain = today.get(
        "降水確率",
        "-"
    )

    wind = today.get(
        "風速",
        "-"
    )

    today_weather = today.get(
        "天気詳細",
        today.get("天気", "")
    )

else:

    high = "-"
    low = "-"
    rain = "-"
    wind = "-"
    today_weather = ""


# =========================================================
# 🥾 登山判定
# =========================================================

judge_text, judge_reason, judge_score = \
    hiking_judgement(df)


# =========================================================
# 🌦️ メイン天気ウィンドウ
# =========================================================

st.markdown(
    f"""
<div class="weather-window">

    <div class="weather-location">
        ⛰️ {mountain}
    </div>

    <div style="font-size:13px;color:#cfd4d8;margin-top:4px;">
        📍 {selected['name']}　標高 {height:.0f}m
    </div>

    <div class="weather-temp">
        {high}℃
    </div>

    <div class="weather-description">
        {get_weather_icon(today_weather)}
        {today_weather}
    </div>

    <div class="weather-sub">
        🌡️ 最低 {low}℃
       　☔ 降水 {rain}%
       　💨 最大風速 {wind} km/h
    </div>

""",
    unsafe_allow_html=True
)


# =========================================================
# 🌦️ 1日の天気の流れ
# =========================================================

if len(hourly) > 0:

    h = hourly.copy()

    h["時刻"] = pd.to_datetime(
        h["時刻"],
        errors="coerce"
    )

    h = h.dropna(
        subset=["時刻"]
    )

    if len(h) > 0:

        target_date = h["時刻"].dt.date.iloc[0]

        today_hourly = h[
            h["時刻"].dt.date == target_date
        ].copy()

        # 3時間おき
        today_hourly = today_hourly.iloc[::3]

        hour_cards = []

        for _, row in today_hourly.iterrows():

            time_text = row["時刻"].strftime(
                "%H:%M"
            )

            weather = row.get(
                "天気詳細",
                row.get("天気", "")
            )

            icon = get_weather_icon(
                weather
            )

            temp = row.get(
                "気温",
                "-"
            )

            rain_hour = row.get(
                "雨量",
                "-"
            )

            wind_hour = row.get(
                "風速",
                "-"
            )

            hour_cards.append(
                f"""
                <div class="hour-card">

                    <div class="hour-time">
                        {time_text}
                    </div>

                    <div class="hour-icon">
                        {icon}
                    </div>

                    <div class="hour-temp">
                        {temp}℃
                    </div>

                    <div class="hour-rain">
                        ☔ {rain_hour} mm
                    </div>

                    <div class="hour-wind">
                        💨 {wind_hour} km/h
                    </div>

                </div>
                """
            )

        st.markdown(
            '<div class="hourly-window">'
            + "".join(hour_cards)
            + "</div>",
            unsafe_allow_html=True
        )


# メインウィンドウ終了
st.markdown(
    "</div>",
    unsafe_allow_html=True
)


# =========================================================
# 🥾 登山判定ウィンドウ
# =========================================================

st.subheader("🥾 本日の登山判定")

st.markdown(
    f"""
<div class="judgement-window">

    <div class="judgement-title">
        登山コンディション
    </div>

    <div class="judgement-main">
        {judge_text}
    </div>

    <div class="judgement-reason">
        {judge_reason}
    </div>

</div>
""",
    unsafe_allow_html=True
)


# =========================================================
# 判定用詳細
# =========================================================

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "最高気温",
    f"{high}℃"
)

c2.metric(
    "最低気温",
    f"{low}℃"
)

c3.metric(
    "降水確率",
    f"{rain}%"
)

c4.metric(
    "最大風速",
    f"{wind} km/h"
)


# =========================================================
# 🎒 装備判定
# =========================================================

st.subheader("🎒 装備判定")

recommended_items, equipment_reasons = \
    equipment_judgement(df)


if equipment_reasons:

    st.warning(
        " / ".join(equipment_reasons)
    )

else:

    st.success(
        "🟢 大きな気象上の装備リスクはありません"
    )


st.markdown(
    '<div class="equipment-window">',
    unsafe_allow_html=True
)

st.write("### 推奨装備")


for item in recommended_items:

    st.checkbox(
        item,
        key=f"equipment_{mountain}_{selected['name']}_{item}"
    )


st.markdown(
    "</div>",
    unsafe_allow_html=True
)


# =========================================================
# 📅 14日予報
# =========================================================

st.subheader("📅 14日予報")


day_cards = []


for i, row in df.iterrows():

    date = str(
        row.get(
            "日付",
            ""
        )
    )

    weather = row.get(
        "天気詳細",
        row.get("天気", "")
    )

    icon = get_weather_icon(
        weather
    )

    # 時間変化データがあれば優先
    try:

        match = change_df[
            change_df["日付"].astype(str)
            == date
        ]

        if len(match) > 0:

            change = match.iloc[0]

            weather = change.get(
                "天気詳細",
                weather
            )

            icon = get_weather_icon(
                weather
            )

    except Exception:
        pass


    card_class = "day-card"

    if i == 0:
        card_class += " today"


    day_cards.append(
        f"""
        <div class="{card_class}">

            <div class="day-date">
                {date}
            </div>

            <div class="day-icon">
                {icon}
            </div>

            <div class="day-weather">
                {weather}
            </div>

            <div class="day-high">
                {row.get('最高気温', '-')}℃
            </div>

            <div class="day-low">
                最低 {row.get('最低気温', '-')}℃
            </div>

            <div class="day-rain">
                ☔ {row.get('降水確率', '-')}%
            </div>

        </div>
        """
    )


st.markdown(
    '<div class="day-scroll">'
    + "".join(day_cards)
    + "</div>",
    unsafe_allow_html=True
)


# =========================================================
# 🌡️ 1日の気温グラフ
# =========================================================

st.subheader("🌡️ 1日の気温変化")


if len(hourly) > 0:

    h_graph = hourly.copy()

    h_graph["時刻"] = pd.to_datetime(
        h_graph["時刻"],
        errors="coerce"
    )

    h_graph = h_graph.dropna(
        subset=["時刻"]
    )

    if "気温" in h_graph.columns:

        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=h_graph["時刻"],
                y=h_graph["気温"],
                mode="lines+markers",
                name="気温",
                line=dict(width=3),
                marker=dict(size=6),
            )
        )

        fig.update_layout(

            height=330,

            margin=dict(
                l=10,
                r=10,
                t=20,
                b=20
            ),

            hovermode="x unified",

            xaxis_title="",

            yaxis_title="気温 ℃",

            showlegend=False,
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )


# =========================================================
# 📈 14日気温
# =========================================================

st.subheader("📈 14日間の気温推移")


if len(df) > 0:

    fig14 = go.Figure()

    fig14.add_trace(
        go.Scatter(
            x=df["日付"],
            y=df["最高気温"],
            mode="lines+markers",
            name="最高気温",
        )
    )

    fig14.add_trace(
        go.Scatter(
            x=df["日付"],
            y=df["最低気温"],
            mode="lines+markers",
            name="最低気温",
        )
    )

    fig14.update_layout(
        height=330,
        margin=dict(
            l=10,
            r=10,
            t=20,
            b=20
        ),
        hovermode="x unified",
        xaxis_title="",
        yaxis_title="気温 ℃",
    )

    st.plotly_chart(
        fig14,
        use_container_width=True
    )


# =========================================================
# 🏔️ 山頂気温
# =========================================================

st.subheader("🏔️ 山頂気温の目安")

try:

    ground_temp = float(
        df.iloc[0]["最高気温"]
    )

    summit = summit_temp(
        ground_temp,
        height
    )

    st.metric(
        "山頂予想気温",
        f"{summit:.1f}℃"
    )

except Exception:

    st.info(
        "山頂気温を計算できませんでした。"
    )


# =========================================================
# 🗺️ 登山地点マップ
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

    ptype = p.get(
        "type",
        "その他"
    )

    color, icon = colors.get(
        ptype,
        ("gray", "info-sign")
    )


    folium.Marker(

        [
            p["lat"],
            p["lon"]
        ],

        popup=folium.Popup(
            f"""
            <b>{p['name']}</b><br>
            種類：{ptype}<br>
            標高：{p.get('height', '-')}m
            """,
            max_width=250
        ),

        icon=folium.Icon(
            color=color,
            icon=icon
        ),

    ).add_to(m)


folium.CircleMarker(

    [
        lat,
        lon
    ],

    radius=9,

    color="black",

    fill=True,

    fill_opacity=0.15,

    popup=(
        f"現在の予報地点："
        f"{selected['name']}"
    ),

).add_to(m)


st_folium(
    m,
    width=None,
    height=560,
    returned_objects=[]
)


# =========================================================
# 📆 90日予報
# =========================================================

with st.expander(
    "📆 90日予報を表示"
):

    try:

        df90 = get_90days(
            lat,
            lon
        )

        st.dataframe(
            df90,
            use_container_width=True,
            hide_index=True
        )

    except Exception as e:

        st.error(
            f"90日予報の取得に失敗しました：{e}"
        )
