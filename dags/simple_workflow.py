from airflow.decorators import dag
from airflow_tm1.airflow import default_args
from airflow_tm1.airflow.simple_task_sample import *


@dag(
    dag_id="simple-task-sample",
    schedule_interval=None,
    catchup=False,
    tags=["airflow implementation"],
    default_args=default_args,
)
def DAG_simple_task_sample():
    simple_task()
    simple_task_with_param(lower_case_name("Alice"))
    print_context()


DAG_simple_task_sample()
