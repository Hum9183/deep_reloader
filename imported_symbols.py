import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


class ImportedSymbols:
    """親モジュールが子モジュールからインポートしたシンボル名のリストを管理するクラス"""

    def __init__(self, names: Optional[List[str]] = None) -> None:
        """ImportedSymbolsを初期化する。

        Args:
            names: from-import文でインポートされるシンボル名の文字列リスト
                  例: from math import sin, cos, pi → ['sin', 'cos', 'pi']
                      from maya.cmds import ls, select → ['ls', 'select']
                      from mymodule import * → ['func1', 'Class1', 'CONST'] (全public属性)
        """
        self.names: List[str] = names or []

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
