import requests
from .utils.const import ROUTE, ROUTE_STOP, STOP, STOP_DETAIL 
from .utils.schema import Route, RouteStop, Stop, Response
from TM1py import TM1Service
from TM1py.Objects import Element
import logging 

logger = logging.getLogger(__name__)


def get_route():
    logger.info("Fetching route data from API...")
    try:
        response = requests.get(ROUTE)
        response.raise_for_status()
        logger.info("Successfully retrieved route data")
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch route data: {str(e)}")
        raise

def get_route_stop():
    logger.info("Fetching route stop data from API...")
    try:
        response = requests.get(ROUTE_STOP)
        response.raise_for_status()
        logger.info("Successfully retrieved route stop data")
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch route stop data: {str(e)}")
        raise

def get_stop_list():
    logger.info("Fetching stop list data from API...")
    try:
        response = requests.get(STOP)
        response.raise_for_status()
        logger.info("Successfully retrieved stop list data")
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch stop list data: {str(e)}")
        raise

def get_stop(stop_id): 
    logger.info(f"Fetching details for stop ID: {stop_id}")
    try:
        response = requests.get(STOP_DETAIL.format(stop_id=stop_id))
        response.raise_for_status()
        logger.info(f"Successfully retrieved details for stop ID: {stop_id}")
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch details for stop ID {stop_id}: {str(e)}")
        raise

def parse_response(response: dict, data_object): 
    logger.debug(f"Parsing response into {data_object.__name__} objects")
    try:
        result = [data_object(**item) for item in Response(**response).data]
        logger.debug(f"Successfully parsed {len(result)} {data_object.__name__} objects")
        return result
    except Exception as e:
        logger.error(f"Error parsing response into {data_object.__name__} objects: {str(e)}")
        raise
    
def sync_route(tm1: TM1Service, routes: list[Route]): 
    """
    Sync route to TM1
    """
    logger.info(f"Starting sync of {len(routes)} routes to TM1")
    dimension_name = 'KMB Route'
    hierarchy_name = 'KMB Route'
    
    logger.debug(f"Fetching existing elements from {dimension_name}")
    exists_element = tm1.elements.get_all_element_identifiers(dimension_name, hierarchy_name)
    
    elements = [route.tm1_element for route in routes if route.tm1_element_name not in exists_element]
    consolidated_elements = set([route.parent_element for route in routes if route.route not in exists_element])
    
    if elements or consolidated_elements:
        logger.info(f"Adding {len(elements)} new route elements and {len(consolidated_elements)} consolidated elements")
        tm1.elements.add_elements(dimension_name, hierarchy_name, elements + list(consolidated_elements))
    else:
        logger.info("No new elements to add")
    
    logger.debug("Deleting existing edges for rebuilding hierarchy")
    tm1.elements.delete_edges(dimension_name, hierarchy_name, tm1.elements.get_edges(dimension_name, hierarchy_name))
    
    edges = {}        
    cellset_values = {}
    for route in routes: 
        edges.update(route.tm1_edges)
        cellset_values.update(route.attributes)
    
    logger.info(f"Adding {len(edges)} edges to hierarchy")
    tm1.elements.add_edges(dimension_name, hierarchy_name, edges)
    
    logger.info(f"Writing {len(cellset_values)} attribute values")
    tm1.cells.write_values('}}ElementAttributes_{}'.format(dimension_name), cellset_values)
    logger.info("Route sync completed successfully")
    
def sync_general_route(tm1: TM1Service):
    logger.info("Starting sync of general route data to TM1")
    
    logger.debug("Fetching route attributes from KMB Route dimension")
    route = set(tm1.elements.get_attribute_of_elements('KMB Route', 'KMB Route', 'Route').values())
    
    logger.debug("Fetching existing elements from Bus Route dimension")
    bus_route = tm1.elements.get_all_element_identifiers('Bus Route', 'Bus Route')
    
    new_routes = [ele for ele in route if ele not in bus_route]
    if new_routes:
        logger.info(f"Adding {len(new_routes)} new routes to Bus Route dimension")
        tm1.elements.add_elements('Bus Route', 'Bus Route', [Element(ele, Element.Types.NUMERIC) for ele in new_routes])
    else:
        logger.info("No new routes to add to Bus Route dimension")
    
    logger.info("General route sync completed successfully")

