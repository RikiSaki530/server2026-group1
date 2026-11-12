# Temperature Temple — 現在の実装と技術構成

最終更新: 2026-11-12（日本時間）

この文書は、このリポジトリの実装状況をまとめたものです。サーバに反映されているバージョンや、各サービスの現在の稼働を保証するものではありません。起動・サーバへの反映手順は [README.md](README.md)、画面の要件は [UI_REQUIREMENTS.md](UI_REQUIREMENTS.md) を参照してください。

## 現在できること

| 機能 | 状態・内容 |
| --- | --- |
| Nature Remo からの取得 | Cloud API の `GET /1/devices` で、トークンから参照できる機器を取得。実機3台で確認済み |
| 定期収集 | 起動直後に収集し、その後は標準300秒間隔。設定可能、最小60秒 |
| 手動収集 | 「データを更新」ボタンで API から取得・保存し、画面を更新。定期収集のタイマーとは独立 |
| データ保存 | Elasticsearch に機器ごとのスナップショットを保存 |
| 現在値の表示 | 機器名、温度、湿度、照度、センサー更新日時、人感の最終検知日時 |
| 接続状態 | API の `online` に基づくオンライン／オフライン、接続確認日時を表示 |
| 未確認の表示 | 収集失敗時、確認から15分超過、接続情報のない旧データは「未確認」。未来の確認日時も未確認扱い |
| グラフ | 温度・湿度・照度、機器の比較、凡例による表示切り替え |
| 表示期間 | 30分・1時間・1日・1週間。前3つは5分平均、1週間は1時間平均 |
| 測定履歴 | 区間平均を表で表示。選択した指標に値がある最新100件 |
| 画面更新 | 保存済みデータを60秒ごとに再取得。自動の画面更新自体は Remo API を呼ばない |
| エラー表示 | 取得・保存の失敗、最終収集成功日時、API の回数制限を表示 |
| 多重実行の防止 | 手動取得中はボタンを無効化。バックエンドでも同一プロセス内の手動取得の同時実行を拒否 |
| デモ | 実測と別インデックスに過去24時間・3台分の生成データを用意。API は呼ばず、画面にデモと表示 |
| 分析 | Kibana の Data View を自動作成。Discover で検索・確認可能。Lens のグラフは手動作成 |
| 見た目 | PC・スマートフォン向けレイアウト、ライト／ダーク切り替え |

「オンライン」は取得時点に API が返した状態です。常時の疎通確認ではありません。データ取得の成功や温度センサーの更新とは分けて扱います。手動取得も Remo 本体のセンサー測定を強制する操作ではありません。

## 使用言語・フレームワーク

以下のバージョンは現時点の lockfile・requirements・Dockerfile・Compose の記載に基づきます。

| 担当 | 使用言語・ファイル形式 | 主な技術・バージョン |
| --- | --- | --- |
| Web UI | TypeScript、Vue SFC（HTML相当のテンプレートとCSSを含む） | Nuxt 4.6.4、Vue 3.5.45 |
| グラフ | TypeScript | Chart.js 4.6.1 |
| フロント側 API 中継 | TypeScript | Nuxt のサーバールート（Nitro / H3） |
| フロントの実行環境 | JavaScript 実行環境 | Node.js 24 系の Docker イメージ。package.json の指定は `^24.15.0 || >=26.0.0` |
| 型チェック | TypeScript | TypeScript 5.9.3、vue-tsc 3.3.14 |
| バックエンド API | Python | Python 3.12、FastAPI 0.115.12、Uvicorn 0.34.2 |
| 定期収集・Kibana 初期設定 | Python | Python 3.12、標準ライブラリ（urllib、datetime など） |
| データベース | JSON のドキュメントを HTTP API で保存・検索 | Elasticsearch 9.5.6 |
| 分析 UI | 既製サービスを使用 | Kibana 9.5.6 |
| コンテナ管理 | YAML、Dockerfile | Docker Compose、Docker |
| 設定・説明 | dotenv、JSON、Markdown | `.env`、package.json、各 `.md` |
| テスト | Python | 標準ライブラリの unittest、実行中 API への検証スクリプト |

