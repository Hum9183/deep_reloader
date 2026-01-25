import importlib
import logging
import sys
from types import ModuleType
from typing import List, Optional

from .import_clause import ImportClause

logger = logging.getLogger(__name__)


class ModuleNode:
    """
    モジュールとその子モジュール(from-import)情報を保持するクラス
    """

    def __init__(self, module: ModuleType) -> None:
        self.module: ModuleType = module
        self.children: List['ModuleNode'] = []
        self.symbols: Optional[ImportClause] = None

    def reload(self, visited=None) -> None:
        """
        再帰的にリロードを実行

        処理の流れ:
        1. sys.modulesから一時削除してキャッシュクリア
        2. importlib.import_module()で新しいモジュールオブジェクト(new_module)を作成
        3. 子モジュールを再帰的にリロード
        4. 子のシンボルをnew_moduleにコピー（関数の__globals__が正しく参照できるように）
        5. self.module.__dict__を更新（削除された属性を除去、新しい属性を追加・上書き）
        6. sys.modules[name]にself.moduleを登録（new_moduleではなく）

        重要な設計思想:
        - self.moduleのオブジェクトIDを保持することで、既存の参照を有効に保つ
        - new_moduleは一時的な作業用オブジェクトとして使用
        - __dict__を更新することで、オブジェクトを置き換えずに中身だけを更新
        """

        # 再帰処理で訪問済みモジュールを記録するセット
        if visited is None:
            visited = set()

        name = self.module.__name__
        # 既に訪問済みのモジュールはスキップ（重複処理防止・処理時間短縮）
        if name in visited:
            return

        # このモジュールの処理が完了したことをマーク
        visited.add(name)

        # 子を再帰的にリロード（子が先に完了する必要がある）
        for child in self.children:
            child.reload(visited)

        # importlib.reload()を使用してリロード
        # これにより、sys.modulesから削除せずに安全にリロードできる
        new_module = importlib.reload(self.module)

        # 子のリロード後、from-importシンボルを新しいモジュールにコピー
        # （new_moduleの関数の__globals__に正しい値を設定するため）
        for child in self.children:
            if child.symbols is not None:
                source_module = sys.modules.get(child.module.__name__, child.module)
                self._copy_symbols_to(child.symbols, source_module, new_module)

        # リロード前のモジュール(self.module)にあって、リロード後のモジュール(new_module)に存在しなくなった属性を削除する
        old_keys = set(self.module.__dict__.keys())
        new_keys = set(new_module.__dict__.keys())
        for key in old_keys - new_keys:
            if not key.startswith('__'):  # __name__, __file__等の特殊属性は保持
                del self.module.__dict__[key]

        # self.module.__dict__をnew_module.__dict__で更新（属性を追加・上書き）
        self.module.__dict__.update(new_module.__dict__)

        # sys.modulesをself.moduleで上書き
        sys.modules[name] = self.module

        logger.debug(f'RELOADED {name}')

    def _copy_symbols_to(self, symbols: ImportClause, source_module, target_module) -> None:
        """
        source_moduleからtarget_moduleへ指定されたシンボルをコピーする

        Args:
            symbols: コピーするシンボル名のリスト
            source_module: コピー元のモジュール
            target_module: コピー先のモジュール
        """
        for name in symbols:
            if hasattr(source_module, name):
                value = getattr(source_module, name)
                setattr(target_module, name, value)
                logger.debug(f'{target_module.__name__}.{name} ← {source_module.__name__}.{name} ({value!r})')
