
from pydantic import BaseModel, field_validator, Field, ConfigDict
from TM1py.Objects import Element
from TM1py.Utils.Utils import get_tm1_time_value_now
import datetime as dt 
import re

from airflow_tm1.utils.tm1 import datetime_to_tm1_timestamp 


class Response(BaseModel):
    type: str 
    version: str 
    generated_timestamp: str 
    data: list[dict]
    
class Route(BaseModel):
    route: str
    bound: str
    service_type: str 
    orig_en: str 
    orig_tc: str
    orig_sc: str 
    dest_en: str
    dest_tc: str
    dest_sc: str

    @field_validator('bound')
    def validate_bound(cls, v):
        if v not in ['I', 'O']:
            raise ValueError('bound must be I or O')
        return v
    
    @property 
    def tm1_element_name(self): 
        return '{} {} {}'.format(self.route, self.bound, self.service_type)
    
    @property 
    def tm1_element(self): 
         return Element(name=self.tm1_element_name, element_type=Element.Types.NUMERIC)
     
    @property 
    def parent_element(self): 
        return Element(name=self.route, element_type=Element.Types.CONSOLIDATED)
     
    @property
    def tm1_edges(self): 
        return {(self.route, self.tm1_element_name): 1}
     
    @property 
    def attributes(self): 
        return {(self.tm1_element_name, 'Origin'): self.orig_tc,
                (self.tm1_element_name, 'Destination'): self.dest_tc,
                (self.tm1_element_name, 'Route'): self.route,
                (self.tm1_element_name, 'update at'): get_tm1_time_value_now()
                }
        

class Stop(BaseModel):
    stop: str
    name_en: str
    name_tc: str
    name_sc: str
    lat: float
    long: float
    
    @property 
    def tm1_element(self): 
        return Element(name=self.stop, element_type=Element.Types.NUMERIC)
    
    @property
    def attributes(self): 
        return {(self.stop, 'Name'): self.name_tc,
                (self.stop, 'Latitude'): self.lat,
                (self.stop, 'Longitude'): self.long,
                (self.stop, 'update at'): get_tm1_time_value_now()
                }
    

class RouteStop(BaseModel):
    route: str
    bound: str 
    service_type: str 
    stop: str
    seq: int

    @property 
    def tm1_cellvalue(self): 
        return {(self.route, self.bound, self.service_type, self.stop, 'Sequence'): self.seq}

class TimeTable(BaseModel):
    model_config = ConfigDict(populate_by_name=True) 
    bound: str 
    # service_type : str 
    day_type: str = Field(alias='DayType')
    bound_time_1: str = Field(alias='BoundTime1')
    service_type_eng: str = Field(alias='ServiceType_Eng')
    bound_text_1: str = Field(alias='BoundText1')
    origin_eng: str = Field(alias='Origin_Eng')
    service_type: str = Field(alias='ServiceType')
    destination_chi: str = Field(alias='Destination_Chi')
    order_seq: int = Field(alias='OrderSeq')
    route: str = Field(alias='Route')
    destination_eng: str = Field(alias='Destination_Eng')
    bound_time_2: str = Field(alias='BoundTime2')
    origin_chi: str = Field(alias='Origin_Chi')
    bound_text_2: str = Field(alias='BoundText2')
    service_type_chi: str = Field(alias='ServiceType_Chi')
    
    def generate_5_mins_sessions(self): 
        """
        Generate 5-minute intervals for the timetable.
        """
        bound_text = self.bound_text_1 or self.bound_text_2
        clock_pattern = r'\d{2}:\d{2}'
        start_end = bound_text.split('-')
        start_time = start_end[0].replace('*', '').strip()
        if not re.match(clock_pattern, start_time):
            yield '00', '00', 'not available'
            return 
        start_hour = int(re.match(clock_pattern, start_time).group(0)[:2])
        start_minute = int(re.match(clock_pattern, start_time).group(0)[3:])

        start_time = dt.datetime.combine(dt.date.today(), dt.time(start_hour, start_minute))

        if len(start_end) == 1:
            yield  str(start_time.hour).zfill(2), str(start_time.minute).zfill(2), self.bound_time_1 or self.bound_time_2
            return 
        
        end_time = start_end[1].strip()
        if not re.match(clock_pattern, end_time):
            # raise ValueError(f"Invalid end time format: {end_time} {bound_text}")
            yield '00', '00', 'not available'
            return 
        end_hour = int(re.match(clock_pattern, end_time).group(0)[:2])
        end_minute = int(re.match(clock_pattern, end_time).group(0)[3:])
        end_time = dt.datetime.combine(dt.date.today(), dt.time(end_hour if end_hour != 24 else 0, end_minute))
        while start_time <= end_time:
            yield str(start_time.hour).zfill(2), str(start_time.minute).zfill(2), self.bound_time_1 or self.bound_time_2
            start_time += dt.timedelta(minutes=5)
    
    @property 
    def tm1_cellvalue(self): 
        return {(self.route.strip(), self.bound.strip(), self.service_type.strip(), hour, minutes, self.day_type.strip()): bound_time.strip() for hour, minutes, bound_time in self.generate_5_mins_sessions()}
    
    def to_dict(self): 
        """
        Convert the object to a dictionary.
        """
        return {
            'bound': self.bound,
            'service_type': self.service_type,
            'day_type': self.day_type,
            'bound_time_1': self.bound_time_1,
            'service_type_eng': self.service_type_eng,
            'bound_text_1': self.bound_text_1,
            'origin_eng': self.origin_eng,
            'service_type': self.service_type,
            'destination_chi': self.destination_chi,
            'order_seq': self.order_seq,
            'route': self.route,
            'destination_eng': self.destination_eng,
            'bound_time_2': self.bound_time_2,
            'origin_chi': self.origin_chi,
            'bound_text_2': self.bound_text_2,
            'service_type_chi': self.service_type_chi
        }
        

