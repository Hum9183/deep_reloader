from ._metadata import __version__, __author__

from .deep_reloader import DeepReloader
from .module_info import ModuleInfo
from .imported_symbols import ImportedSymbols
from .symbol_extractor import SymbolExtractor

import logging


def setup_logging(log_level: int = logging.INFO) -> logging.Logger:
    """deep_reloader パッケージのログを設定し、パッケージロガーを返す。

    Args:
        log_level: ログレベル（logging.DEBUG, logging.INFO, logging.WARNING など）
                  デフォルトは logging.INFO

    Returns:
        logging.Logger: 設定されたパッケージロガー

    Note:
        この関数はパッケージ全体のログレベルを変更します。
        複数のDeepReloaderインスタンスがある場合、すべてに影響します。
        Maya環境では INFO レベルがデフォルトとして適切です。

    Example:
        >>> from deep_reloader import setup_logging
        >>> import logging
        >>> logger = setup_logging(logging.DEBUG)
        >>> logger.info("ログ設定完了")
    """
    # パッケージロガーのレベルを設定
    logger = logging.getLogger(__name__)  # __init__.py では __name__ が直接パッケージ名
    logger.setLevel(log_level)
    return logger


__all__ = [
    'DeepReloader',
    'setup_logging',
    'ModuleInfo',
    'ImportedSymbols',
    'SymbolExtractor',
]
