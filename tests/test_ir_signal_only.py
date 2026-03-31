#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import RPi.GPIO as GPIO

from SIOpinlist import (
    I_plunger_irsensor_sig,
    O_sensors_pwr,
)


POWER_ON_SETTLE_S = 0.5
SAMPLE_INTERVAL_S = 0.05


def main():
    GPIO.setwarnings(False)
    GPIO.cleanup()
    GPIO.setmode(GPIO.BCM)

    signal_pin = I_plunger_irsensor_sig
    power_pins = (O_sensors_pwr,)

    GPIO.setup(signal_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    for pin in power_pins:
        GPIO.setup(pin, GPIO.OUT)

    for pin in power_pins:
        GPIO.output(pin, GPIO.HIGH)
    time.sleep(POWER_ON_SETTLE_S)

    print(f"Reading IR signal pin BCM {signal_pin} (Ctrl+C to stop)")

    try:
        while True:
            state = GPIO.input(signal_pin)
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"{timestamp} - signal={state}")
            time.sleep(SAMPLE_INTERVAL_S)
    except KeyboardInterrupt:
        pass
    finally:
        for pin in power_pins:
            GPIO.output(pin, GPIO.LOW)
        GPIO.cleanup()


if __name__ == "__main__":
    main()
