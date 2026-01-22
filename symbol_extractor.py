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
        for node in ast.walk(self.tree):
            if isinstance(node, ast.ImportFrom):
                # 1つのimport文から複数の依存関係が生まれる可能性があるためextendを使用
                # 例: from . import module1, module2, func → 最大3つのタプルが返る
                results.extend(self._extract_from_node(node))
        return results

    def _extract_from_node(self, node: ast.ImportFrom) -> List[Tuple[ModuleType, ImportedSymbols]]:
        """ImportFromノードから依存関係を抽出する

        戻り値がリストである理由:
        1つのimport文から複数の依存関係が生まれる場合がある
        例: from . import module1, module2, func
            → [(module1, ImportedSymbols(['module1'])),
               (module2, ImportedSymbols(['module2'])),
               (parent_package, ImportedSymbols(['func']))]
        """
        if node.level > 0 and node.module is None:
            # from . import yyy のパターン
            return self._extract_dot_only(node)
        else:
            # 上記以外(from xxx import yyy 系)のパターン
            return self._extract_module_specified(node)

    def _extract_dot_only(self, node: ast.ImportFrom) -> List[Tuple[ModuleType, ImportedSymbols]]:
        """from . import yyy 形式のインポートから依存関係を抽出する

        モジュールインポートとシンボルインポートを自動判別して処理する
        """
        parent_module = self._import_parent_package(node.level)
        if parent_module is None or parent_module is self.module:
            return []

        # 各インポート名をモジュールまたはシンボルとして分類
        module_imports = []
        symbol_names = []

        for alias in node.names:
            child_module = self._import_relative_module(node.level, alias.name)
            if child_module is not None and child_module is not self.module:
                module_imports.append((child_module, alias.name))
            else:
                symbol_names.append(alias.name)

        # 結果をまとめる
        results = []
        for child_module, module_name in module_imports:
            results.append((child_module, ImportedSymbols([module_name])))

        if symbol_names:
            results.append((parent_module, ImportedSymbols(symbol_names)))

        return results

    def _extract_module_specified(self, node: ast.ImportFrom) -> List[Tuple[ModuleType, ImportedSymbols]]:
        """from xxx import yyy 形式のインポートから依存関係を抽出する (モジュール名指定あり)"""
        child_module = self._import_module(node)
        # モジュール解決失敗 or 自己参照の場合は依存関係なし
        if child_module is None or child_module is self.module:
            return []

        symbols = self._extract_symbols(child_module, node)
        return [(child_module, symbols)]

    def _import_module(self, stmt: ast.ImportFrom) -> Optional[ModuleType]:
        """from xxx import yyy 形式のインポートからモジュールを取得"""
        try:
            if stmt.level > 0:
                # 相対インポート(from .xxx import yyy)の場合
                return self._import_relative_module(stmt.level, stmt.module)
            else:
                # 絶対インポート(from xxx import yyy)の場合
                return importlib.import_module(stmt.module)
        except (ModuleNotFoundError, ImportError):
            return None

    def _import_relative_module(self, level: int, module_name: str) -> Optional[ModuleType]:
        """相対パスからモジュールをインポートする

        Args:
            level: 相対インポートのレベル (1 = ".", 2 = "..", ...)
            module_name: インポートするモジュール名

        Returns:
            インポートされたモジュール、失敗時はNone

        例:
            self.moduleがmypackage.sub.mainの場合
            - from . import utils
              → level=1, module_name='utils' → mypackage.sub.utils
            - from .utils import func
              → level=1, module_name='utils' → mypackage.sub.utils

            self.moduleがmypackage.sub（パッケージの__init__.py）の場合
            - from .utils import func
              → level=1, module_name='utils' → mypackage.sub.utils
        """
        try:
            # パッケージ(__path__を持つ)の場合、level - 1 を使用
            # なぜなら、パッケージ自身が既に1レベル下にいるため
            if hasattr(self.module, '__path__'):
                actual_level = level - 1
            else:
                actual_level = level

            if actual_level <= 0:
                # パッケージからのlevel=1の相対インポートの場合、同じパッケージ内
                base_name = self.module.__name__
            else:
                base_name = self.module.__name__.rsplit('.', actual_level)[0]

            target_name = f'{base_name}.{module_name}'
            return importlib.import_module(target_name)
        except (ModuleNotFoundError, ImportError):
            return None

    def _import_parent_package(self, level: int) -> Optional[ModuleType]:
        """相対インポートの親パッケージをインポートする

        Args:
            level: 相対インポートのレベル (1 = ".", 2 = "..", ...)

        Returns:
            インポートされた親パッケージ、失敗時はNone

        例:
            self.moduleがmypackage.sub.mainの場合
            - from . import func
              → level=1 → mypackage.sub
            - from .. import func
              → level=2 → mypackage

            self.moduleがmypackage.sub（パッケージの__init__.py）の場合
            - from . import func
              → level=1 → mypackage.sub（自分自身）
            - from .. import func
              → level=2 → mypackage
        """
        try:
            # パッケージ(__path__を持つ)の場合、level - 1 を使用
            if hasattr(self.module, '__path__'):
                actual_level = level - 1
            else:
                actual_level = level

            if actual_level <= 0:
                # パッケージからのlevel=1の相対インポートの場合、自分自身を返す
                return self.module
            else:
                base_name = self.module.__name__.rsplit('.', actual_level)[0]
                return importlib.import_module(base_name)
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

    def _parse_ast(self) -> Optional[ast.AST]:
        """モジュールをASTにパース"""
        try:
            source = inspect.getsource(self.module)
            return ast.parse(source)
        except (OSError, TypeError, SyntaxError):
            # 組み込みモジュール(os, sys等)、バイナリ拡張(.pyd/.so)、
            # Maya内部モジュール(maya.cmds等)はソースコードが取得できないためNoneを返す
            return None
