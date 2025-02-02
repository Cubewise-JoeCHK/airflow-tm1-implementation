import time
from argparse import ArgumentParser

import requests

from airflow_tm1.utils.config import ProjectConfig

args = ArgumentParser()
args.add_argument("--DAG", required=True)
args.add_argument("--run_by", required=True)
args.add_argument("--config", required=True)
args.add_argument("--instance", required=False, default="")
args.add_argument(
    "params", nargs="*", default=[], help="Extra parameters, format (key:value)"
)
args = args.parse_args()

ProjectConfig.load_config_from_file(args.config)
ProjectConfig.default_instance = args.instance

airflow_update_variable = "{base_url}/api/v1/variables/{variable_key}"
airflow_dags_run = "{base_url}/api/v1/dags/{DAG}/dagRuns"


session = requests.Session()
session.auth = (ProjectConfig.airflow["user"], ProjectConfig.airflow["password"])
response = session.request(
    "PATCH",
    airflow_update_variable.format(
        base_url=ProjectConfig.airflow["url"], variable_key="config-ini"
    ),
    json={"key": "config-ini", "description": "config-ini", "value": args.config},
)


response = session.request(
    "POST",
    airflow_dags_run.format(base_url=ProjectConfig.airflow["url"], DAG=args.DAG),
    json={"conf": {i.split(":")[0]: i.split(":")[1] for i in args.params}},
)

dag_id = response.json()["dag_id"]
dag_run_id = response.json()["dag_run_id"]

while True:
    response = session.request(
        "GET",
        f'{ProjectConfig.airflow["url"]}/api/v1/dags/{dag_id}/dagRuns/{dag_run_id}',
    )
    print(response.json())
    if response.json()["state"] in ["success", "failed", "terminated"]:
        break
    time.sleep(3)
