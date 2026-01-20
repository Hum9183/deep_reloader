import textwrap

try:
    from .test_utils import create_test_modules, update_module
except ImportError:
    from test_utils import create_test_modules, update_module


def test_wildcard_from_import_reload(tmp_path):
    """
    ワイルドカードインポート（from a import *）の更新テスト
    """

    # テスト用パッケージを作成
    modules_dir = create_test_modules(
        tmp_path,
        {
            '__init__.py': '',
            'a.py': textwrap.dedent(
                """
                x = 1
                y = 2
                """
            ),
            'b.py': textwrap.dedent(
                """
                from .a import *
                """
            ),
        },
        package_name='test_package',
    )
    import test_package.b  # type: ignore

    assert test_package.b.x == 1
    assert test_package.b.y == 2

    # a.pyを書き換えて値を変更
    update_module(
        modules_dir,
        'a.py',
        """
        x = 100
        y = 200
        """,
    )

    # deep reloadを実行
    from deep_reloader import deep_reload

    deep_reload(test_package.b)

    # 更新された値を確認
    assert test_package.b.x == 100
    assert test_package.b.y == 200


if __name__ == '__main__':
    from test_utils import run_test_as_script

    run_test_as_script(test_wildcard_from_import_reload, __file__)
