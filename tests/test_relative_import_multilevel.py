import importlib
import textwrap

try:
    from .test_utils import add_temp_path_to_sys, make_temp_module
except ImportError:
    from test_utils import add_temp_path_to_sys, make_temp_module


def test_multilevel_relative_import(tmp_path):
    """
    多階層相対インポート (from ...level3.module import something) のテスト
    """

    # 深い階層のパッケージ構造を作成
    level1 = tmp_path / 'level1'
    level2 = level1 / 'level2'
    level3 = level2 / 'level3'
    level1.mkdir()
    level2.mkdir()
    level3.mkdir()

    # 各階層に __init__.py を作成
    (level1 / '__init__.py').write_text('', encoding='utf-8')
    (level2 / '__init__.py').write_text('', encoding='utf-8')
    (level3 / '__init__.py').write_text('', encoding='utf-8')

    # 最上位に core.py を作成
    (level1 / 'core.py').write_text(
        textwrap.dedent(
            """
            core_value = "original_core"

            def core_function():
                return core_value
            """
        ),
        encoding='utf-8',
    )

    # 最下位から3階層上の core.py をインポート
    (level3 / 'deep_module.py').write_text(
        textwrap.dedent(
            """
            from ...core import core_value, core_function

            def deep_work():
                return f"Deep: {core_value} - {core_function()}"
            """
        ),
        encoding='utf-8',
    )

    # sys.pathに一時ディレクトリを追加
    add_temp_path_to_sys(tmp_path)

    from level1.level2.level3 import deep_module  # noqa: F401  # type: ignore

    assert deep_module.deep_work() == "Deep: original_core - original_core"

    # core.pyを書き換えて値を変更
    (level1 / 'core.py').write_text(
        textwrap.dedent(
            """
            core_value = "updated_core"

            def core_function():
                return "updated_core"
            """
        ),
        encoding='utf-8',
    )

    # deep reloadを実行
    import deep_reloader as dr

    dr.DeepReloader().reload(deep_module)

    # 更新された値を確認
    new_deep_module = importlib.import_module('level1.level2.level3.deep_module')
    assert new_deep_module.deep_work() == "Deep: updated_core - updated_core"


if __name__ == "__main__":
    from test_utils import run_test_as_script

    run_test_as_script(test_multilevel_relative_import, __file__)
