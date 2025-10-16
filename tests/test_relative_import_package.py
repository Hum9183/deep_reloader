import importlib
import textwrap

try:
    from .test_utils import add_temp_path_to_sys, make_temp_module
except ImportError:
    from test_utils import add_temp_path_to_sys, make_temp_module


def test_package_level_relative_import(tmp_path):
    """
    パッケージ自体の相対インポート (from .. import func) のテスト
    """

    # パッケージ構造を作成
    parent_pkg = tmp_path / 'parentpkg'
    child_pkg = parent_pkg / 'childpkg'
    parent_pkg.mkdir()
    child_pkg.mkdir()

    # __init__.py ファイルを作成
    (child_pkg / '__init__.py').write_text('', encoding='utf-8')

    # 親パッケージの __init__.py に関数を定義
    (parent_pkg / '__init__.py').write_text(
        textwrap.dedent(
            """
            package_version = "1.0.0"

            def package_info():
                return f"Package version: {package_version}"
            """
        ),
        encoding='utf-8',
    )

    # 子パッケージのモジュールで親パッケージから直接インポート
    (child_pkg / 'info.py').write_text(
        textwrap.dedent(
            """
            from .. import package_version, package_info

            def get_full_info():
                return f"Child module - {package_info()}"
            """
        ),
        encoding='utf-8',
    )

    # sys.pathに一時ディレクトリを追加
    add_temp_path_to_sys(tmp_path)

    from parentpkg.childpkg import info  # noqa: F401  # type: ignore

    assert info.get_full_info() == "Child module - Package version: 1.0.0"

    # 親パッケージの __init__.pyを書き換えて値を変更
    (parent_pkg / '__init__.py').write_text(
        textwrap.dedent(
            """
            package_version = "2.5.0"

            def package_info():
                return f"Package version: {package_version}"
            """
        ),
        encoding='utf-8',
    )

    # deep reloadを実行
    from deep_reloader import deep_reload

    deep_reload(info)

    # 更新された値を確認
    new_info = importlib.import_module('parentpkg.childpkg.info')
    assert new_info.get_full_info() == "Child module - Package version: 2.5.0"


if __name__ == "__main__":
    from test_utils import run_test_as_script

    run_test_as_script(test_package_level_relative_import, __file__)
