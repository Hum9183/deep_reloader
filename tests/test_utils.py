import importlib
import sys
import tempfile
from pathlib import Path
from typing import Callable, Dict, Optional, Set

# テストで使用した一時ディレクトリのパスを記録（pytest/スクリプト実行の両方）
_test_temp_dirs: Set[Path] = set()

# パッケージ親ディレクトリのパスを記録（スクリプト実行時のみ）
_package_parent_path: Optional[str] = None

# ============================================================
# テスト環境クリーンアップ（インフラ層）
# pytest/スクリプト実行の両方で使用される共通クリーンアップ機能
# ============================================================


def clear_test_environment():
    """一時ディレクトリのモジュールとパスをクリーンアップしてテスト分離を実現"""
    # 記録されている一時ディレクトリ配下のモジュールを削除
    modules_to_remove = []
    for module_name, module in list(sys.modules.items()):
        # __file__属性がないモジュールはスキップ
        if not hasattr(module, '__file__') or not module.__file__:
            continue

        module_path = Path(module.__file__)

        # 記録された一時ディレクトリのいずれかの配下にあるかチェック
        for temp_dir in _test_temp_dirs:
            if temp_dir in module_path.parents or module_path == temp_dir:
                modules_to_remove.append(module_name)
                break  # 見つかったら次のモジュールへ

    # 検出されたモジュールを削除
    for module_name in modules_to_remove:
        sys.modules.pop(module_name, None)

    # 記録されている一時ディレクトリのパスをsys.pathから削除
    paths_to_remove = []
    for path in sys.path:
        path_obj = Path(path)

        # 記録された一時ディレクトリのいずれかと一致するかチェック
        for temp_dir in _test_temp_dirs:
            if path_obj == temp_dir or temp_dir in path_obj.parents:
                paths_to_remove.append(path)
                break  # 見つかったら次のパスへ

    for path in paths_to_remove:
        if path in sys.path:
            sys.path.remove(path)

    importlib.invalidate_caches()

    # クリーンアップ後は記録をクリア
    _test_temp_dirs.clear()

    # パッケージ親ディレクトリのパスを削除
    global _package_parent_path
    if _package_parent_path and _package_parent_path in sys.path:
        sys.path.remove(_package_parent_path)
    _package_parent_path = None


# ============================================================
# テストヘルパー関数
# 各テスト関数が直接使用するユーティリティ
# ============================================================


def add_temp_path_to_sys(tmp_path: Path) -> None:
    """
    一時ディレクトリをsys.pathに追加し、記録する

    Args:
        tmp_path: 一時ディレクトリのPath

    Note:
        重複チェック付きでsys.pathに追加し、後でクリーンアップできるよう記録します。
    """
    # 一時ディレクトリとして記録
    _test_temp_dirs.add(tmp_path)

    tmp_path_str = str(tmp_path)
    if tmp_path_str not in sys.path:
        sys.path.insert(0, tmp_path_str)


def create_test_modules(tmp_path: Path, structure: Dict[str, str], package_name: Optional[str] = None) -> Path:
    """
    辞書で定義されたテストモジュール構造を一括作成し、sys.pathに自動追加

    Args:
        tmp_path: 一時ディレクトリのPath
        structure: モジュール構造を定義した辞書
                  キー: ファイル名（相対パス）
                  値: ファイルの内容
                  例: {'__init__.py': '', 'module_a.py': 'x=1', 'sub/mod.py': 'y=2'}
        package_name: パッケージ名。Noneの場合はtmp_path直下にファイルを作成（パッケージなし）

    Returns:
        パッケージディレクトリのPath（package_nameがNoneの場合はtmp_path）

    Example:
        >>> # パッケージとして作成
        >>> pkg_dir = create_test_modules(
        ...     tmp_path,
        ...     {
        ...         '__init__.py': '',
        ...         'module_a.py': 'x = 1',
        ...         'sub/__init__.py': '',
        ...         'sub/module_b.py': 'y = 2',
        ...     },
        ...     package_name='my_package',
        ... )
        >>> import my_package.module_a
        >>>
        >>> # パッケージなし（tmp_path直下にファイル作成）
        >>> modules_dir = create_test_modules(
        ...     tmp_path,
        ...     {
        ...         'a.py': 'x = 1',
        ...         'b.py': 'y = 2',
        ...     },
        ... )
        >>> import a  # 直接インポート可能
    """
    # モジュール配置ディレクトリを決定
    if package_name is None:
        # パッケージなし: tmp_path直下に作成
        modules_dir = tmp_path
    else:
        # パッケージあり: tmp_path/package_name/に作成
        modules_dir = tmp_path / package_name
        modules_dir.mkdir(parents=True, exist_ok=True)

    # 構造に従ってファイルを作成
    for file_path_str, content in structure.items():
        file_path = modules_dir / file_path_str

        # 親ディレクトリを作成（サブパッケージ対応）
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # ファイルを作成
        file_path.write_text(content, encoding='utf-8')

    # __init__.pyが明示的に指定されていない場合、空の__init__.pyを作成
    # ただし、package_nameがNoneの場合（パッケージなし）は作成しない
    if package_name is not None:
        init_file = modules_dir / '__init__.py'
        if '__init__.py' not in structure and not init_file.exists():
            init_file.write_text('', encoding='utf-8')

    # sys.pathに一時ディレクトリを自動追加
    add_temp_path_to_sys(tmp_path)

    return modules_dir


