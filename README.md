# rctpower_writesupport
Write support for RCT Power Serial Protocol with rctclient

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
