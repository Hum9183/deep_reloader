"""DependencyNodeクラスの単体テスト

注意: DependencyNodeはデータ構造のみを責任とするため、基本的な初期化と構造のみをテスト。
リロード処理は TreeReloader が担当し、統合テストで検証。
"""

from types import ModuleType
from unittest.mock import Mock

from ...domain import DependencyNode


def test_init():
    """DependencyNodeが正しく初期化されることを確認"""
    mock_module = Mock(spec=ModuleType)

    info = DependencyNode(mock_module)

    assert info.module is mock_module
    assert info.children == []
    assert info.symbols is None


def test_children_management():
    """子モジュールの追加と管理ができることを確認"""
    mock_parent = Mock(spec=ModuleType)
    mock_child1 = Mock(spec=ModuleType)
    mock_child2 = Mock(spec=ModuleType)

    parent_info = DependencyNode(mock_parent)
    child_info1 = DependencyNode(mock_child1)
    child_info2 = DependencyNode(mock_child2)

    # 初期状態
    assert len(parent_info.children) == 0

    # 1つ追加
    parent_info.children.append(child_info1)
    assert len(parent_info.children) == 1
    assert parent_info.children[0] is child_info1

    # さらに追加
    parent_info.children.append(child_info2)
    assert len(parent_info.children) == 2
    assert parent_info.children[0] is child_info1
    assert parent_info.children[1] is child_info2


def test_symbols_management():
    """symbolsの設定と取得ができることを確認"""
    mock_module = Mock(spec=ModuleType)
    info = DependencyNode(mock_module)

    # 初期状態
    assert info.symbols is None

    # symbolsのリストを設定
    symbols = ['func1', 'func2', 'VALUE']
    info.symbols = symbols

    assert info.symbols is symbols
    assert list(info.symbols) == ['func1', 'func2', 'VALUE']


def test_tree_structure():
    """ツリー構造を構築できることを確認"""
    mock_root = Mock(spec=ModuleType)
    mock_child1 = Mock(spec=ModuleType)
    mock_child2 = Mock(spec=ModuleType)
    mock_grandchild = Mock(spec=ModuleType)

    root_info = DependencyNode(mock_root)
    child_info1 = DependencyNode(mock_child1)
    child_info2 = DependencyNode(mock_child2)
    grandchild_info = DependencyNode(mock_grandchild)

    # ツリー構造: root -> child1 -> grandchild
    #                  -> child2
    root_info.children.append(child_info1)
    root_info.children.append(child_info2)
    child_info1.children.append(grandchild_info)

    assert len(root_info.children) == 2
    assert len(child_info1.children) == 1
    assert len(child_info2.children) == 0
    assert child_info1.children[0] is grandchild_info
