import ast
import importlib
import inspect
import logging
from types import ModuleType
from typing import List, Optional, Tuple

from .imported_symbols import ImportedSymbols

logger = logging.getLogger(__name__)


class SymbolExtractor:
    """
    モジュールのASTを解析して、from-import文の「子モジュール」と「インポートされるシンボル」を抽出するクラス

    from-import文で参照される子モジュールと、インポートされるシンボル名のペアを
    (ModuleType, ImportedSymbols) の形式で返す。

    例: from math import sin, cos → (math_module, ImportedSymbols(['sin', 'cos']))
        この場合、mathが子モジュール、sin・cosがインポートされるシンボル
    """
    def __init__(self, module: ModuleType) -> None:
        self.module = module
        # TODO: AST解析のパフォーマンス最適化
        # - 解析結果のキャッシュ（モジュールのタイムスタンプベース）
        # - 頻繁にアクセスされるモジュールの優先キャッシュ
        # - メモリ効率的なキャッシュ管理（LRU、サイズ制限）
        self.tree: Optional[ast.AST] = self._parse_ast()

    def extract(self) -> List[Tuple[ModuleType, ImportedSymbols]]:
        """(子モジュール, インポートされたシンボル) のリストを返す
        
        TODO: 組み込みモジュール（os、sys、pathlib等）やサードパーティライブラリ
        （maya.cmds、PySide6、numpy等）の判定とスキップ処理を実装する。
        これらのモジュールはリロード不要かつ危険な場合があるため、
        安全なモジュールのみを対象とする仕組みが必要。
        """
        if self.tree is None:
            return []

        results: List[Tuple[ModuleType, ImportedSymbols]] = []
        for node in ast.walk(self.tree):  # walkで全ノード探索（動的なfrom-import文も検出）
            if isinstance(node, ast.ImportFrom):
                child_module = self._resolve_imported_module(node)
                # 無効な依存関係を除外: 存在しないモジュール(None)と自分自身への参照
                if child_module is None or child_module is self.module:
                    continue
                
                # TODO: ここで組み込み・サードパーティモジュールのスキップ判定を追加
                # 例: if self._should_skip_module(child_module): continue
                # 判定ロジック案:
                # - sys.builtin_module_names による組み込みモジュール判定
                # - __file__ 属性の有無とパスによるサードパーティ判定
                # - 設定可能なブラックリスト/ホワイトリスト
                
                symbols = self._extract_symbols(child_module, node)
                results.append((child_module, symbols))
        return results

    def _parse_ast(self) -> Optional[ast.AST]:
        """モジュールをASTにパース"""
        try:
            source = inspect.getsource(self.module)
            return ast.parse(source)
        except (OSError, TypeError, SyntaxError):
            return None

    def _resolve_imported_module(self, stmt: ast.ImportFrom) -> Optional[ModuleType]:
        """ImportFromノードから実際の子モジュールを解決（相対対応）"""
        try:
            if stmt.level > 0:
                # 相対インポートを絶対パスに変換
                # importlib.import_module()は絶対パス（絶対モジュール名）しか受け付けないため、
                # 相対インポート（from .module や from ..module）を絶対パスに変換する必要がある
                base_name = self.module.__name__.rsplit('.', stmt.level)[0]
                # stmt.moduleがある場合: from ..utils import helper → "parent.utils"
                # stmt.moduleがNoneの場合: from .. import helper → "parent" (パッケージ自体の__init__.py)
                target_name = f'{base_name}.{stmt.module}' if stmt.module else base_name
                return importlib.import_module(target_name)
            else:
                # 絶対インポートの場合は絶対パスのためそのまま使用
                return importlib.import_module(stmt.module)
        except (ModuleNotFoundError, ImportError):
            return None

    def _extract_symbols(self, child_module: ModuleType, stmt: ast.ImportFrom) -> ImportedSymbols:
        """ImportFromノードからシンボル名を抽出"""
        # AST から実際のシンボル名を抽出（エイリアス名ではなく元の名前）
        names = [alias.name for alias in stmt.names]

        if names != ['*']:
            # 通常のインポート: from module import func1, func2
            # → names = ['func1', 'func2']
            return ImportedSymbols(names)
        else:
            # ワイルドカードインポート: from module import *
            if hasattr(child_module, '__all__'):
                # __all__ がある場合: 明示的に定義された公開シンボルを使用
                return ImportedSymbols(list(child_module.__all__))
            else:
                # __all__ がない場合: 特殊属性以外の全属性を使用
                public_attrs = []
                for attr_name in child_module.__dict__:
                    if attr_name.startswith('__') is False:  # __name__, __file__ 等の特殊属性を除外
                        public_attrs.append(attr_name)
                return ImportedSymbols(public_attrs)

    # TODO: 将来の実装用メソッド - 組み込み・サードパーティモジュールの判定
    # def _should_skip_module(self, module: ModuleType) -> bool:
    #     """モジュールをスキップすべきかどうかを判定する
    #     
    #     Args:
    #         module: 判定対象のモジュール
    #         
    #     Returns:
    #         True: スキップすべき（組み込み・サードパーティモジュール）
    #         False: リロード対象（ユーザー作成モジュール）
    #         
    #     判定ロジック案:
    #     1. sys.builtin_module_names による組み込みモジュール判定
    #     2. __file__ が None の場合（C拡張モジュール等）
    #     3. site-packages パス内のモジュール判定
    #     4. maya.* パッケージの特別扱い
    #     5. 設定可能なブラックリスト/ホワイトリスト
    #     """
    #     pass
