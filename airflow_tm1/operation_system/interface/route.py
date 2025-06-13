from airflow.sdk import Asset, task, dag
import requests

from airflow_tm1.utils.tm1_blob_service import BlobService, parse_uri, transfer_pandas_dataframe_to_blob 

DATA_URL = 'https://data.etabus.gov.hk/v1/transport/kmb/route/'

route_asset = Asset('tm1://cubewise-hk/route.csv')
valid_route_asset = Asset('tm1://cubewise-hk/valid-route.csv')

@task(task_id='get-route-lists', outlets=[route_asset])
def get_source_data(): 
    from airflow_tm1.utils.tm1_blob_service import BlobService
    import pandas as pd 
    response = requests.get(DATA_URL)
    response.raise_for_status()
    blob_service = BlobService.from_uri(route_asset.uri)
    df = pd.DataFrame(response.json()['data'])
    blob_service.upload_dataframe(df)

@task(task_id='run-route-update-process', inlets=[route_asset])
def run_update_process():
    from airflow_provider_tm1.hooks.tm1 import TM1Hook
    from airflow_tm1.utils.tm1_blob_service import BlobService
    blob_service = BlobService.from_uri(route_asset.uri)
    assert blob_service.exists(), "Blob file does not exist. Please ensure the file is uploaded before running the process."
    
    with TM1Hook(blob_service.conn_id).get_conn() as tm1:
        from TM1py import TM1Service
        assert tm1.processes.exists('dim.route.update'), "Process 'dim.route.update' does not exist in TM1."
        assert tm1.processes.execute_with_return('dim.route.update', pfile=blob_service.tm1_file_name)[0]
        
    return blob_service.uri

@task(task_id='get-schedule-data-from-tm1', outlets=[valid_route_asset])
def get_valid_route_lists():
    from airflow_provider_tm1.hooks.tm1 import TM1Hook
    from TM1py.Objects import ViewAxisSelection, AnonymousSubset, ViewTitleSelection, NativeView
    from airflow_tm1.utils.tm1_blob_service import BlobService, upload
    import pandas as pd 
    import json

    hour = ViewTitleSelection(
        'Hour', AnonymousSubset(dimension_name='Hour', elements=['No Hour']), 'No Hour'
    )
    minute = ViewTitleSelection(
        'Minutes', AnonymousSubset(dimension_name='Minutes', elements=['No Minute']), 'No Minute'
    )
    stop = ViewTitleSelection(
        'Sequence', AnonymousSubset(dimension_name='Sequence', elements=['0000']), '0000'
    )
    measure = ViewTitleSelection(
        'M ETA', AnonymousSubset(dimension_name='M ETA', elements=['Effective']), 'Effective'
    )
    service = ViewTitleSelection(
        'Service', AnonymousSubset(dimension_name='Service', elements=['All Services']), 'All Services'
    )

    route = ViewAxisSelection(
        'Route', AnonymousSubset(dimension_name='Route', expression="{{[Route].[All Routes].Children}}")
    )
    bound = ViewAxisSelection(
        'Bound', AnonymousSubset(dimension_name='Bound', elements=['I', 'O'], alias='Digit')
    )

    view = NativeView(
        cube_name='ETA',
        view_name='}tm1py.ETA',
        suppress_empty_columns=True,
        suppress_empty_rows=True,
        titles=[hour, minute, stop, measure, service],
        rows=[route],
        columns=[bound]
    )
    blob_service = BlobService.from_uri(valid_route_asset.uri)
    
    with TM1Hook('cubewise-hk').get_conn() as tm1:
        tm1.cubes.views.create(view)
        df: pd.DataFrame = tm1.cells.execute_view_dataframe(view.cube, view.name, use_blob=True)
        tm1.cubes.views.delete(view.cube, view.name)
        upload(tm1, blob_service.tm1_file_name,transfer_pandas_dataframe_to_blob(df))
