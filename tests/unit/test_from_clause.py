"""from句解決関数のテスト"""

from types import ModuleType
from unittest.mock import Mock, patch

from ... import from_clause


def test_resolve_absolute_import():
    """絶対インポート(from math import sin)の解決テスト"""
    mock_base = Mock(spec=ModuleType)

    with patch('importlib.import_module') as mock_import:
        mock_math = Mock(spec=ModuleType)
        mock_import.return_value = mock_math

        result = from_clause.resolve(mock_base, level=0, module_name='math')

        assert result is mock_math
        mock_import.assert_called_once_with('math')


def test_resolve_relative_from_package():
    """パッケージからの相対インポート(from .utils import func)"""
    mock_base = Mock(spec=ModuleType)
    mock_base.__name__ = 'mypackage.subpkg'
    mock_base.__path__ = ['/path/to/mypackage/subpkg']  # パッケージ

    with patch('importlib.import_module') as mock_import:
        mock_utils = Mock(spec=ModuleType)
        mock_import.return_value = mock_utils

        result = from_clause.resolve(mock_base, level=1, module_name='utils')

        assert result is mock_utils
        # パッケージの場合、level-1=0なので同じレベル
        mock_import.assert_called_once_with('mypackage.subpkg.utils')


def test_resolve_relative_from_module():
    """モジュールからの相対インポート(from .utils import func)"""
    mock_base = Mock(spec=ModuleType)
    mock_base.__name__ = 'mypackage.subpkg.module'
    # __path__なし = モジュール

    with patch('importlib.import_module') as mock_import:
        mock_utils = Mock(spec=ModuleType)
        mock_import.return_value = mock_utils

        result = from_clause.resolve(mock_base, level=1, module_name='utils')

        assert result is mock_utils
        # モジュールの場合、levelをそのまま使用
        mock_import.assert_called_once_with('mypackage.subpkg.utils')


def test_resolve_relative_dot_only():
    """from . import yyy パターンのテスト"""
    mock_base = Mock(spec=ModuleType)
    mock_base.__name__ = 'mypackage.subpkg.module'

    with patch('importlib.import_module') as mock_import:
        mock_parent = Mock(spec=ModuleType)
        mock_import.return_value = mock_parent

        result = from_clause.resolve(mock_base, level=1, module_name=None)

        assert result is mock_parent
        mock_import.assert_called_once_with('mypackage.subpkg')


def test_resolve_returns_none_on_import_error():
    """インポート失敗時にNoneを返すことを確認"""
    mock_base = Mock(spec=ModuleType)
    mock_base.__name__ = 'test_module'

    with patch('importlib.import_module') as mock_import:
        mock_import.side_effect = ModuleNotFoundError('nonexistent')

        result = from_clause.resolve(mock_base, level=0, module_name='nonexistent')

        assert result is None


def test_try_import_as_module_success():
    """モジュールとして正しくインポートできることを確認"""
    mock_from_module = Mock(spec=ModuleType)
    mock_from_module.__name__ = 'parent'
    mock_base_module = Mock(spec=ModuleType)

    with patch('importlib.import_module') as mock_import:
        mock_submodule = Mock(spec=ModuleType)
        mock_import.return_value = mock_submodule

        is_module, module = from_clause.try_import_as_module(mock_from_module, mock_base_module, 'os')

        assert is_module is True
        assert module is mock_submodule
        mock_import.assert_called_once_with('parent.os')


def test_try_import_as_module_failure():
    """アトリビュートの場合、Falseを返すことを確認"""
    mock_from_module = Mock(spec=ModuleType)
    mock_from_module.__name__ = 'parent'
    mock_base_module = Mock(spec=ModuleType)

    with patch('importlib.import_module') as mock_import:
        mock_import.side_effect = ModuleNotFoundError()

        is_module, module = from_clause.try_import_as_module(mock_from_module, mock_base_module, 'func')

        assert is_module is False
        assert module is None


def test_try_import_as_module_returns_base_module():
    """自分自身のモジュールを返した場合はFalseを返すことを確認"""
    mock_from_module = Mock(spec=ModuleType)
    mock_from_module.__name__ = 'parent'
    mock_base_module = Mock(spec=ModuleType)

    with patch('importlib.import_module') as mock_import:
        # 自分自身のモジュールを返す
        mock_import.return_value = mock_base_module

        is_module, module = from_clause.try_import_as_module(mock_from_module, mock_base_module, 'name')

        assert is_module is False
        assert module is None
