class DownloadConfig:
    parameters = {}

    @classmethod
    def set_parameter(cls, key, value):
        cls.parameters[key] = value

    @classmethod
    def get_parameter(cls, key):
        return cls.parameters.get(key, None)
