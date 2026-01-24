"""ImportClauseクラスの単体テスト"""

from types import SimpleNamespace
from unittest.mock import Mock

from ...from_clause import FromClause
from ...import_clause import ImportClause


def test_init_with_names():
    """名前リストで初期化できることを確認"""
    names = ['sin', 'cos', 'pi']
    clause = ImportClause(names)

    assert list(clause) == ['sin', 'cos', 'pi']
    assert len(clause) == 3


def test_init_with_empty_list():
    """空リストで初期化できることを確認"""
    clause = ImportClause([])

    assert list(clause) == []
    assert len(clause) == 0


def test_init_with_single_name():
    """単一の名前で初期化できることを確認"""
    clause = ImportClause(['value'])

    assert list(clause) == ['value']
    assert len(clause) == 1


def test_iteration():
    """イテレーション可能であることを確認"""
    names = ['a', 'b', 'c']
    clause = ImportClause(names)

    result = []
    for name in clause:
        result.append(name)

    assert result == ['a', 'b', 'c']


def test_multiple_iterations():
    """複数回イテレーション可能であることを確認"""
    clause = ImportClause(['x', 'y'])

    first_iteration = list(clause)
    second_iteration = list(clause)

    assert first_iteration == ['x', 'y']
    assert second_iteration == ['x', 'y']


def test_expand_with_all_attribute():
    """__all__が定義されているモジュールの展開テスト"""
    # モックモジュール作成
    mock_module = SimpleNamespace(
        __all__=['public1', 'public2'],
        public1='value1',
        public2='value2',
        _private='private_value',
        __name__='mock_module',
    )

    # モックFromClause作成
    mock_from_clause = Mock(spec=FromClause)
    mock_from_clause.module = mock_module

    # ワイルドカード展開
    result = ImportClause.expand_wildcard(mock_from_clause)

    assert list(result) == ['public1', 'public2']
    assert len(result) == 2


def test_expand_without_all_attribute():
    """__all__がないモジュールの展開テスト（特殊属性を除外）"""
    # モックモジュール作成（__all__なし）
    mock_module = SimpleNamespace(
        value1='v1',
        value2='v2',
        _private='private',
        __name__='mock',
        __file__='/path/to/mock.py',
    )

    # モックFromClause作成
    mock_from_clause = Mock(spec=FromClause)
    mock_from_clause.module = mock_module

    # ワイルドカード展開
    result = ImportClause.expand_wildcard(mock_from_clause)

    # __name__, __file__ は除外されるが、_private は含まれる
    result_names = sorted(list(result))
    assert result_names == ['_private', 'value1', 'value2']


def test_expand_with_empty_all():
    """__all__が空リストの場合のテスト"""
    mock_module = SimpleNamespace(
        __all__=[],
        value='some_value',
        __name__='empty_module',
    )

    mock_from_clause = Mock(spec=FromClause)
    mock_from_clause.module = mock_module

    result = ImportClause.expand_wildcard(mock_from_clause)

    assert list(result) == []
    assert len(result) == 0


def test_expand_excludes_special_attributes():
    """特殊属性（__xxx__）が除外されることを確認"""
    mock_module = SimpleNamespace(
        public_var='value',
        __name__='test',
        __file__='test.py',
        __doc__='documentation',
        __package__='pkg',
    )

    mock_from_clause = Mock(spec=FromClause)
    mock_from_clause.module = mock_module

    result = ImportClause.expand_wildcard(mock_from_clause)

    assert list(result) == ['public_var']


def test_expand_includes_private_attributes():
    """プライベート属性（_xxx）は含まれることを確認（Pythonの仕様）"""
    mock_module = SimpleNamespace(
        public='value',
        _private='private',
        __special__='special',
    )

    mock_from_clause = Mock(spec=FromClause)
    mock_from_clause.module = mock_module

    result = ImportClause.expand_wildcard(mock_from_clause)

    # Pythonの仕様: __all__がない場合、_xxxは含まれる（__xxx__のみ除外）
    assert sorted(list(result)) == ['_private', 'public']
