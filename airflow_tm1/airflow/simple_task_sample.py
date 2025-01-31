from pprint import pprint as print

from airflow.decorators import task


@task
def simple_task(**context):
    print("Hello World!")


@task
def simple_task_with_param(name, **context):
    print(f"Hello {name}!")


@task
def simple_task_with_return(**context) -> str:
    return "Hello World!"


@task
def lower_case_name(name, **context) -> str:
    print(context)
    return name.lower()


@task
def print_context(**context):
    print(context)
    return "Context printed!"
