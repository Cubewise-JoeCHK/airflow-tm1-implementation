from airflow.decorators import task
from airflow_tm1.utils.config import Config
from airflow_tm1.utils.tm1 import connect_to_tm1

config = Config.load_config_from_airflow()


@task
def retrieve_static_task_object(**context):
    return ["A", "B", "C"]


@task
def print_Hello_World_with_object(obj, **context):
    print("Hello World with object: ", obj)


@task
def retrieve_tm1_task_object(**context):
    with connect_to_tm1(config["demo"]) as tm1:
        elements_df = tm1.elements.get_elements_dataframe(
            "Airflow Task Group",
            hierarchy_name="Airflow Task Group",
            skip_parents=True,
            skip_consolidations=True,
            skip_weights=True,
        )
    elements_df.set_index("Airflow Task Group", inplace=True)
    return elements_df.loc[elements_df["Activate"] == "1", "Activate"].index.to_list()
