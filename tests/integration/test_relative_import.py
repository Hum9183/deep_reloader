import textwrap

from deep_reloader import deep_reload

from ..test_utils import create_test_modules, update_module


def test_same_level_relative_import(tmp_path):
    """
    同階層の相対インポート (from .module import something) のテスト
    """

    # パッケージ構造を作成
    modules_dir = create_test_modules(
        tmp_path,
        {
            'utils.py': textwrap.dedent(
                """
                helper_value = 42

                def helper_func():
                    return "original"
                """
            ),
            'main.py': textwrap.dedent(
                """
                from .utils import helper_func, helper_value

                value = helper_value
                result = helper_func()
                """
            ),
        },
        package_name='testpkg',
    )

    # 初期値の確認
    import testpkg.main  # type: ignore

    assert testpkg.main.value == 42
    assert testpkg.main.result == "original"

    # utils.py を更新
    update_module(
        modules_dir,
        'utils.py',
        """
        helper_value = 999

        def helper_func():
            return "updated"
    """,
    )

    # deep_reloader でリロード
    deep_reload(testpkg.main)

    # main.py のインポートされたシンボルも更新されることを確認
    assert testpkg.main.value == 999
    assert testpkg.main.result == "updated"


def test_parent_level_relative_import(tmp_path):
    """
    親パッケージからの相対インポート (from .. import module) のテスト
    """

    modules_dir = create_test_modules(
        tmp_path,
        {
            'config.py': textwrap.dedent(
                """
                VERSION = "1.0.0"
                """
            ),
            'sub/__init__.py': '',
            'sub/module.py': textwrap.dedent(
                """
                from ..config import VERSION

                version = VERSION
                """
            ),
        },
        package_name='mypkg',
    )

    # 初期値の確認
    import mypkg.sub.module  # type: ignore

    assert mypkg.sub.module.version == "1.0.0"

    # config.py を更新
    update_module(
        modules_dir,
        'config.py',
        """
        VERSION = "2.0.0"
    """,
    )

    # deep_reloader でリロード
    deep_reload(mypkg.sub.module)

    # 親パッケージの変更が反映されることを確認
    assert mypkg.sub.module.version == "2.0.0"
