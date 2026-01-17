# deep_reloader

> [!WARNING]
> このソフトウェアは現在プレリリース版（v0.2.0）です。APIが変更される可能性があります。

Pythonモジュールの依存関係を解析して、再帰的に再読み込みを行うライブラリです。特にMayaでのスクリプト開発時に、モジュール変更を即座に反映させるために設計されています。

## 機能

- **深い再読み込み**: from-import の依存関係を自動解析
- **AST解析**: 静的解析により from-import文 を正確に検出
- **ワイルドカード対応**: `from module import *` もサポート
- **相対インポート対応**: パッケージ内の相対インポートを正しく処理
- **`__pycache__`クリア**: 古いキャッシュファイルを自動削除

## 制限事項・既知の問題

### Python言語レベルの制約（解決不可能）

- **デコレーターのクロージャ問題**: デコレーター内で例外クラスをキャッチする場合、リロード後に正しくキャッチできません
  - これはPython言語仕様の制約であり、すべてのリロードシステム（`importlib.reload()`, IPythonの`%autoreload`等）が抱える共通の問題です
  - **原因**: デコレーターのクロージャは定義時にクラスオブジェクトへの参照を保持し、リロード後も古いクラスオブジェクトを参照し続けます
  - **例**:
    ```python
    # custom_error.py
    class CustomError(Exception):
        @staticmethod
        def catch(function):
            @functools.wraps(function)
            def wrapper(*args, **kwargs):
                try:
                    return function(*args, **kwargs)
                except CustomError as e:  # ←デコレーター定義時のCustomErrorを保持
                    return f"Caught: {e}"
            return wrapper

    # main.py
    @CustomError.catch  # ←リロード後、このクロージャは古いCustomErrorを参照
    def risky_function():
        raise CustomError("Error")  # ←新しいCustomErrorを投げる
    ```
  - **回避策**:
    - デコレーターを使用せず、直接`try-except`で例外をキャッチする
    - 例外クラスをリロード対象から除外する
    - アプリケーションを再起動する

- **モジュールスコープでのクラス参照**: モジュールレベルでクラスをエイリアスする場合も同様の問題が発生します
  - **例**: `MyError = CustomError` のようなエイリアスは、リロード後も古いクラスを参照します
  - **回避策**: エイリアスを避け、常にオリジナルのクラス名を使用する

### 実装上の制約（将来対応予定）

- **import文未対応**: 現在は `import module` 形式の依存関係は解析対象外です
  - 対応: `from module import something` 形式のみ解析・リロード
  - 今後のバージョンで `import module` にも対応予定
- **循環インポート**: 循環インポート（A → B → A のような相互依存）が存在するモジュール構造では現在エラーが発生します
  - 今後のバージョンで対応予定
  - 回避策: 循環依存を避けた設計に変更するか、手動での部分リロードをご検討ください

## 使用方法

### 基本的な使用方法

```python
# 最もシンプルな使用例
from deep_reloader import deep_reload
deep_reload(your_module)
```

### ログ設定

開発時やデバッグ時には、詳細なログ出力を有効にできます：

```python
from deep_reloader import deep_reload, setup_logging
import logging

# ログレベルを設定（すべてのdeep_reloaderログに影響）
logger = setup_logging(logging.DEBUG)   # 詳細なデバッグ情報

# 返されたロガーを使って直接ログ出力も可能
logger.info("deep_reloaderのログ設定が完了しました")

# その後、通常通り使用
deep_reload(your_module)
```

**ログレベルの説明:**
- `logging.DEBUG`: pycacheクリアなどの詳細情報も表示
- `logging.INFO`: モジュールリロードの状況を表示（デフォルト）
- `logging.WARNING`: エラーと警告のみ表示

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
    ├── LICENSE
    ├── README.md
    └── tests/          # テストファイル（開発・デバッグ用）
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

- **二種の実行をサポート**: 各テストファイルはスクリプト実行とpytest実行の両方に対応
- **条件付きインポート**: 実行環境に応じて相対/絶対インポートを自動切り替え
- **一時ディレクトリ管理**: 手動作成（スクリプト実行）と`tmp_path`（pytest）の両方をサポート

### 動作確認済み環境

**テスト開発環境（Maya以外）:**
- Python 3.11.9+（現在の開発環境で検証済み）
- pytest 8.4.2+（テスト実行時のみ、現在の開発環境で検証済み）

**注意**: 上記はライブラリのテスト・開発で使用している環境です。Maya内での実行環境とは異なります。Mayaのサポートバージョンは確定していません。

## バージョン情報

**現在のバージョン**: v0.2.0 (Pre-release)

### リリース状況
- ✅ コア機能実装完了（from-import対応）
- ✅ テストスイート（9テスト）
- ✅ ドキュメント整備
- 🔄 APIの安定化作業中
- 📋 Maya環境での動作検証
- 📋 import文対応の追加
- 📋 循環インポートエラー対応
- 📋 組み込み・サードパーティモジュールのスキップ処理
- 📋 デバッグログの強化
- 📋 パフォーマンス最適化とキャッシュ機能

## ライセンス

MIT License - 詳細は[LICENSE](LICENSE)ファイルを参照してください。
