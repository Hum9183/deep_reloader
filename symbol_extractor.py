import ast
import importlib
import inspect
import logging
from types import ModuleType
from typing import List, Optional, Tuple

from .imported_symbols import ImportedSymbols

logger = logging.getLogger(__name__)


class SymbolExtractor:
    """
    モジュールのASTを解析して、from-import文の「子モジュール」と「インポートされるシンボル」を抽出するクラス

    子モジュールと、インポートされるシンボル名のペアを(ModuleType, ImportedSymbols)で表現する。

    例: from math import sin, cos → (math_module, ImportedSymbols(['sin', 'cos']))
        この場合、mathが子モジュール、sin・cosがインポートされるシンボル
    """

    def __init__(self, module: ModuleType) -> None:
        self.module: ModuleType = module
        self.tree: Optional[ast.AST] = self._parse_ast()

    def extract(self) -> List[Tuple[ModuleType, ImportedSymbols]]:
        """(子モジュール, インポートされたシンボル) のリストを返す"""
        if self.tree is None:
            return []

        results: List[Tuple[ModuleType, ImportedSymbols]] = []
        for node in ast.walk(self.tree):  # walkで全ノード探索（動的なfrom-import文も検出）
            if isinstance(node, ast.ImportFrom):
                child_module = self._resolve_imported_module(node)
                # 無効な依存関係を除外: 存在しないモジュール(None)と自分自身への参照
                if child_module is None or child_module is self.module:
                    continue

                symbols = self._extract_symbols(child_module, node)
                results.append((child_module, symbols))
        return results

    def _parse_ast(self) -> Optional[ast.AST]:
        """モジュールをASTにパース"""
        try:
            source = inspect.getsource(self.module)
            return ast.parse(source)
        except (OSError, TypeError, SyntaxError):
            # 組み込みモジュール(os, sys等)、バイナリ拡張(.pyd/.so)、
            # Maya内部モジュール(maya.cmds等)はソースコードが取得できないためNoneを返す
            return None

    def _resolve_imported_module(self, stmt: ast.ImportFrom) -> Optional[ModuleType]:
        """ImportFromノードからインポート対象のモジュールを取得"""
        try:
            if stmt.level > 0:
                # 相対インポートを絶対パスに変換
                # importlib.import_module()は絶対パス（絶対モジュール名）しか受け付けないため、
                # 相対インポート（from .module や from ..module）を絶対パスに変換する必要がある
                base_name = self.module.__name__.rsplit('.', stmt.level)[0]
                # stmt.moduleがある場合: from ..utils import helper → "parent.utils"
                # stmt.moduleがNoneの場合: from .. import helper → "parent" (パッケージ自体の__init__.py)
                target_name = f'{base_name}.{stmt.module}' if stmt.module else base_name
                return importlib.import_module(target_name)
            else:
                # 絶対インポートの場合は絶対パスのためそのまま使用
                return importlib.import_module(stmt.module)
        except (ModuleNotFoundError, ImportError):
            return None

    def _extract_symbols(self, child_module: ModuleType, stmt: ast.ImportFrom) -> ImportedSymbols:
        """ImportFromノードからシンボル名を抽出"""
        # AST から実際のシンボル名を抽出（エイリアス名ではなく元の名前）
        names = [alias.name for alias in stmt.names]

        if names != ['*']:
            # 通常のインポート: from module import func1, func2
            # → names = ['func1', 'func2']
            return ImportedSymbols(names)
        else:
            # ワイルドカードインポート: from module import *
            if hasattr(child_module, '__all__'):
                # __all__ がある場合: 明示的に定義された公開シンボルを使用
                return ImportedSymbols(list(child_module.__all__))
            else:
                # __all__ がない場合: 特殊属性以外の全属性を使用
                public_attrs = []
                for attr_name in child_module.__dict__:
                    if attr_name.startswith('__') is False:  # __name__, __file__ 等の特殊属性を除外
                        public_attrs.append(attr_name)
                return ImportedSymbols(public_attrs)
