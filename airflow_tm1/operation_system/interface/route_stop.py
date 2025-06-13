from airflow.sdk import Asset, task
import requests 

DATA_URL = 'https://data.etabus.gov.hk/v1/transport/kmb/route-stop'
BLOB_URI = 'tm1://cubewise-hk/route-stop.csv'

route_stop_asset = Asset('tm1://cubewise-hk/route-stop.csv')

@task(task_id='get-route-stop-lists', outlets=[route_stop_asset])
def get_source_data():
    import pandas as pd  
    from airflow_tm1.utils.tm1_blob_service import BlobService
    response = requests.get(DATA_URL)
    response.raise_for_status()
    blob_service = BlobService.from_uri(route_stop_asset.uri)
    df = pd.DataFrame(response.json()['data'])
    blob_service.upload_dataframe(df)
    
@task(task_id='run-route-stop-update-process', inlets=[route_stop_asset])
def run_update_process():
    from airflow_tm1.utils.tm1_blob_service import BlobService
    from airflow_provider_tm1.hooks.tm1 import TM1Hook
    blob_service = BlobService.from_uri(route_stop_asset.uri)
    assert blob_service.exists(), "Blob file does not exist. Please ensure the file is uploaded before running the process."
    
    with TM1Hook(blob_service.conn_id).get_conn() as tm1:
        assert tm1.processes.exists('dim.route stop sequence.update'), "Process 'dim.route.stop.sequence.update' does not exist in TM1."
        assert tm1.processes.execute_with_return('dim.route stop sequence.update', pfile=blob_service.tm1_file_name)[0]

    return blob_service.uri
