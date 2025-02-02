from configparser import ConfigParser


class Config:
    _config: ConfigParser
    _default_instance: str

    def load_config_from_airflow(self):
        from airflow.models import Variable

        self._config = self.__load_config(Variable.get("config-ini", ""))
        self.default_instance = self._config["env"]["default-instance"]
        return self._config

    def load_config_from_file(self, path):
        self._config = self.__load_config(path)
        self.default_instance = self._config["env"]["default-instance"]
        return self._config

    @staticmethod
    def __load_config(path):
        config = ConfigParser()
        config.read(path)
        return config

    def get_tm1_instance_config(self, instance_name):
        if instance_name:
            if instance_name not in self._config.sections():
                raise ValueError(f"Instance {instance_name} not found in config")
        else:
            instance_name = self.default_instance

        return dict(self._config[instance_name])

    @property
    def airflow(self):
        return self._config["airflow"]

    @property
    def default_instance(self) -> str:
        return self._default_instance

    @default_instance.setter
    def default_instance(self, instance_name: str):
        if instance_name:
            assert (
                instance_name in self._config.sections()
            ), f"Instance {instance_name} not found in config"
            self._default_instance = instance_name
        else:
            self._default_instance = self._config["env"]["default-instance"]


ProjectConfig = Config()
