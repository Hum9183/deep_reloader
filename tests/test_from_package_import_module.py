"""from xxx import yyy 形式でサブモジュールを正しく追跡するテスト

_try_import_submodule() の機能をテスト:
- 相対インポート: from .utils import helper (helperがサブモジュール)
- 絶対インポート: from package import submodule (submoduleがサブモジュール)
"""

import sys
import textwrap

from .test_utils import create_test_modules, update_module


def test_relative_import_submodule(tmp_path):
    """相対インポートでサブモジュールを正しく追跡 (from .utils import helper)"""

    modules_dir = create_test_modules(
        tmp_path,
        {
            '__init__.py': '',
            'utils/__init__.py': '',
            'utils/helper.py': textwrap.dedent(
                """
                VERSION = 1
                """
            ),
            'main.py': textwrap.dedent(
                """
                from .utils import helper

                def get_version():
                    return helper.VERSION
                """
            ),
        },
        package_name='test_pkg',
    )

    from test_pkg import main  # type: ignore

    assert main.get_version() == 1

    # helperモジュールを更新
    update_module(modules_dir, 'utils/helper.py', 'VERSION = 2')

    from deep_reloader import deep_reload

    deep_reload(main)

    # サブモジュールとして追跡されていれば更新される
    assert main.get_version() == 2


def test_absolute_import_submodule(tmp_path):
    """絶対インポートでサブモジュールを正しく追跡 (from package import submodule)"""

    modules_dir = create_test_modules(
        tmp_path,
        {
            '__init__.py': '',
            'api.py': textwrap.dedent(
                """
                def get_value():
                    return "v1"
                """
            ),
            'client.py': textwrap.dedent(
                """
                from base_pkg import api

                def fetch_data():
                    return api.get_value()
                """
            ),
        },
        package_name='base_pkg',
    )

    from base_pkg import client  # type: ignore

    assert client.fetch_data() == 'v1'

    # base_pkg.api を更新
    update_module(
        modules_dir,
        'api.py',
        textwrap.dedent(
            """
            def get_value():
                return "v2"
            """
        ),
    )

    from deep_reloader import deep_reload

    deep_reload(client)

    # 絶対インポートでサブモジュールが追跡されていれば更新される
    assert client.fetch_data() == 'v2'


def test_absolute_import_symbol(tmp_path):
    """絶対インポートでシンボルを正しく追跡 (from package import function)"""

    modules_dir = create_test_modules(
        tmp_path,
        {
            '__init__.py': '',
            'utils.py': textwrap.dedent(
                """
                def helper():
                    return "v1"
                """
            ),
            'client.py': textwrap.dedent(
                """
                from base_pkg import utils

                def fetch_data():
                    return utils.helper()
                """
            ),
        },
        package_name='base_pkg',
    )

    from base_pkg import client  # type: ignore

    assert client.fetch_data() == 'v1'

    # utils.py を更新
    update_module(
        modules_dir,
        'utils.py',
        textwrap.dedent(
            """
            def helper():
                return "v2"
            """
        ),
    )

    from deep_reloader import deep_reload

    deep_reload(client)

    # シンボルが含まれるモジュールが追跡されていれば更新される
    assert client.fetch_data() == 'v2'


def test_absolute_import_package(tmp_path):
    """絶対インポートでパッケージを正しく追跡 (from package import subpackage)"""

    modules_dir = create_test_modules(
        tmp_path,
        {
            '__init__.py': '',
            'api/__init__.py': textwrap.dedent(
                """
                VALUE = "v1"
                """
            ),
            'client.py': textwrap.dedent(
                """
                from base_pkg import api

                def fetch_data():
                    return api.VALUE
                """
            ),
        },
        package_name='base_pkg',
    )

    from base_pkg import client  # type: ignore

    assert client.fetch_data() == 'v1'

    # api/__init__.py を更新
    update_module(
        modules_dir,
        'api/__init__.py',
        textwrap.dedent(
            """
            VALUE = "v2"
            """
        ),
    )

    from deep_reloader import deep_reload

    deep_reload(client)

    # サブパッケージが追跡されていれば更新される
    assert client.fetch_data() == 'v2'


def test_relative_import_package(tmp_path):
    """相対インポート(モジュール指定)でパッケージを正しく追跡 (from .parent import subpackage)"""

    modules_dir = create_test_modules(
        tmp_path,
        {
            '__init__.py': '',
            'parent/__init__.py': '',
            'parent/child_pkg/__init__.py': textwrap.dedent(
                """
                VALUE = "v1"
                """
            ),
            'parent/module.py': textwrap.dedent(
                """
                from .child_pkg import VALUE

                def get_value():
                    return VALUE
                """
            ),
        },
        package_name='test_pkg',
    )

    from test_pkg.parent import module  # type: ignore

    assert module.get_value() == 'v1'

    # child_pkg/__init__.py を更新
    update_module(
        modules_dir,
        'parent/child_pkg/__init__.py',
        textwrap.dedent(
            """
            VALUE = "v2"
            """
        ),
    )

    from deep_reloader import deep_reload

    deep_reload(module)

    # 相対インポートでサブパッケージが追跡されていれば更新される
    assert module.get_value() == 'v2'


if __name__ == '__main__':
    from test_utils import run_test_as_script

    print('=== Test 1: 相対インポート - from .utils import submodule ===')
    run_test_as_script(test_relative_import_submodule, __file__)

    print('\n=== Test 2: 絶対インポート - from package import submodule ===')
    run_test_as_script(test_absolute_import_submodule, __file__)

    print('\n=== Test 3: 絶対インポート - from package import symbol ===')
    run_test_as_script(test_absolute_import_symbol, __file__)

    print('\n=== Test 4: 絶対インポート - from package import subpackage ===')
    run_test_as_script(test_absolute_import_package, __file__)

    print('\n=== Test 5: 相対インポート - from .parent import subpackage ===')
    run_test_as_script(test_relative_import_package, __file__)

    print('\n全テスト成功！')


if __name__ == '__main__':
    from test_utils import run_test_as_script

    print('=== Test 1: 相対インポート - from .utils import helper ===')
    run_test_as_script(test_relative_import_submodule, __file__)

    print('\n=== Test 2: 絶対インポート - from package import submodule ===')
    run_test_as_script(test_absolute_import_submodule, __file__)
