"""SymbolResolverクラスの単体テスト"""

import ast
from types import ModuleType
from unittest.mock import Mock, patch

from ...dependency_extractor import DependencyExtractor


def test_parse_ast_from_source():
    """ソースコードからASTが正しくパースされることを確認"""
    mock_module = Mock(spec=ModuleType)
    source = "from math import sin, cos"

    with patch("inspect.getsource", return_value=source):
        extractor = DependencyExtractor(mock_module)

        assert extractor._ast_tree is not None
        assert isinstance(extractor._ast_tree, ast.Module)


def test_parse_ast_returns_none_for_builtin():
    """組み込みモジュールの場合、ASTがNoneになることを確認"""
    import sys

    extractor = DependencyExtractor(sys)

    assert extractor._ast_tree is None
