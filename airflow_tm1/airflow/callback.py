import json
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
from TM1py.Objects import Element

from airflow.models import Variable
from airflow_tm1.utils.config import Config
from airflow_tm1.utils.tm1 import connect_to_tm1

config = Config.load_config_from_airflow()

template_log_variables = "{dag_id}-log"


def callback(context, instance_name="demo"):
    airflow_task = context["dag"].dag_id

    payload = {
        "airflow task": airflow_task,
        "run at": context["data_interval_start"]
        .astimezone(ZoneInfo("Asia/Hong_Kong"))
        .strftime("%Y-%m-%d %H:%M:%S"),
        "run by": context["params"].get("run_by", "airflow automation"),
        "status": context["dag_run"].state,
        "duration": (
            datetime.now(ZoneInfo("Asia/Hong_Kong"))
            - context["data_interval_start"].astimezone(ZoneInfo("Asia/Hong_Kong"))
        ).total_seconds(),
        "parameters": json.dumps(context["params"]),
        "error": str(context.get("exception", "")),
    }

    send_records_to_log_cube(airflow_task, update_callback_log(airflow_task, payload))


def update_callback_log(dag_id, payload: dict):
    airflow_task_log = template_log_variables.format(dag_id=dag_id)
    records: list[dict] = Variable.get(
        airflow_task_log, default_var=[], deserialize_json=True
    )
    records.insert(0, payload)
    Variable.set(
        airflow_task_log, records[: min(len(records), 21)], serialize_json=True
    )
    return records


def send_records_to_log_cube(airflow_task, records, instance_name="demo"):
    df = pd.DataFrame(records)
    df["Line Item"] = df.index.map(lambda x: str(x + 1).zfill(4))
    with connect_to_tm1(config[instance_name]) as tm1:
        if airflow_task not in tm1.elements.get_element_names(
            "Airflow Task", "Airflow Task"
        ):
            tm1.elements.create(
                "Airflow Task", "Airflow Task", Element(airflow_task, "String")
            )
        tm1.cells.write_dataframe(
            "Airflow Task Log",
            df.melt(
                id_vars=["airflow task", "Line Item"],
                value_vars=[
                    "run at",
                    "status",
                    "parameters",
                    "error",
                    "run by",
                    "duration",
                ],
                var_name="M Airflow Task Log",
                value_name="Value",
            ),
        )
