import importlib
import logging
import sys
from types import ModuleType
from typing import List

from .imported_symbols import ImportedSymbols

logger = logging.getLogger(__name__)


class ModuleInfo:
    """
    モジュールとその子モジュール(from-import)情報を保持するクラス
    """
    def __init__(self, module: ModuleType) -> None:
        self.module: ModuleType = module
        self.children: List['ModuleInfo'] = []
        self.symbols: ImportedSymbols = ImportedSymbols()

    def reload(self, visited=None) -> None:
        """
        再帰的にリロードを実行（親→子の順でリロード）。

        主目的：自分自身のモジュールを最新のファイル内容でリロードすること
              （自身が取り込む子モジュールは最新ではないが今の段階ではそれでOK）。

        なぜ古い子モジュールでリロードするのか：
        1. 通常、親から再帰的にリロードすると（親→子→孫の順で呼び出しが進むため）
           親がリロードする際に古い子を取り込むことになる
        2. このreload()では各モジュールを最新内容に更新することが主目的(子モジュールは最新でなくてもよい)
        3. 子モジュール（from-import）の更新は後でoverwrite_symbols()が解決する設計
        4. リロードロジックとシンボル伝播ロジックは分離させることでよりシンプルに設計を保っている
        """

        # 再帰処理で訪問済みモジュールを記録するセット
        # 最初の呼び出し時のみ作成し、以降の再帰呼び出しでは同じオブジェクトを共有
        if visited is None:
            visited = set()

        name = self.module.__name__
        # 既に訪問済みのモジュールはスキップ（重複処理防止・処理時間短縮）
        if name in visited:
            return

        # キャッシュを消してから再インポート
        if name in sys.modules:
            sys.modules.pop(name, None)
        importlib.invalidate_caches()

        new_module = importlib.import_module(name)
        self.module = new_module
        visited.add(name)

        # リロード完了をログ出力（ログレベルで制御）
        logger.info(f'RELOADED {name}')

        # 子を再帰的にリロード
        for child in self.children:
            child.reload(visited)

    def overwrite_symbols(self) -> None:
        """
        from-import シンボルを親モジュールに上書き（葉から順）
        """
        # 子を先に処理（葉 → 根）
        for child in self.children:
            child.overwrite_symbols()

        # 子モジュールから自分にシンボルをコピー
        for child in self.children:
            child.symbols.copy_to(child.module, self.module)
