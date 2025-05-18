
from pydantic import BaseModel, field_validator, Field
from TM1py.Objects import Element
from TM1py.Utils.Utils import get_tm1_time_value_now
import datetime as dt 
import re 


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
"""
            {
                "DayType": "MF        ",
                "BoundTime1": "30",
                "ServiceType_Eng": "",
                "BoundText1": "05:40-06:10",
                "Origin_Eng": "CHOI WAN",
                "ServiceType": "01   ",
                "Destination_Chi": "紅磡站",
                "OrderSeq": "2",
                "Route": "21",
                "Destination_Eng": "HUNG HOM STATION",
                "BoundTime2": "25-30",
                "Origin_Chi": "彩雲",
                "BoundText2": "06:25-00:15",
                "ServiceType_Chi": ""
            },
"""   
class TimeTable(BaseModel): 
    bound: str 
    service_type : str 
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
        start_time = start_end[0]
        start_hour = int(re.match(clock_pattern, start_time).group(0)[:2])
        start_minute = int(re.match(clock_pattern, start_time).group(0)[3:])

        start_time = dt.datetime.combine(dt.date.today(), dt.time(start_hour, start_minute))

        if len(start_end) == 1:
            print(self.bound_text_1)
            return  
        time_slots = []
        
        end_time = start_end[1]
        end_hour = int(re.match(clock_pattern, end_time).group(0)[:2])
        end_minute = int(re.match(clock_pattern, end_time).group(0)[3:])
        end_time = dt.datetime.combine(dt.date.today(), dt.time(end_hour, end_minute))
        while start_time <= end_time:
            yield str(start_time.hour).zfill(2), str(start_time.minute).zfill(2), self.bound_time_1 or self.bound_time_2
            start_time += dt.timedelta(minutes=5)
    
    @property 
    def tm1_cellvalue(self): 
        return {(self.route.strip(), self.bound.strip(), self.service_type.strip(), hour, minutes, self.day_type.strip()): bound_time.strip() for hour, minutes, bound_time in self.generate_5_mins_sessions()}

class TM1Cube_BusETA(BaseModel): 
    route: str
    bound: str
    measure: str

    @classmethod
    def parse_from_cellset(cls, cellset: str) -> 'TM1Cube_BusETA':
        """
        Parse a cellset string and return an instance of TM1Cube_BusETA.
        """
        data = cellset.split(',')
        assert len(data) == 3, "Cellset must contain exactly 3 elements {}".format(data)
        return cls(
            route=data[0],
            bound=data[1],
            measure=data[2]
        )
