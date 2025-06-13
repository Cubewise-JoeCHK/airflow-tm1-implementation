from airflow.sdk import task, Asset
import requests 
import pandas as pd

from airflow_tm1.utils.tm1_blob_service import BlobService 

DATA_URL = 'https://data.etabus.gov.hk/v1/transport/kmb/stop'

stop_asset = Asset(uri='tm1://cubewise-hk/stop.csv')

@task(task_id='get-stop-lists', outlets=[stop_asset])
def get_source_data(): 
    from airflow_tm1.utils.tm1_blob_service import BlobService
    response = requests.get(DATA_URL)
    response.raise_for_status()
    blob_service = BlobService.from_uri(stop_asset.uri)
    df = pd.DataFrame(response.json()['data'])
    blob_service.upload_dataframe(df)

@task(task_id='run-stop-update-process', inlets=[stop_asset])
def run_update_process():
    from airflow_provider_tm1.hooks.tm1 import TM1Hook
    blob_service = BlobService.from_uri(stop_asset.uri)
    assert blob_service.exists(), "Blob file does not exist. Please ensure the file is uploaded before running the process."
    
    with TM1Hook(blob_service.conn_id).get_conn() as tm1:
        assert tm1.processes.exists('dim.stop.update'), "Process 'dim.stop.update' does not exist in TM1."
        assert tm1.processes.execute_with_return('dim.stop.update', pfile=blob_service.tm1_file_name)[0]
        
    return blob_service.uri
