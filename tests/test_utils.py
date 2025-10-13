import importlib
import sys
import tempfile
from pathlib import Path
from typing import Callable

# TODO: パッケージ構築ユーティリティ関数の追加
# make_temp_module()と同様に、パッケージ構造を簡単に作成するためのユーティリティ関数を追加する。
# 現在はテストファイルごとにディレクトリ作成、__init__.py作成、sys.path追加を手動で行っているが、
# これを自動化する関数が必要。
# 例: make_temp_package(tmp_path, package_structure) のような関数で、
# 辞書やYAMLで構造を定義して一括作成できるようにする。
#
# 実装例:
# def make_temp_package(tmp_path: Path, package_structure: dict) -> None:
#     """
#     辞書で定義されたパッケージ構造を一括作成
#     
#     Args:
#         tmp_path: 一時ディレクトリのPath
#         package_structure: パッケージ構造を定義した辞書
#                           例: {'pkg': {'__init__.py': '', 'mod.py': 'x=1'}}
#     """
#     # 実装予定


def setup_package_parent_path(test_file_path: str) -> None:
    """パッケージの親ディレクトリをsys.pathに追加してパッケージのインポートをサポート"""
    base_path = Path(test_file_path)
    package_parent_dir = base_path.parent.parent.parent
    if str(package_parent_dir) not in sys.path:
        sys.path.insert(0, str(package_parent_dir))


def clear_test_environment():
    """一時ディレクトリのモジュールとパスをクリーンアップしてテスト分離を実現"""
    # 一時ディレクトリのモジュールを検出
    modules_to_remove = []
    for module_name in list(sys.modules.keys()):
        module = sys.modules[module_name]
        if hasattr(module, '__file__') and module.__file__:  # __file__属性を持つモジュールのみ
            module_path = str(module.__file__)
            if _is_temp_path(module_path):  # 一時ディレクトリパスかチェック
                modules_to_remove.append(module_name)

    # 検出されたモジュールを削除
    for module_name in modules_to_remove:
        sys.modules.pop(module_name, None)

    # 一時ディレクトリのパスを検出
    paths_to_remove = []
    for path in sys.path:
        if _is_temp_path(path):
            paths_to_remove.append(path)

    # 検出されたパスを削除
    for path in paths_to_remove:
        if path in sys.path:
            sys.path.remove(path)

    importlib.invalidate_caches()


def add_temp_path_to_sys(tmp_path: Path) -> None:
    """
    一時ディレクトリをsys.pathに追加

    Args:
        tmp_path: 一時ディレクトリのPath

    Note:
        重複チェック付きでsys.pathに追加します。
        単一モジュール作成（make_temp_module）とパッケージ構造作成の両方で使用できます。
    """
    tmp_path_str = str(tmp_path)
    if tmp_path_str not in sys.path:
        sys.path.insert(0, tmp_path_str)


def make_temp_module(tmp_path: Path, name: str, content: str) -> Path:
    """
    指定されたディレクトリに一時モジュールを作成し、自動的にsys.pathに追加

    Args:
        tmp_path: 一時ディレクトリのPath
        name: モジュール名（拡張子なし）
        content: モジュールの内容

    Returns:
        作成されたファイルのPath

    Note:
        add_temp_path_to_sys()を内部で呼び出して自動的にsys.pathに追加します。
        これにより、テストコード内でsys.path.insert()を毎回書く必要がなくなります。
    """
    # ファイル作成
    path = tmp_path / f'{name}.py'
    path.write_text(content, encoding='utf-8')

    # sys.pathに一時ディレクトリを自動追加
    add_temp_path_to_sys(tmp_path)

    return path


def run_test_as_script(test_function: Callable[[Path], None], test_file_path: str) -> None:
    """
    スクリプト実行時の共通ロジック

    pytestが自動的に提供する機能をスクリプト実行時に自動で代替実装：
    - パッケージパスの設定（pytestのカレントディレクトリベース実行）
    - 一時ディレクトリの作成（pytestのtmp_pathフィクスチャ）
    - テスト前後のモジュールクリーンアップ（pytestの分離機能）
    - 例外処理とテスト結果の表示（pytestのレポート機能）

    これにより、pytestとスクリプト実行の両方で同じテストロジックが動作する
    デュアル実行アーキテクチャを実現する。

    Args:
        test_function: 実行するテスト関数
                      pytest形式: (tmp_path: Path) -> None
        test_file_path: テストファイルの絶対パス（通常は __file__ を渡す）

    Raises:
        AssertionError: テスト内でのアサーション失敗
        ImportError: モジュールインポートエラー
        ModuleNotFoundError: モジュールが見つからない
        AttributeError: 属性アクセスエラー
        OSError: ファイルシステム関連エラー
        Exception: その他の予期しないエラー

    Example:
        >>> def test_my_function(tmp_path):
        ...     make_temp_module(tmp_path, 'test', 'x = 1')
        ...     # テストコード（pytestと同じ形式）
        >>>
        >>> if __name__ == "__main__":
        ...     # pytestの機能を自動で代替してスクリプト実行
        ...     run_test_as_script(test_my_function, __file__)
    """
    # パス設定
    setup_package_parent_path(test_file_path)

    # テスト前のクリーンアップ
    clear_test_environment()

    try:
        # 一時ディレクトリでテスト実行
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            # テスト実行
            test_function(tmp_path)
            print("OK: テスト成功！")

    except (AssertionError, ImportError, ModuleNotFoundError, AttributeError) as e:
        print(f"NG: テスト失敗: {e}")
        raise
    except OSError as e:
        print(f"NG: ファイルシステムエラー: {e}")
        raise
    except Exception as e:
        print(f"NG: 予期しないエラー: {e}")
        raise
    finally:
        # テスト後のクリーンアップ
        clear_test_environment()


def _is_temp_path(path: str) -> bool:
    """パスが一時ディレクトリかどうかを判定"""
    # 一時ディレクトリパスパターンの定義
    temp_patterns = [
        'pytest-of-',  # pytest実行時の一時ディレクトリ
        '/tmp/tmp',  # Unix系の一時ディレクトリ
        '/Temp/tmp',  # Windows系の一時ディレクトリ
        '/var/folders/',  # macOSの一時ディレクトリ
    ]

    # パターンマッチングでチェック
    for pattern in temp_patterns:
        if pattern in path:
            return True

    return False
