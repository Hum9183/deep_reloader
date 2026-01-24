"""SymbolExtractorクラスの単体テスト"""

import ast
from types import ModuleType
from unittest.mock import Mock, patch

from ...from_clause import FromClause
from ...import_clause import ImportClause
from ...symbol_extractor import SymbolExtractor


def test_init_with_parseable_module():
    """パース可能なモジュールで初期化できることを確認"""
    # 簡単なモジュールソースを持つモック
    mock_module = Mock(spec=ModuleType)

    with patch('inspect.getsource', return_value='x = 1'):
        extractor = SymbolExtractor(mock_module)

        assert extractor.module is mock_module
        assert extractor.tree is not None
        assert isinstance(extractor.tree, ast.Module)


def test_init_with_unparseable_module():
    """パース不可能なモジュール（組み込みモジュール等）の初期化テスト"""
    mock_module = Mock(spec=ModuleType)

    with patch('inspect.getsource', side_effect=OSError):
        extractor = SymbolExtractor(mock_module)

        assert extractor.module is mock_module
        assert extractor.tree is None


def test_extract_returns_empty_when_tree_is_none():
    """ASTがNoneの場合、空リストを返すことを確認"""
    mock_module = Mock(spec=ModuleType)

    with patch('inspect.getsource', side_effect=OSError):
        extractor = SymbolExtractor(mock_module)
        result = extractor.extract()

        assert result == []


def test_extract_simple_from_import():
    """シンプルなfrom-importの抽出テスト"""
    mock_module = Mock(spec=ModuleType)
    mock_module.__name__ = 'test_module'

    source = 'from math import sin, cos'

    with patch('inspect.getsource', return_value=source):
        extractor = SymbolExtractor(mock_module)

        # FromClause.resolveとImportClause.to_dependenciesをモック
        with patch.object(FromClause, 'resolve') as mock_resolve, patch.object(
            ImportClause, 'to_dependencies'
        ) as mock_to_deps:

            mock_from_clause = Mock(spec=FromClause)
            mock_from_clause.module = Mock(spec=ModuleType)
            mock_resolve.return_value = mock_from_clause

            mock_deps = [(Mock(spec=ModuleType), Mock(spec=ImportClause))]
            mock_to_deps.return_value = mock_deps

            result = extractor.extract()

            assert len(result) == 1
            mock_resolve.assert_called_once()
            mock_to_deps.assert_called_once()


def test_extract_wildcard_import():
    """ワイルドカードインポートの抽出テスト"""
    mock_module = Mock(spec=ModuleType)
    mock_module.__name__ = 'test_module'

    source = 'from math import *'

    with patch('inspect.getsource', return_value=source):
        extractor = SymbolExtractor(mock_module)

        # patch.objectの代わりにパッチパスを使用
        with patch('deep_reloader.symbol_extractor.FromClause') as mock_from_clause_class, patch(
            'deep_reloader.symbol_extractor.ImportClause'
        ) as mock_import_clause_class:

            mock_from_clause = Mock(spec=FromClause)
            mock_from_clause.module = Mock(spec=ModuleType)
            mock_from_clause_class.resolve.return_value = mock_from_clause

            mock_import_clause = Mock(spec=ImportClause)
            mock_import_clause_class.expand_wildcard.return_value = mock_import_clause

            mock_deps = [(Mock(spec=ModuleType), mock_import_clause)]
            mock_import_clause.to_dependencies.return_value = mock_deps

            result = extractor.extract()

            mock_import_clause_class.expand_wildcard.assert_called_once_with(mock_from_clause)
            assert len(result) == 1


def test_should_skip_when_from_clause_is_none():
    """from_clauseがNoneの場合、スキップすべきと判定されることを確認"""
    mock_module = Mock(spec=ModuleType)
    extractor = SymbolExtractor.__new__(SymbolExtractor)
    extractor.module = mock_module

    assert extractor._should_skip(None) is True


