from configparser import ConfigParser

from airflow.models import Variable


class Config:
    _config: ConfigParser

    @classmethod
    def load_config_from_airflow(cls):
        cls._config = cls.__load_config(Variable.get("config-ini", ""))
        return cls._config

    @classmethod
    def load_config_from_file(cls, path):
        cls._config = cls.__load_config(path)
        return cls._config

    @staticmethod
    def __load_config(path):
        config = ConfigParser()
        config.read(path)
        return config

    def get_tm1_instance_config(self, instance_name):
        return dict(self._config[instance_name])
