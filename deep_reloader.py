import importlib
import logging
import shutil
import sys
from pathlib import Path
from types import ModuleType
from typing import List

from .dependency_extractor import DependencyExtractor
from .domain import DependencyNode

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
    visited_modules = set()  # 循環インポート検出用
    root = _build_tree(module, visited_modules, target_package)

    # ツリー全体の __pycache__ を削除
    _clear_pycache_recursive(root)

    # リロード
    reload_tree(root)


def _build_tree(module: ModuleType, visited_modules: set, target_package: str) -> DependencyNode:
    """
    AST 解析して DependencyNode ツリーを構築

    Args:
        module: 解析対象のモジュール
        visited_modules: 循環インポート検出用の訪問済みモジュールセット
        target_package: リロード対象のパッケージ名（例: 'routinerecipe'）
                       このパッケージに属するモジュールのみをリロード対象とする

    Note:
        target_packageに一致しないモジュール（組み込みモジュールやサードパーティライブラリ、その他の自作パッケージ）は
        スキップされ、リロード対象から除外されます。
    """
    node = DependencyNode(module)

    # 循環インポート検出: すでに訪問済みなら子の展開はスキップ（無限ループ防止）
    # ノード自体は作成して返す（将来のデバッグ出力で循環参照を可視化するため）
    if module.__name__ in visited_modules:
        return node

    visited_modules.add(module.__name__)

    extractor = DependencyExtractor(module)
    for dependency in extractor.extract():
        # ターゲットパッケージに属するモジュールのみをツリーに追加
        if not dependency.module.__name__.startswith(target_package):
            logger.debug(f'Skipped module (not in target package): {dependency.module.__name__}')
            continue

        child_node = _build_tree(dependency.module, visited_modules, target_package)
        child_node.symbols = dependency.symbols
        node.children.append(child_node)

    return node


def _clear_pycache_recursive(node: DependencyNode) -> None:
    """
    DependencyNode ツリー全体を再帰的にたどって __pycache__ を削除
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


def reload_tree(node: DependencyNode, visited_modules: set = None) -> None:
    """依存関係ツリーを再帰的にリロード

    DependencyNodeで構成された依存ツリーを深さ優先探索でリロードします。

    処理の流れ:
    1. importlib.reload()で新しいモジュールオブジェクト(reloaded_module)を作成
    2. 子モジュールを再帰的にリロード
    3. 子のインポートされた名前をreloaded_moduleにコピー（関数の__globals__が正しく参照できるように）
    4. node.module.__dict__を更新（削除された属性を除去、新しい属性を追加・上書き）
    5. sys.modules[name]にnode.moduleを登録（reloaded_moduleではなく）

    重要な設計思想:
    - node.moduleのオブジェクトIDを保持することで、既存の参照を有効に保つ
    - reloaded_moduleは一時的な作業用オブジェクトとして使用
    - __dict__を更新することで、オブジェクトを置き換えずに中身だけを更新

    Args:
        node: リロード対象のノード
        visited_modules: 訪問済みモジュールのセット（循環参照防止）
    """
    # 再帰処理で訪問済みモジュールを記録するセット
    if visited_modules is None:
        visited_modules = set()

    name = node.module.__name__
    # 既に訪問済みのモジュールはスキップ（重複処理防止・処理時間短縮）
    if name in visited_modules:
        return

    # このモジュールの処理が完了したことをマーク
    visited_modules.add(name)

    # 子を再帰的にリロード（子が先に完了する必要がある）
    for child in node.children:
        reload_tree(child, visited_modules)

    # importlib.reload()を使用してリロード
    # これにより、sys.modulesから削除せずに安全にリロードできる
    reloaded_module = importlib.reload(node.module)

    # 子のリロード後、from-importで取得した名前を新しいモジュールにコピー
    # （reloaded_moduleの関数の__globals__に正しい値を設定するため）
    for child in node.children:
        if child.symbols is not None:
            source_module = sys.modules.get(child.module.__name__, child.module)
            _copy_symbols_to(child.symbols, source_module, reloaded_module)

    # リロード前のモジュール(node.module)にあって、リロード後のモジュール(reloaded_module)に存在しなくなった属性を削除する
    old_attrs = set(node.module.__dict__.keys())
    new_attrs = set(reloaded_module.__dict__.keys())
    for key in old_attrs - new_attrs:
        if not key.startswith('__'):  # __name__, __file__等の特殊属性は保持
            del node.module.__dict__[key]

    # node.module.__dict__をreloaded_module.__dict__で更新（属性を追加・上書き）
    node.module.__dict__.update(reloaded_module.__dict__)

    # sys.modulesをnode.moduleで上書き
    sys.modules[name] = node.module

    logger.debug(f'RELOADED {name}')


def _copy_symbols_to(symbols: List[str], source_module: ModuleType, target_module: ModuleType) -> None:
    """source_moduleからtarget_moduleへsymbolsで指定された名前をコピーする

    Args:
        symbols: コピーする名前のリスト
        source_module: コピー元のモジュール
        target_module: コピー先のモジュール
    """
    for name in symbols:
        if hasattr(source_module, name):
            value = getattr(source_module, name)
            setattr(target_module, name, value)
            logger.debug(f'{target_module.__name__}.{name} ← {source_module.__name__}.{name} ({value!r})')
