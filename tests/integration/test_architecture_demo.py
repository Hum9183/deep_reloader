"""
テスト設計の思想とその実装

このファイルは、deep_reloaderプロジェクトが採用しているテスト設計の思想、
実装方法、利点について詳細に説明する実動作可能なドキュメントです。

=== このテストの設計思想 ===

同一のテストコードを、以下の2つの方法で実行できる設計：
1. スクリプト実行: `python tests/test_xxx.py`
2. pytest実行: `python -m pytest tests/test_xxx.py`

=== なぜこの設計が必要か ===

【背景】
- 外部Python環境でのテスト実行の需要
- pytestがない環境(mayapy.exe)でのテスト需要
- 開発者の好みや環境に依存しない柔軟性

【従来の問題】
- スクリプト専用: pytestエコシステムの恩恵を受けられない
- pytest専用: 単体では実行できない
- 重複実装: 2つの異なるテストコードを保守する負担

【解決策】
- テストコードで両方をサポート
- 実行方式に関わらず同じテストロジックが動作
- 開発効率と実行環境の柔軟性を両立

=== 技術的実装の詳細 ===

【1. インポート戦略】
try-except文による相対インポートと絶対インポートの自動切り替え

【2. パス管理】
- スクリプト: setup_package_parent_path()によるパッケージ親ディレクトリ追加が必須
- pytest: パッケージ構造の自動認識
  * パッケージの親から実行 (`python -m pytest deep_reloader/tests/test_xxx.py`)
  * テストファイルパスでパッケージ名が明示され、複数パッケージ環境で識別が容易
- 両方式共通: create_test_modules()による一時ディレクトリの自動追加とクリーンアップ

【3. フィクスチャ互換性】
- スクリプト: tempfile.TemporaryDirectory()
- pytest: tmp_pathフィクスチャ

【4. 環境分離】
- スクリプト: 明示的な前後処理(clear_test_environment()による手動クリーンアップ)
- pytest: conftest.pyによる自動クリーンアップ

【5. テスト結果表示】
- スクリプト: test_runner.pyによる自作の表示
- pytest: 標準的なテストレポート

=== 実装パターンの標準化 ===

以下のパターンが、このプロジェクトの全テストファイルで統一されています：

1. インポート戦略
2. tmp_path互換の関数シグネチャ
3. if __name__ == "__main__": ブロック
4. 統一されたテストユーティリティの使用

このテストファイル自体も、上記パターンに従って実装されています。
"""

import sys
import textwrap

from ..test_utils import create_test_modules, update_module


