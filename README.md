# Temperature Temple

## 概要

Nature Remoを利用して室内の温度・湿度などを収集・可視化し、屋外の気象データと比較するIoT環境管理システム。

## 現在の実装状況

使用言語・技術構成、実装済み機能、保存データ、確認済みの範囲、未実装事項は [PROJECT_STATUS.md](PROJECT_STATUS.md) にまとめています。

## やりたいこと

- Nature Remo 3台からセンサーデータを取得する。
- 5分ごとにデータを自動収集し、デバイスごとに保存する。
- 温度・湿度・照度・人感など、取得可能な情報を記録する。
- Web UIで現在の環境と過去の測定履歴を確認できるようにする。
- 気象庁などの外部データソースから屋外の気温・湿度を取得する。
- 室内外の測定データを同時刻で比較できるようにする。

## 開発環境

- Frontend：Nuxt
- Backend：FastAPI
- Database：Elasticsearch
- Analytics：Kibana
- Data Collector：Python
- Docker Composeで各サービスを管理する。
- GitHubで共有し、各自のローカル環境および大学のVMで実行できるようにする。

## 今後の展望

蓄積した室内外の温湿度データを分析し、外気温の変化が室内環境にどのような影響を与えるかを調査する。

さらに、実際の快適性との関係を調べ、**快適に過ごせる室温・湿度を推定するシステム**を目指す。

最終的には、分析結果に基づいてNature Remoからエアコンなどを制御し、室内環境を自動管理できるようにする。

## クローンからの環境構築・起動

以下のコマンドは macOS / Linux のターミナル、または Windows の WSL2 / Git Bash で実行します。

### 1. 必要なツールを準備する

- Git
- Docker と Docker Compose v2（`docker compose` コマンド）
  - macOS / Windows：Docker Desktop をインストールし、起動しておきます。
  - Linux / 大学の VM：Docker Engine と Docker Compose プラグインをインストールし、Docker を起動しておきます。
- Docker Desktop の場合は少なくとも 4 GB のメモリを割り当ててください。

次のコマンドでインストールと Docker の起動を確認します。`docker info` が接続エラーになる場合は、Docker の起動状態や実行権限を確認してください。

```bash
git --version
docker --version
docker compose version
docker info
```

Python・Node.js・Elasticsearch などはコンテナ内に用意されるため、Docker で起動するだけならホストへの個別インストールは不要です。

### 2. リポジトリをクローンする

```bash
git clone https://github.com/RikiSaki530/server2026-group1.git
cd server2026-group1
```

非公開リポジトリの場合は、アクセス権のある GitHub アカウントで認証してください。SSH キーを設定済みの場合は、代わりに次のコマンドでもクローンできます。

```bash
git clone git@github.com:RikiSaki530/server2026-group1.git
cd server2026-group1
```

以降の `docker compose` コマンドは、`compose.yaml` のあるリポジトリ直下で実行します。

### 3. 環境変数を設定する

初回のみ `.env.example` をコピーし、エディタで `.env` を編集します。既存の `.env` は上書きしないでください。

```bash
cp -n .env.example .env
```

実機で収集する場合は、Nature Remo の個人アクセストークンを `NATURE_TOKEN` に設定します。そのトークンで参照できる Remo が自動で収集対象になります。

```dotenv
NATURE_TOKEN=取得した個人アクセストークン
COLLECTION_INTERVAL_SECONDS=300
DEMO_MODE=false
NUXT_PUBLIC_KIBANA_URL=http://localhost:5601
```

実機やトークンなしで動作確認する場合は、代わりに次の設定にします。

```dotenv
NATURE_TOKEN=
COLLECTION_INTERVAL_SECONDS=300
DEMO_MODE=true
NUXT_PUBLIC_KIBANA_URL=http://localhost:5601
```

トークンはブラウザに渡しません。`.env` は Git 管理対象外です。実際のトークンを README やソースコードに書き込まないでください。

### 4. ビルドして起動する

```bash
# Compose の設定を検証（環境変数の値は表示しない）
docker compose config --quiet
# イメージをビルドし、バックグラウンドで起動
docker compose up -d --build
```

初回はイメージのダウンロードとビルド、Elasticsearch・Kibana の初期化に数分かかることがあります。ホストのポート `3000` と `5601` が空いている必要があります。

### 5. 起動状態と画面を確認する

```bash
docker compose ps -a
docker compose logs --tail=100 collector kibana-setup
# FastAPI と Elasticsearch の接続確認
docker compose exec backend python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/health').read().decode())"
```

- Nuxt：<http://localhost:3000> を開き、デバイスの測定値が表示されることを確認します。デモ設定の場合はデモ表示と生成データを確認します。
- Kibana：<http://localhost:5601> を開きます。
- `backend` と `elasticsearch` が `healthy`、常駐サービスが起動中であれば正常です。`kibana-setup` は初期設定用なので、`Exited (0)` が正常終了です。
- API の接続確認で `{"status":"ok"}` が返ることを確認します。Nature Remo の収集成功は画面の収集状態と `collector` のログで別途確認してください。
- Elasticsearch と FastAPI は Compose 内だけで接続し、ホストにポートを公開しません。

