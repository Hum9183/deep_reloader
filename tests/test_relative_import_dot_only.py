"""from . import module 形式のインポートテスト

from . import module1, module2 のような形式のインポートが
正しくリロードされることを確認
"""

import textwrap

from .test_utils import create_test_modules, update_module


def test_dot_only_module_import(tmp_path):
    """from . import module 形式のインポートが正しく更新されることを確認"""

    # パッケージ構造を作成
    modules_dir = create_test_modules(
        tmp_path,
        {
            '__init__.py': '',
            'config.py': textwrap.dedent(
                """
                VALUE = 100
                """
            ),
            'utils.py': textwrap.dedent(
                """
                UTIL_VALUE = 200
                """
            ),
            'main.py': textwrap.dedent(
                """
                from . import config, utils

                def get_values():
                    return f"{config.VALUE}-{utils.UTIL_VALUE}"
                """
            ),
        },
        package_name='test_package',
    )

    from test_package import main  # type: ignore

    assert main.get_values() == '100-200'

    # config.pyとutils.pyを更新
    update_module(modules_dir, 'config.py', 'VALUE = 999')
    update_module(modules_dir, 'utils.py', 'UTIL_VALUE = 888')

    # deep reloadを実行
    from deep_reloader import deep_reload

    deep_reload(main)

    # 更新確認
    assert main.get_values() == '999-888'


def test_dot_only_module_import_with_function(tmp_path):
    """from . import module 形式で関数を使用する場合のテスト"""

    # パッケージ構造を作成
    modules_dir = create_test_modules(
        tmp_path,
        {
            '__init__.py': '',
            'helper.py': textwrap.dedent(
                """
                def get_value():
                    return "v1"
                """
            ),
            'app.py': textwrap.dedent(
                """
                from . import helper

                def run():
                    return f"App: {helper.get_value()}"
                """
            ),
        },
        package_name='test_package2',
    )

    from test_package2 import app  # type: ignore

    assert app.run() == 'App: v1'

    # helper.pyを更新
    update_module(
        modules_dir,
        'helper.py',
        """
        def get_value():
            return "v2"
        """,
    )

    # deep reloadを実行
    from deep_reloader import deep_reload

    deep_reload(app)

    # 更新確認
    assert app.run() == 'App: v2'
