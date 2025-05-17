# [START import]
from airflow.sdk import dag 
import pendulum 
from airflow_tm1.hongkong_bus_eta.airflow import asset_route, asset_route_stop, asset_stop, asset_timetable

    
@dag(dag_id='load_hongkong_bus_data', schedule=[asset_route & asset_route_stop & asset_stop], catchup=False, tags=['OpenData', 'HongKong', 'Bus'], dag_display_name='Load KMB Bus Data Source to TM1')
def load_hongkong_bus_data():
    from airflow_tm1.hongkong_bus_eta.airflow import load_route, load_route_stop, load_stop, retrieve_timetable
    
    route = load_route(conn_id='cubewise-hk')
    route_stop = load_route_stop(conn_id='cubewise-hk') 
    timetable = retrieve_timetable(conn_id='cubewise-hk')
    stop = load_stop(conn_id='cubewise-hk')
    [route, stop] >> route_stop >> timetable

@dag(dag_id='load_hongkong_bus_timetable', schedule=[asset_timetable], catchup=False, tags=['OpenData', 'HongKong', 'Bus'], dag_display_name='Load KMB Bus Timetable to TM1')
def load_hongkong_bus_timetable():
    from airflow_tm1.hongkong_bus_eta.airflow import load_timetable
    load_timetable(conn_id='cubewise-hk')

load_hongkong_bus_data()
load_hongkong_bus_timetable()

# [END]
