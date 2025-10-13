
import importlib
import logging
import shutil
import sys
from pathlib import Path
from types import ModuleType

from .module_info import ModuleInfo
from .symbol_extractor import SymbolExtractor

logger = logging.getLogger(__name__)


class DeepReloader:
    """再帰的なモジュールリロードを行うクラス。

    Maya開発でのモジュール変更を即座に反映させるために設計されています。
    """

    def __init__(self) -> None:
        """DeepReloader を初期化する。

        Note:
            ログレベルの設定には configure_logging() 関数を使用してください。
            例: configure_logging(logging.DEBUG)
        """
        pass

    def reload(self, module: ModuleType) -> None:
        # キャッシュを無効化して .py の変更を認識させる
        importlib.invalidate_caches()

        # ツリー構築（まずツリーを構築して全モジュールを把握）
        root = self._build_tree(module)

        # ツリー全体の __pycache__ を削除
        self._clear_pycache_recursive(root)

        # 親→子へリロード
        root.reload()

        # 子→親へシンボルをコピー（from-import で取得したシンボルを親モジュールに反映）
        root.overwrite_symbols()

    def _build_tree(self, module: ModuleType) -> ModuleInfo:
        """
        AST 解析して ModuleInfo ツリーを構築
        """

        # 念のため sys.modules から最新の正規モジュールを取得する
        module = sys.modules[module.__name__]

        node = ModuleInfo(module)

        extractor = SymbolExtractor(module)
        for child_module, symbols in extractor.extract():
            child_node = self._build_tree(child_module)
            child_node.symbols = symbols
            node.children.append(child_node)

        return node

    def _clear_pycache_recursive(self, node: ModuleInfo) -> None:
        """
        ModuleInfo ツリー全体を再帰的にたどって __pycache__ を削除
        """
        self._clear_single_pycache(node.module)
        for child in node.children:
            self._clear_pycache_recursive(child)

    def _clear_single_pycache(self, module: ModuleType) -> None:
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
