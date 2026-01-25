"""deep_reloader.pyの単体テスト

注意: deep_reload()とその内部関数は複雑な統合処理のため、詳細な動作は統合テストで検証。
ここでは個別の内部関数の基本動作のみをテスト。
"""

import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, Mock, patch

from ...deep_reloader import _build_tree, _clear_single_pycache
from ...module_node import ModuleNode


def test_build_tree_simple_module():
    """単純なモジュールでツリーが構築されることを確認"""
    mock_module = Mock(spec=ModuleType)
    mock_module.__name__ = 'testpkg.main'

    visited = set()
    target_package = 'testpkg'

    with patch('deep_reloader.deep_reloader.SymbolExtractor') as mock_extractor_class:
        mock_extractor = Mock()
        mock_extractor.extract.return_value = []
        mock_extractor_class.return_value = mock_extractor

        result = _build_tree(mock_module, visited, target_package)

        assert isinstance(result, ModuleNode)
        assert result.module is mock_module
        assert len(result.children) == 0
        assert 'testpkg.main' in visited


def test_build_tree_with_children():
    """子モジュールを持つツリーが構築されることを確認"""
    mock_parent = Mock(spec=ModuleType)
    mock_parent.__name__ = 'testpkg.parent'

    mock_child = Mock(spec=ModuleType)
    mock_child.__name__ = 'testpkg.child'

    visited = set()
    target_package = 'testpkg'

    with patch('deep_reloader.deep_reloader.SymbolExtractor') as mock_extractor_class:
        # 親モジュールは子を1つ返す
        parent_extractor = Mock()
        parent_extractor.extract.return_value = [(mock_child, None)]

        # 子モジュールは何も返さない
        child_extractor = Mock()
        child_extractor.extract.return_value = []

        mock_extractor_class.side_effect = [parent_extractor, child_extractor]

        result = _build_tree(mock_parent, visited, target_package)

        assert len(result.children) == 1
        assert result.children[0].module is mock_child
        assert 'testpkg.parent' in visited
        assert 'testpkg.child' in visited


def test_build_tree_skips_different_package():
    """異なるパッケージのモジュールをスキップすることを確認"""
    mock_parent = Mock(spec=ModuleType)
    mock_parent.__name__ = 'testpkg.parent'

    mock_other = Mock(spec=ModuleType)
    mock_other.__name__ = 'otherpkg.module'

    visited = set()
    target_package = 'testpkg'

    with patch('deep_reloader.deep_reloader.SymbolExtractor') as mock_extractor_class:
        parent_extractor = Mock()
        parent_extractor.extract.return_value = [(mock_other, None)]
        mock_extractor_class.return_value = parent_extractor

        result = _build_tree(mock_parent, visited, target_package)

        # otherpkgはスキップされるため子は0個
        assert len(result.children) == 0
        assert 'testpkg.parent' in visited
        # スキップされたモジュールはvisitedに追加されない
        assert 'otherpkg.module' not in visited


def test_build_tree_prevents_circular_import():
    """循環インポートが検出されて無限ループを防ぐことを確認"""
    mock_module = Mock(spec=ModuleType)
    mock_module.__name__ = 'testpkg.circular'

    # すでに訪問済みのセット
    visited = {'testpkg.circular'}
    target_package = 'testpkg'

    with patch('deep_reloader.deep_reloader.SymbolExtractor') as mock_extractor_class:
        result = _build_tree(mock_module, visited, target_package)

        # ノードは作成されるが、extractorは呼ばれない（子の展開がスキップされる）
        assert isinstance(result, ModuleNode)
        assert result.module is mock_module
        mock_extractor_class.assert_not_called()


def test_clear_single_pycache_with_existing_cache():
    """__pycache__が存在する場合に削除されることを確認"""
    mock_module = Mock(spec=ModuleType)
    mock_file = '/path/to/module.py'
    mock_module.__file__ = mock_file

    mock_pycache_path = MagicMock(spec=Path)
    mock_pycache_path.exists.return_value = True

    with patch('deep_reloader.deep_reloader.Path') as mock_path_class, patch(
        'deep_reloader.deep_reloader.shutil.rmtree'
    ) as mock_rmtree:

        mock_module_path = MagicMock(spec=Path)
        mock_module_path.parent = MagicMock()
        mock_module_path.parent.__truediv__ = lambda self, x: mock_pycache_path

        mock_path_class.return_value = mock_module_path

        _clear_single_pycache(mock_module)

        mock_pycache_path.exists.assert_called_once()
        mock_rmtree.assert_called_once_with(mock_pycache_path)


def test_clear_single_pycache_without_file():
    """__file__属性がないモジュールでエラーが発生しないことを確認"""
    mock_module = Mock(spec=ModuleType)
    mock_module.__file__ = None

    with patch('deep_reloader.deep_reloader.shutil.rmtree') as mock_rmtree:
        _clear_single_pycache(mock_module)

        # __file__がNoneの場合、何もしない
        mock_rmtree.assert_not_called()


def test_clear_single_pycache_without_existing_cache():
    """__pycache__が存在しない場合に何もしないことを確認"""
    mock_module = Mock(spec=ModuleType)
    mock_file = '/path/to/module.py'
    mock_module.__file__ = mock_file

    mock_pycache_path = MagicMock(spec=Path)
    mock_pycache_path.exists.return_value = False

    with patch('deep_reloader.deep_reloader.Path') as mock_path_class, patch(
        'deep_reloader.deep_reloader.shutil.rmtree'
    ) as mock_rmtree:

        mock_module_path = MagicMock(spec=Path)
        mock_module_path.parent = MagicMock()
        mock_module_path.parent.__truediv__ = lambda self, x: mock_pycache_path

        mock_path_class.return_value = mock_module_path

        _clear_single_pycache(mock_module)

        mock_pycache_path.exists.assert_called_once()
        # 存在しないので削除は呼ばれない
        mock_rmtree.assert_not_called()


def test_clear_single_pycache_handles_exception():
    """__pycache__削除時の例外が適切に処理されることを確認"""
    mock_module = Mock(spec=ModuleType)
    mock_file = '/path/to/module.py'
    mock_module.__file__ = mock_file

    mock_pycache_path = MagicMock(spec=Path)
    mock_pycache_path.exists.return_value = True

    with patch('deep_reloader.deep_reloader.Path') as mock_path_class, patch(
        'deep_reloader.deep_reloader.shutil.rmtree'
    ) as mock_rmtree:

        mock_module_path = MagicMock(spec=Path)
        mock_module_path.parent = MagicMock()
        mock_module_path.parent.__truediv__ = lambda self, x: mock_pycache_path

        mock_path_class.return_value = mock_module_path
        mock_rmtree.side_effect = PermissionError('Permission denied')

        # 例外が発生してもエラーにならない
        _clear_single_pycache(mock_module)

        mock_rmtree.assert_called_once()