def sync_stop(tm1: TM1Service, stops: list[Stop]): 
    """
    Sync stop to TM1
    """
    logger.info(f"Starting sync of {len(stops)} stops to TM1")
    dimension_name = 'KMB Stop'
    hierarchy_name = 'KMB Stop'
    
    logger.debug(f"Fetching existing elements from {dimension_name}")
    exists_element = tm1.elements.get_all_element_identifiers(dimension_name, hierarchy_name)
    
    elements = [stop.tm1_element for stop in stops if stop.stop not in exists_element]
    if elements:
        logger.info(f"Adding {len(elements)} new stop elements")
        tm1.elements.add_elements(dimension_name, hierarchy_name, elements)
    else:
        logger.info("No new stop elements to add")
    
    logger.debug("Deleting existing edges for rebuilding hierarchy")
    tm1.elements.delete_edges(dimension_name, hierarchy_name, tm1.elements.get_edges(dimension_name, hierarchy_name))
    
    cellset_values = {}
    for stop in stops: 
        cellset_values.update(stop.attributes)
    
    logger.info(f"Writing {len(cellset_values)} attribute values")
    tm1.cells.write_values('}}ElementAttributes_{}'.format(dimension_name), cellset_values)
    logger.info("Stop sync completed successfully")
    
    logger.debug("Deleting existing edges for rebuilding hierarchy")
    tm1.elements.delete_edges(dimension_name, hierarchy_name, tm1.elements.get_edges(dimension_name, hierarchy_name))
    
    edges = {}        
    cellset_values = {}
    for stop in stops: 
        edges.update({('All Stops', stop.stop): 1})
    
    logger.info(f"Adding {len(edges)} edges to hierarchy")
    tm1.elements.add_edges(dimension_name, hierarchy_name, edges)
    
    
def sync_route_stop(tm1: TM1Service, route_stops: list[RouteStop]): 
    """
    Sync route stop to TM1
    """
    logger.info(f"Starting sync of {len(route_stops)} route stops to TM1")
    cube_name = 'Bus ETA'
    
    logger.debug("Fetching existing stops from KMB Stop dimension")
    exists_stops = tm1.elements.get_all_element_identifiers('KMB Stop', 'KMB Stop')
    
    logger.debug("Fetching existing routes from Bus Route dimension")
    exists_route = tm1.elements.get_all_element_identifiers('Bus Route', 'Bus Route')
    
    missing_stops = {}
    cellset = {}
    processed_count = 0
    skipped_count = 0
    
    logger.debug("Processing route stops")
    for route_stop in route_stops:
        if route_stop.stop not in exists_stops:
            missing_stops.update(route_stop.tm1_cellvalue)
            skipped_count += 1
            continue  
        if route_stop.route not in exists_route:
            missing_stops.update(route_stop.tm1_cellvalue)
            skipped_count += 1
            continue
        cellset.update(route_stop.tm1_cellvalue)
        processed_count += 1
    
    logger.info(f"Processed {processed_count} route stops, skipped {skipped_count} due to missing references")
    
    logger.debug(f"Clearing existing data in {cube_name} cube (Sequence measure)")
    tm1.cubes.cells.clear(cube_name, mbuseta='Sequence')
    
    logger.info(f"Writing {len(cellset)} cell values to {cube_name} cube")
    tm1.cubes.cells.write_values(cube_name, cellset)
    
    if missing_stops:
        logger.warning(f'Missing stops: {len(missing_stops)} entries')
        logger.debug(f'Missing stops detail: {missing_stops}')
    
    logger.info("Route stop sync completed successfully")
