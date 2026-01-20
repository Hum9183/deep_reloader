import textwrap

try:
    from .test_utils import create_test_modules, update_module
except ImportError:
    from test_utils import create_test_modules, update_module


def test_parent_level_relative_import(tmp_path):
    """
    親階層への相対インポート (from ..module import something) のテスト
    """

    # パッケージ構造を作成
    modules_dir = create_test_modules(
        tmp_path,
        {
            'shared.py': textwrap.dedent(
                """
                shared_config = "initial"

                def get_config():
                    return shared_config
                """
            ),
            'subpkg/__init__.py': '',
            'subpkg/worker.py': textwrap.dedent(
                """
                from ..shared import shared_config, get_config

                def do_work():
                    return f"Working with: {shared_config} - {get_config()}"
                """
            ),
        },
        package_name='rootpkg',
    )

    from rootpkg.subpkg import worker  # noqa: F401  # type: ignore

    assert worker.do_work() == "Working with: initial - initial"

    # shared.pyを書き換えて値を変更
    update_module(
        modules_dir,
        'shared.py',
        """
        shared_config = "modified"

        def get_config():
            return "modified"
        """,
    )

    # deep reloadを実行
    from deep_reloader import deep_reload

    deep_reload(worker)

    # 更新された値を確認
    assert worker.do_work() == "Working with: modified - modified"


if __name__ == "__main__":
    from test_utils import run_test_as_script

    run_test_as_script(test_parent_level_relative_import, __file__)
