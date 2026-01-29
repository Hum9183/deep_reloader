"""ドメイン層: 依存関係モデル

Dependency データクラスと DependencyNode Entity を含む。
"""

from __future__ import annotations

from dataclasses import dataclass
from types import ModuleType
from typing import List, Optional


@dataclass(frozen=True)
class Dependency:
    """依存関係を表すデータ構造

    Attributes:
        module: 依存先のモジュール
        symbols: インポートするシンボルのリスト（Noneの場合はモジュール全体への依存）
    """

    module: ModuleType
    symbols: Optional[List[str]]


class DependencyNode:
    """依存関係ツリーのノード（Entity）

    モジュールとその子モジュール（from-import）の依存関係を保持します。
    """

    def __init__(self, module: ModuleType) -> None:
        self.module: ModuleType = module
        self.children: List[DependencyNode] = []
        self.symbols: Optional[List[str]] = None
