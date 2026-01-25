"""FromClauseクラスの単体テスト"""

from types import ModuleType, SimpleNamespace
from unittest.mock import Mock, patch

from ...from_clause import FromClause


def test_init():
    """FromClauseが正しく初期化されることを確認"""
    mock_module = Mock(spec=ModuleType)
    mock_base_module = Mock(spec=ModuleType)

    clause = FromClause(mock_module, mock_base_module)

    assert clause.module is mock_module
    assert clause._importing_module is mock_base_module


def test_resolve_absolute_import():
    """絶対インポート(from math import sin)の解決テスト"""
    mock_base = Mock(spec=ModuleType)

    with patch('importlib.import_module') as mock_import:
        mock_math = Mock(spec=ModuleType)
        mock_import.return_value = mock_math

        result = FromClause.resolve(mock_base, level=0, module_name='math')

        assert result is not None
        assert result.module is mock_math
        mock_import.assert_called_once_with('math')


def test_resolve_relative_from_package():
    """パッケージからの相対インポート(from .utils import func)"""
    mock_base = Mock(spec=ModuleType)
    mock_base.__name__ = 'mypackage.subpkg'
    mock_base.__path__ = ['/path/to/mypackage/subpkg']  # パッケージ

    with patch('importlib.import_module') as mock_import:
        mock_utils = Mock(spec=ModuleType)
        mock_import.return_value = mock_utils

        result = FromClause.resolve(mock_base, level=1, module_name='utils')

        assert result is not None
        assert result.module is mock_utils
        # パッケージの場合、level-1=0なので同じレベル
        mock_import.assert_called_once_with('mypackage.subpkg.utils')


def test_resolve_relative_from_module():
    """モジュールからの相対インポート(from .utils import func)"""
    mock_base = Mock(spec=ModuleType)
    mock_base.__name__ = 'mypackage.subpkg'
    # __path__がないのでモジュール

    with patch('importlib.import_module') as mock_import:
        mock_utils = Mock(spec=ModuleType)
        mock_import.return_value = mock_utils

        result = FromClause.resolve(mock_base, level=1, module_name='utils')

        assert result is not None
        assert result.module is mock_utils
        # モジュールの場合、level=1で親のパッケージ
        mock_import.assert_called_once_with('mypackage.utils')


def test_resolve_relative_dot_only():
    """相対インポート(from . import module)の解決テスト"""
    mock_base = Mock(spec=ModuleType)
    mock_base.__name__ = 'mypackage.subpkg.module'

    with patch('importlib.import_module') as mock_import:
        mock_parent = Mock(spec=ModuleType)
        mock_import.return_value = mock_parent

        result = FromClause.resolve(mock_base, level=1, module_name=None)

        assert result is not None
        assert result.module is mock_parent
        mock_import.assert_called_once_with('mypackage.subpkg')


def test_resolve_returns_none_on_import_error():
    """インポート失敗時にNoneを返すことを確認"""
    mock_base = Mock(spec=ModuleType)

    with patch('importlib.import_module', side_effect=ModuleNotFoundError):
        result = FromClause.resolve(mock_base, level=0, module_name='nonexistent')

        assert result is None


def test_try_import_as_module_success():
    """サブモジュールとして正常にインポートできる場合のテスト"""
    mock_module = Mock(spec=ModuleType)
    mock_module.__name__ = 'mypackage'
    mock_base_module = Mock(spec=ModuleType)

    clause = FromClause(mock_module, mock_base_module)

    with patch('importlib.import_module') as mock_import:
        mock_submodule = Mock(spec=ModuleType)
        mock_import.return_value = mock_submodule

        is_module, module = clause.try_import_as_module('helper')

        assert is_module is True
        assert module is mock_submodule
        mock_import.assert_called_once_with('mypackage.helper')


def test_try_import_as_module_failure():
    """サブモジュールのインポートが失敗する場合のテスト（アトリビュート）"""
    mock_module = Mock(spec=ModuleType)
    mock_module.__name__ = 'mypackage'
    mock_base_module = Mock(spec=ModuleType)

    clause = FromClause(mock_module, mock_base_module)

    with patch('importlib.import_module', side_effect=ModuleNotFoundError):
        is_module, module = clause.try_import_as_module('some_function')

        assert is_module is False
        assert module is None


def test_try_import_as_module_returns_base_module():
    """サブモジュールがbase_moduleと同じ場合、アトリビュートとして扱う

    理由: from . import name で name がパッケージ自身を指す場合、
    これは循環参照を避けるためアトリビュートとして扱われる。
    例: パッケージ内のモジュールが "from . import __init__" のようなケース。
    """
    mock_module = Mock(spec=ModuleType)
    mock_module.__name__ = 'mypackage'
    mock_base_module = Mock(spec=ModuleType)

    clause = FromClause(mock_module, mock_base_module)

    with patch('importlib.import_module', return_value=mock_base_module):
        is_module, module = clause.try_import_as_module('name')

        assert is_module is False
        assert module is None


def test_import_from_clause_absolute():
    """絶対インポートの内部メソッドテスト"""
    mock_base = Mock(spec=ModuleType)

    with patch('importlib.import_module') as mock_import:
        mock_module = Mock(spec=ModuleType)
        mock_import.return_value = mock_module

        result = FromClause._import_from_clause(mock_base, level=0, module_name='os')

        assert result is mock_module
        mock_import.assert_called_once_with('os')


def test_import_relative_parent_package_self():
    """親パッケージインポート（自分自身）のテスト"""
    mock_base = Mock(spec=ModuleType)
    mock_base.__name__ = 'pkg.subpkg'
    mock_base.__path__ = ['/path']  # パッケージ

    # level=1, パッケージなのでactual_level=0 → 自分自身
    result = FromClause._import_relative_parent_package(mock_base, level=1)

    assert result is mock_base


def test_import_relative_parent_package_parent():
    """親パッケージインポート（親）のテスト"""
    mock_base = Mock(spec=ModuleType)
    mock_base.__name__ = 'pkg.subpkg.module'
    # モジュール（__path__なし）

    with patch('importlib.import_module') as mock_import:
        mock_parent = Mock(spec=ModuleType)
        mock_import.return_value = mock_parent

        result = FromClause._import_relative_parent_package(mock_base, level=1)

        assert result is mock_parent
        mock_import.assert_called_once_with('pkg.subpkg')
