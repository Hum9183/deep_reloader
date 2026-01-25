"""同じモジュールから複数の属性をインポートするケースのテスト

このテストは、重複モジュール検出の実装ミスを防ぐために追加されました。
誤った実装では、同じモジュールへの2回目以降の依存がスキップされ、
ツリーに含まれなくなる。
"""

import textwrap

from deep_reloader import deep_reload

from ..test_utils import create_test_modules, update_module


def test_multiple_attributes_from_same_module_reload(tmp_path):
    """
    同じモジュールから複数の属性をインポートした場合のリロードテスト

    誤った重複検出実装では、同じモジュールへの2回目以降の依存がスキップされ、
    ツリーに1回しか含まれなくなる。このテストはツリー構造を直接検証して、
    すべての依存関係が正しく処理されていることを確認する。
    """
    modules_dir = create_test_modules(
        tmp_path,
        {
            'utils.py': textwrap.dedent(
                """
                helper_value = 'original_helper'
                config_value = 'original_config'
                extra_value = 'original_extra'
                """
            ),
            'main.py': textwrap.dedent(
                """
                from .utils import helper_value
                from .utils import config_value
                from .utils import extra_value

                def get_values():
                    return [helper_value, config_value, extra_value]
                """
            ),
        },
        package_name='multipkg',
    )

    import multipkg.main  # type: ignore

    # ツリー構造を検証: utils への依存が3回出現することを確認
    from deep_reloader.deep_reloader import _build_tree  # type: ignore

    visited: set[str] = set()
    tree = _build_tree(multipkg.main, visited, 'multipkg')

    utils_dependency_count = sum(1 for child in tree.children if child.module.__name__ == 'multipkg.utils')

    # 正しい実装では3回（各AttributeDependencyに対して1回ずつ）
    # 誤った重複検知実装では1回しか現れない
    assert utils_dependency_count == 3, f'Expected 3 dependencies for 3 attributes, but got {utils_dependency_count}'

    # 初期値の確認
    assert multipkg.main.get_values() == ['original_helper', 'original_config', 'original_extra']

    # utils.pyを更新
    update_module(
        modules_dir,
        'utils.py',
        """
        helper_value = 'updated_helper'
        config_value = 'updated_config'
        extra_value = 'updated_extra'
    """,
    )

    # deep_reloader でリロード
    deep_reload(multipkg.main)

    # 3つすべての属性が更新されていることを確認
    assert multipkg.main.get_values() == ['updated_helper', 'updated_config', 'updated_extra']
