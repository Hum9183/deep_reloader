import importlib
import textwrap

try:
    from .test_utils import add_temp_path_to_sys, make_temp_module
except ImportError:
    from test_utils import add_temp_path_to_sys, make_temp_module


def test_parent_level_relative_import(tmp_path):
    """
    親階層への相対インポート (from ..module import something) のテスト
    """

    # パッケージ構造を作成
    root_package = tmp_path / 'rootpkg'
    sub_package = root_package / 'subpkg'
    root_package.mkdir()
    sub_package.mkdir()

    # __init__.py ファイルを作成
    (root_package / '__init__.py').write_text('', encoding='utf-8')
    (sub_package / '__init__.py').write_text('', encoding='utf-8')

    # 親レベルに shared.py を作成
    (root_package / 'shared.py').write_text(
        textwrap.dedent(
            """
            shared_config = "initial"

            def get_config():
                return shared_config
            """
        ),
        encoding='utf-8',
    )

    # 子レベルに worker.py を作成 (from ..shared import shared_config, get_config)
    (sub_package / 'worker.py').write_text(
        textwrap.dedent(
            """
            from ..shared import shared_config, get_config

            def do_work():
                return f"Working with: {shared_config} - {get_config()}"
            """
        ),
        encoding='utf-8',
    )

    # sys.pathに一時ディレクトリを追加
    add_temp_path_to_sys(tmp_path)

    from rootpkg.subpkg import worker  # noqa: F401  # type: ignore

    assert worker.do_work() == "Working with: initial - initial"

    # shared.pyを書き換えて値を変更
    (root_package / 'shared.py').write_text(
        textwrap.dedent(
            """
            shared_config = "modified"

            def get_config():
                return "modified"
            """
        ),
        encoding='utf-8',
    )

    # deep reloadを実行
    import deep_reloader as dr

    dr.DeepReloader().reload(worker)

    # 更新された値を確認
    new_worker = importlib.import_module('rootpkg.subpkg.worker')
    assert new_worker.do_work() == "Working with: modified - modified"


if __name__ == "__main__":
    from test_utils import run_test_as_script

    run_test_as_script(test_parent_level_relative_import, __file__)
