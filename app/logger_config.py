import logging
import sys


def configure_logger(level = logging.INFO):
    formatter = logging.Formatter(
        '[%(asctime)s.%(msecs)03d] %(module)10s:%(lineno)-3d %(levelname)-7s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.WARNING)

    logging.getLogger("app").setLevel(level)

    root_logger.addHandler(console_handler)

configure_logger(logging.DEBUG)
