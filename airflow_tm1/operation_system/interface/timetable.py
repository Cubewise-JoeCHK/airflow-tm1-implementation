from airflow.sdk import Asset, Metadata
from .route import valid_route_asset
from airflow.sdk import task
DATA_URL = 'https://search.kmb.hk/KMBWebSite/Function/FunctionRequest.ashx?action=getschedule&route={route}&bound={bound}'
from pydantic import BaseModel, Field, ConfigDict
import pandas as pd
import datetime as dt
import re

timetable_asset = Asset(uri='tm1://cubewise-hk/timetable.*.csv')

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
        return [(self.route.strip(), self.bound.strip(), self.service_type.strip(), str(self.order_seq).strip(), hour, minutes, self.day_type.strip(), bound_time.strip())  for hour, minutes, bound_time in self.generate_5_mins_sessions()]

    def to_pandas(self):
        return pd.DataFrame(self.tm1_cellvalue, columns=[
            'Route', 'Bound', 'ServiceType', 'OrderSeq', 'Hour', 'Minutes', 'Measure', 'Value'])



@task(task_id='get-timetable', inlets=[valid_route_asset], outlets=[timetable_asset])
def get_timetable(): 
    from airflow_provider_tm1.hooks.tm1 import TM1Hook

    from airflow_tm1.utils.tm1_blob_service import BlobService, upload, transfer_pandas_dataframe_to_blob

    import pandas as pd
    import asyncio
    import aiohttp
    from airflow_tm1.operation_system.interface.route import valid_route_asset
    
    blob_service = BlobService.from_uri(valid_route_asset.uri)
    df: pd.DataFrame = blob_service.open_as_pandas_dataframe()
    df['url'] = df.apply(
        lambda row: DATA_URL.format(route=row['Route'], bound=row['Bound']), axis=1
    )
    async def fetch_url(session: aiohttp.ClientSession, url: str) -> dict:
        async with session.get(url) as response:
            assert response.status == 200, f"HTTP {response.status} for URL: {url}"
            result = await response.json()
            result.update({'url': url, })
            return result

    async def fetch_all_urls(urls: list[str]) -> list[dict]:
        async with aiohttp.ClientSession() as session:
            tasks = [fetch_url(session, url) for url in urls]
            return await asyncio.gather(*tasks)


    results = asyncio.run(fetch_all_urls(df['url'].tolist()))
    with TM1Hook(blob_service.conn_id).get_conn() as tm1:
        extra = []
        for requests_result in results:
            bound = requests_result['url'][-1]
            if not requests_result['result']:
                continue
            for _, timetable_datalines in requests_result['data'].items():
                if len(timetable_datalines) == 0:
                    continue
                timetable_df = pd.concat([TimeTable(**line, bound=bound).to_pandas() for line in timetable_datalines])
                if timetable_df.empty:
                    continue
                route = timetable_df['Route'].iloc[0].strip()
                bound = timetable_df['Bound'].iloc[0].strip()
                file_name = f'airflow.timetable.{route}.{bound}.csv'
                upload(tm1, file_name, transfer_pandas_dataframe_to_blob(timetable_df))
                extra.append(file_name)
                
    return extra

@task(task_id='commit-timetable-to-tm1', inlets=[timetable_asset])
def commit_timetable_to_tm1(blob_files: list[str]=[]):
    from airflow_provider_tm1.hooks.tm1 import TM1Hook
    from airflow_tm1.utils.tm1_blob_service import BlobService
    from concurrent.futures import ThreadPoolExecutor
    
    blob_service = BlobService.from_uri(timetable_asset.uri)
    with TM1Hook(blob_service.conn_id).get_conn() as tm1:
        with ThreadPoolExecutor(max_workers=5) as executor:
            for file in blob_files:
                executor.submit(
                    tm1.processes.execute,
                    'update.operation system.timetable',
                    pFile=file,
                )
        executor.shutdown(wait=True)


