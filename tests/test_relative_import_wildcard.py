import importlib
import textwrap

try:
    from .test_utils import add_temp_path_to_sys, make_temp_module
except ImportError:
    from test_utils import add_temp_path_to_sys, make_temp_module


def test_wildcard_relative_import(tmp_path):
    """
    ワイルドカード相対インポート (from .module import *) のテスト
    """

    # パッケージ構造を作成
    package_dir = tmp_path / 'testpkg'
    package_dir.mkdir()

    # __init__.py を作成
    (package_dir / '__init__.py').write_text('', encoding='utf-8')

    # constants.py を作成 (__all__ 付き)
    (package_dir / 'constants.py').write_text(
        textwrap.dedent(
            """
            __all__ = ['PUBLIC_CONST', 'public_func']

            PUBLIC_CONST = 100
            PRIVATE_CONST = 200  # __all__ にないので除外される

            def public_func():
                return "public"

            def _private_func():  # __all__ にないので除外される
                return "private"
            """
        ),
        encoding='utf-8',
    )

    # main.py を作成 (from .constants import *)
    (package_dir / 'main.py').write_text(
        textwrap.dedent(
            """
            from .constants import *

            def get_values():
                # PUBLIC_CONST と public_func のみアクセス可能
                return f"{PUBLIC_CONST}-{public_func()}"
            """
        ),
        encoding='utf-8',
    )

    # sys.pathに一時ディレクトリを追加
    add_temp_path_to_sys(tmp_path)

    from testpkg import main  # noqa: F401  # type: ignore

    assert main.get_values() == "100-public"

    # constants.pyを書き換えて値を変更
    (package_dir / 'constants.py').write_text(
        textwrap.dedent(
            """
            __all__ = ['PUBLIC_CONST', 'public_func']

            PUBLIC_CONST = 555
            PRIVATE_CONST = 666  # __all__ にないので除外される

            def public_func():
                return "updated"

            def _private_func():  # __all__ にないので除外される
                return "private"
            """
        ),
        encoding='utf-8',
    )

    # deep reloadを実行
    from deep_reloader import deep_reload

    deep_reload(main)

    # 更新された値を確認
    new_main = importlib.import_module('testpkg.main')
    assert new_main.get_values() == "555-updated"


if __name__ == "__main__":
    from test_utils import run_test_as_script

    run_test_as_script(test_wildcard_relative_import, __file__)
