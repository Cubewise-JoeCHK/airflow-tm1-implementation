from TM1py import TM1Service


def connect_to_tm1(instance_config):
    return TM1Service(**instance_config)
