# rctpower_writesupport

Write support for RCT Power Serial Protocol with rctclient

**Important: For safety reasons, there should be no other connections to the inverter (RCT Power App, HA Integration, OpenWB, EVCC etc.)**

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

## Links
[Special RCT Infos](https://www.photovoltaikforum.com/thread/159603-rct-power-storage-soc-zielauswahl-extern-nutzen/?postID=2656687#post2656687)

[Starting on Page 32](https://www.rct-power.com/de/download-bereich-de.html?file=files/Download-Bereich/Download%20Bereich%20EN/3.1_RCT%20Power%20Storage%20DC%208-10/RCT-Power-Storage-DC10_Manual_Web24V1EN.pdf)