def test_architecture_demonstration(tmp_path):
    """
    テスト設計のデモンストレーション

    このテスト関数は、スクリプト実行とpytest実行の両方で正常に動作します。
    関数シグネチャは意図的にpytestのtmp_pathフィクスチャと互換性を保っています。

    Args:
        tmp_path: 一時ディレクトリのパス
                 - スクリプト実行時: test_utils.run_test_as_script()が提供する
                                   tempfile.TemporaryDirectory()のPathオブジェクト
                 - pytest実行時: pytestが自動的に提供するtmp_pathフィクスチャ

    技術的詳細:
        両方の実行方式で、tmp_pathは同じインターフェースを持つため、
        テストコード内では実行方式を意識する必要がありません。
    """

    # === メインのテストロジック ===
    # ここにテストの本体を記述します
    # スクリプト実行・pytest実行のどちらでも同じコードが動作します

    # 一時モジュールの作成（依存関係のあるモジュール構成）
    # create_test_modules()はtest_utils.pyで定義されたヘルパー関数
    # 自動的にsys.pathに一時ディレクトリが追加されます
    modules_dir = create_test_modules(
        tmp_path,
        {
            '__init__.py': '',
            'config.py': textwrap.dedent(
                """
                # 設定モジュール（依存される側）
                APP_NAME = 'DemoApp'
                VERSION = '1.0.0'
                """
            ),
            'utils.py': textwrap.dedent(
                """
                # ユーティリティモジュール（config に依存）
                from .config import APP_NAME, VERSION

                def get_app_info():
                    return f"{APP_NAME} v{VERSION}"
                """
            ),
            'main.py': textwrap.dedent(
                """
                # メインモジュール（utils に依存）
                from .utils import get_app_info

                def show_info():
                    return f"Running: {get_app_info()}"
                """
            ),
        },
        package_name='test_package',
    )
    # create_test_modules()により自動的にsys.pathが設定されているため直接インポート可能
    import test_package.main  # type: ignore

    # アサーションによる検証（初期値）
    assert test_package.main.show_info() == 'Running: DemoApp v1.0.0'

    # 依存元のconfig.pyを更新
    # update_module()を使ってモジュールの内容を書き換えます
    update_module(
        modules_dir,
        'config.py',
        """
        # 設定モジュール（更新版）
        APP_NAME = 'UpdatedApp'
        VERSION = '2.5.0'
        """,
    )

    # 通常のimportlib.reload()では依存関係が更新されない
    # deep_reload()を使うことで、依存チェーンをすべてリロード
    from deep_reloader import deep_reload

    deep_reload(test_package.main)

    # リロード後の値を確認
    # config.pyの変更がutils.py、main.pyまで伝播していることを確認
    assert test_package.main.show_info() == 'Running: UpdatedApp v2.5.0'

    # 実行方式の検出と表示
    # この情報により、どちらの方式で実行されているかが分かります
    execution_method = _detect_execution_method()
    print(f"実行方式: {execution_method}")
    print(f"更新前: Running: DemoApp v1.0.0")
    print(f"更新後: {test_package.main.show_info()}")
    print("※ deep_reload()により依存チェーン(config -> utils -> main)がすべて更新されました")

    # 成功メッセージ
    print("OK: テスト実行デモンストレーション成功")

    # 注意: sys.pathとsys.modulesのクリーンアップは、
    # test_utils.clear_test_environment()で自動的に実行されます


def _detect_execution_method():
    """
    現在の実行方式を検出するヘルパー関数

    Returns:
        str: 実行方式（"script" または "pytest"）
    """

    # pytestが実行中かどうかを判定
    # pytest実行時は'pytest'モジュールがsys.modulesに存在する
    if 'pytest' in sys.modules:
        return 'pytest'

    # __main__モジュールの__file__属性から判定
    main_module = sys.modules.get('__main__')
    if main_module and hasattr(main_module, '__file__'):
        main_file = main_module.__file__
        if main_file and 'test_architecture_demo.py' in main_file:
            return 'script'

    return 'unknown'


# === このテスト設計の実装例 ===
# このif __name__ == '__main__':ブロックは、テスト設計の
# 核心部分です。スクリプト実行時のみ実行され、pytestのインフラストラクチャを
# 手動で再現します。

if __name__ == '__main__':
    """
    スクリプト実行時のエントリーポイント

    このブロックは、以下の処理を実行します：
    1. test_utils.run_test_as_script()の呼び出し
    2. pytestが自動提供する機能の手動実装
    3. テスト環境の設定とクリーンアップ
    4. エラーハンドリングと結果表示

    技術的詳細:
        run_test_as_script()は、以下のpytest機能を代替実装します：
        - パッケージパスの設定（setup_package_parent_path）
        - 一時ディレクトリの作成（tempfile.TemporaryDirectory）
        - テスト環境のクリーンアップ（clear_test_environment）
        - 例外ハンドリングとレポート（try-except-finally）
    """

    # test_utilsからスクリプト実行用の関数をインポート
    from test_utils import run_test_as_script

    print("=" * 60)
    print("テスト設計 - スクリプト実行モード")
    print("=" * 60)
    print()

    # テスト関数を実行
    print("テスト: test_architecture_demonstration")
    print("-" * 40)

    try:
        run_test_as_script(test_architecture_demonstration, __file__)
        print("OK: 成功")
    except Exception as e:
        print(f"NG: 失敗: {e}")
        raise