class TM1Cube_BusETA(BaseModel): 
    model_config = ConfigDict(populate_by_name=True) 
    
    route: str
    bound: str
    measure: str

    @classmethod
    def parse_from_cellset(cls, cellset: str) -> 'TM1Cube_BusETA':
        """
        Parse a cellset string and return an instance of TM1Cube_BusETA.
        """
        data = cellset.replace('"', '').split(',')
        assert len(data) == 3, "Cellset must contain exactly 3 elements {}".format(data)
        return cls(
            route=data[0],
            bound=data[1],
            measure=data[2]
        )
        
    @classmethod
    def from_dict(cls, data: dict) -> 'TM1Cube_BusETA':
        """
        Create an instance of TM1Cube_BusETA from a dictionary.
        """
        assert 'route' in data, "Missing 'route' in data"
        assert 'bound' in data, "Missing 'bound' in data"
        assert 'measure' in data, "Missing 'measure' in data"
        return cls(
            route=data['route'],
            bound=data['bound'],
            measure=data['measure']
        )
        
    def to_dict(self) -> dict:
        """
        Convert the object to a dictionary.
        """
        return {
            'route': self.route,
            'bound': self.bound,
            'measure': self.measure
        }

class TM1Cube_BusSchedule(BaseModel): 
    model_config = ConfigDict(populate_by_name=True) 
    
    route: str
    service_type: str 
    measure: str
        
    @classmethod
    def parse_from_cellset(cls, cellset: str) -> 'TM1Cube_BusSchedule':
        """
        Parse a cellset string and return an instance of TM1Cube_BusSchedule.
        """
        data = cellset.replace('"', '').split(',')
        assert len(data) == 3, "Cellset must contain exactly 3 elements {}".format(data)
        return cls(
            route=data[0],
            service_type=data[1],
            measure=data[2]
        )
        
    @classmethod
    def from_dict(cls, data: dict) -> 'TM1Cube_BusSchedule':
        """
        Create an instance of TM1Cube_BusSchedule from a dictionary.
        """
        assert 'route' in data, "Missing 'route' in data"
        assert 'service_type' in data, "Missing 'service_type' in data"
        assert 'measure' in data, "Missing 'measure' in data"
        return cls(
            route=data['route'],
            service_type=data['service_type'],
            measure=data['measure']
        )
        
    def to_dict(self) -> dict:
        """
        Convert the object to a dictionary.
        """
        return {
            'route': self.route,
            'service_type': self.service_type,
            'measure': self.measure
        }
        
class TM1Cube_BusStopSequence(BaseModel):
    model_config = ConfigDict(populate_by_name=True) 
    
    bound: str 
    stop: str 
    seq: int
    
    @classmethod
    def parse_from_cellset(cls, cellset: str) -> 'TM1Cube_BusStopSequence':
        """
        Create an instance of TM1Cube_BusStopSequence from a dictionary.
        """
        data = cellset.replace('"', '').split(',')
        assert len(data) == 3, "Cellset must contain exactly 3 elements {}".format(data)
        return cls(
            bound=data[0],
            stop=data[1],
            seq=int(data[2])
        )
        
    def to_dict(self) -> dict:
        """
        Convert the object to a dictionary.
        """
        return {
            'bound': self.bound,
            'stop': self.stop,
            'seq': self.seq
        }
    
    @classmethod 
    def from_dict(cls, data: dict) -> 'TM1Cube_BusStopSequence':
        """
        Create an instance of TM1Cube_BusStopSequence from a dictionary.
        """
        assert 'bound' in data, "Missing 'bound' in data"
        assert 'stop' in data, "Missing 'stop' in data"
        assert 'seq' in data, "Missing 'seq' in data"
        return cls(
            bound=data['bound'],
            stop=data['stop'],
            seq=data['seq']
        )
        

class ETA(BaseModel): 
    route: str
    bound: str
    service_type: str 
    seq: int
    eta_seq: int
    eta: dt.datetime | None
    dest_tc: str 
    dest_sc: str 
    dest_en: str 
    rmk_tc: str 
    rmk_sc: str 
    rmk_en: str 
    data_timestamp: dt.datetime | None
    stop: str = Field(default='')
    
    @classmethod 
    def from_response(cls, data: dict) -> 'ETA':
        return cls(
            route=data['route'],
            bound=data['dir'],
            service_type=str(data['service_type']),
            seq=data['seq'],
            eta_seq=data['eta_seq'],
            eta=dt.datetime.fromisoformat(data['eta']) if data['eta'] else None,
            dest_tc=data['dest_tc'],
            dest_sc=data['dest_sc'],
            dest_en=data['dest_en'],
            rmk_tc=data['rmk_tc'],
            rmk_sc=data['rmk_sc'],
            rmk_en=data['rmk_en'],
            data_timestamp=dt.datetime.fromisoformat(data['data_timestamp']) if data['data_timestamp'] else None
        )

    @property 
    def tm1_cellset(self): 
        return {(self.route, self.bound, self.service_type, self.stop, f'ETA Timeslot {self.eta_seq}'): datetime_to_tm1_timestamp(self.eta)}