def test_should_skip_when_importing_self():
    """自分自身をインポートする場合、スキップすべきと判定されることを確認"""
    mock_module = Mock(spec=ModuleType)
    extractor = SymbolExtractor.__new__(SymbolExtractor)
    extractor.module = mock_module

    mock_from_clause = Mock(spec=FromClause)
    mock_from_clause.module = mock_module  # 自分自身

    assert extractor._should_skip(mock_from_clause) is True


def test_should_not_skip_normal_import():
    """通常のインポートはスキップすべきでないと判定されることを確認"""
    mock_module = Mock(spec=ModuleType)
    mock_other_module = Mock(spec=ModuleType)
    extractor = SymbolExtractor.__new__(SymbolExtractor)
    extractor.module = mock_module

    mock_from_clause = Mock(spec=FromClause)
    mock_from_clause.module = mock_other_module

    assert extractor._should_skip(mock_from_clause) is False


def test_extract_from_node_skips_failed_resolve():
    """FromClause.resolveが失敗した場合、空リストを返すことを確認"""
    mock_module = Mock(spec=ModuleType)
    extractor = SymbolExtractor.__new__(SymbolExtractor)
    extractor.module = mock_module

    # ImportFromノードを作成
    node = ast.ImportFrom(module='nonexistent', names=[ast.alias(name='func', asname=None)], level=0)

    with patch.object(FromClause, 'resolve', return_value=None):
        result = extractor._extract_from_node(node)

        assert result == []


def test_extract_from_node_skips_self_import():
    """自分自身をインポートする場合、空リストを返すことを確認"""
    mock_module = Mock(spec=ModuleType)
    extractor = SymbolExtractor.__new__(SymbolExtractor)
    extractor.module = mock_module

    node = ast.ImportFrom(module='self', names=[ast.alias(name='func', asname=None)], level=0)

    mock_from_clause = Mock(spec=FromClause)
    mock_from_clause.module = mock_module  # 自分自身

    # to_dependencies() が自分自身を含む依存を返すと仮定
    mock_dependencies = [(mock_module, Mock())]  # 自分自身への依存

    with patch.object(FromClause, 'resolve', return_value=mock_from_clause):
        with patch.object(ImportClause, 'to_dependencies', return_value=mock_dependencies):
            result = extractor._extract_from_node(node)

            # 自分自身への依存はフィルタリングされる
            assert result == []


def test_extract_from_node_filters_only_self():
    """自分自身への依存のみをフィルタリングし、他の依存は残すことを確認"""
    mock_module = Mock(spec=ModuleType)
    mock_other_module = Mock(spec=ModuleType)
    extractor = SymbolExtractor.__new__(SymbolExtractor)
    extractor.module = mock_module

    node = ast.ImportFrom(module=None, names=[ast.alias(name='helper', asname=None)], level=1)

    mock_from_clause = Mock(spec=FromClause)
    mock_from_clause.module = mock_module  # from . の場合、自分自身（パッケージ）

    # to_dependencies() が複数の依存を返す場合
    # 例: from . import helper → [(helper_module, None), (self_module, ImportClause(['helper']))]
    mock_helper_module = mock_other_module
    mock_dependencies = [
        (mock_helper_module, None),  # helper モジュール
        (mock_module, Mock()),  # 自分自身（パッケージ）への依存
    ]

    with patch.object(FromClause, 'resolve', return_value=mock_from_clause):
        with patch.object(ImportClause, 'to_dependencies', return_value=mock_dependencies):
            result = extractor._extract_from_node(node)

            # 自分自身への依存のみが除外され、他の依存は残る
            assert len(result) == 1
            assert result[0] == (mock_helper_module, None)


def test_parse_ast_with_syntax_error():
    """構文エラーのあるソースの場合、Noneを返すことを確認"""
    mock_module = Mock(spec=ModuleType)

    with patch('inspect.getsource', return_value='invalid python syntax {{{'):
        extractor = SymbolExtractor(mock_module)

        assert extractor.tree is None


def test_parse_ast_with_type_error():
    """TypeErrorの場合、Noneを返すことを確認"""
    mock_module = Mock(spec=ModuleType)

    with patch('inspect.getsource', side_effect=TypeError):
        extractor = SymbolExtractor(mock_module)

        assert extractor.tree is None
