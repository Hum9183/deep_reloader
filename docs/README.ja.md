# deep_reloader

[English Version](../README.md) | [中文版](README.zh-CN.md)

> [!WARNING]
> このソフトウェアは現在プレリリース版です。APIが変更される可能性があります。

Pythonモジュールの依存関係を解析して、再帰的にリロードを行うライブラリです。特にMayaでのスクリプト開発時に、モジュール変更を即座に反映させるために設計されています。

## 機能

- **深いリロード**: 深い階層でもリロードが可能
- **AST解析**: 静的解析により from-import文 を正確に検出
- **ワイルドカード対応**: `from module import *` もサポート
- **相対インポート対応**: パッケージ内の相対インポートを正しく処理
- **循環参照対応**: Pythonで動作する循環インポートを正しくリロード

## 動作環境

- Maya 2022
- Maya 2023
- Maya 2024
- Maya 2025
- Maya 2026

## インストール

Pythonパスが通っている場所であればどこでも配置可能です。
本READMEでは一般的なMayaのscriptsフォルダーを例として説明します。

```
~/Documents/maya/scripts/  (例)
└── deep_reloader/
    ├── __init__.py
    ├── _metadata.py
    ├── deep_reloader.py
    ├── dependency_extractor.py
    ├── domain.py
    ├── from_clause.py
    ├── import_clause.py
    ├── LICENSE
    ├── README.md
    └── tests/
```

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

## テスト実行

**注意: テストはpytestで実行してください。Maya内部での実行はサポートしていません。**

このプロジェクトのテストはpytest専用です。開発環境でpytestを使用してテストを実行してください。

```shell
# リポジトリルートに移動（例）
cd ~/Documents/maya/scripts/deep_reloader

# 全テスト実行
pytest tests/ -v

# 特定のテストファイル実行
pytest tests/integration/test_absolute_import.py -v

# より詳細な出力
pytest tests/ -vv

# 簡潔な出力
pytest tests/ -q
```

### 動作確認済み環境

**テスト開発環境（Maya以外）:**
- Python 3.11.9+（現在の開発環境で検証済み）
- pytest 8.4.2+（テスト実行に必須）

**注意**: 上記はライブラリのテスト・開発で使用している環境です。Maya内での実行環境とは異なります。

## 制限事項・既知の問題

### isinstance()の失敗（Python言語仕様の制約）

リロード前に作成したインスタンスは、リロード後のクラスで`isinstance()`が失敗します。これはPython言語仕様の制約であり、すべてのリロードシステムが抱える共通の問題です。

**原因**: リロード後、クラスオブジェクトのIDが変わるため。

**例**:
```python
# リロード前
my_class = MyClass()
isinstance(my_class, MyClass)  # True

deep_reload(MyClass)         # リロード

isinstance(my_class, MyClass)  # False（my_classは古いMyClassのインスタンス、MyClassは新しいクラス）
```

**回避策**:
- リロード後にインスタンスを再作成する
- クラス名での文字列比較を使用する（`type(my_class).__name__ == 'MyClass'`）
- Mayaを再起動する

### import文非対応（仕様）

`import xxx` 形式の依存関係は対応していません。

**理由**: リロード時に親モジュールへ自動追加された属性を復元する処理が複雑になるため。

**対応形式**: from-import形式のみ
- `from xxx import yyy` 形式
- `from .xxx import yyy` 形式
- `from . import yyy` 形式

### そのパッケージの`__init__.py`で明示的にインポートされていないモジュールはパッケージをインポートしても検出されない（仕様）

AST解析は`__init__.py`のコードを解析するため、そこで明示的にインポートされていない場合そのパッケージ配下のモジュールは検出できません。

**例**:

ファイル構造:
- `mypackage/__init__.py` (中身は空)
- `mypackage/utils.py`
- `main.py`

```python
# main.py
import mypackage

# パッケージをリロード
deep_reload(mypackage)
mypackage.utils.some_function() # utilsはリロードされない
```

**回避策**: モジュールを直接リロードする
```python
# main.py
from mypackage import utils
deep_reload(utils)
```


### 単一パッケージのみリロード（仕様）

`deep_reload()`は、渡されたモジュールと同じパッケージに属するモジュールのみをリロードします。

**理由**: 組み込みモジュール（`sys`等）やサードパーティライブラリ（`maya.cmds`, `PySide2`等）のリロードを防ぎ、システムの安定性を保つため。

**例**: `deep_reload(myutils)` を実行すると、`myutils`が属するパッケージのモジュールがリロード対象になります。

**複数の自作パッケージを開発している場合**:
パッケージ間に依存関係がある場合、正常にリロードできない可能性があります。基本的には単一パッケージを使用することを推奨します。
どうしても必要な場合は、依存関係の順序を考慮して複数回`deep_reload()`を呼び出してください。
```python
# 複数のパッケージでリロードしたい場合（非推奨）
deep_reload(myutils)
deep_reload(mytools)
```

### パッケージ構造が必須（仕様）

`deep_reload()`はパッケージ化されたモジュールのみをサポートします。

**理由**: 単体モジュールでは、標準ライブラリとユーザーコードの区別ができず、システムモジュールを誤ってリロードする危険性があるため。

**非対応**: 単体の`.py`ファイル（例: `~/maya/scripts/my_tool.py`）

**単体モジュールの場合**: 標準の`importlib.reload()`を使用してください。

**複数モジュールを使用する場合**: パッケージ化してください（`__init__.py`を含むディレクトリ構造を推奨）。

## リリース状況

- ✅ コア機能実装完了（from-import対応）
- ✅ テストスイート
- ✅ ドキュメント整備
- ✅ Maya環境での動作検証
- ✅ 循環インポート対応
- 🔄 APIの安定化作業中
- 📋 デバッグログの強化
- 📋 パフォーマンス最適化とキャッシュ機能

## ライセンス

MIT License - 詳細は[LICENSE](LICENSE)ファイルを参照してください。
