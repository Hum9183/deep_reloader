import importlib
import logging
import shutil
import sys
from pathlib import Path
from types import ModuleType

from .module_node import ModuleNode
from .symbol_extractor import SymbolExtractor

logger = logging.getLogger(__name__)


def deep_reload(module: ModuleType) -> None:
    """モジュールを再帰的にリロードする。

    Maya開発でのモジュール変更を即座に反映させるために設計されています。

    リロード後、引数で渡されたモジュールオブジェクトの内容が自動的に更新されるため、
    戻り値を受け取る必要はありません。

    Args:
        module: リロード対象のモジュール

    Note:
        ログレベルの設定には setup_logging() 関数を使用してください。
        例: setup_logging(logging.DEBUG)

    Example:
        ```python
        from mypackage import main
        from deep_reloader import deep_reload

        deep_reload(main)  # mainの中身が自動的に更新される
        main.restart()     # 新しいコードが実行される
        ```
    """
    # キャッシュを無効化して .py の変更を認識させる
    importlib.invalidate_caches()

    # ターゲットパッケージ名を自動推定
    module_name = module.__name__
    if '.' in module_name:
        target_package = module_name.split('.')[0]
    else:
        target_package = module_name

    # TODO: パフォーマンス最適化 - ファイル変更検出による差分リロード
    # - ファイルのタイムスタンプキャッシュで変更検出
    # - 変更されたモジュールのみのリロード（現在は全モジュール対象）
    # - AST解析結果のキャッシュ（頻繁にアクセスされるモジュール用）
    # - 依存関係ツリーのキャッシュ（構造変更時のみ再構築）

    # ツリー構築（まずツリーを構築して全モジュールを把握）
    # TODO: ツリー構造のデバッグ出力機能を追加
    # - 依存関係ツリーの視覚的表示（階層構造、インデント付き）
    # - 各モジュールの詳細情報（パス、サイズ、最終更新時刻）
    # - スキップされるモジュールの理由と一覧
    visited = set()  # 循環インポート検出用
    root = _build_tree(module, visited, target_package)

    # ツリー全体の __pycache__ を削除
    _clear_pycache_recursive(root)

    # リロード
    root.reload()


def _build_tree(module: ModuleType, visited: set, target_package: str) -> ModuleNode:
    """
    AST 解析して ModuleNode ツリーを構築

    Args:
        module: 解析対象のモジュール
        visited: 循環インポート検出用の訪問済みモジュールセット
        target_package: リロード対象のパッケージ名（例: 'routinerecipe'）
                       このパッケージに属するモジュールのみをリロード対象とする

    Note:
        target_packageに一致しないモジュール（組み込みモジュールやサードパーティライブラリ、その他の自作パッケージ）は
        スキップされ、リロード対象から除外されます。
    """
    node = ModuleNode(module)

    # 循環インポート検出: すでに訪問済みなら子の展開はスキップ（無限ループ防止）
    # ノード自体は作成して返す（将来のデバッグ出力で循環参照を可視化するため）
    if module.__name__ in visited:
        return node

    visited.add(module.__name__)

    extractor = SymbolExtractor(module)
    for child_module, symbols in extractor.extract():
        # ターゲットパッケージに属するモジュールのみをツリーに追加
        if not child_module.__name__.startswith(target_package):
            logger.debug(f'Skipped module (not in target package): {child_module.__name__}')
            continue

        child_node = _build_tree(child_module, visited, target_package)
        child_node.symbols = symbols
        node.children.append(child_node)

    return node


def _clear_pycache_recursive(node: ModuleNode) -> None:
    """
    ModuleNode ツリー全体を再帰的にたどって __pycache__ を削除
    """
    _clear_single_pycache(node.module)
    for child in node.children:
        _clear_pycache_recursive(child)


def _clear_single_pycache(module: ModuleType) -> None:
    """
    1つのモジュールに対応する __pycache__ を削除
    """
    module_file = getattr(module, '__file__', None)
    if module_file is None:
        return

    module_dir = Path(module_file).parent
    pycache_dir = module_dir / '__pycache__'

    if pycache_dir.exists():
        try:
            shutil.rmtree(pycache_dir)
            logger.debug(f'Cleared pycache {pycache_dir}')
        except Exception as e:
            logger.warning(f'Failed to clear pycache {pycache_dir}: {e!r}')
