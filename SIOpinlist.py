# this file contains a list of RPi GPIO pins used by SIO

O_retract_solenoid			= 21 #rpi40
#GND							 #rpi39
O_plunger_solenoid			= 20 #rpi38
O_sensors_pwr				= 26 #rpi37
O_plunger_irsensor_enable	= 16 #rpi36 (deprecated: plunger IR sensor now always enabled in hardware)
#empty						= 19 #rpi35
#GND							 #rpi34
O_spray_ctrl				= 13 #rpi33
I_plunger_irsensor_sig		= 12 #rpi32
I_cryostat_sensor_sig		= 6  #rpi31



# HW changes to original SIO design: 
# 1) Plunger IR sensor is now always enabled (legacy enable pin retained only for compatibility)
# 2) Spray control pin added (MOSFET controls power to piezo spray))
# 3) Cryostat sensor (interlock) changed to simple reed switch and pin to pullup. (switch normally open, when closed it pulls down pin to gnd)


