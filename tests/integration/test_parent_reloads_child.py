"""親モジュールが子モジュールをreloadするケースのテスト

親モジュールが子モジュールをimportした後、importlib.reload()を呼び出すケースで、
deep_reloaderが正しく動作することを確認します。

バグの経緯:
- 親モジュールが子モジュールをimportした後、importlib.reload()を呼び出すパターンが存在
- deep_reloaderが sys.modules.pop() + import_module() パターンを使っていた時、
  "ImportError: module xxx not in sys.modules" エラーが発生
- importlib.reload() パターンに変更することで解決

このテストは、将来的にsys.modules.pop() + import_module() パターンに戻さないことを保証します。
"""

import textwrap

from deep_reloader import deep_reload

from ..test_utils import create_test_modules


def test_parent_module_reloads_child_modules(tmp_path):
    """親モジュールが子モジュールをimportした後、importlib.reload()を呼び出すケースのテスト

    パッケージ構造:
        testpkg/
            __init__.py
            child_a.py          # 子モジュールA
            child_b.py          # 子モジュールB
            parent.py           # 親モジュール

    parent.pyの動作:
        1. from . import child_a, child_b  # 子をimport
        2. importlib.reload(child_a)        # 子Aをreload
        3. importlib.reload(child_b)        # 子Bをreload

    バグの発生条件:
        - 複数の子モジュールをreloadする必要がある（1つだけではエラーにならない）
        - sys.modules.pop() + import_module()パターンでリロードすると、
          2つ目の子モジュールをreloadしようとした時にsys.modulesから既に削除されているため
          ImportErrorが発生する

    期待される動作:
        - deep_reload(parent) が ImportError を発生させずに成功する
    """

    # テスト用パッケージを作成
    _ = create_test_modules(
        tmp_path,
        {
            '__init__.py': '',
            'child_a.py': textwrap.dedent(
                """
                VALUE_A = "v1"
                """
            ),
            'child_b.py': textwrap.dedent(
                """
                VALUE_B = "v1"
                """
            ),
            'parent.py': textwrap.dedent(
                """
                import importlib
                from . import child_a
                from . import child_b

                # 複数の子モジュールをreload
                importlib.reload(child_a)
                importlib.reload(child_b)
                """
            ),
        },
        package_name='testpkg',
    )

    # 親モジュールをimport
    import testpkg.parent  # type: ignore

    # sys.modules.pop() + import_module()パターンでは以下でImportErrorが発生する
    # 理由: deep_reloadがparentモジュールをpop()して再importする際、
    #       parentモジュールのトップレベルコードが再実行され、
    #       child_aをリロードした後、child_bをリロードしようとするが、
    #       child_aは既にpop()によってsys.modulesから削除されているため、
    #       2つ目のreload(child_b)で "module testpkg.child_b not in sys.modules" エラーが発生する
    #
    # 正しいimportlib.reload()パターンでは、sys.modulesから削除せずにリロードするため成功する
    try:
        deep_reload(testpkg.parent)
    except ImportError as e:
        raise AssertionError(f"deep_reload should not raise ImportError: {e}")
