from datetime import timedelta

from airflow_tm1.utils.config import ProjectConfig

default_args = {
    "owner": "Joe",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

ProjectConfig.load_config_from_airflow()
