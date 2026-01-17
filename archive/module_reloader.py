# -*- coding: utf-8 -*-

"""deep_reloaderの初期型"""

import _ast
import ast
import importlib
import inspect
import shutil
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Dict, List, Tuple, cast

# ref. https://graphics.hatenablog.com/entry/2019/12/22/052819

__package_name = ''


def module_reloader(module: ModuleType) -> None:
    """deep_reloaderの初期型

    Args:
        module: リロード対象のモジュール
    """
    global __package_name

    # モジュール名からパッケージ名を自動推定
    module_name = module.__name__
    if '.' in module_name:
        # パッケージの一部の場合は、最上位パッケージ名を使用
        __package_name = module_name.split('.')[0]
    else:
        # トップレベルモジュールの場合はモジュール名をそのまま使用
        __package_name = module_name

    _delete_modules()

    from_import_symbols: List[Tuple[ModuleType, Dict[ModuleType, List[str]]]] = _get_symbols(module)

    parent: ModuleType
    children_symbols: Dict[ModuleType, List[str]]
    for parent, children_symbols in from_import_symbols:
        _reload(children_symbols)
        _overwrite_with_reloaded_symbols(parent, children_symbols)


def _delete_modules() -> None:
    global __package_name

    # パッケージ名に基づいてsys.modulesからモジュールを削除
    for module_name in list(sys.modules.keys()):
        if module_name.startswith(__package_name):
            del sys.modules[module_name]


def _get_symbols(parent: ModuleType) -> List[Tuple[ModuleType, Dict[ModuleType, List[str]]]]:
    children_symbols: Dict[ModuleType, List[str]] = get_children_symbols(parent)
    result = []
    for child_module in children_symbols.keys():
        result.extend(_get_symbols(child_module))
    result.append((parent, children_symbols))
    return result


def get_children_symbols(module: ModuleType):
    children_symbols: Dict[ModuleType, List[Any]] = {}

    try:
        source = inspect.getsource(module)
    except Exception:
        # ソースコードが取得できない場合（組み込みモジュールなど）はスキップ
        return children_symbols

    tree: _ast.Module = ast.parse(source)

    stmt: _ast.stmt
    for stmt in tree.body:
        # TODO: import xxx の場合のサポートも必要？
        # from xxx import でないならcontinue
        if stmt.__class__ != _ast.ImportFrom:
            continue

        imp_frm = cast(_ast.ImportFrom, stmt)

        # モジュール名を取得（相対インポートの場合の特別処理を含む）
        module_name = imp_frm.module

        # モジュールのフルネームを取得
        if imp_frm.level == 0:
            # 絶対インポート: from module import something
            if module_name is None:
                continue
            module_full_name = f'{module_name}'
        elif imp_frm.level == 1:
            # 同階層相対インポート: from .module import something
            if module_name is None:
                # from . import something (現在のパッケージから直接インポート)
                module_full_name = module.__package__
            else:
                # from .module import something
                module_full_name = f'{module.__package__}.{module_name}'
        elif imp_frm.level >= 2:
            # 上位階層相対インポート: from ..module import something
            package_names = module.__package__.split('.')
            package_names = package_names[: -(imp_frm.level - 1)]
            package_names = '.'.join(package_names)
            if module_name is None:
                # from .. import something (上位パッケージから直接インポート)
                module_full_name = package_names
            else:
                # from ..module import something
                module_full_name = f'{package_names}.{module_name}'
        else:
            raise Exception('module_reloaderにて例外が発生しました。ソースコードを確認してください')

        # リロード対象ではないならcontinue
        global __package_name
        if not module_full_name.startswith(__package_name):
            continue

        try:
            new_module: ModuleType = importlib.import_module(module_full_name)
        except Exception:
            # インポートに失敗した場合はスキップ
            continue

        # packageならスキップ（フリーズ防止のため重要）
        if _is_package(new_module):
            # NOTE: from xxx import yyy のyyyがモジュールのため、シンボルを上書きする必要はない。
            continue

        symbol_names: List[str] = [x.name for x in imp_frm.names]

        # wildcard importの場合
        if symbol_names[0] == '*':
            if '__all__' in new_module.__dict__:
                symbol_names = new_module.__dict__['__all__']
            else:
                symbol_names = [x for x in new_module.__dict__ if not x.startswith('__')]

        children_symbols[new_module] = symbol_names

    return children_symbols


def _is_package(module: ModuleType) -> bool:
    """モジュールがパッケージ（__init__.py）かどうかを判定"""
    file = module.__file__
    return file is None or file.endswith('__init__.py')


def _reload(children_symbols: Dict[ModuleType, List[str]]) -> None:
    for child_module in children_symbols.keys():
        # 強力なリロード: sys.modulesから削除してから再インポート
        module_name = child_module.__name__

        # .pycファイルを削除（キャッシュクリア）
        _clear_single_pycache(child_module)

        # sys.modulesから削除
        if module_name in sys.modules:
            del sys.modules[module_name]

        # キャッシュをクリア
        importlib.invalidate_caches()

        # 再インポート
        try:
            reloaded_module = importlib.import_module(module_name)

            # 元のモジュールオブジェクトの辞書を更新
            child_module.__dict__.clear()
            child_module.__dict__.update(reloaded_module.__dict__)

        except Exception:
            # フォールバック: 通常のリロード
            importlib.reload(child_module)


def _clear_single_pycache(module: ModuleType) -> None:
    """
    1つのモジュールに対応する __pycache__ を削除
    """
    module_file = getattr(module, '__file__', None)
    if module_file is None:
        return

    module_dir = Path(module_file).parent
    pycache_dir = module_dir / '__pycache__'

    if pycache_dir.exists():
        try:
            shutil.rmtree(pycache_dir)
        except Exception:
            pass  # エラーは無視


def _overwrite_with_reloaded_symbols(parent: ModuleType, children_symbols: Dict[ModuleType, List[str]]) -> None:
    no_key = 'no key'

    for child_module, child_symbol_names in children_symbols.items():
        for child_symbol_name in child_symbol_names:
            val = child_module.__dict__.get(child_symbol_name, no_key)
            if val == no_key:
                print(f'sys.modulesに{child_symbol_name}が存在しません')
            else:
                parent.__dict__[child_symbol_name] = val
