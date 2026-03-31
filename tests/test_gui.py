#!/usr/bin/env python3
"""
Test environment touch GUI for direct access to all SIO GPIO pins.
Provides toggle buttons for outputs and live indicators for inputs.
"""

import sys
import os
import time
from threading import Thread
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle, Ellipse, RoundedRectangle
from kivy.clock import Clock

from SIOpinlist import (
    O_retract_solenoid,
    O_plunger_solenoid,
    O_sensors_pwr,
    O_plunger_irsensor_enable,
    O_spray_ctrl,
    I_plunger_irsensor_sig,
    I_cryostat_sensor_sig,
)
from sio_widgets import COLORS, TerminalBox, StatusIndicator as StatusDot

try:
    import RPi.GPIO as GPIO
except ImportError:
    GPIO = None

# Set window size for 1280x720 display minus taskbar and title bar
Window.size = (1280, 640)

# ---------- Pin definitions ----------
OUTPUT_PINS = [
    {"name": "Retract Solenoid",    "pin": O_retract_solenoid,        "gpio": 21},
    {"name": "Plunger Solenoid",    "pin": O_plunger_solenoid,        "gpio": 20},
    {"name": "Sensors Power",       "pin": O_sensors_pwr,             "gpio": 26},
    {"name": "IR Sensor Enable",    "pin": O_plunger_irsensor_enable, "gpio": 16},
]

INPUT_PINS = [
    {"name": "Plunger IR Sensor",   "pin": I_plunger_irsensor_sig,    "gpio": 12},
    {"name": "Cryostat Sensor",     "pin": I_cryostat_sensor_sig,     "gpio": 6},
]


class OutputPinRow(BoxLayout):
    """A single output pin: label + toggle button + state dot."""
    def __init__(self, pin_info, terminal, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = 62
        self.spacing = 10
        self.padding = [10, 4, 10, 4]
        self.pin_num = pin_info["pin"]
        self.pin_name = pin_info["name"]
        self.terminal = terminal
        self.state = False

        # Background
        with self.canvas.before:
            Color(*COLORS["panel"])
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[8])
        self.bind(pos=self._upd_rect, size=self._upd_rect)

        # Pin label
        lbl = Label(
            text=f'{self.pin_name}\nGPIO {pin_info["gpio"]}',
            color=COLORS["text"],
            font_size='16sp',
            size_hint_x=0.45,
            halign='left',
            valign='middle',
            markup=False,
        )
        lbl.bind(size=lbl.setter('text_size'))

        # Toggle button
        self.toggle_btn = Button(
            text='OFF',
            font_size='20sp',
            size_hint_x=0.35,
            background_normal='',
            background_color=COLORS["off"],
            bold=True,
        )
        self.toggle_btn.bind(on_press=self.toggle)

        # Status dot
        self.dot = StatusDot()
        self.dot.set_color(COLORS["off"])

        self.add_widget(lbl)
        self.add_widget(self.toggle_btn)
        self.add_widget(self.dot)

    def _upd_rect(self, *_):
        self._rect.pos = self.pos
        self._rect.size = self.size

    def toggle(self, *_):
        self.state = not self.state
        if self.state:
            self._set_high()
        else:
            self._set_low()

    def _set_high(self):
        self.state = True
        self.toggle_btn.text = 'ON'
        self.toggle_btn.background_color = COLORS["on"]
        self.dot.set_color(COLORS["on"])
        if GPIO:
            try:
                GPIO.output(self.pin_num, GPIO.HIGH)
            except Exception as exc:
                self.terminal.add_message(f'{self.pin_name}: GPIO error – {exc}', 'error')
                return
        self.terminal.add_message(f'{self.pin_name} (GPIO {self.pin_num}) → HIGH', 'success')

    def _set_low(self):
        self.state = False
        self.toggle_btn.text = 'OFF'
        self.toggle_btn.background_color = COLORS["off"]
        self.dot.set_color(COLORS["off"])
        if GPIO:
            try:
                GPIO.output(self.pin_num, GPIO.LOW)
            except Exception as exc:
                self.terminal.add_message(f'{self.pin_name}: GPIO error – {exc}', 'error')
                return
        self.terminal.add_message(f'{self.pin_name} (GPIO {self.pin_num}) → LOW', 'info')

    def force_off(self):
        """Force pin LOW without logging (used during cleanup)."""
        self.state = False
        self.toggle_btn.text = 'OFF'
        self.toggle_btn.background_color = COLORS["off"]
        self.dot.set_color(COLORS["off"])
        if GPIO:
            try:
                GPIO.output(self.pin_num, GPIO.LOW)
            except Exception:
                pass


