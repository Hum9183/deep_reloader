from types import ModuleType
from typing import Iterator, List, Optional, Tuple

from .from_clause import FromClause


class ImportClause:
    """import句でインポートされる名前のリストを保持し、分類処理を担当するクラス

    from xxx import yyy の yyy 部分（import句）の名前を保持し、
    モジュール/アトリビュートの分類処理を行います。

    Attributes:
        _names: import句でインポートされる名前の文字列リスト
               例: from math import sin, cos, pi → ['sin', 'cos', 'pi']
                   from maya.cmds import ls, select → ['ls', 'select']
                   from mymodule import * → ['func1', 'Class1', 'CONST'] (展開後)
                   from .utils import get_value as get_val → ['get_value'] (元の名前)

    Note:
        as句（エイリアス）の情報は保持しません。
        エイリアスは__dict__.update()で自動的に更新されるため不要です。
    """

    def __init__(self, names: List[str]) -> None:
        self._names = names

    def __iter__(self) -> Iterator[str]:
        """名前をイテレート可能にする"""
        return iter(self._names)

    def __len__(self) -> int:
        """名前の個数を返す"""
        return len(self._names)

    @classmethod
    def expand_wildcard(cls, from_clause: FromClause) -> 'ImportClause':
        """ワイルドカードインポートを展開してImportClauseを生成

        Args:
            from_clause: from句

        Returns:
            展開された名前から作成されたImportClause
        """
        # ワイルドカードインポート: from module import *
        module = from_clause.module
        if hasattr(module, '__all__'):
            # __all__ がある場合: 明示的に定義された公開名を使用
            names = list(module.__all__)
        else:
            # __all__ がない場合: 特殊属性以外の全属性を使用
            names = [
                attr_name
                for attr_name in module.__dict__
                if not attr_name.startswith('__')  # __name__, __file__ 等の特殊属性を除外
            ]
        return cls(names)

    def to_dependencies(
        self,
        from_clause: FromClause,
    ) -> List[Tuple[ModuleType, Optional['ImportClause']]]:
        """インポートされる名前をモジュールかアトリビュートかに分類して依存関係を返す

        Args:
            from_clause: from句

        Returns:
            依存関係のリスト
        """
        import_clause_modules = []
        import_clause_attrs = []

        for name in self._names:
            is_module, import_clause_module = from_clause.try_import_as_module(name)
            if is_module:
                import_clause_modules.append((import_clause_module, name))
            else:
                import_clause_attrs.append(name)

        # 結果をまとめる
        results = []
        for import_clause_module, module_name in import_clause_modules:
            # モジュールインポートの場合、モジュール自体の依存関係を追加
            results.append((import_clause_module, None))
            # さらに、from_clauseにmodule_nameを属性として設定するための依存関係も追加
            results.append((from_clause.module, ImportClause([module_name])))

        if import_clause_attrs:
            results.append((from_clause.module, ImportClause(import_clause_attrs)))

        return results
