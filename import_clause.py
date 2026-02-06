"""import句の解決関数

from xxx import yyy の yyy 部分（import句）を解決する関数群。
"""

from types import ModuleType
from typing import List

from . import from_clause
from .domain import Dependency


def expand_if_wildcard(from_module: ModuleType, names: List[str]) -> List[str]:
    """ワイルドカードの場合はシンボルを展開する

    Args:
        from_module: from句で解決されたモジュール
        names: import句の名前リスト（['*'] の場合はワイルドカード）

    Returns:
        展開されたシンボル名のリスト

    例:
        - from math import sin, cos → ['sin', 'cos']
        - from module import * → ['func1', 'Class1', 'CONST']（展開後）
    """
    if names and names[0] == '*':
        return _expand_wildcard(from_module)
    else:
        return names


def create_dependencies(from_module: ModuleType, base_module: ModuleType, symbols: List[str]) -> List[Dependency]:
    """シンボルリストから依存関係を生成する

    モジュールインポートの場合、2つの依存関係を生成:
    1. サブモジュール自体への依存 (module, None)
    2. 親パッケージへのアトリビュートとしての依存 (from_module, [name])

    これにより、`from package import submodule` の際に:
    - submodule モジュールがリロードされる
    - package.submodule というアトリビュートが設定される

    Args:
        from_module: from句で解決されたモジュール
        base_module: 基準となるモジュール（import文が記述されているモジュール）
        symbols: インポートされるシンボル名のリスト

    Returns:
        Dependency オブジェクトのリスト
        symbols=None ならモジュール依存、symbols=[...] ならアトリビュート依存
    """
    results: List[Dependency] = []
    attributes: List[str] = []

    for name in symbols:
        is_module, module = from_clause.try_import_as_module(from_module, base_module, name)
        if is_module:
            # 1. サブモジュール自体への依存
            results.append(Dependency(module, None))
            # 2. 親パッケージのアトリビュートとしての依存
            results.append(Dependency(from_module, [name]))
        else:
            attributes.append(name)

    # アトリビュートは同じfrom句から来るため、1つのDependencyにまとめる
    if attributes:
        results.append(Dependency(from_module, attributes))

    return results


def _expand_wildcard(module: ModuleType) -> List[str]:
    """ワイルドカードインポートのシンボルリストを返す

    Args:
        module: ワイルドカード展開対象のモジュール

    Returns:
        展開されたシンボルリスト
    """
    if hasattr(module, '__all__'):
        return list(module.__all__)
    else:
        result = []
        for name in module.__dict__:
            if not name.startswith('__'):
                result.append(name)
        return result
