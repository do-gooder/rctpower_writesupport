# rctpower_writesupport

Write support for RCT Power Serial Protocol with rctclient

**Important: For safety reasons, there should be no other connections to the inverter (RCT Power App, HA Integration, OpenWB, EVCC etc.)**

**Also important: This is an experimental tool and therefore not function nor dangerous conditions or damage to the controlled system can be excluded. All risk lies on the owner of the equipment!** <br> 

Refer also to: [rctclient | write support](https://rctclient.readthedocs.io/en/latest/cli_write_support.html)


## Scenarios

### Charging from the grid for e.g. Tibber

1. Set ``power_mng.soc_strategy`` to 2
2. Set ``power_mng.battery_power_external`` to the desired charging power (e.g. -6000 = 6 kW)
3. Wait until SOC target is reached
4. Set ``power_mng.soc_strategy`` to 4
5. Set ``power_mng.battery_power_extern`` to 0


### Discharge lock during e-car charging

1. Set ``power_mng.soc_strategy`` to 2
2. Set ``power_mng.battery_power_external`` to 0
3. Wait as long as the car is charging
4. Set ``power_mng.soc_strategy`` to 4

### Emergency power reserve

To adjust the available emergency power reserve for the dark season, the value ``power_mng.soc_min`` can be increased. You should then also increase ``power_mng.soc_charge`` in order to recharge from the grid to maintain ``power_mng.soc_min``.

Increase:
1. Set ``power_mng.soc_min`` to 0.30 (for 30%)
2. Set ``power_mng.soc_charge`` to 0.28 (for 28%)

Set to default:
1. Set ``power_mng.soc_min`` to 0.07 (for 7%)
2. Set ``power_mng.soc_charge`` to 0.05 (for 5%)

## Usage
```
rct.py get <parameter> --host=<ip_address_or_hostname>
rct.py set <parameter> <value> --host=<ip_address_or_hostname>

Valid Parameters:
  power_mng.soc_strategy - SOC charging strategy
    Valid Values:
      0: SOC target = SOC (State of Charge)
      1: Konstant (Constant)
      2: Extern (External)
      3: Mittlere Batteriespannung (Average Battery Voltage)
      4: Intern (Internal)
      5: Zeitplan (Schedule)
    Default Value: 4 (Internal)
  power_mng.soc_target_set - Force SOC target
    Valid Range: 0.00 to 1.00, with at most two decimal places
    Default Value: 0.50
  power_mng.battery_power_extern - Battery target power
    Valid Range: -6000 to 6000
      Positive values indicate discharge, negative values indicate charge
    Default Value: 0
  power_mng.soc_min - Min SOC target
    Valid Range: 0.00 to 1.00, with at most two decimal places
    Default Value: 0.07
  power_mng.soc_max - Max SOC target
    Valid Range: 0.00 to 1.00, with at most two decimal places
    Default Value: 0.97
  power_mng.soc_charge_power - Charging power to reach SOC target
    Default Value: 100
  power_mng.soc_charge - Trigger for charging to SOC_min
    Default Value: 0.05
```

## Homeassistant Integration
This is an elementary example, how the script could be used within Homeassistant.

### Preperations
1. Install pyscript according to the installation instructions from this [documentation](https://hacs-pyscript.readthedocs.io/en/stable/installation.html).<br>
Afterwards, the integration is available:
![image](https://github.com/user-attachments/assets/314d502f-8c25-4060-8a71-ca270dd27f2b)
Within the the integration settings, make sure that all imports of all packackes is allowed:
![image](<Bildschirmfoto 2024-08-07 um 08.56.24.png>)
Hint: The internal integration "Python Scripts" of Home Assistant is not sufficient, because it is not possible to use Python imports with this integration. 
Refer to: [Home Assistant | Integrations | Python Scripts](https://www.home-assistant.io/integrations/python_script/). <br><br>
The integration should be ready for use, if basics Pyscript services are provided like this:
![image](<Bildschirmfoto 2024-08-07 um 09.13.11.png>)

### Implementation as Service
First, set up the follwing folders in the config folder of Home Assistant and copy the files "rct.py" and "rct_ha_call.py" from this repository to the folders:
```
Home Assistant Root Folder:
└── config
    └── pyscript
        ├── modules
        │   └── rct.py
        └── rct_ha_call.py
```

within the file `rct_ha_call.py` update the default arguments according to your needs:
```python
@service
def rct_ha_call(action='set', parameter='power_mng.soc_max', value=0.97, host='192.168.0.99'):
    #"""Using rct.py to set/get parameter of the RCT inverter"""

    from rct import get_value, set_value

    output = set_value(parameter=parameter, value=value, host=host)
    print(output)
    log.info(f"rct_ha_call: {output}")
```
If a default value is provided, less arguments are needed when the service is called from Home Assistant as a service later.
In this case, I just want to use to **set** the parameter of **power_mng.soc_max** of fixed inverter with IP **192.168.0.99**.

### Testing
Now, the service "rct_ha_call" should be available and the `value: 0.97` is the data supplied to the service as the maximum state of charge:
![image](<Bildschirmfoto 2024-08-07 um 09.35.41.png>)

### Usage
Just my implementation for usage as an example:
1. `input_number.rtc_soc_maximum` is used to provide max. SOC
2. automation is calling the service, when the input number changes:
```yaml
alias: Batterie RCT setze SOC Maximum
description: Setzt den den maximalen Speicherwert der Batterie über ein Python-Skript
trigger:
  - platform: state
    entity_id:
      - input_number.rtc_soc_maximum
    for:
      hours: 0
      minutes: 0
      seconds: 3
condition: []
action:
  - service: pyscript.rct_ha_call
    data:
      value: "{{states('input_number.rtc_soc_maximum')|multiply(0.01)|round(2)}}"
mode: single
```
Hint: Do not forget to scale the input number from percentage (i.e. 97%) to fractions (i.e. 0.97) by using the pipeline `|multiply(0.01)|round(2)`, as the script expects values from 0...1 as input.

## Links
[Rctclient's documentation](https://rctclient.readthedocs.io/en/latest/index.html)

[Special RCT Infos](https://www.photovoltaikforum.com/thread/159603-rct-power-storage-soc-zielauswahl-extern-nutzen/?postID=2656687#post2656687)

[Starting on Page 32](https://www.rct-power.com/de/download-bereich-de.html?file=files/Download-Bereich/Download%20Bereich%20EN/3.1_RCT%20Power%20Storage%20DC%208-10/RCT-Power-Storage-DC10_Manual_Web24V1EN.pdf)

[HF-A21-SMT, Chapter 1.4.3](https://ptelectronics.ru/wp-content/uploads/HF-A21-SMT-User-Manual-V1.120150203.pdf)

[Pyscript: Python Scripting for Home Assistant | Documentation](https://hacs-pyscript.readthedocs.io/en/stable/)