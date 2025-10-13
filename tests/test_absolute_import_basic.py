import importlib
import textwrap

try:
    from .test_utils import make_temp_module
except ImportError:
    from test_utils import make_temp_module


def test_simple_from_import_reload(tmp_path):
    """
    シンプルなfrom-importの更新テスト
    """

    # テスト用モジュールを作成
    make_temp_module(
        tmp_path,
        'a',
        textwrap.dedent(
            """
            x = 1
            """
        ),
    )
    make_temp_module(
        tmp_path,
        'b',
        textwrap.dedent(
            """
            from a import x
            """
        ),
    )

    import a  # noqa: F401  # type: ignore
    import b  # type: ignore

    assert b.x == 1

    # a.pyを書き換えて値を変更
    (tmp_path / 'a.py').write_text('x = 999\n', encoding='utf-8')

    # deep reloadを実行
    import deep_reloader as dr

    dr.DeepReloader().reload(b)

    # 更新された値を確認
    new_b = importlib.import_module('b')
    assert new_b.x == 999


if __name__ == "__main__":
    from test_utils import run_test_as_script

    run_test_as_script(test_simple_from_import_reload, __file__)
