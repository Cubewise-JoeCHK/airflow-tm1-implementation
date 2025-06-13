from airflow.sdk import task
from airflow.sdk import Asset, Metadata
from airflow_tm1.utils.tm1_blob_service import BlobService, parse_uri, transfer_pandas_dataframe_to_blob 


effective_route_asset = Asset(uri='tm1://cubewise-hk/effective-route.csv')
eta_data_asset = Asset(uri='tm1://cubewise-hk/eta.*.csv',)
DATA_URL = 'https://data.etabus.gov.hk/v1/transport/kmb/route-eta/{route}/{service_type}'


@task(task_id='get-effective-route', outlets=[effective_route_asset])
def get_effective_route():
    from airflow_provider_tm1.hooks.tm1 import TM1Hook
    from TM1py.Objects import ViewAxisSelection, AnonymousSubset, ViewTitleSelection, NativeView
    from airflow_tm1.utils.tm1_blob_service import BlobService, upload
    import pandas as pd 
    import json

    hour = ViewTitleSelection(
        'Hour', AnonymousSubset(dimension_name='Hour', elements=['Current']), 'Current'
    )
    minute = ViewTitleSelection(
        'Minutes', AnonymousSubset(dimension_name='Minutes', elements=['Current']), 'Current'
    )
    stop = ViewTitleSelection(
        'Sequence', AnonymousSubset(dimension_name='Sequence', elements=['0000']), '0000'
    )
    measure = ViewTitleSelection(
        'M ETA', AnonymousSubset(dimension_name='M ETA', elements=['Effective']), 'Effective'
    )
    bound = ViewTitleSelection(
        'Bound', AnonymousSubset(dimension_name='Bound', elements=['All Bounds']), 'All Bounds'
    )

    route = ViewAxisSelection(
        'Route', AnonymousSubset(dimension_name='Route', expression="{{[Route].[All Routes].Children}}")
    )

    service = ViewAxisSelection(
        'Service', AnonymousSubset(dimension_name='Service', expression="{{[Service].[All Services].Children}}")
    )

    view = NativeView(
        cube_name='ETA',
        view_name='Effective Route',
        suppress_empty_columns=True,
        suppress_empty_rows=True,
        titles=[hour, minute, stop, measure, bound],
        rows=[route],
        columns=[service]
    )
    blob_service = BlobService.from_uri(effective_route_asset.uri)
    
    with TM1Hook('cubewise-hk').get_conn() as tm1:
        tm1.cubes.views.create(view)
        df: pd.DataFrame = tm1.cells.execute_view_dataframe(view.cube, view.name, use_blob=True)
        tm1.cubes.views.delete(view.cube, view.name)
        upload(tm1, blob_service.tm1_file_name, transfer_pandas_dataframe_to_blob(df))

@task(task_id='get-eta-data', inlets=[effective_route_asset], outlets=[eta_data_asset])
def get_eta_data():
    from airflow_provider_tm1.hooks.tm1 import TM1Hook

    from airflow_tm1.utils.tm1_blob_service import BlobService, upload, transfer_pandas_dataframe_to_blob
    from airflow_tm1.utils.tm1 import datetime_to_tm1_timestamp
    import datetime as dt
    import pandas as pd
    import asyncio
    import aiohttp
    
    blob_service = BlobService.from_uri(effective_route_asset.uri)
    df: pd.DataFrame = blob_service.open_as_pandas_dataframe()
    df['url'] = df.apply(
        lambda row: DATA_URL.format(route=row['Route'], service_type=row['Service']), axis=1
    )
    async def fetch_url(session: aiohttp.ClientSession, url: str) -> dict:
        async with session.get(url) as response:
            assert response.status == 200, f"HTTP {response.status} for URL: {url}"
            result = await response.json()
            return result['data']

    async def fetch_all_urls(urls: list[str]) -> list[dict]:
        async with aiohttp.ClientSession() as session:
            tasks = [fetch_url(session, url) for url in urls]
            return await asyncio.gather(*tasks)

    results = asyncio.run(fetch_all_urls(df['url'].tolist()))
    with TM1Hook(blob_service.conn_id).get_conn() as tm1:
        extra = []
        for requests_result in results:
            df = pd.DataFrame(requests_result)
            result = df.loc[df['eta_seq'] == 1, ['route', 'dir', 'service_type', 'seq', 'eta']]
            result['eta'] = result.eta.apply(
                lambda x: datetime_to_tm1_timestamp(dt.datetime.fromisoformat(x)) if isinstance(x, str) else None
            )
            result.dropna(subset=['eta'], inplace=True)
            if result.empty:
                continue
            route = result['route'].iloc[0].strip()
            bound = result['dir'].iloc[0].strip()
            file_name = f'airflow.eta.{route}.{bound}.csv'
            upload(tm1, file_name, transfer_pandas_dataframe_to_blob(result))
            extra.append(file_name)
        yield Metadata(asset=eta_data_asset, extra={'files': extra})

    return extra

@task(task_id='commit-eta-data-to-tm1', inlets=[eta_data_asset])
def commit_eta_data_to_tm1(triggering_asset_events=None): 
    from airflow_provider_tm1.hooks.tm1 import TM1Hook
    from concurrent.futures import ThreadPoolExecutor
    conn_id, _ = parse_uri(eta_data_asset.uri)
    with TM1Hook(conn_id).get_conn() as tm1:
        for asset_event in triggering_asset_events[eta_data_asset]:
            with ThreadPoolExecutor(max_workers=10) as executor:
                for file in asset_event.extra.get('files', []):
                    
                    executor.submit(tm1.processes.execute, 'update.operation system.eta', pFile=file)
