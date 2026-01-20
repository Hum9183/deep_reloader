import textwrap

try:
    from .test_utils import create_test_modules, update_module
except ImportError:
    from test_utils import create_test_modules, update_module


def test_wildcard_relative_import(tmp_path):
    """
    ワイルドカード相対インポート (from .module import *) のテスト
    """

    # パッケージ構造を作成
    modules_dir = create_test_modules(
        tmp_path,
        {
            'constants.py': textwrap.dedent(
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
            'main.py': textwrap.dedent(
                """
                from .constants import *

                def get_values():
                    # PUBLIC_CONST と public_func のみアクセス可能
                    return f"{PUBLIC_CONST}-{public_func()}"
                """
            ),
        },
        package_name='testpkg',
    )

    from testpkg import main  # noqa: F401  # type: ignore

    assert main.get_values() == "100-public"

    # constants.pyを書き換えて値を変更
    update_module(
        modules_dir,
        'constants.py',
        """
        __all__ = ['PUBLIC_CONST', 'public_func']

        PUBLIC_CONST = 555
        PRIVATE_CONST = 666  # __all__ にないので除外される

        def public_func():
            return "updated"

        def _private_func():  # __all__ にないので除外される
            return "private"
        """,
    )

    # deep reloadを実行
    from deep_reloader import deep_reload

    deep_reload(main)

    # 更新された値を確認
    assert main.get_values() == '555-updated'


if __name__ == '__main__':
    from test_utils import run_test_as_script

    run_test_as_script(test_wildcard_relative_import, __file__)
