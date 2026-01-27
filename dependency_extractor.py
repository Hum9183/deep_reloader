import ast
import inspect
import logging
from types import ModuleType
from typing import List, Optional

from . import from_clause, import_clause
from .domain import Dependency

logger = logging.getLogger(__name__)


class DependencyExtractor:
    """
    モジュールのASTを解析して、依存関係を抽出するクラス

    from-import文を解析し、Dependency オブジェクトを抽出します。

    例: from math import sin, cos → Dependency(math, ['sin', 'cos'])
        from .utils import helper → Dependency(package.utils.helper, None)
    """

    def __init__(self, module: ModuleType) -> None:
        self._module: ModuleType = module
        self._ast_tree: Optional[ast.AST] = self._parse_ast()

    def extract(self) -> List[Dependency]:
        """依存関係のリストを返す

        Returns:
            Dependency オブジェクトのリスト
            symbols=None ならモジュール依存、symbols=[...] ならアトリビュート依存
        """
        if self._ast_tree is None:
            return []

        dependencies: List[Dependency] = []
        for node in ast.walk(self._ast_tree):
            if isinstance(node, ast.ImportFrom):
                # 1つのimport文から複数の依存関係が生まれる可能性があるためextendを使用
                # 例: from . import module1, module2, func → 最大3つの依存関係が返る
                dependencies.extend(self._extract_from_node(node))
        return dependencies

    def _extract_from_node(self, node: ast.ImportFrom) -> List[Dependency]:
        """ImportFromノードから依存関係を抽出する

        戻り値がリストである理由:
        1つのimport文から複数の依存関係が生まれる場合がある
        例: from . import module1, module2, func
            → [Dependency(module1, None),
               Dependency(parent_package, ['module1']),
               Dependency(module2, None),
               Dependency(parent_package, ['module2']),
               Dependency(parent_package, ['func'])]
        """
        # from句を解決
        from_module = from_clause.resolve(self._module, node.level, node.module)
        if from_module is None:
            return []

        # import句のシンボルを解決（ワイルドカード展開含む）
        names = [alias.name for alias in node.names]
        symbols = import_clause.resolve(from_module, names)

        # 依存関係を生成
        dependencies = import_clause.create_dependencies(from_module, self._module, symbols)

        # 自分自身への依存のみをフィルタリング
        # 例: from . import helper の場合、Dependency(testpkg.helper, None) は残し、
        #     Dependency(testpkg, ['helper']) は除外
        return [dep for dep in dependencies if dep.module is not self._module]

    def _parse_ast(self) -> Optional[ast.AST]:
        """モジュールをASTにパース"""
        try:
            source = inspect.getsource(self._module)
            return ast.parse(source)
        except (OSError, TypeError, SyntaxError):
            # 組み込みモジュール(os, sys等)、バイナリ拡張(.pyd/.so)、
            # Maya内部モジュール(maya.cmds等)はソースコードが取得できないためNoneを返す
            return None