class InputPinRow(BoxLayout):
    """A single input pin: label + live state indicator."""
    def __init__(self, pin_info, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = 62
        self.spacing = 10
        self.padding = [10, 4, 10, 4]
        self.pin_num = pin_info["pin"]
        self.pin_name = pin_info["name"]

        # Background
        with self.canvas.before:
            Color(*COLORS["panel"])
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[8])
        self.bind(pos=self._upd_rect, size=self._upd_rect)

        # Pin label
        lbl = Label(
            text=f'{self.pin_name}\nGPIO {pin_info["gpio"]}',
            color=COLORS["text"],
            font_size='16sp',
            size_hint_x=0.45,
            halign='left',
            valign='middle',
        )
        lbl.bind(size=lbl.setter('text_size'))

        # State text
        self.state_label = Label(
            text='--',
            color=COLORS["muted"],
            font_size='20sp',
            size_hint_x=0.35,
            bold=True,
        )

        # Status dot
        self.dot = StatusDot()
        self.dot.set_color(COLORS["muted"])

        self.add_widget(lbl)
        self.add_widget(self.state_label)
        self.add_widget(self.dot)

    def _upd_rect(self, *_):
        self._rect.pos = self.pos
        self._rect.size = self.size

    def update(self):
        """Read the pin and update the indicator. Called periodically."""
        if GPIO is None:
            return
        try:
            val = GPIO.input(self.pin_num)
        except Exception:
            self.state_label.text = 'ERR'
            self.state_label.color = COLORS["danger"]
            self.dot.set_color(COLORS["danger"])
            return
        if val:
            self.state_label.text = 'HIGH'
            self.state_label.color = COLORS["input_hi"]
            self.dot.set_color(COLORS["input_hi"])
        else:
            self.state_label.text = 'LOW'
            self.state_label.color = COLORS["input_lo"]
            self.dot.set_color(COLORS["input_lo"])


class SprayControlRow(BoxLayout):
    """Dedicated spray button-emulation test row.

    Idle state is HIGH. Pressing the pulse button drives LOW briefly,
    then returns HIGH.
    """

    PULSE_DURATION_S = 0.08

    def __init__(self, terminal, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = 72
        self.spacing = 10
        self.padding = [10, 4, 10, 4]
        self.terminal = terminal

        with self.canvas.before:
            Color(*COLORS["panel"])
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[8])
        self.bind(pos=self._upd_rect, size=self._upd_rect)

        label = Label(
            text=f'Sprayer Ctrl Pulse\\nGPIO {O_spray_ctrl}',
            color=COLORS["text"],
            font_size='16sp',
            size_hint_x=0.42,
            halign='left',
            valign='middle',
        )
        label.bind(size=label.setter('text_size'))

        self.state_label = Label(
            text='--',
            color=COLORS["muted"],
            font_size='20sp',
            size_hint_x=0.18,
            bold=True,
        )

        self.dot = StatusDot()
        self.dot.set_color(COLORS["muted"])

        self.pulse_btn = Button(
            text='PULSE LOW',
            font_size='18sp',
            size_hint_x=0.30,
            background_normal='',
            background_color=COLORS["warn"],
            bold=True,
        )
        self.pulse_btn.bind(on_press=self.pulse)

        self.add_widget(label)
        self.add_widget(self.state_label)
        self.add_widget(self.dot)
        self.add_widget(self.pulse_btn)

    def _upd_rect(self, *_):
        self._rect.pos = self.pos
        self._rect.size = self.size

    def _set_indicator(self, is_high):
        if is_high:
            self.state_label.text = 'HIGH'
            self.state_label.color = COLORS["input_hi"]
            self.dot.set_color(COLORS["input_hi"])
        else:
            self.state_label.text = 'LOW'
            self.state_label.color = COLORS["warn"]
            self.dot.set_color(COLORS["warn"])

    def set_idle_high(self):
        if GPIO is None:
            self._set_indicator(True)
            return
        try:
            GPIO.output(O_spray_ctrl, GPIO.HIGH)
            self._set_indicator(True)
            self.terminal.add_message('Sprayer control set to idle HIGH', 'info')
        except Exception as exc:
            self.terminal.add_message(f'Sprayer control error: {exc}', 'error')

    def pulse(self, *_):
        if GPIO is None:
            self._set_indicator(False)
            self._set_indicator(True)
            self.terminal.add_message('Simulation pulse LOW -> HIGH', 'warning')
            return

        self.pulse_btn.disabled = True

        def run_pulse():
            try:
                GPIO.output(O_spray_ctrl, GPIO.LOW)
                Clock.schedule_once(lambda dt: self._set_indicator(False), 0)
                time.sleep(self.PULSE_DURATION_S)
                GPIO.output(O_spray_ctrl, GPIO.HIGH)
                Clock.schedule_once(lambda dt: self._set_indicator(True), 0)
                Clock.schedule_once(
                    lambda dt: self.terminal.add_message('Sprayer pulse LOW -> HIGH completed', 'success'),
                    0,
                )
            except Exception as exc:
                Clock.schedule_once(
                    lambda dt: self.terminal.add_message(f'Sprayer pulse error: {exc}', 'error'),
                    0,
                )
            finally:
                Clock.schedule_once(lambda dt: setattr(self.pulse_btn, 'disabled', False), 0)

        Thread(target=run_pulse, daemon=True).start()


