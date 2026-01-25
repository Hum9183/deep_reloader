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
        self.import_clause: Optional[ImportClause] = None

    def reload(self, visited_modules=None) -> None:
        """
        再帰的にリロードを実行

        処理の流れ:
        1. sys.modulesから一時削除してキャッシュクリア
        2. importlib.import_module()で新しいモジュールオブジェクト(reloaded_module)を作成
        3. 子モジュールを再帰的にリロード
        4. 子のインポートされた名前をreloaded_moduleにコピー（関数の__globals__が正しく参照できるように）
        5. self.module.__dict__を更新（削除された属性を除去、新しい属性を追加・上書き）
        6. sys.modules[name]にself.moduleを登録（reloaded_moduleではなく）

        重要な設計思想:
        - self.moduleのオブジェクトIDを保持することで、既存の参照を有効に保つ
        - reloaded_moduleは一時的な作業用オブジェクトとして使用
        - __dict__を更新することで、オブジェクトを置き換えずに中身だけを更新
        """

        # 再帰処理で訪問済みモジュールを記録するセット
        if visited_modules is None:
            visited_modules = set()

        name = self.module.__name__
        # 既に訪問済みのモジュールはスキップ（重複処理防止・処理時間短縮）
        if name in visited_modules:
            return

        # このモジュールの処理が完了したことをマーク
        visited_modules.add(name)

        # 子を再帰的にリロード（子が先に完了する必要がある）
        for child in self.children:
            child.reload(visited_modules)

        # importlib.reload()を使用してリロード
        # これにより、sys.modulesから削除せずに安全にリロードできる
        reloaded_module = importlib.reload(self.module)

        # 子のリロード後、from-importで取得した名前を新しいモジュールにコピー
        # （reloaded_moduleの関数の__globals__に正しい値を設定するため）
        for child in self.children:
            if child.import_clause is not None:
                source_module = sys.modules.get(child.module.__name__, child.module)
                self._copy_import_clause_to(child.import_clause, source_module, reloaded_module)

        # リロード前のモジュール(self.module)にあって、リロード後のモジュール(reloaded_module)に存在しなくなった属性を削除する
        old_attrs = set(self.module.__dict__.keys())
        new_attrs = set(reloaded_module.__dict__.keys())
        for key in old_attrs - new_attrs:
            if not key.startswith('__'):  # __name__, __file__等の特殊属性は保持
                del self.module.__dict__[key]

        # self.module.__dict__をreloaded_module.__dict__で更新（属性を追加・上書き）
        self.module.__dict__.update(reloaded_module.__dict__)

        # sys.modulesをself.moduleで上書き
        sys.modules[name] = self.module

        logger.debug(f'RELOADED {name}')

    def _copy_import_clause_to(
        self,
        import_clause: ImportClause,
        source_module: ModuleType,
        target_module: ModuleType,
    ) -> None:
        """
        source_moduleからtarget_moduleへimport_clauseで指定された名前をコピーする

        Args:
            import_clause: コピーする名前を保持するImportClause
            source_module: コピー元のモジュール
            target_module: コピー先のモジュール
        """
        for name in import_clause:
            if hasattr(source_module, name):
                value = getattr(source_module, name)
                setattr(target_module, name, value)
                logger.debug(f'{target_module.__name__}.{name} ← {source_module.__name__}.{name} ({value!r})')
