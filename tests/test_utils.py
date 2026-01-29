import importlib
import sys
import tempfile
from pathlib import Path
from typing import Dict, Optional, Set

# ============================================================
# テスト環境クリーンアップ（インフラ層）
# ============================================================


def cleanup_temp_modules() -> None:
    """
    一時ディレクトリ配下のモジュールとパスをクリーンアップ

    Note:
        pytestの一時ディレクトリ配下のすべてのモジュールを削除します。
        これにより、異なるテストが同じパッケージ名を使っても干渉しません。
    """
    # pytestの一時ディレクトリのベースパスを取得
    temp_base = Path(tempfile.gettempdir())

    # 一時ディレクトリ配下のモジュールを削除
    modules_to_remove = []
    for module_name, module in list(sys.modules.items()):
        if not hasattr(module, '__file__') or not module.__file__:
            continue

        module_path = Path(module.__file__)

        # 一時ディレクトリ配下にあるかチェック
        try:
            if temp_base in module_path.parents:
                modules_to_remove.append(module_name)
        except (ValueError, OSError):
            # パス比較で問題が発生した場合はスキップ
            continue

    for module_name in modules_to_remove:
        sys.modules.pop(module_name, None)

    # 一時ディレクトリのパスをsys.pathから削除
    paths_to_remove = []
    for path in sys.path:
        try:
            path_obj = Path(path)
            if temp_base in path_obj.parents or path_obj.parent == temp_base:
                paths_to_remove.append(path)
        except (ValueError, OSError):
            # パス比較で問題が発生した場合はスキップ
            continue

    for path in paths_to_remove:
        if path in sys.path:
            sys.path.remove(path)

    importlib.invalidate_caches()


# ============================================================
# テストヘルパー関数
# ============================================================


def add_temp_path_to_sys(tmp_path: Path) -> None:
    """
    一時ディレクトリをsys.pathに追加

    Args:
        tmp_path: 一時ディレクトリのPath

    Note:
        重複チェック付きでsys.pathに追加します。
        クリーンアップはpytest fixtureが自動的に行います。
    """
    tmp_path_str = str(tmp_path)
    if tmp_path_str not in sys.path:
        sys.path.insert(0, tmp_path_str)


def create_test_modules(
    tmp_path: Path,
    structure: Dict[str, str],
    package_name: Optional[str] = None,
    create_init: bool = True,
) -> Path:
    """
    辞書で定義されたテストモジュール構造を一括作成し、sys.pathに自動追加

    Args:
        tmp_path: 一時ディレクトリのPath
        structure: モジュール構造を定義した辞書
                  キー: ファイル名（相対パス）
                  値: ファイルの内容
                  例: {'__init__.py': '', 'module_a.py': 'x=1', 'sub/mod.py': 'y=2'}
        package_name: パッケージ名。Noneの場合はtmp_path直下にファイルを作成（パッケージなし）
        create_init: __init__.pyを自動作成するか（デフォルトTrue）。Falseの場合はnamespace package

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
    # ただし、package_nameがNoneの場合（パッケージなし）またはcreate_init=Falseの場合は作成しない
    if create_init and package_name is not None:
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
