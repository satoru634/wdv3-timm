# 実行方法

```sh
python wdv3_timm.py path/to/image.png --model <vit|swinv2|convnext|eva02|vit-large>
```

- 第1引数（位置引数）`image_file` は画像パス
- `--model`（デフォルト `vit`。`vit`/`swinv2`/`convnext`/`eva02`/`vit-large` から選択。`wdv3_timm.py` 内 `MODEL_REPO_MAP` で Hugging Face リポジトリ ID にマッピング）
- `--gen_threshold`（デフォルト 0.35）、`--char_threshold`（デフォルト 0.75）で一般タグ／キャラクタータグの確信度しきい値を調整可能
- CLI 引数解析は標準ライブラリ `argparse` を使用（`parse_args()` 関数が `ScriptOptions` dataclass を組み立てる）

テストフレームワークは設定されていない。動作確認は実際に画像を渡してスクリプトを実行することで行う。
