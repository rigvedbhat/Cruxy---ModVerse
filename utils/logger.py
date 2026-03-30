import logging
import sys


def setup_logging():
    fmt = logging.Formatter(
        "[%(asctime)s] %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(fmt)

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    if not root.handlers:
        root.addHandler(handler)
    else:
        root.handlers.clear()
        root.addHandler(handler)

    logging.getLogger("discord").setLevel(logging.WARNING)
    logging.getLogger("aiosqlite").setLevel(logging.WARNING)

    return logging.getLogger("seromod")


log = setup_logging()
