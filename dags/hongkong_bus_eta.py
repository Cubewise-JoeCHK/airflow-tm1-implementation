# [START import]
from airflow.sdk import dag 
from airflow_tm1.hongkong_bus_eta.airflow import asset_route, asset_route_stop, asset_stop, asset_kmb_timetable
from airflow.providers.standard.operators.trigger_dagrun import TriggerDagRunOperator
    
@dag(dag_id='load_hongkong_bus_data', schedule=[asset_route & asset_route_stop & asset_stop], catchup=False, tags=['OpenData', 'HongKong', 'Bus'], dag_display_name='Load KMB Bus Data Source to TM1')
def load_hongkong_bus_data():
    from airflow_tm1.hongkong_bus_eta.airflow import load_route, load_route_stop, load_stop
    
    route = load_route(conn_id='cubewise-hk')
    route_stop = load_route_stop(conn_id='cubewise-hk') 
    stop = load_stop(conn_id='cubewise-hk')
    update_timetable = TriggerDagRunOperator(
        task_id='trigger-update-timetable-data', 
        trigger_dag_id='produce-timetable-data',
        wait_for_completion=False, 
        deferrable=False, 
        
    )
    [route, stop] >> route_stop >> update_timetable

@dag(dag_id='produce-timetable-data', schedule='@daily', catchup=False, tags=['OpenData', 'HongKong', 'Bus'], dag_display_name='Produce KMB Bus Timetable Data')
def get_timetable_data_dag():
    from airflow_tm1.hongkong_bus_eta.airflow import get_valid_route, get_timetable
    get_timetable.override(max_active_tis_per_dag=8).expand(bus_info=get_valid_route(conn_id='cubewise-hk'))
    
@dag(dag_id='update-timetable-data-to-tm1', schedule=[asset_kmb_timetable], catchup=False, tags=['OpenData', 'HongKong', 'Bus'], dag_display_name='Update KMB Bus Timetable Data to TM1')
def update_timetable_data_to_tm1(): 
    from airflow_tm1.hongkong_bus_eta.airflow import load_timetable_to_tm1
    load_timetable_to_tm1(conn_id='cubewise-hk')
    # [END]
    
@dag(dag_id='one-shot-update-kwb-data-to-tm1', schedule=None, catchup=False, tags=['OpenData', 'HongKong', 'Bus'], dag_display_name='One Shot Update KMB Bus Data to TM1')
def one_shot_update_kmb_data_to_tm1():
    route = TriggerDagRunOperator(
        task_id='trigger-load-route-data', 
        trigger_dag_id='asset_route',
        wait_for_completion=False, 
        deferrable=False, 
    )
    route_stop = TriggerDagRunOperator(
        task_id='trigger-load-route-stop-data', 
        trigger_dag_id='asset_route_stop',
        wait_for_completion=False, 
        deferrable=False, 
    )
    stop = TriggerDagRunOperator(
        task_id='trigger-load-stop-data', 
        trigger_dag_id='asset_stop',
        wait_for_completion=False, 
        deferrable=False, 
    )
    
    [route, stop] >> route_stop
    
load_hongkong_bus_data()
get_timetable_data_dag()
update_timetable_data_to_tm1()
one_shot_update_kmb_data_to_tm1()
# [END]
