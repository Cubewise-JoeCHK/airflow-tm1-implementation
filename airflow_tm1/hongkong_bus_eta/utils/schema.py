from pydantic import BaseModel, field_validator
from TM1py.Objects import Element
from TM1py.Utils.Utils import get_tm1_time_value_now
import datetime as dt 

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
