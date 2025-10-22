import importlib
import textwrap

try:
    from .test_utils import create_test_modules, update_module
except ImportError:
    from test_utils import create_test_modules, update_module


def test_wildcard_from_import_reload(tmp_path):
    """
    ワイルドカードインポート（from a import *）の更新テスト
    """

    # テスト用モジュールを作成
    modules_dir = create_test_modules(
        tmp_path,
        {
            'a.py': textwrap.dedent(
                """
                x = 1
                y = 2
                """
            ),
            'b.py': textwrap.dedent(
                """
                from a import *
                """
            ),
        },
    )
    import b  # type: ignore

    assert b.x == 1
    assert b.y == 2

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

    deep_reload(b)

    # 更新された値を確認
    new_b = importlib.import_module('b')
    assert new_b.x == 100
    assert new_b.y == 200


if __name__ == "__main__":
    from test_utils import run_test_as_script

    run_test_as_script(test_wildcard_from_import_reload, __file__)
