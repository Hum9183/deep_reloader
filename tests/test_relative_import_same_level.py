import importlib
import textwrap

try:
    from .test_utils import create_test_modules, update_module
except ImportError:
    from test_utils import create_test_modules, update_module


def test_same_level_relative_import(tmp_path):
    """
    同階層の相対インポート (from .module import something) のテスト
    """

    # パッケージ構造を作成
    modules_dir = create_test_modules(
        tmp_path,
        {
            'utils.py': textwrap.dedent(
                """
                helper_value = 42

                def helper_func():
                    return "original"
                """
            ),
            'main.py': textwrap.dedent(
                """
                from .utils import helper_value, helper_func

                def get_result():
                    return f"{helper_value}-{helper_func()}"
                """
            ),
        },
        package_name='mypackage',
    )

    from mypackage import main  # noqa: F401  # type: ignore

    assert main.get_result() == "42-original"

    # utils.pyを書き換えて値を変更
    update_module(
        modules_dir,
        'utils.py',
        """
        helper_value = 999

        def helper_func():
            return "updated"
        """,
    )

    # deep reloadを実行
    from deep_reloader import deep_reload

    deep_reload(main)

    # 更新された値を確認
    new_main = importlib.import_module('mypackage.main')
    assert new_main.get_result() == "999-updated"


if __name__ == "__main__":
    from test_utils import run_test_as_script

    run_test_as_script(test_same_level_relative_import, __file__)
