# 実行方法

```sh
# 画像ファイルを1枚指定
python wdv3_timm.py -i path/to/image.png --model <vit|swinv2|convnext|eva02|vit-large>

# ディレクトリを指定（サブディレクトリ含め再帰的に画像を処理）
python wdv3_timm.py -i path/to/dir --model <vit|swinv2|convnext|eva02|vit-large>

# 結果をJSONファイルに保存（ディレクトリ指定時は全画像分の結果を配列としてまとめて保存）
python wdv3_timm.py -i path/to/dir -o result.json
```

- `-i`/`--input`（必須）: タグ付け対象の画像ファイル、またはディレクトリのパス。ディレクトリの場合はサブディレクトリも含めて再帰的に画像ファイル（`.png`/`.jpg`/`.jpeg`/`.webp`/`.bmp`/`.gif`）を探索する（`find_image_files()`）
- `--model`（デフォルト `vit`。`vit`/`swinv2`/`convnext`/`eva02`/`vit-large` から選択。`wdv3_timm.py` 内 `MODEL_REPO_MAP` で Hugging Face リポジトリ ID にマッピング）
- `--gen_threshold`（デフォルト 0.35）、`--char_threshold`（デフォルト 0.75）で一般タグ／キャラクタータグの確信度しきい値を調整可能
- `--output`/`-o`: 結果をJSON形式で保存するファイルパス。画像1枚のみの場合はオブジェクト、複数枚（ディレクトリ指定）の場合は配列として保存する。指定しない場合は標準出力にテキスト表示（複数枚のときは画像ごとにファイルパスの見出しを付けて連続表示）
- CLI 引数解析は標準ライブラリ `argparse` を使用（`parse_args()` 関数が `ScriptOptions` dataclass を組み立てる）

テストフレームワークは設定されていない。動作確認は実際に画像（またはディレクトリ）を渡してスクリプトを実行することで行う。

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
