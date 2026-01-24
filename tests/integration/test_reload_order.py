"""モジュールレベルコードのリロードテスト

モジュールインポート時にトップレベルで実行されるコードが、
子モジュールの最新の値を参照できることを検証します。

このテストは copy_to() の影響を受けないケースを検証し、
子モジュールのリロードが親モジュールのインポートより先に行われることを保証します。
"""

import textwrap

from ..test_utils import create_test_modules, update_module


def test_child_reload_before_parent_import(tmp_path):
    """モジュールレベルコードが正しく更新されることを確認

    このテストは、親モジュールが子モジュールをインポートする際に
    モジュールレベルで実行されるコードが、子モジュールの最新の値を
    参照できることを検証します。

    もし子のリロードが親のインポートより後だと、
    親のモジュールレベルコードは古い子の値を使って実行されてしまいます。
    """

    # テスト用パッケージを作成
    modules_dir = create_test_modules(
        tmp_path,
        {
            '__init__.py': '',
            'config.py': textwrap.dedent(
                """
                VERSION = "1.0"
                """
            ),
            'app.py': textwrap.dedent(
                """
                from .config import VERSION

                # モジュールレベルで実行されるコード（インポート時に実行）
                APP_TITLE = f"MyApp v{VERSION}"
                """
            ),
        },
        package_name='test_package',
    )
    import test_package.app  # type: ignore

    assert test_package.app.APP_TITLE == "MyApp v1.0"

    # config.pyを書き換えてバージョンを変更
    update_module(modules_dir, 'config.py', 'VERSION = "2.0"')

    # deep reloadを実行
    from deep_reloader import deep_reload

    deep_reload(test_package.app)

    # 重要: APP_TITLEはモジュールインポート時に生成される
    # もし子のリロードが親のインポートより後だと、古いVERSIONを使ってしまう
    assert test_package.app.APP_TITLE == "MyApp v2.0"
