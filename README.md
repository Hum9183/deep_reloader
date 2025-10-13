# deep_reloader

> [!WARNING]
> このソフトウェアは現在プレリリース版（v0.1.0）です。APIが変更される可能性があります。

Pythonモジュールの依存関係を解析して、再帰的に再読み込みを行うライブラリです。特にMayaでのスクリプト開発時に、モジュール変更を即座に反映させるために設計されています。

## 機能

- **深い再読み込み**: from-import の依存関係を自動解析
- **AST解析**: 静的解析によりimport文を正確に検出
- **ワイルドカード対応**: `from module import *` もサポート
- **相対インポート対応**: パッケージ内の相対インポートを正しく処理
- **`__pycache__`クリア**: 古いキャッシュファイルを自動削除

## 使用方法

### 基本的な使用方法

```python
# 基本的な使用方法
import deep_reloader
dr = deep_reloader.DeepReloader()
dr.reload(your_module)

# from-import での使用方法
from deep_reloader import DeepReloader
DeepReloader().reload(your_module)
```

## インストール

Pythonパスが通っている場所であればどこでも配置可能です。
本READMEでは一般的なMayaのscriptsフォルダーを例として説明します。

```
~/Documents/maya/scripts/  (例)
└── deep_reloader/
    ├── __init__.py
    ├── _metadata.py
    ├── deep_reloader.py
    ├── imported_symbols.py
    ├── module_info.py
    ├── symbol_extractor.py
    └── tests/
```

## テスト実行

**注意: テストはVSCodeやコマンドラインで実行してください。Maya内部での実行はサポートしていません。**

このプロジェクトでは、スクリプト実行とpytest実行の両方をサポートしています。Maya開発環境での利便性を考慮し、pytestが利用できない環境でも直接スクリプトとしてテストを実行できます。

### スクリプト実行

各テストファイルを直接Python スクリプトとして実行できます：

#### コマンドライン実行

```shell
# 全テストを一括実行（フルパス指定）
python ~/Documents/maya/scripts/deep_reloader/tests/test_runner.py

# 個別テスト実行（フルパス指定）
python ~/Documents/maya/scripts/deep_reloader/tests/test_absolute_import_basic.py
```

#### VSCode実行

VSCodeでテストファイルを開いて「▶️ Run Python File」ボタンで実行できます。

### pytest実行

pytestが利用可能な環境では、より高機能なテスト実行が可能です：

```shell
# パッケージの親ディレクトリに移動 (例)
cd ~/Documents/maya/scripts/

# 全テスト実行
python -m pytest deep_reloader/tests/ -v

# 特定のテストファイル実行
python -m pytest deep_reloader/tests/test_absolute_import_basic.py -v

# より詳細な出力
python -m pytest deep_reloader/tests/ -vv
```

### テストアーキテクチャの特徴

- **デュアル実行サポート**: 各テストファイルはスクリプト実行とpytest実行の両方に対応
- **件付きインポート**: 実行環境に応じて相対/絶対インポートを自動切り替え
- **一時ディレクトリ管理**: 手動作成（スクリプト実行）と`tmp_path`（pytest）の両方をサポート

### 動作確認済み環境

- Python 3.11.9+（現在の開発環境で検証済み）
- pytest 8.4.2+（テスト実行時のみ、現在の開発環境で検証済み）

## バージョン情報

**現在のバージョン**: v0.1.0 (Pre-release)

### リリース状況
- ✅ コア機能実装完了
- ✅ テストスイート（9テスト）
- ✅ ドキュメント整備
- 🔄 APIの安定化作業中
- 📋 今後の改善予定項目あり

## ライセンス

MIT License - 詳細は[LICENSE](LICENSE)ファイルを参照してください。
