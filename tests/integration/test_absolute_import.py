import textwrap

from ..test_utils import create_test_modules, update_module


def test_simple_from_import_reload(tmp_path):
    """
    シンプルなfrom-importの更新テスト
    """

    # テスト用パッケージを作成
    modules_dir = create_test_modules(
        tmp_path,
        {
            '__init__.py': '',
            'a.py': textwrap.dedent(
                """
                x = 1
                """
            ),
            'b.py': textwrap.dedent(
                """
                from .a import x
                """
            ),
        },
        package_name='test_package',
    )
    import test_package.b  # type: ignore

    assert test_package.b.x == 1

    # a.pyを書き換えて値を変更
    update_module(modules_dir, 'a.py', 'x = 999')

    # deep reloadを実行
    from deep_reloader import deep_reload

    deep_reload(test_package.b)

    # 更新された値を確認
    assert test_package.b.x == 999
