def builder(cls):
    class Builder:
        def __init__(self):
            self.instance = cls()

        def __getattr__(self, attr):
            def _builder_method(*args, **kwargs):
                setattr(self.instance, attr, *args, **kwargs)
                return self

            return _builder_method

        def build(self):
            return self.instance

    cls.Builder = Builder
    return cls
