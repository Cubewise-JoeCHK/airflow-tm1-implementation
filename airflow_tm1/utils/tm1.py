from TM1py import TM1Service

from airflow_tm1.utils.config import ProjectConfig
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

def connect_to_tm1(instance_name: str = ""):
    return TM1Service(**ProjectConfig.get_tm1_instance_config(instance_name))

def datetime_to_tm1_timestamp(dt: datetime | None) -> float:
    """
    Convert a Python datetime object to an IBM TM1 timestamp.

    TM1 timestamp is a serial number where day 0 corresponds to 1960-01-01.
    The integer part is the number of days since 1960-01-01.
    The fractional part is the fraction of the day passed.

    Args:
        dt (datetime): A datetime object (naive or timezone-aware).

    Returns:
        float: TM1 timestamp serial number.
    """
    # If timezone-aware, convert to UTC and drop tzinfo
    if dt is None: 
        return 0
    assert dt is not None, "Input datetime cannot be None"
    tm1_epoch = datetime(1960, 1, 1, tzinfo=ZoneInfo("Asia/Hong_Kong"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("Asia/Hong_Kong"))
    else:
        dt = dt.astimezone(ZoneInfo("Asia/Hong_Kong"))
    assert dt.tzinfo is not None, "Datetime must have tzinfo"
    delta = dt - tm1_epoch
    return delta.days + (delta.seconds  / 86400.0)
