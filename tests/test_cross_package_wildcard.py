"""
異なるパッケージ間のワイルドカードインポートのテスト

deep_reloadを2回実行することで、異なるパッケージ間でも
正しくリロードできることを確認します。

READMEの「複数の自作パッケージを開発している場合」のパターンをテストします。
"""

import sys
import textwrap
from pathlib import Path

try:
    from .test_utils import create_test_modules, update_module
except ImportError:
    from test_utils import create_test_modules, update_module


def test_cross_package_wildcard_single_reload(tmp_path):
    """異なるパッケージ間のワイルドカードインポート - 1回のdeep_reloadのみ（更新されない）"""

    # package_a作成（値を提供する側）
    pkg_a_dir = create_test_modules(
        tmp_path,
        {
            '__init__.py': textwrap.dedent(
                """
                __all__ = ['VALUE', 'get_value']

                VALUE = 100

                def get_value():
                    return "package_a_value"
            """
            ),
        },
        package_name='package_a',
    )

    # package_b作成（package_aを使う側）
    pkg_b_dir = create_test_modules(
        tmp_path,
        {
            '__init__.py': '',
            'consumer.py': textwrap.dedent(
                """
                from package_a import *

                def show_value():
                    return f"VALUE={VALUE}, get_value={get_value()}"
            """
            ),
        },
        package_name='package_b',
    )

    from package_b import consumer  # type: ignore

    assert consumer.show_value() == "VALUE=100, get_value=package_a_value"

    # package_aを更新
    update_module(
        pkg_a_dir,
        '__init__.py',
        """
        __all__ = ['VALUE', 'get_value']

        VALUE = 999

        def get_value():
            return "UPDATED_package_a_value"
        """,
    )

    # deep_reload(consumer)のみ実行
    from deep_reloader import deep_reload

    deep_reload(consumer)

    # package_aはリロード対象外なので、更新されない
    assert consumer.show_value() == "VALUE=100, get_value=package_a_value"


def test_cross_package_wildcard_double_reload(tmp_path):
    """異なるパッケージ間のワイルドカードインポート - 2回のdeep_reloadで更新成功"""

    # package_a作成（値を提供する側）
    pkg_a_dir = create_test_modules(
        tmp_path,
        {
            '__init__.py': textwrap.dedent(
                """
                __all__ = ['VALUE', 'get_value']

                VALUE = 100

                def get_value():
                    return "package_a_value"
            """
            ),
        },
        package_name='package_a',
    )

    # package_b作成（package_aを使う側）
    pkg_b_dir = create_test_modules(
        tmp_path,
        {
            '__init__.py': '',
            'consumer.py': textwrap.dedent(
                """
                from package_a import *

                def show_value():
                    return f"VALUE={VALUE}, get_value={get_value()}"
            """
            ),
        },
        package_name='package_b',
    )

    import package_a  # type: ignore
    from package_b import consumer  # type: ignore

    assert consumer.show_value() == "VALUE=100, get_value=package_a_value"

    # package_aを更新
    update_module(
        pkg_a_dir,
        '__init__.py',
        """
        __all__ = ['VALUE', 'get_value']

        VALUE = 999

        def get_value():
            return "UPDATED_package_a_value"
        """,
    )

    # 2回のdeep_reloadを実行（依存先 → 依存元）
    from deep_reloader import deep_reload

    # 1. 依存先のpackage_aをリロード
    deep_reload(package_a)

    # この時点でpackage_aは更新されているが、consumerはまだ古い値を参照
    assert consumer.show_value() == "VALUE=100, get_value=package_a_value"

    # 2. 依存元のconsumerをリロード
    deep_reload(consumer)

    # consumerが新しい値を取得して更新される
    assert consumer.show_value() == "VALUE=999, get_value=UPDATED_package_a_value"


def test_cross_package_wildcard_submodule_double_reload(tmp_path):
    """異なるパッケージのサブモジュールからのワイルドカードインポート"""

    # package_a作成（サブモジュール含む）
    pkg_a_dir = create_test_modules(
        tmp_path,
        {
            '__init__.py': '',
            'config.py': textwrap.dedent(
                """
                __all__ = ['SETTING', 'get_setting']

                SETTING = "initial"

                def get_setting():
                    return f"setting_{SETTING}"
            """
            ),
        },
        package_name='package_a',
    )

    # package_b作成（package_a.configを使う側）
    pkg_b_dir = create_test_modules(
        tmp_path,
        {
            '__init__.py': '',
            'app.py': textwrap.dedent(
                """
                from package_a.config import *

                def show_config():
                    return f"SETTING={SETTING}, get_setting={get_setting()}"
            """
            ),
        },
        package_name='package_b',
    )

    import package_a.config  # type: ignore
    from package_b import app  # type: ignore

    assert app.show_config() == "SETTING=initial, get_setting=setting_initial"

    # package_a.configを更新
    update_module(
        pkg_a_dir,
        'config.py',
        """
        __all__ = ['SETTING', 'get_setting']

        SETTING = "updated"

        def get_setting():
            return f"setting_{SETTING}"
        """,
    )

    # 2回のdeep_reloadを実行
    from deep_reloader import deep_reload

    deep_reload(package_a.config)  # 依存先をリロード
    deep_reload(app)  # 依存元をリロード

    # 更新が反映される
    assert app.show_config() == "SETTING=updated, get_setting=setting_updated"


if __name__ == '__main__':
    from test_utils import run_test_as_script

    run_test_as_script(test_cross_package_wildcard_double_reload, __file__)
