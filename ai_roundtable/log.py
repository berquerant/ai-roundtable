import logging
import sys
from typing import cast


__debug: bool = False
__quiet: bool = False
__logger: None | logging.Logger = None


def __level() -> int:
    global __quiet
    global __debug
    if __quiet:
        return logging.CRITICAL
    if __debug:
        return logging.DEBUG
    return logging.INFO


def __init() -> None:
    """Initialize the logger."""
    global __logger, __debug
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(message)s",
    )
    __logger = logging.getLogger(__name__)
    __logger.addHandler(logging.StreamHandler(sys.stderr))
    __logger.setLevel(__level())


def __get() -> logging.Logger:
    global __logger
    if __logger is None:
        __init()
    return cast(logging.Logger, __logger)


def debug() -> None:
    """Enable debug log."""
    global __debug
    __debug = True


def quiet() -> None:
    """Quiet log."""
    global __quiet
    __quiet = True


def log() -> logging.Logger:
    """Return the logger instance."""
    return __get()
