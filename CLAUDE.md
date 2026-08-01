# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## リポジトリ概要

`wdv3-timm` は、`timm` ライブラリを使って WD Tagger V3 モデル（SmilingWolf 製の画像タギングモデル）で推論を行う方法を示す単一スクリプトのサンプルリポジトリです。本体は `wdv3_timm.py` のみで構成されています。

セットアップ手順は [.claude/setup.md](.claude/setup.md)、実行方法は [.claude/usage.md](.claude/usage.md)、内部処理の流れは [.claude/architecture.md](.claude/architecture.md) を参照してください。

## 開発ルール

- テストフレームワークは設定されていない。動作確認は実際に画像を渡してスクリプトを実行することで行う。
- モデルの重み・タグリストはリポジトリに含めず、実行時に Hugging Face Hub からダウンロードする方針を維持する。
- 依存関係を追加する場合は `requirements.txt` に追記する。
- `.venv` はコミットしない。
- ファイルの変更や追加を行う前に、作業ブランチを切ること。
- 指示があるまでコミットしないこと。
- ファイルやディレクトリ構成を変更した場合は、CLAUDE.md および `.claude` 配下に記載の該当箇所も変更する。
- プルリクマージ後は、作業ブランチをローカル・リモート共に削除し、`main` ブランチを最新にする。

## コーディング規約

`.vscode/settings.json` の設定に準拠する。

- インデントはスペース4つ、タブサイズ4
- 行の目安は100〜120文字（`editor.rulers`）
- 行末の余分な空白は削除する（Markdown を除く）
- Python は `ruff` でフォーマット・import 整理を行う（保存時に自動実行）
