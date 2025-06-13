from airflow.sdk import dag, task
from airflow_tm1.operation_system.interface import route, stop, route_stop, eta
from airflow_tm1.utils.tm1_blob_service import remove_tm1_blob_file
import datetime 

@dag(dag_id='update-operation-system-data-to-TM1',
     schedule='@daily',
     catchup=False,
     tags=['TM1', 'Operation System', 'Daily Update'],
     dag_display_name='Pull Data from Operation System',
     )
def daily_sync_dag():
    stop.get_source_data()
    route.get_source_data()
    route_stop.get_source_data()
    

@dag(dag_id='sync-operation-system-data-to-TM1',
     schedule=[stop.stop_asset, route.route_asset, route_stop.route_stop_asset],
     catchup=False,
     tags=['TM1', 'Operation System', 'Daily Sync'],
     dag_display_name='Sync Operation System Data to TM1',
     description='Sync Operation System Data to TM1',
     )
def sync_operation_system_data_to_tm1(): 
    
    stop_run = stop.run_update_process()
    route_run = route.run_update_process()
    route_stop_run = route_stop.run_update_process()
    clean_up_first_round = [remove_tm1_blob_file(stop.stop_asset.uri),
                                                  remove_tm1_blob_file(route.route_asset.uri),
                                                  remove_tm1_blob_file(route_stop.route_stop_asset.uri)]
    valid_route_list = route.get_valid_route_lists()
    [stop_run, route_run] >>  route_stop_run >> clean_up_first_round >> valid_route_list

@dag(dag_id='update-operation-system-schedule-data', schedule=[route.valid_route_asset] )
def update_operation_system_schedule_data():
    from airflow_tm1.operation_system.interface import timetable
    timetable_blob_files = timetable.get_timetable()
    timetable_blob_files >> timetable.commit_timetable_to_tm1(timetable_blob_files) >> [remove_tm1_blob_file(file_names=timetable_blob_files, conn_id='cubewise-hk'), remove_tm1_blob_file(asset_uri = route.valid_route_asset.uri)]

@dag(dag_id='automatic-eta-update', schedule=datetime.timedelta(seconds=30),)
def automatic_eta_update():
    from airflow_tm1.operation_system.interface import eta
    eta.get_effective_route() >> eta.get_eta_data()
    
@dag(dag_id='push-eta-data-to-tm1', schedule=[eta.eta_data_asset])
def push_eta_data_to_tm1():
    from airflow_tm1.operation_system.interface import eta
    eta.commit_eta_data_to_tm1()
    
daily_sync_dag()
sync_operation_system_data_to_tm1()
update_operation_system_schedule_data()
automatic_eta_update()
push_eta_data_to_tm1()
