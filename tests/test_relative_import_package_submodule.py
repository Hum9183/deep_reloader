"""
深層的な相対インポート + パッケージサブモジュール のテスト

問題：
  from ..MainFunction import ageha_api のとき、
  ageha_api パッケージ内の pbd_node_api などのサブモジュールが
  正しく追跡され、リロードされるか

テスト内容：
  1. パッケージからサブモジュールをインポート
  2. 深いレベルの相対インポートで関数を参照
  3. リロード時にサブモジュール内の関数が更新されるか確認
"""

import textwrap

from .test_utils import create_test_modules, update_module


def test_package_init_imports_submodule(tmp_path):
    """
    パッケージの__init__.pyがサブモジュールをインポートしている場合のテスト

    構造:
        parent_package/
        ├── __init__.py
        ├── middle_package/
        │   ├── __init__.py
        │   └── user.py (from ..parent_pkg import core_func)
        └── parent_pkg/
            ├── __init__.py (from .core_api import create_node)
            └── core_api.py (def create_node(): return "v1")

    user.py が parent_pkg パッケージをインポートしたとき、
    core_api.py のサブモジュール内の create_node() が更新されるか
    """

    # テスト用パッケージ構造を作成
    modules_dir = create_test_modules(
        tmp_path,
        {
            '__init__.py': '',
            # core_api.py: サブモジュール
            'parent_pkg/__init__.py': textwrap.dedent(
                """
                from .core_api import create_node
                """
            ),
            'parent_pkg/core_api.py': textwrap.dedent(
                """
                def create_node():
                    return "v1"
                """
            ),
            # user.py: 相対インポートで parent_pkg を参照
            'middle_package/__init__.py': '',
            'middle_package/user.py': textwrap.dedent(
                """
                from ..parent_pkg import create_node

                def get_node_info():
                    return create_node()
                """
            ),
        },
        package_name='test_pkg',
    )

    # モジュールをインポート
    import test_pkg.middle_package.user  # noqa: F401  # type: ignore

    # 初期値を確認
    assert test_pkg.middle_package.user.get_node_info() == 'v1'

    # core_api.py を書き換えて値を変更
    update_module(
        modules_dir,
        'parent_pkg/core_api.py',
        """
        def create_node():
            return "v2"
        """,
    )

    # deep reloadを実行
    from deep_reloader import deep_reload

    deep_reload(test_pkg.middle_package.user)

    # 更新された値を確認
    assert test_pkg.middle_package.user.get_node_info() == 'v2'
