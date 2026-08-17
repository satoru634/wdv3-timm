# アーキテクチャ

`wdv3_timm.py` は一本のスクリプトで完結しており、処理は以下の流れ：

1. **入力パスの解決**: `-i`/`--input` に指定されたパスがファイルかディレクトリかを判定。ディレクトリの場合は `find_image_files()` がサブディレクトリを含めて再帰的に画像ファイル（`IMAGE_EXTENSIONS`）を探索し、パス昇順のリストを得る。ファイルの場合は単一要素のリストとして扱う。
2. **モデルロード**: `timm.create_model("hf-hub:" + repo_id)` でモデル構造を構築し、`timm.models.load_state_dict_from_hf` で重みを取得して読み込む。GPU が利用可能な場合はこの時点でモデルを GPU に移動し、全画像の推論が終わるまで維持する。
3. **タグリスト取得**: `load_labels_hf()` が Hugging Face リポジトリから `selected_tags.csv` をダウンロードし、`category` 列でタグを `rating`（9）・`general`（0）・`character`（4）の3グループに分類した `LabelData` dataclass を返す。
4. **画像ごとの処理（`process_image()`）**: 各画像について `pil_ensure_rgb()` で RGB/RGBA に統一 → `pil_pad_square()` で白背景の正方形にパディング → `timm` の `create_transform`/`resolve_data_config` で得た transform でテンソル化 → RGB→BGR にチャンネル入れ替え（モデルが BGR 入力を期待するため）→ `torch.inference_mode()` 下で forward し、`timm` がモデル内に活性化関数を含まないため出力に手動で `sigmoid` を適用。
5. **後処理**: `get_tags()` が確信度としきい値からレーティング・キャラクタータグ・一般タグを抽出し、確信度降順にソート。カンマ区切りキャプション文字列と、アンダースコア→スペース変換＋括弧エスケープ済みのタグリスト文字列の両方を生成する（後者は Danbooru 系キャプション形式を想定）。
6. **出力**: `--output` 指定時は `build_result_dict()` で画像ごとの結果を辞書化し、`save_results_json()` が画像1枚なら単一オブジェクト、複数枚なら配列としてJSONファイルに保存する。未指定時は `show_results()` が標準出力にテキスト表示（複数枚の場合は画像パスの見出しを付けて連続表示）。

モデル・タグリストは実行のたびに Hugging Face Hub からダウンロードされる（ローカルキャッシュされるが、リポジトリ内に重みは含まれない）。

## サーバーモード（`--serve`、`run_serve_mode()`）

通常モードは実行のたびにモデルをロードして1回限りの処理で終了する単発 CLI だが、他ツールから複数画像を連続してタグ付けする用途ではこの都度ロードが大きなオーバーヘッドになる。`--serve` はこれを避けるための常駐サーバーモードで、`main()` は `opts.serve` が真の場合、通常モードの入力パス解決・バッチループに入る前に `run_serve_mode()` へ処理を委譲する。

1. **モデルロード（1度だけ）**: 通常モードの `main()` と同じ手順（`timm.create_model` → `load_state_dict_from_hf` → GPU 転送、`load_labels_hf()`、`create_transform`/`resolve_data_config`）でモデル・タグリスト・transform を構築する。進捗ログはすべて標準エラー出力に書く（標準出力は後述のプロトコル専用のため）。
2. **準備完了通知**: ロード完了後、標準出力へ1行だけ `{"status": "ready"}` を出力する（`flush=True`）。他ツール側はこの1行を読むまでブロックして待機する想定。
3. **リクエストループ**: `for line in sys.stdin:` で標準入力を1行ずつ読む。各行は `{"image_path": "<パス>"}` の JSON として解釈し、`process_image()`（通常モードと共通のバッチ内1画像処理関数）を呼んで `caption`（アンダースコア保持・括弧未エスケープの生タグ文字列、`build_result_dict()` の `caption` と同一形式）を取得し、`{"status": "ok", "tags": caption}` を標準出力へ1行返す。JSON パース失敗・ファイル欠落・画像破損など、リクエスト処理中に起きた例外はすべて `except Exception` で捕捉し `{"status": "error", "message": str(e)}` として応答する（1件の失敗でサーバー自体を落とさない設計。`ComfyUILibs.Services.CaptioningService.ProcessImageAsync` が1画像の例外を捕捉して処理を継続するのと同じ考え方）。
4. **終了**: クライアントが標準入力を閉じる（EOF）と `for line in sys.stdin:` ループが自然に終了し、`run_serve_mode()` から戻って `main()` も終了する（終了コード0）。

このプロトコルは他ツール（例: C# 版 [ComfyUILibs](https://github.com/satoru634/ComfyUILibs) の `Services/IWdV3TimmProcessClient.cs`）から常駐プロセスとして起動されることを想定して設計されている。プロトコルの詳細な契約は [usage.md](usage.md) の「サーバーモード」節を参照。

## launcher.py（exe 化用ランチャー）

`wdv3_timm.py` を PyInstaller でそのまま exe 化すると、torch 同梱によりファイルサイズが肥大化するうえ、PyInstaller のブートローダー環境下で torch のネイティブ DLL 初期化が失敗する（`WinError 1114` / `ERROR_DLL_INIT_FAILED`）既知の非互換が発生する。

そのため `launcher.py`（標準ライブラリのみで構成）だけを PyInstaller で exe 化し、実行時に本リポジトリの `.venv\Scripts\python.exe` で `wdv3_timm.py` をサブプロセス起動する構成にしている。`.venv` と `wdv3_timm.py` の場所は `sys.executable`（frozen 実行時）／`__file__`（スクリプト実行時）を基準にした相対解決で求めており、`wdv3_timm.exe` はリポジトリ直下（`.venv`・`wdv3_timm.py` と同じフォルダ）に置いた状態で使う必要がある（フォルダごとであれば移動・コピーしても動作する）。標準入出力・終了コードはサブプロセスからそのまま透過する。
