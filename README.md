# MountainWeatherAI
MountainWeatherAI/
│
├── app.py                 ← メイン画面
├── weather.py             ← 天気取得
├── mountains.py           ← 山データ
├── danger.py              ← 危険度判定
├── equipment.py           ← 装備提案
├── mountain.py            ← 山頂気温計算
├── calendar_view.py       ← カレンダー表示
├── map_view.py            ← 地図表示
├── route.py               ← コース情報
├── hydration.py           ← 必要水分量計算
├── packing.py             ← パッキング重量
├── ai_comment.py          ← AIコメント
├── database.py            ← SQLite
├── style.css              ← デザイン
├── requirements.txt
├── README.md
│
├── data/
│   ├── mountains.csv
│   ├── routes.csv
│   ├── gear.csv
│   └── huts.csv
│
├── images/
│
└── .streamlit/
    └── config.toml

さらに、GitHubのリリースを分けて管理すると開発しやすいです。

バージョン	内容
v1.0	14日天気・AIコメント
v1.1	カレンダー表示
v1.2	AI装備・危険度
v2.0	地図・GPX・登山口
v3.0	90日登山計画・AI分析
v4.0	登山記録・SQLite・クラウド同期

そして、README.md には完成イメージを載せておくと、あとから見返しやすくなります。

🏔 Mountain Weather AI

AIが登山計画をサポートするPythonアプリ

機能
✅ 14日天気予報
✅ 90日登山計画
✅ AI危険度判定
✅ AI装備提案
✅ 地図表示
✅ GPXルート
✅ パッキング重量計算
✅ 必要水分量計算
✅ 登山記録
私からの提案

このプロジェクトはかなり本格的なので、「完成版」を目標に設計していきましょう。

目標は、市販の登山アプリにも負けないレベルです。

🏔 山の天気
🗺 地図
📅 90日計画
🤖 AI分析
🥾 装備管理
🎒 パッキング
📷 登山記録
☁️ GitHubで管理
🌐 将来的にはWeb公開

この方針なら、長く育てられるプロジェクトになります。
