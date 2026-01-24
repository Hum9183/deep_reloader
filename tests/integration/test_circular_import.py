"""循環インポートのテスト

A → B → A のような循環インポート構造が正しくリロードされることを確認
"""

import textwrap

from deep_reloader import deep_reload

from ..test_utils import create_test_modules, update_module


def test_circular_import(tmp_path):
    """循環インポート（A → B → A）が正しく処理されることを確認"""

    # パッケージ構造を作成
    modules_dir = create_test_modules(
        tmp_path,
        {
            'module_a.py': textwrap.dedent(
                """
                def func_a():
                    return "A-v1"

                def call_b():
                    from .module_b import func_b
                    return func_b()
                """
            ),
            'module_b.py': textwrap.dedent(
                """
                def func_b():
                    return "B-v1"

                def call_a():
                    from .module_a import func_a
                    return func_a()
                """
            ),
        },
        package_name='circular_pkg',
    )

    from circular_pkg import module_a  # noqa: F401  # type: ignore

    # 初期値確認
    assert module_a.func_a() == 'A-v1'
    assert module_a.call_b() == 'B-v1'

    # モジュールを更新
    update_module(
        modules_dir,
        'module_a.py',
        """
        def func_a():
            return "A-v2"

        def call_b():
            from .module_b import func_b
            return func_b()
        """,
    )

    update_module(
        modules_dir,
        'module_b.py',
        """
        def func_b():
            return "B-v2"

        def call_a():
            from .module_a import func_a
            return func_a()
        """,
    )

    # deep reloadを実行
    deep_reload(module_a)

    # 更新確認
    assert module_a.func_a() == 'A-v2'
    assert module_a.call_b() == 'B-v2'
