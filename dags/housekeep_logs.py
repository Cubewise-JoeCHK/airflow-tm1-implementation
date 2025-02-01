from datetime import datetime, timedelta

from airflow.models import DAG
from airflow.operators.bash import BashOperator
from airflow.utils.dates import days_ago

default_args = {
    "owner": "Airflow",
    "start_date": days_ago(1),  # Use days_ago to handle relative start dates
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
    "email_on_retry": False,
}

# Define the DAG
with DAG(
    dag_id="housekeep-logs",
    default_args=default_args,
    description="A DAG to clean scheduler logs older than 30 days",
    schedule_interval="@daily",
    catchup=False,
) as dag:
    server_path = "/home/cubejoe/airflow"
    # Define the BashOperator task to clean scheduler logs
    clean_scheduler_logs = BashOperator(
        task_id="clean_scheduler_logs",
        bash_command=f"""
        echo "Cleaning scheduler logs older than 7 days..."
        find {server_path}/logs/scheduler -type f -mtime +7 -print -delete
        """,
    )

    clean_dag_logs = BashOperator(
        task_id="clean_dag_logs",
        bash_command=f"""
        BASE_LOG_FOLDER="{server_path}/logs"
        MAX_LOG_AGE_IN_DAYS=30
        echo "Cleaning DAG logs in $BASE_LOG_FOLDER older than $MAX_LOG_AGE_IN_DAYS days..."
        find $BASE_LOG_FOLDER -type f -name '*.log' -mtime +$MAX_LOG_AGE_IN_DAYS -print -delete
        find $BASE_LOG_FOLDER -type d -empty -print -delete
        """,
    )

    # ask dependencies
    clean_dag_logs >> clean_scheduler_logs
