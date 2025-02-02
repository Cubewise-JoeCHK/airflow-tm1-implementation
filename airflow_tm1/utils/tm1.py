from TM1py import TM1Service

from airflow_tm1.utils.config import ProjectConfig


def connect_to_tm1(instance_name: str = ""):
    return TM1Service(**ProjectConfig.get_tm1_instance_config(instance_name))
