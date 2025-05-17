from TM1py import TM1Service
import requests
from TM1py.Objects import ViewAxisSelection, AnonymousSubset, ViewTitleSelection, NativeView
from airflow_tm1.hongkong_bus_eta.utils.schema import TimeTable
from .utils.const import TIMETABLE
import logging 

logger = logging.getLogger(__name__)

def retrieve_timetable_list(tm1: TM1Service): 
    logger.info("Starting to retrieve timetable list from TM1")
    try:
        logger.info("Creating view title and axis selections")
        measure = ViewTitleSelection('M Bus ETA', AnonymousSubset(dimension_name='M Bus ETA', elements=['Sequence']), 'Sequence')
        stop = ViewTitleSelection('KMB Stop', AnonymousSubset(dimension_name='KMB Stop', elements=['All Stops']), 'All Stops')
        
        logger.info("Getting leaf element names for Bus Route")
        route = ViewAxisSelection('Bus Route', AnonymousSubset(dimension_name='Bus Route', elements=tm1.elements.get_leaf_element_names('Bus Route', 'Bus Route')))
        bound = ViewAxisSelection('Bus Bound', AnonymousSubset(dimension_name='Bus Bound', elements=['I', 'O'], alias='KMB'))
        
        logger.info("Getting leaf element names for Bus Service")
        service = ViewAxisSelection('Bus Service', AnonymousSubset(dimension_name='Bus Service', elements=tm1.elements.get_leaf_element_names('Bus Service', 'Bus Service')))
        
        logger.info("Creating native view for Bus ETA cube")
        view = NativeView(
            cube_name='Bus ETA', 
            view_name='Service', suppress_empty_columns=True, suppress_empty_rows=True, titles=[measure, stop], rows=[route, bound],
            columns=[service],)
        
        logger.info("Creating view in TM1")
        tm1.cubes.views.create(view)
        
        logger.info("Executing view to retrieve cellset data")
        cellset = tm1.cubes.cells.execute_view_csv('Bus ETA', 'Service')
        
        logger.info("Cleaning up - deleting temporary view")
        tm1.cubes.views.delete('Bus ETA', 'Service')
        
        logger.info("Successfully retrieved timetable list")
        return cellset
    except Exception as e:
        logger.error(f"Error retrieving timetable list: {str(e)}", exc_info=True)
        raise

def get_timetable(route: str, bound: str) -> dict:
    """
    Get the timetable for a specific route and bound.
    
    Args:
        route (str): The bus route number.
        bound (str): The bus bound (e.g., "I" for inbound, "O" for outbound).
    
    Returns:
        dict: The timetable data.
    """
    logger.info(f"Retrieving timetable for route={route} and bound={bound}")
    try:
        url = TIMETABLE.format(route=route, bound=bound)
        logger.info(f"Making HTTP request to {url}")
        response = requests.get(url)
        
        if response.status_code == 200:
            logger.info(f"Successfully retrieved timetable data for route={route}, bound={bound}")
            return response.json()
        else:
            logger.error(f"Failed to fetch timetable data: HTTP {response.status_code}")
            response.raise_for_status()
            raise Exception(f"Failed to fetch timetable data: {response.status_code}")
    except Exception as e:
        logger.error(f"Error getting timetable for route={route}, bound={bound}: {str(e)}", exc_info=True)
        raise

def sync_timetable(tm1: TM1Service, timetable_data: list[TimeTable], route: str, bound: str, service_type: str):
    logger.info(f"Starting to sync timetable for route={route}, bound={bound}")
    try:
        cube_name = 'Bus TimeTable'
        logger.info(f"Clearing existing data in cube '{cube_name}' for route={route}, bound={bound}, service_type={service_type}")
        tm1.cubes.cells.clear(cube_name, route=f'{{[Route].[{route}]}}', bound=f'{{[Bound].[{bound}]}}', 
                              service_type=f'{{[Service Type].[{service_type}]}}', mbustimetable='{[M Bus TimeTable].[Business Day], [M Bus TimeTable].[Holiday], [M Bus TimeTable].[Weekend]}')
        
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
