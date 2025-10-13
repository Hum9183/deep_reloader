"""
pytest専用の設定ファイル

test_utils.pyの機能をラップしてpytest fixtureとして提供する。
スクリプト実行時はtest_utilsを直接使用するため、このファイルをインポートする必要はない。
"""

import pytest

from .test_utils import clear_test_environment


@pytest.fixture(autouse=True)
def auto_clear_test_environment():
    """pytest実行時の一時ディレクトリ自動クリア"""
    # sys.pathはpytestが実行場所に応じて適切に設定

    # テスト前のクリア
    clear_test_environment()
    yield
    # テスト後のクリア
    clear_test_environment()
