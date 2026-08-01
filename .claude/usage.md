# 実行方法

```sh
python wdv3_timm.py <swinv2|convnext|vit> path/to/image.png
```

- 第1引数はモデル種別（`vit`/`swinv2`/`convnext`。`wdv3_timm.py` 内 `MODEL_REPO_MAP` で Hugging Face リポジトリ ID にマッピング）
- 第2引数（`--image_file`、実質は位置引数）は画像パス
- `--gen_threshold`（デフォルト 0.35）、`--char_threshold`（デフォルト 0.75）で一般タグ／キャラクタータグの確信度しきい値を調整可能
- CLI 引数解析は `simple_parsing` の `parse_known_args` を使用（`ScriptOptions` dataclass 定義）

テストフレームワークは設定されていない。動作確認は実際に画像を渡してスクリプトを実行することで行う。