起動できない場合は、次のコマンドで各サービスのログを確認します。

```bash
docker compose logs --tail=100 frontend backend elasticsearch kibana collector kibana-setup
```

初回収集は起動直後、以降は標準で 300 秒間隔です。`COLLECTION_INTERVAL_SECONDS` で変更できます（最小60秒）。画面は60秒ごとに保存済みデータを再取得します。「データを更新」ボタンでは、定期収集とは別に Nature Remo API からその時点の最新情報を取得・保存し、画面に反映します。取得中はボタンを無効化します。Remo 本体のセンサー測定を強制するものではないため、値やセンサー更新日時が変わらない場合もあります。

トークン未設定・APIエラー時は実測値を捏造せず、画面に収集状態と最終成功日時を表示します。

### 6. 停止・再起動する

```bash
# 停止（保存済みデータは volume に残る）
docker compose down
# 再起動、または .env・コードの変更を反映
docker compose up -d --build
```

`docker compose down -v` は保存済みデータも削除するため、通常の停止では使わないでください。

### データの流れ

```text
Nature Remo Cloud API → Python Collector → Elasticsearch
                                             ↑
                           Nuxt → FastAPI ────┤
                                   Kibana ────┘
```

すべての利用可能な Remo を自動で収集します。温度・湿度・照度を5分ごとのスナップショットとして保存し、各センサーの更新日時と人感の最終検知日時を別に保持します。センサーを搭載していない機種の値は欠損として扱います。`@timestamp` は収集日時です。同じセンサー値が返った場合も、その時点で取得したスナップショットとして記録します。

画面にはデバイス別の現在値、温度・湿度・照度の折れ線グラフ、測定履歴の表があります。期間は30分・1時間・1日・1週間。凡例を押すと比較するデバイスを切り替えられます。グラフは区間平均で、欠測区間は線で結びません。時刻は日本時間です。15分以上古い収集・温度センサー更新には表示を付けます。屋外気象データの取得と空調制御は未実装です。

### Kibana で分析する

`kibana-setup` が現在のモードに対応する Data View を自動作成します（正常終了後は `Exited (0)` で正常です）。

1. Kibana の Discover で `Temperature Temple` を選択。
2. 時間範囲を「過去24時間」などに変更。
3. Dashboard → Create dashboard → Create visualization で Lens を開く。
4. 横軸に `@timestamp`、縦軸に `temperature` の Average、系列に `device_name` を設定すると部屋別グラフになります。`humidity` や `illumination` も同様に追加できます。

実測インデックスは `temperature-readings-v1`、デモは `temperature-demo-v1`。収集状態は `temperature-collector-status-v1` に保存します。測定データは volume に保持します。`docker compose down -v` はデータも削除するため、通常の停止には `docker compose down` を使ってください。自動削除・保存期間の制限はまだ設定していません。

### デモで画面を試す

`.env` に `DEMO_MODE=true` を設定して `docker compose up -d --build` を実行します。過去24時間の3台分の生成データを初回のみ作成し、その後も5分ごとに追加します。Nature Remo API は呼び出しません。画面にデモと明示し、実測インデックスと分けて保存します。実測に戻す場合は `DEMO_MODE=false` に変更して再度起動してください。

### Git 経由でサーバへ反映する

ローカルでコード・Dockerfile・Compose・`frontend/package-lock.json` をコミットして push し、サーバで以下を実行します。サーバの `.env` は別途作成してください。

```bash
git pull
docker compose up -d --build
docker compose ps -a
docker compose logs --tail=100 collector kibana-setup
```

現在は認証なし・localhost 限定の閉じた開発構成です。サーバ上の画面は SSH トンネルで利用できます。

```bash
ssh -L 3000:127.0.0.1:3000 -L 5601:127.0.0.1:5601 user@server
```

接続中に手元のブラウザから上記 localhost URL を開きます。Webで外部公開する場合は、先にリバースプロキシの HTTPS・認証、Elasticsearch の認証・TLSを設定してください。Kibana のリンク先は `.env` の `NUXT_PUBLIC_KIBANA_URL` で変更できます。

### 開発と検証

```bash
docker compose run --rm --no-deps -v "$PWD/tests:/app/tests:ro" backend python -m unittest discover -s tests -v
# 起動中の API を全期間検証
docker compose exec -T backend python - < tests/smoke.py
cd frontend
# Node.js 24.15 以降（Docker ビルドでは Node.js 24 を利用）
npm ci
npm run typecheck
npm run build
```

API は手動収集の `POST /collect`、`GET /health`、`GET /dashboard?period=30m|1h|1d|1w` を提供します。Nuxt の `/api/dashboard` がサーバ側で FastAPI に中継します。


### デバイスの接続状態

Nature Remo Cloud API の `online` を収集・保存し、カードと最新値の表にオンライン／オフラインを表示します。これは API 取得時点の状態で、常時の疎通監視ではありません。手動取得または定期収集で更新します。取得失敗時、確認から15分以上経過、接続情報のない古いデータは「未確認」、生成データは「デモ」と表示します。接続確認日時を併記し、センサー更新日時・収集成功とは別に扱います。既存インデックスにも起動時に boolean 型の online フィールドを追加します。