class SIOTestApp(App):
    INPUT_POLL_INTERVAL = 0.15  # seconds

    def build(self):
        self.title = 'SIO Test Environment'
        Window.clearcolor = COLORS["bg"]

        root = BoxLayout(orientation='vertical', padding=12, spacing=10)

        # ---- Header ----
        header = Label(
            text='SIO Pin Test Environment',
            color=COLORS["accent"],
            font_size='28sp',
            size_hint_y=None,
            height=42,
            bold=True,
        )

        # ---- Columns: outputs | inputs ----
        columns = BoxLayout(orientation='horizontal', spacing=15, size_hint_y=1)

        # -- Output column --
        out_col = BoxLayout(orientation='vertical', spacing=6, size_hint_x=0.55)
        out_header = Label(
            text='Outputs  (toggle)',
            color=COLORS["text"],
            font_size='18sp',
            size_hint_y=None,
            height=28,
            bold=True,
        )
        out_col.add_widget(out_header)

        self.output_rows = []
        # Terminal created early so rows can log into it
        self.terminal = TerminalBox(size_hint_y=None, height=150)

        for pinfo in OUTPUT_PINS:
            row = OutputPinRow(pinfo, self.terminal)
            self.output_rows.append(row)
            out_col.add_widget(row)

        self.spray_control_row = SprayControlRow(self.terminal)
        out_col.add_widget(self.spray_control_row)

        # All-off button
        all_off_btn = Button(
            text='ALL OFF',
            font_size='20sp',
            size_hint_y=None,
            height=52,
            background_normal='',
            background_color=COLORS["danger"],
            bold=True,
        )
        all_off_btn.bind(on_press=self.all_off)
        out_col.add_widget(all_off_btn)

        # Spacer to push content up
        out_col.add_widget(Widget())

        # -- Input column --
        in_col = BoxLayout(orientation='vertical', spacing=6, size_hint_x=0.45)
        in_header = Label(
            text='Inputs  (live)',
            color=COLORS["text"],
            font_size='18sp',
            size_hint_y=None,
            height=28,
            bold=True,
        )
        in_col.add_widget(in_header)

        self.input_rows = []
        for pinfo in INPUT_PINS:
            row = InputPinRow(pinfo)
            self.input_rows.append(row)
            in_col.add_widget(row)

        # Spacer
        in_col.add_widget(Widget())

        columns.add_widget(out_col)
        columns.add_widget(in_col)

        # ---- Assemble ----
        root.add_widget(header)
        root.add_widget(columns)
        root.add_widget(self.terminal)

        # ---- GPIO init ----
        self._gpio_ready = False
        self._init_gpio()

        # ---- Start polling inputs ----
        Clock.schedule_interval(self._poll_inputs, self.INPUT_POLL_INTERVAL)

        return root

    # ---- GPIO helpers ----
    def _init_gpio(self):
        if GPIO is None:
            self.terminal.add_message('RPi.GPIO not available – running in simulation mode', 'warning')
            return

        try:
            GPIO.setwarnings(False)
            GPIO.setmode(GPIO.BCM)

            for pinfo in OUTPUT_PINS:
                GPIO.setup(pinfo["pin"], GPIO.OUT, initial=GPIO.LOW)

            GPIO.setup(O_spray_ctrl, GPIO.OUT, initial=GPIO.HIGH)

            for pinfo in INPUT_PINS:
                GPIO.setup(pinfo["pin"], GPIO.IN, pull_up_down=GPIO.PUD_UP)

            self._gpio_ready = True
            self.terminal.add_message('GPIO initialized – all outputs LOW, inputs pulled UP', 'success')
            self.spray_control_row.set_idle_high()
        except Exception as exc:
            self.terminal.add_message(f'GPIO init failed: {exc}', 'error')

    def _poll_inputs(self, _dt):
        for row in self.input_rows:
            row.update()

    def all_off(self, *_):
        for row in self.output_rows:
            row.force_off()
        self.spray_control_row.set_idle_high()
        self.terminal.add_message('All outputs forced LOW', 'warning')

    def on_stop(self):
        for row in self.output_rows:
            row.force_off()
        if GPIO is not None and self._gpio_ready:
            try:
                GPIO.cleanup()
            except Exception:
                pass


if __name__ == '__main__':
    SIOTestApp().run()
