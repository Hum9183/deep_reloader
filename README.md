# deep_reloader

> [!WARNING]
> このソフトウェアは現在プレリリース版です。APIが変更される可能性があります。

Pythonモジュールの依存関係を解析して、再帰的にリロードを行うライブラリです。特にMayaでのスクリプト開発時に、モジュール変更を即座に反映させるために設計されています。

## 機能

- **深いリロード**: 深い階層でもリロードが可能
- **AST解析**: 静的解析により from-import文 を正確に検出
- **ワイルドカード対応**: `from module import *` もサポート
- **相対インポート対応**: パッケージ内の相対インポートを正しく処理
- **循環参照対応**: Pythonで動作する循環インポートを正しくリロード

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

**注意: テストはpytestで実行してください。Maya内部での実行はサポートしていません。**

このプロジェクトのテストはpytest専用です。開発環境でpytestを使用してテストを実行してください。

### pytest実行

```shell
# パッケージの親ディレクトリに移動 (例)
cd ~/Documents/maya/scripts/

# 全テスト実行
python -m pytest deep_reloader/tests/ -v

# 特定のテストファイル実行
python -m pytest deep_reloader/tests/test_absolute_import_basic.py -v

# より詳細な出力
python -m pytest deep_reloader/tests/ -vv

# 簡潔な出力
python -m pytest deep_reloader/tests/ -q
```

### 動作確認済み環境

**テスト開発環境（Maya以外）:**
- Python 3.11.9+（現在の開発環境で検証済み）
- pytest 8.4.2+（テスト実行に必須）

**注意**: 上記はライブラリのテスト・開発で使用している環境です。Maya内での実行環境とは異なります。Mayaのサポートバージョンはまだ確定していません。

## 制限事項・既知の問題

- **isinstance()チェックの失敗**（Python言語仕様の制約 - 解決不可能）
  - リロード前に作成したインスタンスは、リロード後のクラスで`isinstance()`チェックが失敗します
  - これはPython言語仕様の制約であり、すべてのリロードシステムが抱える共通の問題です
  - **原因**: リロード後、クラスオブジェクトのIDが変わるため、リロード前のインスタンスは古いクラスを参照し続けます
  - **例**:
    ```python
    # リロード前
    obj = MyClass()
    isinstance(obj, MyClass)  # True

    # deep_reload後
    isinstance(obj, MyClass)  # False（objは古いMyClassのインスタンス、MyClassは新しいクラス）
    ```
  - **回避策**:
    - リロード後にインスタンスを再作成する
    - クラス名での文字列比較を使用する（`type(obj).__name__ == 'MyClass'`）
    - アプリケーションを再起動する

- **デコレーターのクロージャ問題**（Python言語仕様の制約 - 解決不可能）
  - デコレーター内で例外クラスをキャッチする場合、リロード後に正しくキャッチできません
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

- **import文非対応**（仕様）
  - `import module` 形式の依存関係は解析対象外です
  - 現在対応しているのはfrom-import形式です。具体的には、
    - `from xxx import yyy` 形式
    - `from .xxx import yyy` 形式
    - `from . import yyy` 形式
    - の3つです

  - **理由**:
    - `import xxx` は主に標準ライブラリや外部ライブラリで使用され、これらはリロード対象外です
    - 自作パッケージ内では from-import を使うのが一般的な慣習です

- **単一パッケージのみリロード**（仕様）
  - `deep_reload()`は、指定されたモジュールと同じパッケージに属するモジュールのみをリロードします
  - **理由**: 組み込みモジュール（`sys`等）やサードパーティライブラリ（`maya.cmds`, `PySide2`等）のリロードを防ぎ、システムの安定性を保つため
  - **例**: `deep_reload(myutils)` を実行すると、`myutils`パッケージ内のモジュールのみがリロードされます
  - **複数の自作パッケージを開発している場合**:
    ```python
    # myutils と myfunctions の両方を開発中の場合
    deep_reload(myutils.helper)   # myutilsパッケージをリロード
    deep_reload(myfunctions.main) # myfunctionsパッケージをリロード
    ```

### リリース状況
- ✅ コア機能実装完了（from-import対応）
- ✅ テストスイート（12テスト）
- ✅ ドキュメント整備
- ✅ Maya環境での動作検証
- ✅ 循環インポート対応
- 🔄 APIの安定化作業中
- 📋 デバッグログの強化
- 📋 パフォーマンス最適化とキャッシュ機能

## ライセンス

MIT License - 詳細は[LICENSE](LICENSE)ファイルを参照してください。
