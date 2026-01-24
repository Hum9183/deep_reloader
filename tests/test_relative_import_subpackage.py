"""from . import subpackage 形式のサブパッケージインポートテスト

from . import subpkg のような形式で、サブパッケージをインポートする場合の
リロードが正しく動作することを確認
"""

import textwrap

from .test_utils import create_test_modules, update_module


def test_import_subpackage_directly(tmp_path):
    """from . import subpackage 形式でサブパッケージをインポートした場合のテスト"""

    # パッケージ構造を作成
    modules_dir = create_test_modules(
        tmp_path,
        {
            '__init__.py': '',
            'subpkg/__init__.py': textwrap.dedent(
                """
                VERSION = "1.0.0"

                def get_version():
                    return VERSION
                """
            ),
            'main.py': textwrap.dedent(
                """
                from . import subpkg

                def show_version():
                    return f"Version: {subpkg.get_version()}"
                """
            ),
        },
        package_name='test_package',
    )

    from test_package import main  # type: ignore

    assert main.show_version() == 'Version: 1.0.0'

    # subpkgの__init__.pyを更新
    update_module(
        modules_dir,
        'subpkg/__init__.py',
        """
        VERSION = "2.0.0"

        def get_version():
            return VERSION
        """,
    )

    # deep reloadを実行
    from deep_reloader import deep_reload

    deep_reload(main)

    # 更新確認
    assert main.show_version() == 'Version: 2.0.0'


def test_import_subpackage_and_module_mixed(tmp_path):
    """from . import subpackage, module の混在テスト"""

    # パッケージ構造を作成
    modules_dir = create_test_modules(
        tmp_path,
        {
            '__init__.py': '',
            'config.py': textwrap.dedent(
                """
                CONFIG_VALUE = 100
                """
            ),
            'subpkg/__init__.py': textwrap.dedent(
                """
                PKG_VALUE = 200
                """
            ),
            'main.py': textwrap.dedent(
                """
                from . import config, subpkg

                def get_values():
                    return f"{config.CONFIG_VALUE}-{subpkg.PKG_VALUE}"
                """
            ),
        },
        package_name='test_package2',
    )

    from test_package2 import main  # type: ignore

    assert main.get_values() == '100-200'

    # 両方更新
    update_module(modules_dir, 'config.py', 'CONFIG_VALUE = 999')
    update_module(modules_dir, 'subpkg/__init__.py', 'PKG_VALUE = 888')

    # deep reloadを実行
    from deep_reloader import deep_reload

    deep_reload(main)

    # 更新確認
    assert main.get_values() == '999-888'
