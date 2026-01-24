import textwrap

from ..test_utils import create_test_modules, update_module


def test_wildcard_from_import_reload(tmp_path):
    """
    ワイルドカードインポート (from a import *) の更新テスト
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

                result = x + y
                """
            ),
        },
        package_name='wildcard_pkg',
    )

    # 初期値の確認
    import wildcard_pkg.b  # type: ignore

    assert wildcard_pkg.b.result == 3
    assert wildcard_pkg.b.x == 1
    assert wildcard_pkg.b.y == 2

    # a.py を更新
    update_module(
        modules_dir,
        'a.py',
        """
        x = 10
        y = 20
    """,
    )

    # deep_reloader でリロード
    from deep_reloader import deep_reload

    deep_reload(wildcard_pkg.b)

    # b.py のワイルドカードインポートで取得したシンボルも更新されることを確認
    assert wildcard_pkg.b.x == 10
    assert wildcard_pkg.b.y == 20
    assert wildcard_pkg.b.result == 30