YAML・JSON・Markdown は設定や文書に使う形式で、アプリ本体の主な実装言語は **TypeScript と Python** です。現在 PostgreSQL は使用していません。

## 全体構成とデータの流れ

```text
Nature Remo 本体 → Nature Remo Cloud
                         ↑
                         ├─ Python Collector（定期取得） ──┐
                         └─ FastAPI（手動取得） ──────────┤
                                                          ↓
                                                    Elasticsearch
                                                       ↑       ↑
                                                    FastAPI   Kibana
                                                       ↑
                                              Nuxt サーバールート
                                                       ↑
                                                  Nuxt の画面
```

- ブラウザは Nuxt の `/api/dashboard` と `/api/collect` にアクセスする。
- Nuxt がサーバ側で FastAPI の `/dashboard` と `/collect` に中継する。
- 定期取得と手動取得は `collector/main.py` の収集処理を共用する。
- Nature Remo のトークンは backend と collector にだけ渡し、ブラウザには渡さない。
- `kibana-setup` は Data View を初期化して終了する。`Exited (0)` は正常。

## データの保存構成

Elasticsearch では、テーブルに相当する単位を「インデックス」、1行に相当するデータを「ドキュメント」と呼びます。

| インデックス | 用途 |
| --- | --- |
| `temperature-readings-v1` | Nature Remo から取得した実測スナップショット |
| `temperature-demo-v1` | デモ用の生成データ |
| `temperature-collector-status-v1` | 収集の最終試行・最終成功日時、エラー、取得台数。モードのインデックス名をIDとして更新 |

測定データは **1台 × 1回の収集で1件**。3台の場合、定期収集・手動収集のたびに通常3件増えます。機器ごとに別インデックスを作らず、`device_id` で区別します。ドキュメントIDは機器IDと収集日時から生成し、同じ組み合わせの再保存は上書きします。

### 測定データの保存項目

| 項目 | Elasticsearch の型 | 内容 |
| --- | --- | --- |
| `@timestamp` | date | 収集日時（UTC）。画面は日本時間で表示 |
| `device_id` | keyword | 機器ID |
| `device_name` | keyword | 機器名 |
| `source` | keyword | `nature_remo` または `demo` |
| `online` | boolean | API 取得時点の接続状態。デモでは省略 |
| `temperature` | float | 温度（℃） |
| `humidity` | float | 湿度（%） |
| `illumination` | float | 照度の値 |
| `temperature_updated_at` | date | 温度センサー更新日時 |
| `humidity_updated_at` | date | 湿度センサー更新日時 |
| `illumination_updated_at` | date | 照度センサー更新日時 |
| `motion_detected_at` | date | 人感の最終検知日時 |

取得できない項目は省略します。同じ値が返っても、収集ごとのスナップショットとして保存します。**収集日時とセンサー更新日時は別**です。データと Kibana の保存情報は Docker volume に保持します。

### 現在は保存していない情報

`GET /1/devices` の応答全体を保存しているわけではありません。ファームウェアバージョン、シリアル番号、MACアドレス、機器の作成・更新日時、温湿度の補正値、ユーザー情報などは保存対象外です。人感イベントも日時だけを保存し、値自体は保存していません。

- `temperature_offset` / `humidity_offset` は温湿度の補正値だが、現在は保存・独自適用を行っていない。
- 測定値は API の `newest_events` から返された値をそのまま保存する。
- 返却値に補正が適用済みかどうかは、この実装では検証していない。
- 登録家電・エアコン設定などを取得する別 API は呼び出していない。

## 主要ファイル

