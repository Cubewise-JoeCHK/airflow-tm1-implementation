from airflow.decorators import task
from airflow.models import Variable
from airflow_tm1.airflow.dynamic_task_group_sample import retrieve_tm1_task_object


@task
def write_to_airflow_variable(elements, **context):
    Variable.set("task_list", elements, serialize_json=True)
