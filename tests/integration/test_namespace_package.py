"""
namespace package（__init__.pyなし）でのdeep_reload動作テスト

Python 3.3以降（PEP 420）では__init__.pyなしでもパッケージとして機能します。
このテストはdeep_reloaderがそのようなnamespace packageを正しく扱えるかを検証します。
"""

import textwrap

from deep_reloader import deep_reload

from ..test_utils import create_test_modules, update_module


def test_namespace_package_without_init(tmp_path):
    """
    __init__.pyなしのnamespace packageでリロードできるか
    """
    # __init__.pyなしでパッケージを作成
    modules_dir = create_test_modules(
        tmp_path,
        {
            'a.py': textwrap.dedent(
                """
                x = 1
                """
            ),
            'b.py': textwrap.dedent(
                """
                from .a import x
                """
            ),
        },
        package_name='namespace_pkg',
        create_init=False,  # namespace packageとして作成
    )

    # __init__.pyが存在しないことを確認
    assert not (modules_dir / '__init__.py').exists()

    import namespace_pkg.b  # type: ignore

    assert namespace_pkg.b.x == 1

    # a.pyを書き換えて値を変更
    update_module(modules_dir, 'a.py', 'x = 999')

    # deep reloadを実行
    deep_reload(namespace_pkg.b)

    # 更新された値を確認
    assert namespace_pkg.b.x == 999


def test_namespace_package_relative_import(tmp_path):
    """
    __init__.pyなしのnamespace packageで相対インポートが動作するか
    """
    modules_dir = create_test_modules(
        tmp_path,
        {
            'utils.py': textwrap.dedent(
                """
                def helper():
                    return "original"
                """
            ),
            'main.py': textwrap.dedent(
                """
                from .utils import helper
                
                def process():
                    return helper()
                """
            ),
        },
        package_name='namespace_app',
        create_init=False,  # namespace packageとして作成
    )

    # __init__.pyが存在しないことを確認
    assert not (modules_dir / '__init__.py').exists()

    import namespace_app.main  # type: ignore

    assert namespace_app.main.process() == "original"

    # utils.pyを書き換え
    update_module(
        modules_dir,
        'utils.py',
        textwrap.dedent(
            """
            def helper():
                return "updated"
            """
        ),
    )

    # deep reloadを実行
    deep_reload(namespace_app.main)

    # 更新された値を確認
    assert namespace_app.main.process() == "updated"
