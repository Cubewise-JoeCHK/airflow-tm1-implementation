from airflow.sdk import task, Metadata, asset
from . import sync_db
from airflow_provider_tm1.hooks.tm1 import TM1Hook
# from airflow_provider_tm1.hooks import TM1Hook

@asset(uri='file://tmp/route', schedule='@daily', tags=['OpenData', 'HongKong', 'Bus'], dag_display_name='Data.Gov.HK KMB Bus Route DataSource')
def asset_route(self): 
    yield Metadata(self, sync_db.get_route())
    
@asset(uri='file://tmp/route_stop', schedule='@daily', tags=['OpenData', 'HongKong', 'Bus'], dag_display_name='Data.Gov.HK KMB Bus Route Stop DataSource')
def asset_route_stop(self): 
    yield Metadata(self, sync_db.get_route_stop())
    
@asset(uri='file://tmp/stop', schedule='@daily', tags=['OpenData', 'HongKong', 'Bus'], dag_display_name='Data.Gov.HK KMB Bus Stop DataSource')
def asset_stop(self): 
    yield Metadata(self, sync_db.get_stop_list())

@task(inlets=[asset_route])
def load_route(conn_id: str, *, triggering_asset_events=None): 
    with TM1Hook(conn_id).get_conn() as tm1: 
        for event in triggering_asset_events[asset_route]:
            sync_db.sync_route(tm1, sync_db.parse_response(event.extra, sync_db.Route))

@task(inlets=[asset_route_stop])
def load_route_stop(conn_id: str, *, triggering_asset_events=None): 
    with TM1Hook(conn_id).get_conn() as tm1: 
        for event in triggering_asset_events[asset_route_stop]:
            sync_db.sync_route_stop(tm1, route_stops=sync_db.parse_response(event.extra, sync_db.RouteStop))
                
@task(inlets=[asset_stop])
def load_stop(conn_id: str, *, triggering_asset_events): 
    with TM1Hook(conn_id).get_conn() as tm1: 
        for event in triggering_asset_events[asset_stop]:
            sync_db.sync_stop(tm1, sync_db.parse_response(event.extra, sync_db.Stop))