| 場所 | 役割 |
| --- | --- |
| `compose.yaml` | 各サービス、接続先、ポート、volume、起動順を設定 |
| `frontend/app/app.vue` | ダッシュボード、操作、状態表示、レイアウト |
| `frontend/app/components/HistoryChart.vue` | Chart.js の履歴グラフ |
| `frontend/shared/types.ts` | 画面で使うデータ型 |
| `frontend/server/api/` | 表示用 GET と手動取得用 POST の中継 |
| `frontend/nuxt.config.ts` | Nuxt 設定・サーバ側の接続先 |
| `frontend/package-lock.json` | フロント依存関係の固定 |
| `backend/main.py` | ヘルスチェック、検索・集計、手動取得、接続状態の判定 |
| `collector/main.py` | Nature Remo の取得、正規化、保存、定期実行、デモ生成 |
| `collector/setup_kibana.py` | Kibana Data View の初期設定 |
| `common/storage.py` | インデックス・mapping、HTTP通信、保存処理 |
| `tests/` | 収集・手動取得・接続状態のテスト、期間別 API 検証 |
| `.env.example` | 必要な環境変数の例。実際の秘密情報は含めない |
| `database/init.sql` | 以前の構成用の空ファイル。現在の Compose では使用しない |

## 設定と運用の現状

| 環境変数 | 用途・標準値 |
| --- | --- |
| `NATURE_TOKEN` | Nature Remo の個人アクセストークン。実測取得に必要 |
| `COLLECTION_INTERVAL_SECONDS` | 定期収集の待機秒数。標準300、最小60 |
| `DEMO_MODE` | 標準 `false`。`true` でデモ用インデックスを使用 |
| `NUXT_PUBLIC_KIBANA_URL` | ブラウザから開く Kibana のURL。標準 `http://localhost:5601` |

- 標準の Compose は Nuxt を `127.0.0.1:3000`、Kibana を `127.0.0.1:5601` に公開する。
- FastAPI と Elasticsearch はホストにポートを公開せず、Compose 内から接続する。
- 現在の Elasticsearch は単一ノード・認証なしの開発構成。ログイン機能、公開用の認証・HTTPS は未実装。
- Remo 本体の電源・インターネット接続と、収集を実行するPCまたはサーバの稼働が必要。
- `.env` は Git 管理対象外。サーバごとに用意する。
- 2026-11-12 のローカル検証では、SSH転送とのポート競合を避けるため、一時 override で Nuxt を3001、Kibanaを5602に変更した。リポジトリの標準ポートは変更していない。
- 手動取得・オンライン表示はローカルで確認済み。このチャットでは Git への push・サーバへの反映は行っていないため、サーバ側に同じ機能があるかは別途確認が必要。

## 確認済みの範囲

2026-11-12 までの実装作業で以下を確認しました。この文書作成時にはコンテナの再起動や追加の API 取得は行っていません。

- 実機3台の定期収集、Elasticsearch への保存、Nuxt の現在値・グラフ・履歴表示。
- 手動ボタン操作後、実機3台分の3件が追加され、画面に反映されること。
- 実機3台のオンライン状態、既存インデックスへの `online` フィールド追加。
- Kibana Data View の作成と Discover での実測データ表示。
- デモの24時間履歴生成と、実測から分離した API 応答。
- 収集・手動取得・接続状態に関する unittest 16件。
- 4期間の API 応答と、不正な期間の拒否。
- Nuxt の型チェック・本番ビルド、Compose 設定の検証。

オフライン・未確認・取得エラーの分岐は自動テストで確認しています。実機の電源を切る試験は実施していません。

## 未実装・今後の検討事項

- 屋外気象データの収集と、室内外を同時刻で比較するグラフ。
- 温湿度の補正値・機器メタデータ・API 応答全体の保存。
- エアコンなどの家電情報の取得・操作、自動制御。
- 快適性の記録・分析、推奨室温・湿度の推定。
- Kibana の保存済みダッシュボードの自動作成。
- 自動バックアップ、保存期間の制限、古いデータの自動削除。
- 公開環境向けの認証・HTTPS、多ノード構成。
- サーバへの自動デプロイと常時監視。
