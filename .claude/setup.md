# セットアップ

```sh
# Linux
bash setup.sh

# Windows
setup.bat
```

いずれも `.venv` を作成し、`requirements.txt` の依存関係をインストールする。`timm` は PyPI 版ではなく GitHub の `main` ブランチから直接インストールされる点に注意（`requirements.txt` 参照）。

手動セットアップの場合、Python 3.10 系を使用する（`python3.10 -m venv .venv`）。CPU 専用環境では PyTorch を CPU 版で個別インストールする必要がある。
