import importlib
import sys
import tempfile
from pathlib import Path
from typing import Callable, Dict, Optional

# TODO: 循環インポートエラーの対応
# 現在、循環インポート（A → B → A のような相互依存）が存在するモジュール構造では
# deep_reloaderがエラーになることが判明している。
#
# 問題:
# - 循環インポートのあるモジュールをリロードしようとするとエラーが発生
# - 依存関係の解析時に無限ループに陥る可能性
#
# 対策案:
# 1. 循環依存の検出機能を追加
# 2. 循環が検出された場合の適切なエラーハンドリング
# 3. 循環インポートを安全にリロードするアルゴリズムの実装
# 4. 循環インポートのテストケース追加
#
# 優先度: 高（実用性に大きく影響）

# TODO: import文対応の追加
# 現在はfrom-import形式（from module import something）のみ対応しており、
# import文形式（import module）の依存関係は解析されない制限がある。
#
# 問題:
# - import module 形式の依存関係が見落とされる
# - 完全な依存関係の把握ができない
# - ユーザーが混乱する可能性（一部のインポートのみ対応）
#
# 対策案:
# 1. AST解析でimport文も検出するよう拡張
# 2. import文での依存関係もModuleInfoツリーに追加
# 3. import文用のテストケース追加
# 4. ドキュメントの更新
#
# 優先度: 中（機能の完全性向上）


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
    """
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
