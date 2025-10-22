import importlib
import textwrap

try:
    from .test_utils import create_test_modules, update_module
except ImportError:
    from test_utils import create_test_modules, update_module


def test_chained_from_import_reload(tmp_path):
    """
    c → b → a の多段 from-import が再帰的に更新されるかテスト
    """

    # テスト用モジュールを作成
    modules_dir = create_test_modules(
        tmp_path,
        {
            'a.py': textwrap.dedent(
                """
                value = 1
                """
            ),
            'b.py': textwrap.dedent(
                """
                from a import value
                """
            ),
            'c.py': textwrap.dedent(
                """
                from b import value
                """
            ),
        },
    )
    import a  # type: ignore
    import b  # type: ignore
    import c  # type: ignore

    assert a.value == 1
    assert b.value == 1
    assert c.value == 1

    # a.pyを書き換えて値を変更
    update_module(modules_dir, 'a.py', 'value = 777')

    # deep reloadを実行（c からスタート）
    from deep_reloader import deep_reload

    deep_reload(c)

    # 更新された値を確認
    new_a = importlib.import_module('a')
    new_b = importlib.import_module('b')
    new_c = importlib.import_module('c')

    assert new_a.value == 777
    assert new_b.value == 777
    assert new_c.value == 777


if __name__ == "__main__":
    from test_utils import run_test_as_script

    run_test_as_script(test_chained_from_import_reload, __file__)
