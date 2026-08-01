# アーキテクチャ

`wdv3_timm.py` は一本のスクリプトで完結しており、処理は以下の流れ：

1. **モデルロード**: `timm.create_model("hf-hub:" + repo_id)` でモデル構造を構築し、`timm.models.load_state_dict_from_hf` で重みを取得して読み込む。
2. **タグリスト取得**: `load_labels_hf()` が Hugging Face リポジトリから `selected_tags.csv` をダウンロードし、`category` 列でタグを `rating`（9）・`general`（0）・`character`（4）の3グループに分類した `LabelData` dataclass を返す。
3. **画像前処理**: `pil_ensure_rgb()` で RGB/RGBA に統一 → `pil_pad_square()` で白背景の正方形にパディング → `timm` の `create_transform`/`resolve_data_config` で得た transform でテンソル化 → RGB→BGR にチャンネル入れ替え（モデルが BGR 入力を期待するため）。
4. **推論**: `torch.inference_mode()` 下で forward し、`timm` がモデル内に活性化関数を含まないため出力に手動で `sigmoid` を適用。GPU が利用可能なら推論前後でモデル/テンソルを CPU⇔GPU 間で移動。
5. **後処理**: `get_tags()` が確信度としきい値からレーティング・キャラクタータグ・一般タグを抽出し、確信度降順にソート。カンマ区切りキャプション文字列と、アンダースコア→スペース変換＋括弧エスケープ済みのタグリスト文字列の両方を生成する（後者は Danbooru 系キャプション形式を想定）。

モデル・タグリストは実行のたびに Hugging Face Hub からダウンロードされる（ローカルキャッシュされるが、リポジトリ内に重みは含まれない）。
