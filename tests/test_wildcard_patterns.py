"""
ワイルドカードインポートの全パターンを検証するテスト

以下のパターンをカバー:
1. from .subpackage import * (相対サブパッケージ)
2. from package import * (絶対パッケージ)
"""

import sys
import textwrap
from pathlib import Path

try:
    from .test_utils import create_test_modules, update_module
except ImportError:
    from test_utils import create_test_modules, update_module

from deep_reloader.symbol_extractor import SymbolExtractor


def test_relative_subpackage_wildcard(tmp_path):
    """from .subpackage import * のテスト"""

    modules_dir = create_test_modules(
        tmp_path,
        {
            '__init__.py': '',
            'subpkg/__init__.py': textwrap.dedent(
                """
                __all__ = ['VALUE', 'func']

                VALUE = 100

                def func():
                    return "hello"

                def _private():
                    return "private"
            """
            ),
            'main.py': textwrap.dedent(
                """
                from .subpkg import *

                def get_values():
                    return f"{VALUE}-{func()}"
            """
            ),
        },
        package_name='test_pkg',
    )

    from test_pkg import main  # type: ignore

    assert main.get_values() == "100-hello"

    # サブパッケージを更新
    update_module(
        modules_dir,
        'subpkg/__init__.py',
        """
        __all__ = ['VALUE', 'func']

        VALUE = 999

        def func():
            return "updated"

        def _private():
            return "private"
        """,
    )

    # deep reloadを実行
    from deep_reloader import deep_reload

    deep_reload(main)

    # 更新された値を確認
    assert main.get_values() == "999-updated"


def test_absolute_package_wildcard(tmp_path):
    """from package import * のテスト（同じパッケージ内のサブパッケージ）"""

    # 親パッケージの下にサブパッケージを配置
    modules_dir = create_test_modules(
        tmp_path,
        {
            '__init__.py': '',
            'abs_pkg/__init__.py': textwrap.dedent(
                """
                __all__ = ['CONST', 'helper']

                CONST = 42

                def helper():
                    return "help"
            """
            ),
            'consumer.py': textwrap.dedent(
                """
                from test_pkg.abs_pkg import *

                def get_values():
                    return f"{CONST}-{helper()}"
            """
            ),
        },
        package_name='test_pkg',
    )

    from test_pkg import consumer  # type: ignore

    assert consumer.get_values() == "42-help"

    # abs_pkgを更新
    update_module(
        modules_dir,
        'abs_pkg/__init__.py',
        """
        __all__ = ['CONST', 'helper']

        CONST = 999

        def helper():
            return "updated_help"
        """,
    )

    # deep reloadを実行
    from deep_reloader import deep_reload

    deep_reload(consumer)

    # 更新された値を確認
    assert consumer.get_values() == "999-updated_help"


def test_subpackage_wildcard_with_submodule(tmp_path):
    """from .subpackage import * でサブモジュールも含むケース"""

    modules_dir = create_test_modules(
        tmp_path,
        {
            '__init__.py': '',
            'subpkg/__init__.py': textwrap.dedent(
                """
                from . import helper

                __all__ = ['helper', 'VALUE']

                VALUE = 999
            """
            ),
            'subpkg/helper.py': textwrap.dedent(
                """
                def helper_func():
                    return "helper"
            """
            ),
            'main.py': textwrap.dedent(
                """
                from .subpkg import *

                def get_values():
                    return f"{VALUE}-{helper.helper_func()}"
            """
            ),
        },
        package_name='parent_pkg',
    )

    from parent_pkg import main  # type: ignore

    assert main.get_values() == "999-helper"

    # helper.pyを更新
    update_module(
        modules_dir,
        'subpkg/helper.py',
        """
        def helper_func():
            return "updated_helper"
        """,
    )

    # サブパッケージも更新
    update_module(
        modules_dir,
        'subpkg/__init__.py',
        """
        from . import helper

        __all__ = ['helper', 'VALUE']

        VALUE = 111
        """,
    )

    # deep reloadを実行
    from deep_reloader import deep_reload

    deep_reload(main)

    # 更新された値を確認
    assert main.get_values() == "111-updated_helper"


def test_absolute_module_wildcard(tmp_path):
    """from module import * のテスト"""

    # simple_moduleとconsumer_moduleを両方含むパッケージとして作成
    modules_dir = create_test_modules(
        tmp_path,
        {
            'simple_module.py': textwrap.dedent(
                """
                __all__ = ['VAR1', 'func1']

                VAR1 = 100
                VAR2 = 200  # __all__にない

                def func1():
                    return "f1"

                def func2():
                    return "f2"  # __all__にない
            """
            ),
            'consumer_module.py': textwrap.dedent(
                """
                from .simple_module import *

                def get_values():
                    return f"{VAR1}-{func1()}"
            """
            ),
        },
        package_name='test_absolute_mod',
    )

    from test_absolute_mod import consumer_module  # type: ignore

    assert consumer_module.get_values() == "100-f1"

    # simple_module.pyを更新
    update_module(
        modules_dir,
        'simple_module.py',
        """
        __all__ = ['VAR1', 'func1']

        VAR1 = 999
        VAR2 = 200

        def func1():
            return "updated_f1"

        def func2():
            return "f2"
        """,
    )

    # deep reloadを実行
    from deep_reloader import deep_reload

    deep_reload(consumer_module)

    # 更新された値を確認
    assert consumer_module.get_values() == "999-updated_f1"


def test_absolute_submodule_wildcard(tmp_path):
    """from package.submodule import * のテスト"""

    # パッケージとサブモジュールを同じツリー内に作成
    modules_dir = create_test_modules(
        tmp_path,
        {
            '__init__.py': '',
            'config.py': textwrap.dedent(
                """
                __all__ = ['SETTING1', 'get_config']

                SETTING1 = "value1"
                SETTING2 = "value2"  # __all__にない

                def get_config():
                    return "config"

                def _private_config():
                    return "private"
            """
            ),
            'app.py': textwrap.dedent(
                """
                from test_pkg.config import *

                def get_values():
                    return f"{SETTING1}-{get_config()}"
            """
            ),
        },
        package_name='test_pkg',
    )

    from test_pkg import app  # type: ignore

    assert app.get_values() == "value1-config"

    # config.pyを更新
    update_module(
        modules_dir,
        'config.py',
        """
        __all__ = ['SETTING1', 'get_config']

        SETTING1 = "updated_value"
        SETTING2 = "value2"

        def get_config():
            return "updated_config"

        def _private_config():
            return "private"
        """,
    )

    # deep reloadを実行
    from deep_reloader import deep_reload

    deep_reload(app)

    # 更新された値を確認
    assert app.get_values() == "updated_value-updated_config"


if __name__ == '__main__':
    from test_utils import run_test_as_script

    run_test_as_script(test_relative_subpackage_wildcard, __file__)
