# アーキテクチャ

`wdv3_timm.py` は一本のスクリプトで完結しており、処理は以下の流れ：

1. **入力パスの解決**: `-i`/`--input` に指定されたパスがファイルかディレクトリかを判定。ディレクトリの場合は `find_image_files()` がサブディレクトリを含めて再帰的に画像ファイル（`IMAGE_EXTENSIONS`）を探索し、パス昇順のリストを得る。ファイルの場合は単一要素のリストとして扱う。
2. **モデルロード**: `timm.create_model("hf-hub:" + repo_id)` でモデル構造を構築し、`timm.models.load_state_dict_from_hf` で重みを取得して読み込む。GPU が利用可能な場合はこの時点でモデルを GPU に移動し、全画像の推論が終わるまで維持する。
3. **タグリスト取得**: `load_labels_hf()` が Hugging Face リポジトリから `selected_tags.csv` をダウンロードし、`category` 列でタグを `rating`（9）・`general`（0）・`character`（4）の3グループに分類した `LabelData` dataclass を返す。
4. **画像ごとの処理（`process_image()`）**: 各画像について `pil_ensure_rgb()` で RGB/RGBA に統一 → `pil_pad_square()` で白背景の正方形にパディング → `timm` の `create_transform`/`resolve_data_config` で得た transform でテンソル化 → RGB→BGR にチャンネル入れ替え（モデルが BGR 入力を期待するため）→ `torch.inference_mode()` 下で forward し、`timm` がモデル内に活性化関数を含まないため出力に手動で `sigmoid` を適用。
5. **後処理**: `get_tags()` が確信度としきい値からレーティング・キャラクタータグ・一般タグを抽出し、確信度降順にソート。カンマ区切りキャプション文字列と、アンダースコア→スペース変換＋括弧エスケープ済みのタグリスト文字列の両方を生成する（後者は Danbooru 系キャプション形式を想定）。
6. **出力**: `--output` 指定時は `build_result_dict()` で画像ごとの結果を辞書化し、`save_results_json()` が画像1枚なら単一オブジェクト、複数枚なら配列としてJSONファイルに保存する。未指定時は `show_results()` が標準出力にテキスト表示（複数枚の場合は画像パスの見出しを付けて連続表示）。

モデル・タグリストは実行のたびに Hugging Face Hub からダウンロードされる（ローカルキャッシュされるが、リポジトリ内に重みは含まれない）。
