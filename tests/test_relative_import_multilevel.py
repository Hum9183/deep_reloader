import textwrap

from .test_utils import create_test_modules, update_module


def test_multilevel_relative_import(tmp_path):
    """
    多階層相対インポート (from ...level3.module import something) のテスト
    """

    # 深い階層のパッケージ構造を作成
    modules_dir = create_test_modules(
        tmp_path,
        {
            'core.py': textwrap.dedent(
                """
                core_value = "original_core"

                def core_function():
                    return core_value
                """
            ),
            'level2/__init__.py': '',
            'level2/level3/__init__.py': '',
            'level2/level3/deep_module.py': textwrap.dedent(
                """
                from ...core import core_value, core_function

                def deep_work():
                    return f"Deep: {core_value} - {core_function()}"
                """
            ),
        },
        package_name='level1',
    )

    from level1.level2.level3 import deep_module  # noqa: F401  # type: ignore

    assert deep_module.deep_work() == "Deep: original_core - original_core"

    # core.pyを書き換えて値を変更
    update_module(
        modules_dir,
        'core.py',
        """
        core_value = "updated_core"

        def core_function():
            return "updated_core"
        """,
    )

    # deep reloadを実行
    from deep_reloader import deep_reload

    deep_reload(deep_module)

    # 更新された値を確認
    assert deep_module.deep_work() == "Deep: updated_core - updated_core"
