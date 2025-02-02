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


@dag(
    dag_id="simple-task-sample-second-method",
    schedule_interval=None,
    catchup=False,
    tags=["airflow implementation"],
    default_args=default_args,
)
def DAG_simple_task_sample_method_2():

    name = lower_case_name("Alice")
    simple_task()
    print_context()
    name >> simple_task_with_param(name)


DAG_simple_task_sample()
DAG_simple_task_sample_method_2()
