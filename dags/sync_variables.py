import datetime

from airflow.decorators import dag
from airflow_tm1.airflow import default_args
from airflow_tm1.airflow.simple_task_sample import simple_task_with_param
from airflow_tm1.airflow.synchronize_variables import *


@dag(
    dag_id="synchronize-variables",
    schedule_interval=datetime.timedelta(seconds=30),
    start_date=datetime.datetime(2021, 1, 1),
    catchup=False,
    tags=["airflow implementation"],
    default_args=default_args,
)
def DAG_sync_variable_from_tm1():
    write_to_airflow_variable(retrieve_tm1_task_object())


DAG_sync_variable_from_tm1()

for element in Variable.get("task_list", deserialize_json=True):

    @dag(
        dag_id=f"dynamic-task-{element.replace(' ', '-')}",
        schedule_interval=None,
        catchup=False,
        tags=["airflow implementation"],
        default_args=default_args,
    )
    def DAG_dynamic_task():
        simple_task_with_param(element)

    DAG_dynamic_task()
