 #!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import RPi.GPIO as GPIO

from SIOpinlist import (
    I_plunger_irsensor_sig,
    O_sensors_pwr,
    O_spray_ctrl,
)


SAMPLE_WINDOW_S = 0.000605
LOOP_DELAY_S = 0.000263
POWER_ON_SETTLE_S = 0.5
SAMPLE_INTERVAL_S = 0.00020


def main():
    GPIO.setwarnings(False)
    GPIO.cleanup()
    GPIO.setmode(GPIO.BCM)

    signal_pin = I_plunger_irsensor_sig
    power_pins = (O_sensors_pwr, O_spray_ctrl)

    GPIO.setup(signal_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    for pin in power_pins:
        GPIO.setup(pin, GPIO.OUT)

    for pin in power_pins:
        GPIO.output(pin, GPIO.HIGH)
    time.sleep(POWER_ON_SETTLE_S)

    try:
        while True:
            sample_count = int(round(SAMPLE_WINDOW_S / SAMPLE_INTERVAL_S))
            samples = []
            for index in range(sample_count):
                samples.append("1" if GPIO.input(signal_pin) == GPIO.HIGH else "0")
                if index < sample_count - 1:
                    time.sleep(SAMPLE_INTERVAL_S)
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"{timestamp} - reads={''.join(samples)}")
            time.sleep(LOOP_DELAY_S)
    except KeyboardInterrupt:
        pass
    finally:
        for pin in power_pins:
            GPIO.output(pin, GPIO.LOW)
        GPIO.cleanup()


if __name__ == "__main__":
    main()
