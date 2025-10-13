import importlib
import textwrap

try:
    from .test_utils import make_temp_module
except ImportError:
    from test_utils import make_temp_module


def test_chained_from_import_reload(tmp_path):
    """
    c → b → a の多段 from-import が再帰的に更新されるかテスト
    """

    # テスト用モジュールを作成
    make_temp_module(
        tmp_path,
        'a',
        textwrap.dedent(
            """
            value = 1
            """
        ),
    )
    make_temp_module(
        tmp_path,
        'b',
        textwrap.dedent(
            """
            from a import value
            """
        ),
    )
    make_temp_module(
        tmp_path,
        'c',
        textwrap.dedent(
            """
            from b import value
            """
        ),
    )

    import a  # noqa: F401  # type: ignore
    import b  # type: ignore
    import c  # type: ignore

    assert a.value == 1
    assert b.value == 1
    assert c.value == 1

    # a.pyを書き換えて値を変更
    (tmp_path / 'a.py').write_text('value = 777\n', encoding='utf-8')

    # deep reloadを実行（c からスタート）
    import deep_reloader as dr

    dr.DeepReloader().reload(c)

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
