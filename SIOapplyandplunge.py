#!/usr/bin/env python3

import RPi.GPIO as GPIO
import time
import argparse
from SIOpinlist import O_spray_ctrl


SPRAY_CTRL_ACTIVE_LEVEL = GPIO.LOW   # button press pulls pin LOW
SPRAY_CTRL_INACTIVE_LEVEL = GPIO.HIGH # idle / rest state is HIGH
SPRAY_BUTTON_PRESS_S = 0.08
SPRAY_BUTTON_GAP_S = 0.12


def spray_button_press():
    GPIO.output(O_spray_ctrl, SPRAY_CTRL_ACTIVE_LEVEL)
    time.sleep(SPRAY_BUTTON_PRESS_S)
    GPIO.output(O_spray_ctrl, SPRAY_CTRL_INACTIVE_LEVEL)
    time.sleep(SPRAY_BUTTON_GAP_S)


def spray_start():
    # Two presses to start spraying
    spray_button_press()
    spray_button_press()


def spray_stop():
    # One press to stop spraying
    spray_button_press()


def applysample(wait, duration):
    time.sleep(wait)
    spray_start()
    time.sleep(duration)
    spray_stop()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='SIO spray sequence')
    parser.add_argument('--stime', help='Spray pulse duration (seconds)', type=float, required=True)
    parser.add_argument('--sdelay', help='Delay before spray starts (seconds)', default=0, type=float, required=False)
    args = parser.parse_args()

    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(O_spray_ctrl, GPIO.OUT)
    GPIO.output(O_spray_ctrl, SPRAY_CTRL_INACTIVE_LEVEL)

    print("Run timing:")
    print("Spray start:", args.sdelay)
    print("Spray end:", args.sdelay + args.stime)

    try:
        applysample(args.sdelay, args.stime)
        print("Spray sequence completed")
    finally:
        GPIO.output(O_spray_ctrl, SPRAY_CTRL_INACTIVE_LEVEL)

