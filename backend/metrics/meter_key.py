from service.config.config import config

namespace = config.namespace

class MeterKey:
    def __init__(self, path, method):
        self.path = path
        self.method = method
        self.namespace = namespace
        