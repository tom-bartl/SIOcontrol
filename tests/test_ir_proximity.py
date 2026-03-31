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


SIGNAL_ACTIVE_LOW = True
SIGNAL_PULL = GPIO.PUD_UP
FIRST_READ_DELAY_US = 210
SECOND_READ_DELAY_US = 395
LOOP_DELAY_US = 2630000
POWER_ON_SETTLE_S = 0.5
POWER_OFF_ON_EXIT = True


def main():
    GPIO.setwarnings(False)
    GPIO.cleanup()
    GPIO.setmode(GPIO.BCM)

    signal_pin = I_plunger_irsensor_sig
    power_pins = (O_sensors_pwr,)

    GPIO.setup(signal_pin, GPIO.IN, pull_up_down=SIGNAL_PULL)
    for pin in power_pins:
        GPIO.setup(pin, GPIO.OUT)

    signal_active_high = not SIGNAL_ACTIVE_LOW

    def is_active():
        value = GPIO.input(signal_pin)
        return (value == GPIO.HIGH) == signal_active_high

    def read_detection():
        time.sleep(FIRST_READ_DELAY_US / 1_000_000.0)
        first_active = is_active()
        time.sleep(SECOND_READ_DELAY_US / 1_000_000.0)
        second_active = is_active()
        time.sleep(FIRST_READ_DELAY_US / 1_000_000.0)
        third_active = is_active()
        time.sleep(SECOND_READ_DELAY_US / 1_000_000.0)
        fourth_active = is_active()

        active_count = sum(
            1
            for value in (first_active, second_active, third_active, fourth_active)
            if value
        )
        if active_count >= 3:
            result = True
        elif active_count <= 1:
            result = False
        else:
            result = None
        return result, (first_active, second_active, third_active, fourth_active)

    for pin in power_pins:
        GPIO.output(pin, GPIO.HIGH)
    time.sleep(POWER_ON_SETTLE_S)

    try:
        while True:
            detected, reads = read_detection()
            raw_value = GPIO.input(signal_pin)

            if detected is not None:
                status = "DETECTED" if detected else "CLEAR"
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                read_values = "".join("1" if value else "0" for value in reads)
                print(
                    f"{timestamp} - {status} (raw={raw_value}, reads={read_values})"
                )
            time.sleep(LOOP_DELAY_US / 1_000_000.0)
    except KeyboardInterrupt:
        pass
    finally:
        if POWER_OFF_ON_EXIT:
            for pin in power_pins:
                GPIO.output(pin, GPIO.LOW)
        GPIO.cleanup()


if __name__ == "__main__":
    main()
