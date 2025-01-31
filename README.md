# airflow-tm1-implementation
this is the TM1 airflow implementation example

## `airflow.cfg` Configuration
three critical configuration should be paid attention on before the airflow solution development
### DAGs Examples
```ini
# Whether to load the DAG examples that ship with Airflow. It's good to
# get started, but you probably want to set this to ``False`` in a production
# environment
#
# Variable: AIRFLOW__CORE__LOAD_EXAMPLES
#
load_examples = True
```
### DAGs Folder Location
```ini
# The folder where your airflow pipelines live, most likely a
# subfolder in a code repository. This path must be absolute.
#
# Variable: AIRFLOW__CORE__DAGS_FOLDER
#
dags_folder = /home/cubejoe/airflow/dags
```
### API Entrypoints
```ini
# Comma separated list of auth backends to authenticate users of the API. See
# `Security: API
# <https://airflow.apache.org/docs/apache-airflow/stable/security/api.html>`__ for possible values.
# ("airflow.api.auth.backend.default" allows all requests for historic reasons)
#
# Variable: AIRFLOW__API__AUTH_BACKENDS
#
auth_backends = airflow.api.auth.backend.session
```
