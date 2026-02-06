"""import句解決関数のテスト"""

from types import ModuleType
from unittest.mock import Mock

from ... import import_clause


def test_resolve_import_symbols_basic():
    """基本的なシンボル解決のテスト"""
    mock_module = Mock(spec=ModuleType)
    symbols = ['func', 'Class']

    result = import_clause.expand_if_wildcard(mock_module, symbols)

    assert result == ['func', 'Class']


def test_resolve_import_symbols_wildcard_with_all():
    """__all__属性を持つモジュールからのワイルドカード展開"""
    mock_module = Mock(spec=ModuleType)
    mock_module.__all__ = ['public1', 'public2']

    result = import_clause.expand_if_wildcard(mock_module, ['*'])

    assert result == ['public1', 'public2']


def test_resolve_import_symbols_wildcard_without_all():
    """__all__属性がない場合のワイルドカード展開（__で始まる名前を除外）"""
    mock_module = Mock(spec=ModuleType)
    mock_module.__dict__ = {
        'public1': 'value1',
        'public2': 'value2',
        '_private': 'private',
        '__internal': 'internal',
    }

    result = import_clause.expand_if_wildcard(mock_module, ['*'])

    assert set(result) == {'public1', 'public2', '_private'}
    assert '__internal' not in result
