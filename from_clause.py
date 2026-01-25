import importlib
from types import ModuleType
from typing import Optional, Tuple


class FromClause:
    """from句のモジュールを保持し、from句関連の処理を担当するクラス

    from xxx import yyy の xxx 部分（from句）のモジュールを保持し、
    サブモジュールのインポートやモジュール/アトリビュート判定を行います。

    Attributes:
        _module: from句で指定されたモジュール
        _importing_module: 基準となるモジュール（import文が記述されているモジュール）
    """

    def __init__(self, module: ModuleType, base_module: ModuleType) -> None:
        self._module = module
        self._importing_module = base_module

    @property
    def module(self) -> ModuleType:
        """from句のモジュールを取得"""
        return self._module

    @classmethod
    def resolve(cls, base_module: ModuleType, level: int, module_name: Optional[str]) -> Optional['FromClause']:
        """from句のモジュールを解決してFromClauseインスタンスを生成

        Args:
            base_module: 基準となるモジュール（import文が記述されているモジュール）
            level: 相対インポートのレベル (0=絶対, 1=".", 2="..", ...)
            module_name: モジュール名（from . import yyy の場合はNone）

        Returns:
            FromClauseインスタンス、失敗時はNone

        例:
            - from math import sin
              → level=0, module_name='math' → mathモジュール
            - from . import helper
              → level=1, module_name=None → 親パッケージ
            - from .utils import func
              → level=1, module_name='utils' → utilsモジュール
            - from ..config import VALUE
              → level=2, module_name='config' → configモジュール
        """
        if level > 0 and module_name is None:
            # from . import yyy パターン
            module = cls._import_relative_parent_package(base_module, level)
        else:
            # from xxx import yyy パターン
            module = cls._import_from_clause(base_module, level, module_name)

        if module is None:
            return None

        return cls(module, base_module)

    def try_import_as_module(self, name: str) -> Tuple[bool, Optional[ModuleType]]:
        """nameをモジュールとしてインポート試行（モジュール/アトリビュート判定のため）

        モジュール/アトリビュートの分類判定に使用。
        成功すればモジュール、失敗すればアトリビュート（関数/クラス/変数）と判断される。

        Args:
            name: インポートする名前

        Returns:
            (is_module, module): is_moduleがTrueならモジュール、Falseならアトリビュート
        """
        # どちらのパターンでもサブモジュールとしてインポートを試行
        module_candidate = self._try_import_submodule(name)

        is_module = module_candidate is not None and module_candidate is not self._importing_module
        return (is_module, module_candidate if is_module else None)

    def _try_import_submodule(self, name: str) -> Optional[ModuleType]:
        """from句のモジュールから指定された名前をサブモジュールとしてインポートを試行

        Args:
            name: インポートする名前

        Returns:
            インポートされたサブモジュール、失敗時はNone
        """
        try:
            full_name = f'{self._module.__name__}.{name}'
            return importlib.import_module(full_name)
        except (ModuleNotFoundError, ImportError):
            return None

    @staticmethod
    def _import_from_clause(base_module: ModuleType, level: int, module_name: Optional[str]) -> Optional[ModuleType]:
        """from句で指定されたモジュールをインポート

        Args:
            base_module: 基準となるモジュール
            level: 相対インポートのレベル (0=絶対, 1=".", 2="..", ...)
            module_name: モジュール名
        """
        try:
            if level > 0:
                # 相対インポート(from .xxx import yyy)の場合
                return FromClause._import_from_clause_relative(base_module, level, module_name)
            else:
                # 絶対インポート(from xxx import yyy)の場合
                return importlib.import_module(module_name)
        except (ModuleNotFoundError, ImportError):
            return None

    @staticmethod
    def _import_from_clause_relative(base_module: ModuleType, level: int, module_name: str) -> Optional[ModuleType]:
        """from句の相対インポートでモジュールをインポートする

        Args:
            base_module: 基準となるモジュール
            level: 相対インポートのレベル (1 = ".", 2 = "..", ...)
            module_name: インポートするモジュール名

        Returns:
            インポートされたモジュール、失敗時はNone
        """
        try:
            # パッケージ(__path__を持つ)の場合、level - 1 を使用
            if hasattr(base_module, '__path__'):
                actual_level = level - 1
            else:
                actual_level = level

            if actual_level == 0:
                base_name = base_module.__name__
            else:
                base_name = base_module.__name__.rsplit('.', actual_level)[0]

            target_name = f'{base_name}.{module_name}'
            return importlib.import_module(target_name)
        except (ModuleNotFoundError, ImportError):
            return None

    @staticmethod
    def _import_relative_parent_package(base_module: ModuleType, level: int) -> Optional[ModuleType]:
        """相対インポートの親パッケージをインポートする

        Args:
            base_module: 基準となるモジュール
            level: 相対インポートのレベル (1 = ".", 2 = "..", ...)

        Returns:
            インポートされた親パッケージ、失敗時はNone
        """
        try:
            # パッケージ(__path__を持つ)の場合、level - 1 を使用
            if hasattr(base_module, '__path__'):
                actual_level = level - 1
            else:
                actual_level = level

            if actual_level == 0:
                # 自分自身のパッケージ
                return base_module
            else:
                parent_name = base_module.__name__.rsplit('.', actual_level)[0]
                return importlib.import_module(parent_name)
        except (ModuleNotFoundError, ImportError, ValueError):
            return None
