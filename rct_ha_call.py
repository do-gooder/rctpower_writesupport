@service(supports_response="optional")
def rct_ha_call(action='set', parameter='power_mng.soc_max', value=0.97, host='192.168.0.99'):
    from rct import get_value, set_value
    import logging

    value = str(value)

    if action == 'get':
        output = get_value(parameter=parameter, host=host)
    elif action == 'set':
        output = set_value(parameter=parameter, value=value, host=host)

    print(output)
    log.info(f"rct_ha_call: {output}")

    # numerischen Wert aus dem Ergebnis extrahieren, falls es sich um einen Log-String handelt
    if isinstance(output, str) and '=' in output:
        result_value = output.split('=')[-1].strip()
    else:
        result_value = output

    return {"value": result_value}