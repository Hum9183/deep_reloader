"""
統合テストの設計パターンデモ

pytestフィクスチャ（tmp_path）とtest_utils（create_test_modules、update_module）を
使った標準的なテスト実装例。conftest.pyが環境を自動クリーンアップ。
"""

import textwrap

from deep_reloader import deep_reload

from ..test_utils import create_test_modules, update_module


def test_architecture_demonstration(tmp_path):
    """
    テスト設計のデモンストレーション

    このテスト関数は、deep_reloaderのテスト設計パターンを示します。

    Args:
        tmp_path: pytestが自動的に提供する一時ディレクトリフィクスチャ
                 各テスト実行ごとに独立した一時ディレクトリが作成されます

    技術的詳細:
        - create_test_modules()で一時的なモジュール構造を作成
        - update_module()でモジュールを動的に更新
        - deep_reload()で依存関係を含めてリロード
        - conftest.pyが自動的にテスト環境をクリーンアップ
    """

    # === メインのテストロジック ===
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
    deep_reload(test_package.main)

    # リロード後の値を確認
    # config.pyの変更がutils.py、main.pyまで伝播していることを確認
    assert test_package.main.show_info() == 'Running: UpdatedApp v2.5.0'

    # 注意: sys.pathとsys.modulesのクリーンアップは、
    # conftest.pyで定義されたフィクスチャにより自動的に実行されます
