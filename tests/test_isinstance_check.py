# -*- coding: utf-8 -*-
"""
モジュール参照の一貫性テスト

sys.modules[name] = self.module により、リロード後も既存のモジュール参照が有効であることを確認する。
これは deep_reloader の重要な特徴：モジュールオブジェクトのIDを保持することで、
既存の参照から最新の内容にアクセスできる。
"""
import textwrap

try:
    from .test_utils import create_test_modules, update_module
except ImportError:
    from test_utils import create_test_modules, update_module


def test_module_reference_consistency(tmp_path):
    """リロード前のモジュール参照が、リロード後も同じIDを保持し、最新の内容にアクセスできることを確認"""

    # テスト用のモジュール構造を作成
    modules_dir = create_test_modules(
        tmp_path,
        {
            '__init__.py': '',
            'main.py': textwrap.dedent(
                '''
                version = 1

                def get_version():
                    return version
            '''
            ),
        },
        package_name='test_pkg',
    )

    import test_pkg.main  # type: ignore

    # 重要：変数に保存して、同じオブジェクトを参照し続ける
    main_ref = test_pkg.main

    # リロード前のIDと値を記録
    module_id_before = id(main_ref)
    version_before = main_ref.get_version()

    assert version_before == 1

    # モジュールを変更
    update_module(
        modules_dir,
        'main.py',
        textwrap.dedent(
            '''
            version = 2

            def get_version():
                return version
        '''
        ),
    )

    # deep_reload を実行
    from deep_reloader import deep_reload

    deep_reload(main_ref)

    # リロード後のIDと値を確認
    module_id_after = id(main_ref)
    version_after = main_ref.get_version()

    # 重要：モジュールオブジェクトのIDが変わっていないことを確認
    assert (
        module_id_before == module_id_after
    ), f'モジュールIDが変わっている: before={module_id_before}, after={module_id_after}'

    # 重要：既存の参照から最新の内容にアクセスできることを確認
    assert version_after == 2, 'リロード後の値が反映されていない'


if __name__ == '__main__':
    from test_utils import run_test_as_script

    run_test_as_script(test_module_reference_consistency, __file__)
