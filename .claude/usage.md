# 実行方法

```sh
# 画像ファイルを1枚指定
python wdv3_timm.py -i path/to/image.png --model <vit|swinv2|convnext|eva02|vit-large>

# ディレクトリを指定（サブディレクトリ含め再帰的に画像を処理）
python wdv3_timm.py -i path/to/dir --model <vit|swinv2|convnext|eva02|vit-large>

# 結果をJSONファイルに保存（ディレクトリ指定時は全画像分の結果を配列としてまとめて保存）
python wdv3_timm.py -i path/to/dir -o result.json
```

- `-i`/`--input`（`--serve` 指定時を除き必須）: タグ付け対象の画像ファイル、またはディレクトリのパス。ディレクトリの場合はサブディレクトリも含めて再帰的に画像ファイル（`.png`/`.jpg`/`.jpeg`/`.webp`/`.bmp`/`.gif`）を探索する（`find_image_files()`）
- `--model`（デフォルト `vit`。`vit`/`swinv2`/`convnext`/`eva02`/`vit-large` から選択。`wdv3_timm.py` 内 `MODEL_REPO_MAP` で Hugging Face リポジトリ ID にマッピング）
- `--gen_threshold`（デフォルト 0.35）、`--char_threshold`（デフォルト 0.75）で一般タグ／キャラクタータグの確信度しきい値を調整可能
- `--output`/`-o`: 結果をJSON形式で保存するファイルパス。画像1枚のみの場合はオブジェクト、複数枚（ディレクトリ指定）の場合は配列として保存する。指定しない場合は標準出力にテキスト表示（複数枚のときは画像ごとにファイルパスの見出しを付けて連続表示）
- `--serve`: 常駐サーバーモードで起動する（詳細は下記「サーバーモード」節を参照）。指定時は `-i`/`--input` 不要
- CLI 引数解析は標準ライブラリ `argparse` を使用（`parse_args()` 関数が `ScriptOptions` dataclass を組み立てる）

テストフレームワークは設定されていない。動作確認は実際に画像（またはディレクトリ）を渡してスクリプトを実行することで行う。

## サーバーモード（`--serve`）

他ツール（例: C# 版 `ComfyUILibs.Services.WdV3TimmTaggerRunner`）から複数の画像を連続してタグ付けする際、
画像 1 枚ごとにプロセスを起動するとモデルの再ロード（Hugging Face からのダウンロード確認・
`timm.create_model`・重みロード・GPU 転送）が毎回発生し実用的な速度が出ない。`--serve` はこれを避けるため、
モデルを一度だけロードして常駐し、標準入出力経由で複数のタグ付けリクエストを処理し続けるモード。

```sh
python wdv3_timm.py --serve --model vit -g 0.35 -c 0.75
```

### プロトコル（`run_serve_mode()` が実装、他ツール側の実装と対になる契約）

- **起動**: `-i`/`--input` は不要。`--model`/`--gen_threshold`/`--char_threshold` は起動時に1度だけ指定し、
  以降の全リクエストに適用される（リクエストごとに変更することはできない）
- **準備完了シグナル**: モデル・タグリストのロードが完了すると、標準出力へ**1行だけ** `{"status": "ready"}` を出力する。
  モデルロード中の進捗ログ（`Loading model '...'` 等）はすべて標準エラー出力に書く。
  **標準出力はプロトコル専用**であり、人間が読むログを混在させてはならない
- **リクエスト**: 標準入力から1行1JSON `{"image_path": "<画像ファイルの絶対パス>"}` を受け取る
- **応答**: 標準出力へ1行1JSON で返す
  - 成功時: `{"status": "ok", "tags": "1girl, blue_eyes, solo, ..."}`
    （`tags` は `build_result_dict()` の `caption` と同じ形式＝アンダースコアを保持し括弧もエスケープしないカンマ区切り文字列。
    アンダースコア→スペース変換・括弧エスケープ済みの `taglist` 形式ではない点に注意）
  - 失敗時: `{"status": "error", "message": "<エラー内容>"}`。
    画像 1 枚の処理失敗（ファイル欠落・破損画像・不正なリクエスト JSON 等）はエラー応答を返すのみで
    プロセスは終了せず、次のリクエストを待ち受け続ける
- **終了**: クライアントが標準入力を閉じる（EOF）と、処理中のリクエストを終えてからループを抜け、
  終了コード 0 でプロセスを終了する

### 動作確認

```sh
python -c "
import json, subprocess
p = subprocess.Popen(['.venv/Scripts/python.exe', 'wdv3_timm.py', '--serve', '--model', 'vit'],
                      stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
print(p.stdout.readline())  # {\"status\": \"ready\"}
p.stdin.write(json.dumps({'image_path': 'path/to/image.png'}) + '\n'); p.stdin.flush()
print(p.stdout.readline())  # {\"status\": \"ok\", \"tags\": \"...\"}
p.stdin.close(); p.wait()
"
```

## 実行ファイル（exe）として使う

他ツールから Python 環境を意識せずに呼び出せるよう、`launcher.py` を PyInstaller で exe 化できる。

```sh
build_exe.bat
```

リポジトリ直下に `wdv3_timm.exe` が生成される。使い方は `python wdv3_timm.py ...` と同じ引数をそのまま渡せる。

```sh
wdv3_timm.exe -i path/to/image.png --model vit
```

`launcher.py` は標準ライブラリのみで構成した薄いラッパーで、実際の推論（torch 等）は本リポジトリの `.venv` 上でサブプロセスとして実行される（詳細は [architecture.md](architecture.md) を参照）。`wdv3_timm.exe` は exe 自身の設置場所を基準に `.venv`／`wdv3_timm.py` を参照するため、**リポジトリ直下に置いたまま**使う必要がある（フォルダごと移動・コピーする場合は問題ない）。標準出力・標準エラー出力・終了コードはそのまま透過されるため、通常の CLI ツールと同様に他ツールから呼び出せる。

exe を再生成したい場合（依存関係やスクリプトを更新した場合など）は `build_exe.bat` を再実行すればよい。
