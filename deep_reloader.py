import importlib
import logging
import shutil
import sys
from pathlib import Path
from types import ModuleType

from .module_info import ModuleInfo
from .symbol_extractor import SymbolExtractor

logger = logging.getLogger(__name__)


def deep_reload(module: ModuleType) -> None:
    """モジュールを再帰的にリロードする。

    Maya開発でのモジュール変更を即座に反映させるために設計されています。

    Args:
        module: リロード対象のモジュール

    Note:
        ログレベルの設定には setup_logging() 関数を使用してください。
        例: setup_logging(logging.DEBUG)
    """
    # キャッシュを無効化して .py の変更を認識させる
    importlib.invalidate_caches()

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
    root = _build_tree(module)

    # ツリー全体の __pycache__ を削除
    _clear_pycache_recursive(root)

    # 親→子へリロード
    # TODO: リロード順序とプロセスの詳細ログ追加
    # - 各モジュールのリロード開始/完了タイミング
    # - リロード中のエラーとリカバリ状況
    # - パフォーマンス情報（各段階の実行時間）
    root.reload()

    # 子→親へシンボルをコピー（from-import で取得したシンボルを親モジュールに反映）
    # TODO: シンボルコピー処理の詳細ログ追加
    # - コピーされるシンボルの詳細（名前、型、ソース）
    # - シンボルの競合や上書き状況
    # - 失敗したシンボルとその理由
    root.overwrite_symbols()


def _build_tree(module: ModuleType) -> ModuleInfo:
    """
    AST 解析して ModuleInfo ツリーを構築

    TODO: 組み込みモジュール（os、pathlib等）やサードパーティライブラリ（maya.cmds、PySide6等）の
    スキップ処理を実装する必要がある。現在は全ての依存関係をリロード対象としているため、
    不要なリロードや潜在的な危険性がある。
    """

    # 念のため sys.modules から最新の正規モジュールを取得する
    module = sys.modules[module.__name__]

    node = ModuleInfo(module)

    extractor = SymbolExtractor(module)
    for child_module, symbols in extractor.extract():
        child_node = _build_tree(child_module)
        child_node.symbols = symbols
        node.children.append(child_node)

    return node


def _clear_pycache_recursive(node: ModuleInfo) -> None:
    """
    ModuleInfo ツリー全体を再帰的にたどって __pycache__ を削除
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


# TODO: 将来の実装用メソッド - デバッグ情報の出力機能
# def _print_tree_structure(root: ModuleInfo, level: int = 0) -> None:
#     """依存関係ツリーを視覚的に表示する
#
#     出力例:
#     my_package.main
#     ├── my_package.utils (from utils import helper, calculator)
#     │   └── my_package.math_utils (from .math_utils import add, subtract)
#     ├── my_package.config (from .config import settings)
#     └── os [SKIPPED: builtin module]
#     """
#     pass
#
# def _log_reload_summary(root: ModuleInfo) -> None:
#     """リロード処理の概要を詳細ログ出力
#
#     出力内容:
#     - 処理開始/終了時刻
#     - 総モジュール数、リロード対象数、スキップ数
#     - 各段階の所要時間（ツリー構築、リロード、シンボルコピー）
#     - 検出されたエラーや警告の統計
#     """
#     pass
#
# TODO: 将来の実装用 - パフォーマンス最適化キャッシュシステム
# def _init_cache_system() -> None:
#     """キャッシュシステムの初期化
#
#     キャッシュ対象:
#     - ファイルタイムスタンプ（変更検出用）
#     - AST解析結果（重いパース処理の削減）
#     - 依存関係ツリー（構造変更時のみ再構築）
#     - モジュール判定結果（組み込み/サードパーティ判定キャッシュ）
#     """
#     pass
#
# def _should_reload_module(module: ModuleType) -> bool:
#     """モジュールがリロード必要かキャッシュベースで判定
#
#     判定基準:
#     - ファイルタイムスタンプの変更
#     - 依存関係の変更
#     - 強制リロードフラグ
#     """
#     pass
