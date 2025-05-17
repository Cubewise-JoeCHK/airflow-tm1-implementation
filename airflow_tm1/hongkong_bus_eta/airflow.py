from airflow.sdk import task, Metadata, asset, AssetAlias

from airflow_tm1.hongkong_bus_eta.utils.schema import TimeTable
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
    
@asset(uri='file://tmp/timetable', schedule=None, tags=['OpenData', 'HongKong', 'Bus'], dag_display_name='Data.Gov.HK KMB Bus Timetable DataSource')
def asset_timetable(self, conn_id: str = 'cubewise-hk'):
    with TM1Hook(conn_id).get_conn() as tm1:
        data = timetable.retrieve_timetable_list(tm1)
        attr = tm1.elements.get_attribute_of_elements('Bus Bound', 'Bus Bound', 'KMB')
    extra = []
    for row in data.split('\r\n'):
        if row.startswith('Bus Route'):
            continue
        route, bound = row.split(',')[:2]
        data = timetable.get_timetable(route=route, bound=attr.get(bound))['data']
        dataset = [{'service_type': service_type, 'bound': bound, 'route': route, 'data': [d for d in data]} for service_type, data in data.items()]
        if not dataset:
            continue
        extra += dataset
    yield Metadata(self, {'data': extra})

            
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

@task(inlets=[asset_timetable])
def load_timetable(conn_id: str, *, triggering_asset_events=None): 
    with TM1Hook(conn_id).get_conn() as tm1: 
        for event in triggering_asset_events[asset_timetable]:
            dataset = event.extra 
            service_type = dataset['service_type']
            bound = dataset['bound']
            route = dataset['route']
            timetable_data = [TimeTable(**d, service_type=service_type, bound=bound) for d in dataset['data']]
            timetable.sync_timetable(tm1, timetable_data, route=route, bound=bound, service_type=service_type)
                

@task(outlets=[bus_data])
def retrieve_timetable(conn_id: str, outlet_events=None, **context, ): 
    with TM1Hook(conn_id).get_conn() as tm1:
        data = timetable.retrieve_timetable_list(tm1)
        attr = tm1.elements.get_attribute_of_elements('Bus Bound', 'Bus Bound', 'KMB')
    return [tuple(row.split(',')[:2]) for row in data.split('\r\n') if not row.startswith('Bus Route') and len(row.split(',')) > 2]
    for row in data.split('\r\n'):
        if row.startswith('Bus Route'):
            continue
        route, bound = row.split(',')[:2]
        data = timetable.get_timetable(route=route, bound=attr.get(bound))['data']
        dataset = [{'service_type': service_type, 'bound': bound, 'route': route, 'data': [d for d in data]} for service_type, data in data.items()] 
        outlet_events[bus_data].add(asset_timetable, extra=dataset)
