from airflow.decorators import dag
from airflow_tm1.airflow import default_args
from airflow_tm1.airflow.callback import callback
from airflow_tm1.airflow.dynamic_task_group_sample import *


@dag(
    dag_id="dynamic-task-gorup-static-list",
    schedule_interval=None,
    catchup=False,
    tags=["airflow implementation"],
    default_args=default_args,
    on_failure_callback=callback,
    on_success_callback=callback,
)
def DAG_static_list():
    print_Hello_World_with_object.expand(obj=retrieve_static_task_object())


DAG_static_list()


@dag(
    dag_id="dynamic-task-gorup-tm1-list",
    schedule_interval=None,
    catchup=False,
    tags=["airflow implementation"],
    default_args=default_args,
    on_failure_callback=callback,
    on_success_callback=callback,
)
def DAG_tm1_list():
    print_Hello_World_with_object.expand(obj=retrieve_tm1_task_object())


DAG_tm1_list()
