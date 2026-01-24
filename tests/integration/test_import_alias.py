"""
import文のas句（エイリアス）のテスト

from module import name as alias の形式でインポートした場合、
リロード後にaliasが新しいオブジェクトを参照するか確認します。
"""

import textwrap

from deep_reloader import deep_reload

from ..test_utils import create_test_modules, update_module


def test_import_with_alias(tmp_path):
    """from module import name as alias のテスト"""

    modules_dir = create_test_modules(
        tmp_path,
        {
            '__init__.py': '',
            'utils.py': textwrap.dedent(
                """
                VERSION = 1

                def get_value():
                    return "original"

                class MyClass:
                    VALUE = 100
                """
            ),
            'main.py': textwrap.dedent(
                """
                from .utils import get_value as get_val
                from .utils import MyClass as Cls
                from .utils import VERSION as VER

                def run():
                    obj = Cls()
                    return f"{get_val()}-{obj.VALUE}-{VER}"
                """
            ),
        },
        package_name='test_pkg',
    )

    from test_pkg import main  # type: ignore

    # リロード前の確認
    assert main.run() == "original-100-1"
    assert main.get_val() == "original"
    assert main.Cls.VALUE == 100
    assert main.VER == 1

    # utils.pyを更新
    update_module(
        modules_dir,
        'utils.py',
        """
        VERSION = 2

        def get_value():
            return "updated"

        class MyClass:
            VALUE = 999
        """,
    )

    # deep_reloadでリロード
    deep_reload(main)

    # リロード後の確認 - エイリアスが新しいオブジェクトを参照すべき
    assert main.run() == "updated-999-2", "run()の結果が更新されていない"
    assert main.get_val() == "updated", "エイリアス get_val が更新されていない"
    assert main.Cls.VALUE == 999, "エイリアス Cls が更新されていない"
    assert main.VER == 2, "エイリアス VER が更新されていない"


def test_import_with_multiple_aliases(tmp_path):
    """複数のエイリアスを使ったインポートのテスト"""

    modules_dir = create_test_modules(
        tmp_path,
        {
            '__init__.py': '',
            'helpers.py': textwrap.dedent(
                """
                def func_a():
                    return "A"

                def func_b():
                    return "B"
                """
            ),
            'consumer.py': textwrap.dedent(
                """
                from .helpers import func_a as fa, func_b as fb

                def get_combined():
                    return f"{fa()}-{fb()}"
                """
            ),
        },
        package_name='test_pkg',
    )

    from test_pkg import consumer  # type: ignore

    # リロード前
    assert consumer.get_combined() == "A-B"
    assert consumer.fa() == "A"
    assert consumer.fb() == "B"

    # helpers.pyを更新
    update_module(
        modules_dir,
        'helpers.py',
        """
        def func_a():
            return "X"

        def func_b():
            return "Y"
        """,
    )

    # deep_reloadでリロード
    deep_reload(consumer)

    # リロード後 - 両方のエイリアスが更新されるべき
    assert consumer.get_combined() == "X-Y"
    assert consumer.fa() == "X"
    assert consumer.fb() == "Y"


def test_import_mixed_alias_and_original(tmp_path):
    """エイリアスと元の名前を混在させたインポートのテスト"""

    modules_dir = create_test_modules(
        tmp_path,
        {
            '__init__.py': '',
            'config.py': textwrap.dedent(
                """
                SETTING1 = "value1"
                SETTING2 = "value2"
                """
            ),
            'app.py': textwrap.dedent(
                """
                from .config import SETTING1 as S1, SETTING2

                def get_settings():
                    return f"{S1}-{SETTING2}"
                """
            ),
        },
        package_name='test_pkg',
    )

    from test_pkg import app  # type: ignore

    # リロード前
    assert app.get_settings() == "value1-value2"
    assert app.S1 == "value1"
    assert app.SETTING2 == "value2"

    # config.pyを更新
    update_module(
        modules_dir,
        'config.py',
        """
        SETTING1 = "updated1"
        SETTING2 = "updated2"
        """,
    )

    # deep_reloadでリロード

    deep_reload(app)

    # リロード後 - エイリアスと元の名前の両方が更新されるべき
    assert app.get_settings() == "updated1-updated2"
    assert app.S1 == "updated1", "エイリアス S1 が更新されていない"
    assert app.SETTING2 == "updated2", "元の名前 SETTING2 が更新されていない"


if __name__ == '__main__':
    from test_utils import run_test_as_script

    run_test_as_script(test_import_with_alias, __file__)
