# ひかり塾 定期テスト演習 準備＆記録システム（バックエンド）

集団授業塾向けの「学校別・定期テスト演習」準備＆記録システムの MVP バックエンド（FastAPI + SQLAlchemy + SQLite）。
フロントエンドは別リポジトリ（`kikut/260915hackathon`, Next.js）。

## セットアップ

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
alembic upgrade head
python scripts/seed.py
uvicorn app.main:app --reload
```

起動後 `http://127.0.0.1:8000/docs` でAPIドキュメントを確認できます。

## 環境変数（`backend/.env`）

| 変数 | 説明 | デフォルト |
|---|---|---|
| `DATABASE_URL` | SQLite の接続文字列 | `sqlite:///./data/app.db` |
| `CORS_ORIGIN` | フロントエンドのオリジン（許可する1件） | `http://localhost:3000` |
| `GEMINI_API_KEY` | Gemini APIキー（LLM機能を使う場合のみ必須） | （空） |
| `GEMINI_MODEL` | Gemini モデルID | `gemini-3.5-flash` |
| `GEMINI_TIMEOUT_MS` | Gemini呼び出しのタイムアウト（ミリ秒） | `60000` |
| `REQUIRED_MULTIPLIER` | 問題バンクの必要数倍率 | `3` |
| `LOW_ACCURACY_NO_HINT_THRESHOLD` | 見直し候補フラグ：難易度1のヒントなし正答率しきい値 | `0.4` |
| `HIGH_WRONG_AFTER_HINT3_THRESHOLD` | 見直し候補フラグ：ヒント3でも誤答の割合しきい値 | `0.2` |

## DB について

PostgreSQL ではなく SQLite を使用します（Docker不使用）。DBファイルは `backend/data/app.db` に作成され、`.gitignore` 済みです。
接続時に `PRAGMA foreign_keys=ON` と `PRAGMA journal_mode=WAL` を有効化し、外部キー制約と同時読み書きの安全性を確保しています。
塾内の少人数運用を想定したMVPのため、SQLiteの「同時書き込みは1本まで」という制約は許容しています。

## 初期ユーザー（seed）

| login_id | password | role |
|---|---|---|
| operator1 | password123 | operator |
| teacher1 | password123 | teacher |

## マイグレーション

```bash
# 新しいマイグレーションを作成（モデル変更後）
alembic revision --autogenerate -m "説明"

# 適用
alembic upgrade head
```

## LLM（Gemini）連携について

`backend/app/llm/` に実装を集約しています。SDKは `google-genai`（Python）を使用し、2026年6月にGAとなった **Interactions API**（`client.interactions.create(...)`）を新規開発向けの推奨API として採用しています（従来の`generate_content`は現在レガシー扱い）。

- 構造化出力は `response_format={"type":"text","mime_type":"application/json","schema": PydanticModel.model_json_schema()}` を渡し、`interaction.output_text` をJSONとしてパースしたうえで、こちらのPydanticモデルで再検証しています
- `store=False` を指定し、Google側にもリクエスト・レスポンスを保持させません（画像を一切残さないという要件に合わせています）
- 各呼び出しにサーバー側の追加検証を実装済み：unit_id/format_id/worksheet_item_idは実在するIDのみ受理（それ以外はnullにして「要確認」扱い）、difficulty(1-3)・hint_step(0-3)は範囲外ならクランプ、ヒントがちょうど3段でない問題案は破棄
- 画像（`image_base64`）はリクエストのメモリ上でのみ扱い、`LLM_JOB.request_params` を含めディスク・DB・ログに一切保存しません
- `GEMINI_MODEL` のデフォルト値 `gemini-3.5-flash` は、インストール済みSDK（`google-genai`）の型定義から実在を確認したモデルIDです。正式な性能・料金等はGoogle AI for Developersの最新ドキュメントで確認してください
- `GEMINI_API_KEY` が未設定（プレースホルダーのまま）の場合、LLM系4エンドポイントは `502 LLM_ERROR` を返します。`pytest` はSDKを完全にモックしているため、実キーなしでも全テストが通ります

## テスト

```bash
pytest
```

## スマホ実機でカメラ機能を試す方法（フロントエンド側 / 参考）

`getUserMedia()` は安全なコンテキスト（HTTPS または localhost）でのみ動作します。開発PCとスマホを同一ネットワークに置いた上で、以下のいずれかで HTTPS 化してください。

- `next dev --experimental-https` などフレームワーク組み込みのHTTPS開発オプションを使う
- `mkcert` でローカル証明書を発行し、Next.js の開発サーバーに `--experimental-https-key` / `--experimental-https-cert` を指定する
- `ngrok http 3000` のようなトンネリングツールで一時的にHTTPS URLを発行する

いずれの場合も、バックエンドの `CORS_ORIGIN` をその HTTPS URL に合わせて更新してください。
