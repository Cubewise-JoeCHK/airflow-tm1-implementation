from airflow.sdk import task, Metadata, asset, AssetAlias, dag, Asset

from airflow_tm1.hongkong_bus_eta.utils.schema import TimeTable, TM1Cube_BusETA
from . import sync_db, timetable
from airflow_provider_tm1.hooks.tm1 import TM1Hook
from TM1py import TM1Service
import time 
import logging 

logger = logging.getLogger(__name__)

bus_data = AssetAlias('bus_data')

@asset(uri='file://tmp/route', schedule='@daily', tags=['OpenData', 'HongKong', 'Bus'], dag_display_name='Data.Gov.HK KMB Bus Route DataSource')
def asset_route(self): 
    yield Metadata(self, sync_db.get_route())
    
@asset(uri='file://tmp/route_stop', schedule='@daily', tags=['OpenData', 'HongKong', 'Bus'], dag_display_name='Data.Gov.HK KMB Bus Route Stop DataSource')
def asset_route_stop(self): 
    yield Metadata(self, sync_db.get_route_stop())
    
@asset(uri='file://tmp/stop', schedule='@daily', tags=['OpenData', 'HongKong', 'Bus'], dag_display_name='Data.Gov.HK KMB Bus Stop DataSource')
def asset_stop(self): 
    yield Metadata(self, sync_db.get_stop_list())
    
asset_kmb_timetable = Asset(name='TimeTable', uri='file://tmp/kmb_timetable')

            
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
def load_stop(conn_id: str, *, triggering_asset_events=None): 
    with TM1Hook(conn_id).get_conn() as tm1: 
        for event in triggering_asset_events[asset_stop]:
            sync_db.sync_stop(tm1, sync_db.parse_response(event.extra, sync_db.Stop))

@task
def get_valid_route(conn_id: str): 
    with TM1Hook(conn_id).get_conn() as tm1:
        data = timetable.retrieve_timetable_list(tm1)
    return [d.to_dict() for d in data]

@task(outlets=[asset_kmb_timetable])
def get_timetable(bus_info: dict, outlet_events=None, **context): 
    yield Metadata(asset_kmb_timetable, extra={'data': timetable.get_timetable(TM1Cube_BusETA.from_dict(bus_info))})
    
@task
def clear_timetable_cube(conn_id: str, bus_info: dict): 
    with TM1Hook(conn_id).get_conn() as tm1:
        timetable.clear_timetable(tm1, bus_info=TM1Cube_BusETA.from_dict(bus_info))

@task(inlets=[asset_kmb_timetable])
def load_timetable_to_tm1(conn_id: str, *, triggering_asset_events=None): 
    with TM1Hook(conn_id).get_conn() as tm1:
        for event in triggering_asset_events[asset_kmb_timetable]:
            timetable_list = [TimeTable(**d) for d in event.extra['data']]
            for timetable_data in timetable_list:
                timetable.update_timetable(tm1, timetable_data)
