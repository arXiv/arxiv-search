"""Provides a logger factory that applies app-wide logging configuration."""

import logging
import sys

from search.context import get_application_config

CONFIG = get_application_config()
default_format = '%(asctime)s - %(name)s - %(levelname)s: %(message)s'
default_level = int(CONFIG.get('LOGLEVEL', logging.INFO))
LOGFILE = CONFIG.get('LOGFILE', None)


def getLogger(name: str, fmt: str = default_format,
              level: int = default_level) -> logging.Logger:
    """
    Wrapper for :func:`logging.getLogger` that applies configuration.

    Parameters
    ----------
    name : str
    fmt : str
    level : int

    Returns
    -------
    :class:`logging.Logger`
    """
    logging.basicConfig(format=fmt)
    logger = logging.getLogger(name)
    logger.setLevel(level)
    if LOGFILE is not None:
        logger.handlers = []
        logger.addHandler(logging.FileHandler(LOGFILE))
        logger.propagate = False
    return logger
