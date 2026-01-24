"""
from . import * パターンのテスト

パッケージ内で from . import * を使用した場合の依存関係抽出をテストする
"""

import sys
import textwrap
from pathlib import Path
from types import ModuleType

try:
    from .test_utils import create_test_modules, update_module
except ImportError:
    from test_utils import create_test_modules, update_module

from deep_reloader.symbol_extractor import SymbolExtractor


def test_relative_wildcard_with_all(tmp_path):
    """from . import * (__all__あり) のテスト"""

    modules_dir = create_test_modules(
        tmp_path,
        {
            '__init__.py': textwrap.dedent(
                """
                __all__ = ['func1', 'func2']

                def func1():
                    return "v1"

                def func2():
                    return "v2"

                def _private_func():
                    return "private"
            """
            ),
            'main.py': textwrap.dedent(
                """
                from . import *

                def get_values():
                    return f"{func1()}-{func2()}"
            """
            ),
        },
        package_name='pkg_with_all',
    )

    from pkg_with_all import main  # type: ignore

    assert main.get_values() == "v1-v2"

    # __init__.pyを更新
    update_module(
        modules_dir,
        '__init__.py',
        """
        __all__ = ['func1', 'func2']

        def func1():
            return "updated1"

        def func2():
            return "updated2"

        def _private_func():
            return "private"
        """,
    )

    # deep reloadを実行
    from deep_reloader import deep_reload

    deep_reload(main)

    # 更新された値を確認
    assert main.get_values() == "updated1-updated2"


def test_relative_wildcard_without_all(tmp_path):
    """from . import * (__all__なし) のテスト"""

    modules_dir = create_test_modules(
        tmp_path,
        {
            '__init__.py': textwrap.dedent(
                """
                def public_func():
                    return "pub"

                VALUE = 42

                def _private_func():
                    return "priv"
            """
            ),
            'main.py': textwrap.dedent(
                """
                from . import *

                def get_values():
                    return f"{VALUE}-{public_func()}"
            """
            ),
        },
        package_name='pkg_without_all',
    )

    from pkg_without_all import main  # type: ignore

    assert main.get_values() == "42-pub"

    # __init__.pyを更新
    update_module(
        modules_dir,
        '__init__.py',
        """
        def public_func():
            return "updated_pub"

        VALUE = 999

        def _private_func():
            return "priv"
        """,
    )

    # deep reloadを実行
    from deep_reloader import deep_reload

    deep_reload(main)

    # 更新された値を確認
    assert main.get_values() == "999-updated_pub"


def test_relative_wildcard_with_submodule(tmp_path):
    """from . import * でサブモジュールを含むケース"""

    modules_dir = create_test_modules(
        tmp_path,
        {
            '__init__.py': textwrap.dedent(
                """
                from . import helper

                __all__ = ['helper', 'func1']

                def func1():
                    return "f1"
            """
            ),
            'helper.py': textwrap.dedent(
                """
                def helper_func():
                    return "help"
            """
            ),
            'main.py': textwrap.dedent(
                """
                from . import *

                def get_values():
                    return f"{func1()}-{helper.helper_func()}"
            """
            ),
        },
        package_name='pkg_with_submodule',
    )

    from pkg_with_submodule import main  # type: ignore

    assert main.get_values() == "f1-help"

    # helper.pyを更新
    update_module(
        modules_dir,
        'helper.py',
        """
        def helper_func():
            return "updated_help"
        """,
    )

    # __init__.pyも更新
    update_module(
        modules_dir,
        '__init__.py',
        """
        from . import helper

        __all__ = ['helper', 'func1']

        def func1():
            return "updated_f1"
        """,
    )

    # deep reloadを実行
    from deep_reloader import deep_reload

    deep_reload(main)

    # 更新された値を確認
    assert main.get_values() == "updated_f1-updated_help"


def test_relative_wildcard_with_subpackage(tmp_path):
    """from . import * でサブパッケージを含むケース"""

    # パッケージ構造を作成
    pkg_dir = tmp_path / "pkg_with_subpackage"
    pkg_dir.mkdir()

    # サブパッケージ作成
    subpkg_dir = pkg_dir / "subpkg"
    subpkg_dir.mkdir()
    (subpkg_dir / "__init__.py").write_text("VALUE = 100\n")

    # __init__.py で __all__ にサブパッケージを含め、subpkgをインポート
    (pkg_dir / "__init__.py").write_text("__all__ = ['subpkg']\nfrom . import subpkg\n")

    # main.py で from . import * を実行
    (pkg_dir / "main.py").write_text(
        textwrap.dedent(
            """
            from . import *

            def get_value():
                return subpkg.VALUE
        """
        )
    )

    sys.path.insert(0, str(tmp_path))
    try:
        from pkg_with_subpackage import main  # type: ignore

        assert main.get_value() == 100

        # サブパッケージを更新
        (subpkg_dir / "__init__.py").write_text("VALUE = 999\n")

        # deep reloadを実行
        from deep_reloader import deep_reload

        deep_reload(main)

        # 更新された値を確認
        assert main.get_value() == 999
    finally:
        sys.path.remove(str(tmp_path))


if __name__ == '__main__':
    from test_utils import run_test_as_script

    run_test_as_script(test_relative_wildcard_with_all, __file__)
