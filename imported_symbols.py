from typing import List, Iterator, Optional
import logging

logger = logging.getLogger(__name__)


class ImportedSymbols:
    """モジュールから親モジュールへコピーされるシンボル集合を保持する軽量コンテナ。

    logging:
        シンボルコピーの詳細ログはDEBUGレベルで出力されます。
        ログレベルは DeepReloader の verbose パラメータで制御してください。
    """
    def __init__(self, names: Optional[List[str]]=None) -> None:
        """ImportedSymbolsを初期化する。

        Args:
            names: from-import文でインポートされるシンボル名の文字列リスト
                  例: from math import sin, cos, pi → ['sin', 'cos', 'pi']
                      from maya.cmds import ls, select → ['ls', 'select']
                      from mymodule import * → ['func1', 'Class1', 'CONST'] (全public属性)
        """
        self.names: List[str] = names or []

    def __iter__(self) -> Iterator[str]:
        return iter(self.names)

    def __len__(self) -> int:
        return len(self.names)

    def __repr__(self) -> str:
        return f'ImportedSymbols({self.names})'

    def __contains__(self, name: str) -> bool:
        """指定したシンボル名が含まれているかを返す"""
        return name in self.names

    def __bool__(self) -> bool:
        """空でなければ True を返す（if symbols: が可能）"""
        return bool(self.names)

    def to_list(self) -> List[str]:
        """シンボル名のリストをコピーして返す"""
        return list(self.names)

    def add(self, *new_names: str) -> None:
        """新しいシンボル名を追加（重複は自動的に除去）"""
        for name in new_names:
            if name not in self.names:
                self.names.append(name)

    def merge(self, other: 'ImportedSymbols') -> None:
        """他の ImportedSymbols と結合（重複除去）"""
        for name in other.names:
            if name not in self.names:
                self.names.append(name)

    def copy_to(self, source_module, target_module) -> None:
        """
        source_module（例：a）から target_module（例：b）へ
        指定されたシンボルをコピーする
        """
        for name in self.names:
            if hasattr(source_module, name):
                value = getattr(source_module, name)
                setattr(target_module, name, value)
                logger.debug(f'{target_module.__name__}.{name} ← {source_module.__name__}.{name} ({value!r})')
