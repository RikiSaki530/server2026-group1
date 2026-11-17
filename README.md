# Temperature Temple

Nature Remo の温度・湿度などを収集して、ブラウザで確認するアプリです。
詳しい実装状況は [PROJECT_STATUS.md](PROJECT_STATUS.md) を参照してください。

## 初回の準備

Git と Docker をインストールし、Docker を起動しておきます。
Docker Desktop を使う場合は、メモリを 4 GB 以上に設定してください。

以下は macOS / Linux、Windows の WSL2 / Git Bash で実行するコマンドです。

### 1. ダウンロードする

```bash
git clone https://github.com/RikiSaki530/server2026-group1.git
cd server2026-group1
```

以降のコマンドも、このフォルダ内で実行します。

### 2. 設定ファイルを作る

```bash
cp -n .env.example .env
nano .env
```

`.env` の次の項目を書き換えます。他の項目はそのままで大丈夫です。

```dotenv
NATURE_TOKEN=自分のNature Remoのトークン
DEMO_MODE=false
```

`nano` では `Ctrl + O` → Enter で保存し、`Ctrl + X` で閉じます。
トークンは他の人に共有しないでください。

実機なしで試す場合は、代わりに次の設定にします。

```dotenv
NATURE_TOKEN=
DEMO_MODE=true
```

### 3. 起動する

```bash
docker compose up -d --build
```

初回は数分かかることがあります。

### 4. 画面を開く

自分の PC で起動した場合は、そのままブラウザで開きます。

- アプリ：[http://localhost:3000](http://localhost:3000)
- 分析画面（Kibana）：[http://localhost:5601](http://localhost:5601)

VM で起動した場合は、次の手順で開きます。

## VM で動かす場合

### 1. VM に接続する

自分の PC のターミナルで実行します。`ユーザー名` と `VMのIPアドレス` は自分の接続先に置き換えてください。

```bash
ssh ユーザー名@VMのIPアドレス
```

### 2. VM 上で準備・起動する

上の「初回の準備」の手順 1〜3 を VM 上で実行します。
VM にも Git と Docker が必要です。

### 3. 自分の PC から画面を開く

自分の PC で別のターミナルを開き、次を実行します。

```bash
ssh -L 3000:127.0.0.1:3000 -L 5601:127.0.0.1:5601 ユーザー名@VMのIPアドレス
```

このターミナルは接続したままにして、自分の PC のブラウザで開きます。

- アプリ：[http://localhost:3000](http://localhost:3000)
- 分析画面（Kibana）：[http://localhost:5601](http://localhost:5601)

## 更新する

起動した PC または VM のプロジェクトフォルダ内で実行します。

```bash
git pull
docker compose up -d --build
```

`.env` を変更したときも、次のコマンドで反映します。

```bash
docker compose up -d --build
```

## 停止・再開する

停止：

```bash
docker compose down
```

再開：

```bash
docker compose up -d --build
```

保存したデータを残すため、停止時に `-v` は付けないでください。

## 動かないとき

起動状態を確認します。

```bash
docker compose ps -a
```

`backend` と `elasticsearch` が `healthy`、ほかのサービスが起動中なら正常です。
`kibana-setup` の `Exited (0)` は正常です。

エラーの内容を確認します。

```bash
docker compose logs --tail=100
```
