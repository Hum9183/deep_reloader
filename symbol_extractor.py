import ast
import inspect
import logging
from types import ModuleType
from typing import List, Optional, Tuple

from .from_clause import FromClause
from .import_clause import ImportClause

logger = logging.getLogger(__name__)


class SymbolExtractor:
    """
    モジュールのASTを解析して、from-import文の「子モジュール」と「インポートされるシンボル」を抽出するクラス

    子モジュールと、インポートされるシンボル名のペアを(ModuleType, ImportClause)で表現する。

    例: from math import sin, cos → (math (ModuleType), ['sin', 'cos'] (ImportClause))
        この場合、mathが子モジュール、sin・cosがインポートされるシンボル
    """

    def __init__(self, module: ModuleType) -> None:
        self.module: ModuleType = module
        self.tree: Optional[ast.AST] = self._parse_ast()

    def extract(self) -> List[Tuple[ModuleType, Optional[ImportClause]]]:
        """(子モジュール, インポートされたシンボル) のリストを返す"""
        if self.tree is None:
            return []

        results: List[Tuple[ModuleType, Optional[ImportClause]]] = []
        for node in ast.walk(self.tree):
            if isinstance(node, ast.ImportFrom):
                # 1つのimport文から複数の依存関係が生まれる可能性があるためextendを使用
                # 例: from . import module1, module2, func → 最大3つのタプルが返る
                results.extend(self._extract_from_node(node))
        return results

    def _should_skip(self, from_clause: Optional[FromClause]) -> bool:
        """from句をスキップすべきかを判定

        Args:
            from_clause: from句

        Returns:
            スキップすべきならTrue、処理すべきならFalse

        スキップするケース:
            - from_clauseがNone (インポート失敗)
            - from_clauseのモジュールがself.module (自分自身をインポート、循環参照)
        """
        return from_clause is None or from_clause.module is self.module

    def _extract_from_node(self, node: ast.ImportFrom) -> List[Tuple[ModuleType, Optional[ImportClause]]]:
        """ImportFromノードから依存関係を抽出する

        戻り値がリストである理由:
        1つのimport文から複数の依存関係が生まれる場合がある
        例: from . import module1, module2, func
            → [(module1, ImportClause(['module1'])),
               (module2, ImportClause(['module2'])),
               (parent_package, ImportClause(['func']))]
        """
        # from句を取得
        from_clause = FromClause.resolve(self.module, node.level, node.module)
        if self._should_skip(from_clause):
            return []

        # ワイルドカードの場合はシンボルを展開、通常はAST→文字列変換
        if node.names[0].name == '*':
            import_clause = ImportClause.expand_wildcard(from_clause)
        else:
            import_clause = ImportClause([alias.name for alias in node.names])

        return import_clause.to_dependencies(from_clause, node.level, node.module)

    def _parse_ast(self) -> Optional[ast.AST]:
        """モジュールをASTにパース"""
        try:
            source = inspect.getsource(self.module)
            return ast.parse(source)
        except (OSError, TypeError, SyntaxError):
            # 組み込みモジュール(os, sys等)、バイナリ拡張(.pyd/.so)、
            # Maya内部モジュール(maya.cmds等)はソースコードが取得できないためNoneを返す
            return None
