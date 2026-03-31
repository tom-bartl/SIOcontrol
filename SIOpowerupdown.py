#!/usr/bin/env python3

import RPi.GPIO as GPIO
import argparse
from SIOpinlist import O_spray_ctrl


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='SIO spray-control arm/disarm')
    parser.add_argument('--updown', help='Select power state', required=True, choices=('up', 'down'))
    args = parser.parse_args()

    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(O_spray_ctrl, GPIO.OUT)

    if args.updown == 'up':
        GPIO.output(O_spray_ctrl, GPIO.HIGH)
        print("Spray control armed")
    else:
        GPIO.output(O_spray_ctrl, GPIO.LOW)
        print("Spray control disarmed")

    print("Operation completed")

