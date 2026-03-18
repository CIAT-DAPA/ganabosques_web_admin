import logging


def log_print(log, message, level="info"):
    """Imprime y loguea un mensaje simultáneamente."""
    print(message)
    getattr(log, level, log.info)(message)
