import logging
import logging.config
import os
import threading
import time

import yaml


class Logging:
    def __init__(self):
        log_config_file = os.environ.get("LOG_CONFIG_PATH", "./conf/logging/log-config.yml")
        if not os.path.exists("./logs"):
            os.makedirs("./logs")
        try:
            with open(log_config_file, 'rt') as f:
                config = yaml.safe_load(f.read())
            logging.config.dictConfig(config)
        except FileNotFoundError:
            logging.basicConfig(level=logging.INFO)

    @staticmethod
    def get_logger(name=None):
        return logging.getLogger(name)


service_logger = Logging().get_logger("service")
algo_logger = Logging().get_logger("algo")
access_logger = Logging().get_logger("access")
custom_logging_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "()": "uvicorn.logging.DefaultFormatter",
            "fmt": "%(asctime)s %(levelprefix)s %(message)s",
            "use_colors": None,
        },
        "access": {
            "()": "uvicorn.logging.AccessFormatter",
            "fmt": '%(asctime)s %(levelprefix)s %(client_addr)s - "%(request_line)s" %(status_code)s',  # noqa: E501
        },
    },
    "handlers": {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
        "access": {
            "formatter": "access",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
    },
    "loggers": {
        "uvicorn": {"handlers": ["default"], "level": "INFO", "propagate": False},
        "uvicorn.error": {"level": "INFO"},
        "uvicorn.access": {"handlers": ["access"], "level": "INFO", "propagate": False},
    },
}
