import textwrap

from .test_utils import create_test_modules, update_module


def test_package_level_relative_import(tmp_path):
    """
    パッケージ自体の相対インポート (from .. import func) のテスト
    """

    # パッケージ構造を作成
    modules_dir = create_test_modules(
        tmp_path,
        {
            '__init__.py': textwrap.dedent(
                """
                package_version = '1.0.0'

                def package_info():
                    return f'Package version: {package_version}'
                """
            ),
            'childpkg/__init__.py': '',
            'childpkg/info.py': textwrap.dedent(
                """
                from .. import package_version, package_info

                def get_full_info():
                    return f"Child module - {package_info()}"
                """
            ),
        },
        package_name='parentpkg',
    )

    from parentpkg.childpkg import info  # noqa: F401  # type: ignore

    assert info.get_full_info() == 'Child module - Package version: 1.0.0'

    # 親パッケージの __init__.pyを書き換えて値を変更
    update_module(
        modules_dir,
        '__init__.py',
        """
        package_version = '2.5.0'

        def package_info():
            return f'Package version: {package_version}'
        """,
    )

    # deep reloadを実行
    from deep_reloader import deep_reload

    deep_reload(info)

    # 更新された値を確認
    assert info.get_full_info() == 'Child module - Package version: 2.5.0'