def update_module(modules_dir: Path, filename: str, content: str) -> None:
    """
    ディレクトリ内のモジュールファイルを更新

    Args:
        modules_dir: create_test_modules()の戻り値（モジュール群のディレクトリPath）
        filename: 更新するファイル名（相対パス）
        content: 新しいファイル内容（自動的にdedentされる）

    Example:
        >>> # パッケージの場合
        >>> pkg_dir = create_test_modules(
        ...     tmp_path,
        ...     {'utils.py': 'x = 1'},
        ...     package_name='mypackage',
        ... )
        >>> update_module(pkg_dir, 'utils.py', '''
        ...     x = 999
        ...     def new_func():
        ...         return x
        ... ''')
        >>>
        >>> # パッケージなしの場合
        >>> modules_dir = create_test_modules(
        ...     tmp_path,
        ...     {'utils.py': 'x = 1'},
        ... )
        >>> update_module(modules_dir, 'utils.py', 'x = 999')
    """
    import textwrap

    file_path = modules_dir / filename
    file_path.write_text(textwrap.dedent(content), encoding='utf-8')


# ============================================================
# スクリプト実行サポート
# スクリプト実行時のみ使用（pytestは使わない）
# ============================================================


def setup_package_parent_path(test_file_path: str) -> None:
    """パッケージの親ディレクトリをsys.pathに追加してパッケージのインポートをサポート"""
    global _package_parent_path
    base_path = Path(test_file_path)
    package_parent_dir = base_path.parent.parent.parent
    package_parent_dir_str = str(package_parent_dir)

    if package_parent_dir_str not in sys.path:
        sys.path.insert(0, package_parent_dir_str)
        _package_parent_path = package_parent_dir_str


def run_test_as_script(test_function: Callable[[Path], None], test_file_path: str) -> None:
    """
    スクリプト実行時の共通ロジック

    pytestが自動的に提供する機能をスクリプト実行時に自動で代替実装：
    - パッケージパスの設定（pytestのカレントディレクトリベース実行）
    - 一時ディレクトリの作成（pytestのtmp_pathフィクスチャ）
    - テスト前後のモジュールクリーンアップ（pytestの分離機能）
    - 例外処理とテスト結果の表示（pytestのレポート機能）

    これにより、pytestとスクリプト実行の両方で同じテストロジックが動作する
    テストアーキテクチャを実現する。

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
        ...     modules = create_test_modules(tmp_path, None, {'test.py': 'x = 1'})
        ...     # テストコード（pytestと同じ形式）
        >>>
        >>> if __name__ == "__main__":
        ...     # pytestの機能を自動で代替してスクリプト実行
        ...     run_test_as_script(test_my_function, __file__)
    """
    # パス設定
    setup_package_parent_path(test_file_path)

    try:
        # 一時ディレクトリでテスト実行
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            # テスト実行
            test_function(tmp_path)
            print('OK: テスト成功！')

    except (AssertionError, ImportError, ModuleNotFoundError, AttributeError) as e:
        print(f'NG: テスト失敗: {e}')
        raise
    except OSError as e:
        print(f'NG: ファイルシステムエラー: {e}')
        raise
    except Exception as e:
        print(f'NG: 予期しないエラー: {e}')
        raise
    finally:
        # テスト後のクリーンアップ
        clear_test_environment()
