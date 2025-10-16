import importlib
import textwrap

try:
    from .test_utils import add_temp_path_to_sys, make_temp_module
except ImportError:
    from test_utils import add_temp_path_to_sys, make_temp_module


def test_same_level_relative_import(tmp_path):
    """
    同階層の相対インポート (from .module import something) のテスト
    """

    # パッケージ構造を作成
    package_dir = tmp_path / 'mypackage'
    package_dir.mkdir()

    # __init__.py を作成
    (package_dir / '__init__.py').write_text('', encoding='utf-8')

    # utils.py を作成
    (package_dir / 'utils.py').write_text(
        textwrap.dedent(
            """
            helper_value = 42

            def helper_func():
                return "original"
            """
        ),
        encoding='utf-8',
    )

    # main.py を作成 (from .utils import helper_value, helper_func)
    (package_dir / 'main.py').write_text(
        textwrap.dedent(
            """
            from .utils import helper_value, helper_func

            def get_result():
                return f"{helper_value}-{helper_func()}"
            """
        ),
        encoding='utf-8',
    )

    # sys.pathに一時ディレクトリを追加
    add_temp_path_to_sys(tmp_path)

    from mypackage import main  # noqa: F401  # type: ignore

    assert main.get_result() == "42-original"

    # utils.pyを書き換えて値を変更
    (package_dir / 'utils.py').write_text(
        textwrap.dedent(
            """
            helper_value = 999

            def helper_func():
                return "updated"
            """
        ),
        encoding='utf-8',
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
