from datetime import timedelta

default_args = {
    "owner": "Joe",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}
