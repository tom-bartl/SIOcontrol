#!/usr/bin/env python3

import RPi.GPIO as GPIO
import argparse
from SIOpinlist import O_spray_ctrl


SPRAY_CTRL_ACTIVE_LEVEL = GPIO.LOW
SPRAY_CTRL_INACTIVE_LEVEL = GPIO.HIGH


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='SIO spray-control arm/disarm')
    parser.add_argument('--updown', help='Select power state', required=True, choices=('up', 'down'))
    args = parser.parse_args()

    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(O_spray_ctrl, GPIO.OUT)

    if args.updown == 'up':
        GPIO.output(O_spray_ctrl, SPRAY_CTRL_INACTIVE_LEVEL)
        print("Spray control armed")
    else:
        GPIO.output(O_spray_ctrl, SPRAY_CTRL_INACTIVE_LEVEL)
        print("Spray control set to inactive level")

    print("Operation completed")

