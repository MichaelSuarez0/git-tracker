import logging
from pathlib import Path
from typing import Optional


def ensure_logger(logger: Optional[logging.Logger] = None) -> logging.Logger:
    if logger is not None:
        return logger
    return logging.getLogger(__name__)


def setup_logger(
    name: str,
    log_file: Optional[Path] = None,
    level: int = logging.INFO,
    log_to_console: bool = True,
    log_to_file: bool = False
) -> logging.Logger:
    """
    Configura el logger principal.

    Args:
        name: Nombre del logger (por módulo).
        log_file: Ruta al archivo de log si log_to_file=True.
        level: Nivel de log (logging.INFO, DEBUG, etc).
        log_to_console: Mostrar logs en consola.
        log_to_file: Guardar logs en archivo.

    Returns:
        Logger ya configurado.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Evitar duplicar handlers
    if logger.hasHandlers():
        logger.handlers.clear()

    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    if log_to_console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter('[%(levelname)s] %(message)s'))
        logger.addHandler(console_handler)

    if log_to_file:
        log_file = log_file if log_file else Path("logs") / f"{name}.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8", mode="a")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
