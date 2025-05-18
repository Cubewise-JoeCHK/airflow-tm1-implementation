from TM1py import TM1Service
import requests
from TM1py.Objects import ViewAxisSelection, AnonymousSubset, ViewTitleSelection, NativeView
from airflow_tm1.hongkong_bus_eta.utils.schema import TimeTable
from .utils.const import TIMETABLE
from .utils.schema import TM1Cube_BusETA
import logging 


logger = logging.getLogger(__name__)

def retrieve_timetable_list(tm1: TM1Service): 
    logger.info("Starting to retrieve timetable list from TM1")
    try:
        logger.info("Creating view title and axis selections")
        measure = ViewTitleSelection('M Bus ETA', AnonymousSubset(dimension_name='M Bus ETA', elements=['Sequence']), 'Sequence')
        stop = ViewTitleSelection('KMB Stop', AnonymousSubset(dimension_name='KMB Stop', elements=['All Stops']), 'All Stops')
        service=ViewTitleSelection('Bus Service', AnonymousSubset(dimension_name='Bus Service', elements=['All Service']), 'All Service')
        
        logger.info("Getting leaf element names for Bus Route")
        route = ViewAxisSelection('Bus Route', AnonymousSubset(dimension_name='Bus Route', elements=tm1.elements.get_leaf_element_names('Bus Route', 'Bus Route')))
        bound = ViewAxisSelection('Bus Bound', AnonymousSubset(dimension_name='Bus Bound', elements=['I', 'O'], alias='KMB'))
        
        logger.info("Creating native view for Bus ETA cube")
        view = NativeView(
            cube_name='Bus ETA', 
            view_name='Service', suppress_empty_columns=True, suppress_empty_rows=True, titles=[measure, stop, service], rows=[route],
            columns=[bound],)
        
        logger.info("Creating view in TM1")
        tm1.cubes.views.create(view)
        
        logger.info("Executing view to retrieve cellset data")
        cellset = tm1.cubes.cells.execute_view_csv('Bus ETA', 'Service', use_blob=True)
        
        logger.info("Cleaning up - deleting temporary view")
        tm1.cubes.views.delete('Bus ETA', 'Service')
        
        logger.info("Successfully retrieved timetable list")
        return [TM1Cube_BusETA.parse_from_cellset(cell) for cell in cellset.split('\r\n') if not cell.startswith('"Bus') and cell]
    except Exception as e:
        logger.error(f"Error retrieving timetable list: {str(e)}", exc_info=True)
        raise

def get_timetable(bus_info: TM1Cube_BusETA) -> list[TimeTable]:
    """
    Get the timetable for a specific route and bound.
    
    Args:
        route (str): The bus route number.
        bound (str): The bus bound (e.g., "I" for inbound, "O" for outbound).
    
    Returns:
        dict: The timetable data.
    """
    logger.info(f"Retrieving timetable for route={bus_info.route} and bound={bus_info.bound}")
    try:
        url = TIMETABLE.format(route=bus_info.route, bound=bus_info.bound)
        logger.info(f"Making HTTP request to {url}")
        response = requests.get(url)
        
        if response.status_code == 200:
            logger.info(f"Successfully retrieved timetable data for route={bus_info.route}, bound={bus_info.bound}")
            data = response.json()['data']
            concat_list = []
            for service_type, details in data.items():
                concat_list += [TimeTable(service_type=service_type, bound=bus_info.bound, **tb) for tb in details]
            return concat_list
        else:
            logger.error(f"Failed to fetch timetable data: HTTP {response.status_code}")
            response.raise_for_status()
            raise Exception(f"Failed to fetch timetable data: {response.status_code}")
    except Exception as e:
        logger.error(f"Error getting timetable for route={bus_info.route}, bound={bus_info.bound}: {str(e)}", exc_info=True)
        raise
    
def clear_timetable(tm1: TM1Service, bus_info: TM1Cube_BusETA):
    """
    Clear the timetable data for a specific route and bound.
    
    Args:
        route (str): The bus route number.
        bound (str): The bus bound (e.g., "I" for inbound, "O" for outbound).
    """
    logger.info(f"Clearing timetable for route={bus_info.route} and bound={bus_info.bound}")
    try:
        cube_name = 'Bus TimeTable'
        logger.info(f"Clearing existing data in cube '{cube_name}' for route={bus_info.route}, bound={bus_info.bound}")
        tm1.cubes.cells.clear(cube_name, route=f'{{[Route].[{bus_info.route}]}}', bound=f'{{[Bound].[{bus_info.bound}]}}', mbustimetable='EXCEPT({{[M Bus TimeTable].Members}}, {{[M Bus TimeTable].[Valid]}})')
        logger.info(f"Successfully cleared timetable data for route={bus_info.route}, bound={bus_info.bound}")
    except Exception as e:
        logger.error(f"Error clearing timetable for route={bus_info.route}, bound={bus_info.bound}: {str(e)}", exc_info=True)
        raise

def sync_timetable(tm1: TM1Service, timetable_data: list[TimeTable]):
    logger.info(f"Starting to sync timetable for route={route}, bound={bound}")
    try:
        cube_name = 'Bus TimeTable'
        logger.info(f"Clearing existing data in cube '{cube_name}' for route={route}, bound={bound}, service_type={service_type}")
        tm1.cubes.cells.clear(cube_name, route=f'{{[Route].[{route}]}}', bound=f'{{[Bound].[{bound}]}}', mbustimetable='Except({{[M Bus TimeTable].Members}}, {{[M Bus TimeTable].[Valid]}})')
        
        logger.info(f"Processing {len(timetable_data)} timetable entries")
        cellset = {}
        for i, timetable in enumerate(timetable_data):
            cellset.update(timetable.tm1_cellvalue)
            if (i + 1) % 1000 == 0:  # Log progress for large datasets
                logger.info(f"Processed {i + 1} of {len(timetable_data)} entries")
        
        logger.info(f"Writing {len(cellset)} cell values to cube '{cube_name}'")
        tm1.cubes.cells.write_values(cube_name, cellset)
        logger.info(f"Successfully synced timetable data for route={route}, bound={bound}")
    except Exception as e:
        logger.error(f"Error syncing timetable for route={route}, bound={bound}: {str(e)}", exc_info=True)
        raise
