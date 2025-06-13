from TM1py import TM1Service
import pandas as pd 
import io 
from airflow.decorators import task

def upload(tm1: TM1Service, file_name: str, file_content: bytes):
    tm1.files.update_or_create(file_name, file_content)
    
def transfer_pandas_dataframe_to_blob(df: pd.DataFrame): 
    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    return buffer.getvalue().encode('utf-8')

def exists(tm1: TM1Service, file_name: str) -> bool:
    return tm1.files.exists(file_name)

def remove(tm1: TM1Service, file_name: str):
    tm1.files.delete(file_name)
    
def open(tm1: TM1Service, file_name: str) -> bytes:
    return tm1.files.get(file_name)
    
def parse_uri(uri: str):
    assert uri.startswith('tm1://'), "URI must start with 'tm1://'"
    conn_id, file_name = uri[6:].split('/', 1)
    return conn_id, file_name

def search_string_in_name(tm1: TM1Service, search_string: str) -> list[str]:
    file_partition = search_string.split('*')
    name_contains = file_partition 
    return tm1.files.search_string_in_name(
        name_contains=name_contains
    )


class BlobService:
    conn_id: str = '' 
    file_name: str = ''
    uri: str = ''

    @classmethod
    def from_uri(cls, uri: str):
        assert uri.startswith('tm1://'), "URI must start with 'tm1://'"
        conn_id, file_name = uri[6:].split('/', 1)
        blob_service = cls()
        blob_service.conn_id = conn_id
        blob_service.file_name = file_name
        blob_service.uri = uri
        return blob_service


    def upload_file(self, file_content: bytes|io.StringIO):
        from airflow_provider_tm1.hooks.tm1 import TM1Hook
        if isinstance(file_content, io.StringIO):
            file_content = file_content.getvalue().encode('utf-8')
        with TM1Hook(self.conn_id).get_conn() as tm1:
            upload(tm1, 'airflow.' + self.file_name, file_content)

    def upload_dataframe(self, df: pd.DataFrame):
        self.upload_file(transfer_pandas_dataframe_to_blob(df))

    def exists(self) -> bool:
        from airflow_provider_tm1.hooks.tm1 import TM1Hook
        with TM1Hook(self.conn_id).get_conn() as tm1:
            print(f"Checking existence of {self.tm1_file_name} in TM1")
            return exists(tm1, self.tm1_file_name)
        
    def remove(self): 
        from airflow_provider_tm1.hooks.tm1 import TM1Hook
        
        with TM1Hook(self.conn_id).get_conn() as tm1:
            remove(tm1, self.tm1_file_name)

    def open(self) -> bytes:
        from airflow_provider_tm1.hooks.tm1 import TM1Hook
        with TM1Hook(self.conn_id).get_conn() as tm1:
            return open(tm1, self.tm1_file_name)
        
    def open_as_pandas_dataframe(self) -> pd.DataFrame:
        from airflow_provider_tm1.hooks.tm1 import TM1Hook
        with TM1Hook(self.conn_id).get_conn() as tm1:
            content = open(tm1, self.tm1_file_name)
            return pd.read_csv(io.StringIO(content.decode('utf-8')))
        
    def dir(self) -> list[str]:
        from airflow_provider_tm1.hooks.tm1 import TM1Hook
        with TM1Hook(self.conn_id).get_conn() as tm1:
            return search_string_in_name(tm1, self.tm1_file_name)

    @property 
    def tm1_file_name(self) -> str:
        return f'airflow.{self.file_name}'

@task(task_id='remove-tm1-blob-file')
def remove_tm1_blob_file(asset_uri: str = '', file_names: list[str] = [], conn_id: str = ''):
    from airflow_provider_tm1.hooks.tm1 import TM1Hook
    
    assert asset_uri or (file_names and conn_id), "At least one of asset_uri, file_names must be provided."
    if asset_uri:
        blob_service = BlobService.from_uri(asset_uri)
        for file_name in blob_service.dir(): 
            with TM1Hook(blob_service.conn_id).get_conn() as tm1:
                remove(tm1, file_name)
    elif file_names:
        with TM1Hook(conn_id).get_conn() as tm1:
            for file_name in file_names:
                if not exists(tm1, file_name):
                    print(f"not exists {file_name} from TM1")
                    continue
                remove(tm1, file_name)
