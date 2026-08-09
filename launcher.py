"""wdv3_timm.py を呼び出す軽量ランチャー。

PyInstaller で本体（torch 等の重量級ライブラリ一式）を直接 exe 化すると、
- exe サイズが肥大化する
- torch のネイティブ DLL 初期化が PyInstaller のブートローダー環境下で失敗する
  （WinError 1114 / ERROR_DLL_INIT_FAILED。torch 単体の最小構成でも再現する既知の非互換）
という問題がある。

そこで、この launcher.py だけを PyInstaller で exe 化し、実行時に本リポジトリの
.venv（通常の Python プロセス）で wdv3_timm.py をサブプロセス起動する方式にする。
標準入出力・終了コードはそのまま透過するため、他ツールからは通常の CLI ツールと
同じ感覚で呼び出せる。

exe 化した場合、venv・本体スクリプトの場所は exe 自身の設置場所（＝リポジトリ直下）
を基準に解決する。そのため wdv3_timm.exe は .venv・wdv3_timm.py と同じフォルダに
置いた状態で配置する必要がある（フォルダごと移動・コピーすれば動作する）。

PyInstaller --onefile で固めた exe を実行すると `__file__` は実ファイルの場所ではなく、
実行時に展開される一時ディレクトリ（%TEMP%\\_MEIxxxxx\\...）を指してしまうため、
frozen 実行時は `sys.executable`（実際の exe のパス）を基準にする。
launcher.py をスクリプトのまま実行する開発時は `__file__` を基準にする。
"""

import subprocess
import sys
from pathlib import Path

if getattr(sys, "frozen", False):
    REPO_ROOT = Path(sys.executable).resolve().parent
else:
    REPO_ROOT = Path(__file__).resolve().parent

VENV_PYTHON = REPO_ROOT / ".venv" / "Scripts" / "python.exe"
SCRIPT_PATH = REPO_ROOT / "wdv3_timm.py"


def main() -> None:
    if not VENV_PYTHON.exists():
        print(f"エラー: Python 実行環境が見つかりません: {VENV_PYTHON}", file=sys.stderr)
        sys.exit(1)
    if not SCRIPT_PATH.exists():
        print(f"エラー: wdv3_timm.py が見つかりません: {SCRIPT_PATH}", file=sys.stderr)
        sys.exit(1)

    result = subprocess.run([str(VENV_PYTHON), str(SCRIPT_PATH), *sys.argv[1:]])
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
