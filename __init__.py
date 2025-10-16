import logging

from ._metadata import __author__, __version__
from .deep_reloader import deep_reload
from .imported_symbols import ImportedSymbols
from .module_info import ModuleInfo
from .symbol_extractor import SymbolExtractor


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
    'deep_reload',
    'setup_logging',
    'ModuleInfo',
    'ImportedSymbols',
    'SymbolExtractor',
]
