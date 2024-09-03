@service
def rct_ha_call(action='set', parameter='power_mng.soc_max', value=0.97, host='192.168.0.99'):
    #"""Using rct.py to set/get parameter of the RCT inverter"""

    from rct import get_value, set_value

    value = str(value) # some parameters (like power_mng.soc_strategy) only accept values as a string

    output = set_value(parameter=parameter, value=value, host=host)
    print(output)
    log.info(f"rct_ha_call: {output}")