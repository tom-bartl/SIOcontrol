#!/usr/bin/env python3
import RPi.GPIO as GPIO
import time, argparse
from SIOpinlist import O_spray_ctrl


SPRAY_CTRL_ACTIVE_LEVEL = GPIO.LOW   # button press pulls pin LOW
SPRAY_CTRL_INACTIVE_LEVEL = GPIO.HIGH # idle / rest state is HIGH
SPRAY_BUTTON_PRESS_S = 0.08
SPRAY_BUTTON_GAP_S = 0.12
INTER_CYCLE_WAIT_S = 0.2


def spray_button_press():
    GPIO.output(O_spray_ctrl, SPRAY_CTRL_ACTIVE_LEVEL)
    time.sleep(SPRAY_BUTTON_PRESS_S)
    GPIO.output(O_spray_ctrl, SPRAY_CTRL_INACTIVE_LEVEL)
    time.sleep(SPRAY_BUTTON_GAP_S)


def spray_start():
    spray_button_press()
    spray_button_press()


def spray_stop():
    spray_button_press()


if __name__ == '__main__':

    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(O_spray_ctrl, GPIO.OUT)
    
    parser = argparse.ArgumentParser(description='SIO spray cleaning routine')
    parser.add_argument('--stime', help='Cycle length (seconds)', default=0.2, type=float, required=False)
    parser.add_argument('--cycles', help='Number of cleaning pulses', default=5, type=int, required=False)
    args = parser.parse_args()

    print(
        f"[SIOclean] Starting cleaning: {args.cycles} cycles, "
        f"{args.stime}s cycle length, {INTER_CYCLE_WAIT_S}s inter-cycle wait",
        flush=True,
    )

    try:
        GPIO.output(O_spray_ctrl, SPRAY_CTRL_INACTIVE_LEVEL)

        for cycle in range(1, args.cycles + 1):
            print(f"[SIOclean] Cycle {cycle}/{args.cycles}: spray START", flush=True)
            spray_start()
            time.sleep(args.stime)

            print(f"[SIOclean] Cycle {cycle}/{args.cycles}: spray STOP", flush=True)
            spray_stop()
            if cycle < args.cycles:
                print(
                    f"[SIOclean] Cycle {cycle}/{args.cycles}: waiting {INTER_CYCLE_WAIT_S}s",
                    flush=True,
                )
                time.sleep(INTER_CYCLE_WAIT_S)

        print("[SIOclean] Operation completed", flush=True)
    finally:
        GPIO.output(O_spray_ctrl, SPRAY_CTRL_INACTIVE_LEVEL)
