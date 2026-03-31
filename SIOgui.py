#!/usr/bin/env python3

import os
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.uix.checkbox import CheckBox
from kivy.uix.widget import Widget
from kivy.uix.scrollview import ScrollView
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle, Ellipse
from kivy.clock import Clock
from subprocess import Popen, PIPE, STDOUT
from threading import Thread

from SIOpinlist import (
    I_cryostat_sensor_sig,
    I_plunger_irsensor_sig,
    O_sensors_pwr,
    O_plunger_solenoid,
    O_retract_solenoid,
)
from sio_widgets import COLORS, TerminalBox, StatusIndicator

try:
    import RPi.GPIO as GPIO
except ImportError:
    GPIO = None

# Set window size for 1280x720 display minus taskbar and title bar
Window.size = (1280, 640)


class NumericInputRow(BoxLayout):
    """Custom widget for numeric input with +/- buttons"""
    def __init__(self, label_text, default_value="5", step=1, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = 46
        self.spacing = 6
        self.step = step
        
        # Label
        label = Label(
            text=label_text,
            color=COLORS["text"],
            font_size='20sp',
            size_hint_x=0.4,
            halign='left',
            valign='middle'
        )
        label.bind(size=label.setter('text_size'))
        
        # Minus button
        self.minus_btn = Button(
            text='-',
            font_size='30sp',
            size_hint_x=0.15,
            background_color=COLORS["muted"],
            background_normal=''
        )
        self.minus_btn.bind(on_press=self.decrement)
        
        # Text input
        self.text_input = TextInput(
            text=default_value,
            multiline=False,
            font_size='18sp',
            size_hint_x=0.3,
            background_color=COLORS["panel"],
            foreground_color=COLORS["text"],
            padding=[5, 8, 5, 8],
            halign='center',
            input_filter='int'
        )
        
        # Plus button
        self.plus_btn = Button(
            text='+',
            font_size='30sp',
            size_hint_x=0.15,
            background_color=COLORS["muted"],
            background_normal=''
        )
        self.plus_btn.bind(on_press=self.increment)
        
        self.add_widget(label)
        self.add_widget(self.minus_btn)
        self.add_widget(self.text_input)
        self.add_widget(self.plus_btn)
    
    def increment(self, instance):
        try:
            current = int(self.text_input.text)
            self.text_input.text = str(current + self.step)
        except ValueError:
            self.text_input.text = str(self.step)
    
    def decrement(self, instance):
        try:
            current = int(self.text_input.text)
            new_value = max(0, current - self.step)
            self.text_input.text = str(new_value)
        except ValueError:
            self.text_input.text = "0"
    
    def get_value(self):
        return self.text_input.text


class ControlPanel(BoxLayout):
    """Main control panel widget"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = 10
        self.spacing = 8
        self.terminal = None  # Will be set by main app
        self.app = None       # Will be set by main app
        self.armed = False
        self.aborting = False
        
        # Add background color
        with self.canvas.before:
            Color(*COLORS["panel"])
            self.rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_rect, size=self._update_rect)
        
        # Title
        title = Label(
            text='Run Cycle',
            color=COLORS["text"],
            font_size='22sp',
            size_hint_y=None,
            height=26,
            bold=True
        )
        
        # Subtitle
        subtitle = Label(
            text='Adjust timings, power up, then start.',
            color=COLORS["muted"],
            font_size='13sp',
            size_hint_y=None,
            height=15
        )
        
        # Spray time input
        self.spray_time = NumericInputRow('Spray time (ms)', default_value='5', step=1)
        
        # Plunge delay input
        self.plunge_delay = NumericInputRow('Plunge delay (ms)', default_value='5', step=1)
        
        # Buttons block (two rows) with checkbox column
        buttons_block = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=110,
            spacing=10
        )

        buttons_column = BoxLayout(
            orientation='vertical',
            size_hint_x=0.75,
            spacing=6
        )

        buttons_row = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=52,
            spacing=8
        )
        
        self.powerup_btn = Button(
            text='Ready',
            font_size='18sp',
            size_hint_x=0.22,
            background_color=COLORS["accent"],
            background_normal='',
            disabled=True
        )
        self.powerup_btn.bind(on_release=self.power_up)
        
        self.powerdown_btn = Button(
            text='Abort',
            font_size='18sp',
            size_hint_x=0.22,
            background_color=COLORS["warn"],
            background_normal=''
        )
        self.powerdown_btn.bind(on_release=self.power_down)
        
        buttons_row.add_widget(self.powerup_btn)
        buttons_row.add_widget(self.powerdown_btn)

        # Start button row
        start_row = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=52
        )
        self.start_btn = Button(
            text='Spray & Plunge',
            font_size='22sp',
            background_color=COLORS["danger"],
            background_normal='',
            disabled=True
        )
        self.start_btn.bind(on_release=self.start_process)
        start_row.add_widget(self.start_btn)

        # Checkbox column (label below the checkbox)
        checkbox_column = BoxLayout(
            orientation='vertical',
            size_hint_x=0.25,
            spacing=4,
            padding=[0, 4, 0, 4]
        )
        self.donotplunge_check = CheckBox(
            size_hint=(None, None),
            size=(24, 24),
            color=COLORS["accent"]
        )
        checkbox_label = Label(
            text='Do not plunge',
            color=COLORS["text"],
            font_size='14sp',
            size_hint_y=None,
            height=20,
            halign='center',
            valign='middle'
        )
        checkbox_label.bind(size=checkbox_label.setter('text_size'))
        checkbox_column.add_widget(self.donotplunge_check)
        checkbox_column.add_widget(checkbox_label)

        buttons_column.add_widget(buttons_row)
        buttons_column.add_widget(start_row)
        buttons_block.add_widget(buttons_column)
        buttons_block.add_widget(checkbox_column)
        
        # Add all widgets
        self.add_widget(title)
        self.add_widget(subtitle)
        self.add_widget(self.spray_time)
        self.add_widget(self.plunge_delay)
        self.add_widget(buttons_block)
    
    def _update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size
    
    def power_up(self, instance):
        app = App.get_running_app()
        if not app.try_begin_operation('ready'):
            if self.terminal:
                self.terminal.add_message('System busy: finish current operation first', 'warning')
            return

        if self.terminal:
            self.terminal.add_message('Powering up system...', 'info')
        self.powerup_btn.disabled = True

        # Energize plunger solenoid to hold plunger in ready position
        if GPIO:
            try:
                GPIO.output(O_plunger_solenoid, GPIO.HIGH)
            except Exception as exc:
                if self.terminal:
                    self.terminal.add_message(f'Plunger solenoid error: {exc}', 'error')
                self.powerup_btn.disabled = False
                app.end_operation('ready')
                return

        arguments = ["python3", "SIOpowerupdown.py", "--updown", "up"]
        process = Popen(arguments)

        def wait_done():
            process.wait()
            def on_done(dt):
                self.powerup_btn.disabled = False
                if process.returncode == 0:
                    self.armed = True
                    if self.terminal:
                        self.terminal.add_message('Plunger solenoid energized, spray armed', 'success')
                        self.terminal.add_message('Waiting for plunger ready position...', 'info')
                else:
                    # Arming subprocess failed — de-energize plunger solenoid
                    if GPIO:
                        try:
                            GPIO.output(O_plunger_solenoid, GPIO.LOW)
                        except Exception:
                            pass
                    if self.terminal:
                        self.terminal.add_message('Spray arm failed', 'error')
                app.end_operation('ready')
            Clock.schedule_once(on_done, 0)

        Thread(target=wait_done, daemon=True).start()
    
    def power_down(self, instance):
        app = App.get_running_app()
        if not app.try_begin_operation('abort'):
            if self.terminal:
                self.terminal.add_message('System busy: finish current operation first', 'warning')
            return

        print("Power down")
        if self.terminal:
            self.terminal.add_message('Abort — disarming spray, waiting for plunger to retract...', 'warning')
        self.armed = False
        self.aborting = True
        self.start_btn.disabled = True
        self.powerdown_btn.disabled = True

        # Disarm spray and release retract solenoid immediately
        # Keep plunger solenoid energized until plunger physically retracts
        if GPIO:
            try:
                GPIO.output(O_retract_solenoid, GPIO.LOW)
            except Exception:
                pass

        arguments = ["python3", "SIOpowerupdown.py", "--updown", "down"]
        process = Popen(arguments)

        def wait_done():
            process.wait()
            # Plunger solenoid de-energized by poll loop once sensor confirms plunger retracted
        Thread(target=wait_done, daemon=True).start()
    
    def start_process(self, instance):
        app = App.get_running_app()
        if not app.try_begin_operation('spray_plunge'):
            if self.terminal:
                self.terminal.add_message('System busy: finish current operation first', 'warning')
            return

        print("Starting process")
        spraytime_s = float(self.spray_time.get_value()) / 1000
        plunge_delay_s = float(self.plunge_delay.get_value()) / 1000
        spraytime = str(spraytime_s)
        plungedelay = str(plunge_delay_s)
        if self.terminal:
            self.terminal.add_message(f'Starting spray & plunge (spray: {spraytime}s, delay: {plungedelay}s)', 'info')

        self.start_btn.disabled = True
        self.armed = False

        # Build spray-only subprocess command
        scripts_dir = os.path.dirname(os.path.abspath(__file__))
        script_path = os.path.join(scripts_dir, "SIOapplyandplunge.py")
        arguments = ["python3", script_path, "--stime", spraytime]
        plunge_disabled = self.donotplunge_check.active
        if plunge_disabled and self.terminal:
            self.terminal.add_message('Plunge disabled', 'warning')

        def run_sequence():
            import time as _time

            # 1) Spray first for spray time.
            process = Popen(
                arguments,
                cwd=scripts_dir,
                stdout=PIPE,
                stderr=STDOUT,
                text=True,
                bufsize=1,
            )
            if process.stdout is not None:
                for line in process.stdout:
                    msg = line.rstrip()
                    if msg and self.terminal:
                        Clock.schedule_once(
                            lambda dt, text=msg: self.terminal.add_message(text, 'info'),
                            0,
                        )
            process.wait()

            if process.returncode != 0:
                if self.terminal:
                    Clock.schedule_once(
                        lambda dt: self.terminal.add_message(
                            f'Spray process failed (exit {process.returncode})',
                            'error',
                        ),
                        0,
                    )
                Clock.schedule_once(lambda dt: app.end_operation('spray_plunge'), 0)
                return

            if plunge_disabled:
                if self.terminal:
                    Clock.schedule_once(lambda dt: self.terminal.add_message('Spray completed (no plunge)', 'success'), 0)
                Clock.schedule_once(lambda dt: app.end_operation('spray_plunge'), 0)
                return

            # 2) Wait half of plunge delay, then energize retract.
            half_delay = max(0.0, plunge_delay_s / 2.0)
            remaining_delay = max(0.0, plunge_delay_s - half_delay)

            if half_delay > 0:
                if self.terminal:
                    Clock.schedule_once(
                        lambda dt: self.terminal.add_message(f'Waiting {half_delay:.3f}s before retract', 'info'),
                        0,
                    )
                _time.sleep(half_delay)

            if GPIO:
                try:
                    GPIO.output(O_retract_solenoid, GPIO.HIGH)
                    if self.terminal:
                        Clock.schedule_once(lambda dt: self.terminal.add_message('Retract solenoid energized', 'info'), 0)
                except Exception as exc:
                    if self.terminal:
                        Clock.schedule_once(
                            lambda dt, err=str(exc): self.terminal.add_message(f'Retract solenoid error: {err}', 'error'),
                            0,
                        )

            # 3) Wait rest of delay, then plunge.
            if remaining_delay > 0:
                _time.sleep(remaining_delay)

            if GPIO:
                try:
                    GPIO.output(O_plunger_solenoid, GPIO.LOW)
                    GPIO.output(O_retract_solenoid, GPIO.LOW)
                except Exception as exc:
                    if self.terminal:
                        Clock.schedule_once(
                            lambda dt, err=str(exc): self.terminal.add_message(f'Plunge solenoid error: {err}', 'error'),
                            0,
                        )

            def on_done(dt):
                if self.terminal:
                    self.terminal.add_message('Process completed', 'success')
                app.end_operation('spray_plunge')
            Clock.schedule_once(on_done, 0)

        Thread(target=run_sequence, daemon=True).start()


class CleaningPanel(BoxLayout):
    """Cleaning panel widget"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = 10
        self.spacing = 8
        self.terminal = None  # Will be set by main app
        
        # Add background color
        with self.canvas.before:
            Color(*COLORS["panel"])
            self.rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_rect, size=self._update_rect)
        
        # Title
        title = Label(
            text='Cleaning',
            color=COLORS["text"],
            font_size='22sp',
            size_hint_y=None,
            height=26,
            bold=True
        )
        
        # Subtitle
        subtitle = Label(
            text='Define pulse and cycles, then run.',
            color=COLORS["muted"],
            font_size='13sp',
            size_hint_y=None,
            height=15
        )
        
        # Cleaning cycles input
        self.clean_cycles = NumericInputRow('Cleaning cycles', default_value='5', step=1)
        
        # Cleaning pulse input
        self.clean_pulse = NumericInputRow('Cleaning pulse (ms)', default_value='200', step=10)
        
        # Clean button
        self.clean_btn = Button(
            text='Clean',
            font_size='22sp',
            size_hint_y=None,
            height=60,
            background_color=COLORS["accent"],
            background_normal=''
        )
        self.clean_btn.bind(on_release=self.clean_process)
        
        # Add all widgets
        self.add_widget(title)
        self.add_widget(subtitle)
        self.add_widget(self.clean_cycles)
        self.add_widget(self.clean_pulse)
        self.add_widget(self.clean_btn)
    
    def _update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size
    
    def clean_process(self, instance):
        app = App.get_running_app()
        if not app.try_begin_operation('clean'):
            if self.terminal:
                self.terminal.add_message('System busy: finish current operation first', 'warning')
            return

        print("Starting clean process")
        spraytime = str(float(self.clean_pulse.get_value()) / 1000)
        cycles = self.clean_cycles.get_value()
        self.clean_btn.disabled = True
        if self.terminal:
            self.terminal.add_message(f'Starting cleaning ({cycles} cycles, {spraytime}s pulse)', 'info')
        scripts_dir = os.path.dirname(os.path.abspath(__file__))
        script_path = os.path.join(scripts_dir, "SIOclean.py")
        arguments = ["python3", script_path, "--stime", spraytime, "--cycles", cycles]
        process = Popen(
            arguments,
            cwd=scripts_dir,
            stdout=PIPE,
            stderr=STDOUT,
            text=True,
            bufsize=1,
        )
        
        # Stream subprocess output and update completion only when it really exits.
        def wait_for_completion():
            if process.stdout is not None:
                for line in process.stdout:
                    msg = line.rstrip()
                    if msg:
                        Clock.schedule_once(
                            lambda dt, text=msg: self.terminal.add_message(text, 'info'),
                            0,
                        )

            process.wait()

            def on_done(dt):
                self.clean_btn.disabled = False
                if process.returncode == 0:
                    self.terminal.add_message('Cleaning process completed', 'success')
                else:
                    self.terminal.add_message(
                        f'Cleaning process failed (exit {process.returncode})',
                        'error',
                    )
                app.end_operation('clean')

            Clock.schedule_once(on_done, 0)
        
        Thread(target=wait_for_completion, daemon=True).start()


class StatusBar(BoxLayout):
    """Status indicator bar for device status"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = 40
        self.padding = 10
        self.spacing = 20
        
        # Add background color
        with self.canvas.before:
            Color(*COLORS["panel"])
            self.rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_rect, size=self._update_rect)
        
        # Status label
        status_label = Label(
            text='Status:',
            color=COLORS["text"],
            font_size='18sp',
            size_hint_x=0.15,
            bold=True,
            halign='left',
            valign='middle'
        )
        status_label.bind(size=status_label.setter('text_size'))
        
        # Cryostat interlock indicator
        cryostat_layout = BoxLayout(orientation='horizontal', spacing=15, size_hint_x=0.4)
        self.cryostat_indicator = StatusIndicator()
        cryostat_label = Label(
            text='Cryostat Interlock',
            color=COLORS["text"],
            font_size='17sp',
            halign='left',
            valign='middle'
        )
        cryostat_label.bind(size=cryostat_label.setter('text_size'))
        self.cryostat_state_label = Label(
            text='Unknown',
            color=COLORS["muted"],
            font_size='16sp',
            size_hint_x=0.35,
            halign='left',
            valign='middle'
        )
        self.cryostat_state_label.bind(size=self.cryostat_state_label.setter('text_size'))
        cryostat_layout.add_widget(self.cryostat_indicator)
        cryostat_layout.add_widget(cryostat_label)
        cryostat_layout.add_widget(self.cryostat_state_label)
        
        # Plunger position indicator
        plunger_layout = BoxLayout(orientation='horizontal', spacing=15, size_hint_x=0.4)
        self.plunger_indicator = StatusIndicator()
        plunger_label = Label(
            text='Plunger Position',
            color=COLORS["text"],
            font_size='17sp',
            halign='left',
            valign='middle'
        )
        plunger_label.bind(size=plunger_label.setter('text_size'))
        self.plunger_state_label = Label(
            text='Unknown',
            color=COLORS["muted"],
            font_size='16sp',
            size_hint_x=0.35,
            halign='left',
            valign='middle'
        )
        self.plunger_state_label.bind(size=self.plunger_state_label.setter('text_size'))
        plunger_layout.add_widget(self.plunger_indicator)
        plunger_layout.add_widget(plunger_label)
        plunger_layout.add_widget(self.plunger_state_label)
        
        # Add all widgets
        self.add_widget(status_label)
        self.add_widget(cryostat_layout)
        self.add_widget(plunger_layout)
    
    def _update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size
    
    def set_cryostat_status(self, active):
        """Update cryostat interlock status - True = OK, False = EMPTY, None = unknown"""
        if active is True:
            self.cryostat_indicator.set_color(COLORS["accent"])
            self.cryostat_state_label.text = 'OK'
            self.cryostat_state_label.color = COLORS["accent"]
        elif active is False:
            self.cryostat_indicator.set_color(COLORS["danger"])
            self.cryostat_state_label.text = 'EMPTY'
            self.cryostat_state_label.color = COLORS["danger"]
        else:
            self.cryostat_indicator.set_color(COLORS["muted"])
            self.cryostat_state_label.text = 'N/A'
            self.cryostat_state_label.color = COLORS["muted"]
    
    def set_plunger_status(self, position):
        """Update plunger position - 'ready' = green, 'plunged' = red, else muted"""
        if position == 'ready':
            self.plunger_indicator.set_color(COLORS["accent"])
            self.plunger_state_label.text = 'READY'
            self.plunger_state_label.color = COLORS["accent"]
        elif position == 'plunged':
            self.plunger_indicator.set_color(COLORS["danger"])
            self.plunger_state_label.text = 'PLUNGED'
            self.plunger_state_label.color = COLORS["danger"]
        else:
            self.plunger_indicator.set_color(COLORS["muted"])
            self.plunger_state_label.text = 'N/A'
            self.plunger_state_label.color = COLORS["muted"]


class ShakeItOffApp(App):
    INTERLOCK_POLL_INTERVAL_S = 0.2

    def build(self):
        self.active_operation = None
        self.interlock_poll_event = None
        self.interlock_monitor_ready = False
        self.interlock_error_logged = False
        self.plunger_error_logged = False
        self.interlock_pin_ready = False
        self.plunger_pin_ready = False

        # Set window background color
        Window.clearcolor = COLORS["bg"]
        
        # Main layout with proper constraints
        main_layout = BoxLayout(
            orientation='vertical',
            padding=15,
            spacing=10
        )
        
        # Header - fixed height
        header_layout = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            height=70,
            spacing=4
        )
        
        header = Label(
            text='Shake-it-off',
            color=COLORS["accent"],
            font_size='32sp',
            size_hint_y=None,
            height=44,
            bold=True
        )
        
        # subheader = Label(
        #    text='Ergonomic control for spray, plunge, and cleaning cycles',
        #    color=COLORS["muted"],
        #    font_size='16sp',
        #    size_hint_y=None,
        #    height=30
        #)
        
        header_layout.add_widget(header)
        #header_layout.add_widget(subheader)
        
        # Content layout (two panels side by side) - proportional
        content_layout = BoxLayout(
            orientation='horizontal',
            spacing=15,
            size_hint_y=0.8
        )
        
        # Control panel
        self.control_panel = ControlPanel(size_hint_x=0.6, size_hint_y=1)
        
        # Cleaning panel
        self.cleaning_panel = CleaningPanel(size_hint_x=0.4, size_hint_y=1)
        
        # Add panels to content layout
        content_layout.add_widget(self.control_panel)
        content_layout.add_widget(self.cleaning_panel)
        
        # Terminal message box - proportional
        self.terminal = TerminalBox(size_hint_y=0.2)
        
        # Status bar at bottom - fixed height
        self.status_bar = StatusBar(size_hint_y=None, height=55)
        
        # Add to main layout in order
        main_layout.add_widget(header_layout)
        main_layout.add_widget(content_layout)
        main_layout.add_widget(self.terminal)
        main_layout.add_widget(self.status_bar)
        
        # Link terminal to panels for message logging
        self.control_panel.terminal = self.terminal
        self.control_panel.app = self
        self.cleaning_panel.terminal = self.terminal
        self.cleaning_panel.app = self
        
        # Initial messages
        self.terminal.add_message('System initialized', 'success')
        self.terminal.add_message('Ready for operations', 'info')

        self.setup_interlock_monitor()
        
        return main_layout

    def try_begin_operation(self, name):
        if self.active_operation is not None:
            return False
        self.active_operation = name
        return True

    def end_operation(self, name=None):
        if name is None or self.active_operation == name:
            self.active_operation = None

    def setup_interlock_monitor(self):
        if GPIO is None:
            self.status_bar.set_cryostat_status(None)
            self.status_bar.set_plunger_status('unknown')
            self.terminal.add_message('Cryostat interlock + plunger monitor unavailable (RPi.GPIO not found)', 'warning')
            return

        try:
            GPIO.setwarnings(False)
            GPIO.setmode(GPIO.BCM)
        except Exception as exc:
            self.status_bar.set_cryostat_status(None)
            self.status_bar.set_plunger_status('unknown')
            self.terminal.add_message(f'Failed to initialize GPIO monitor: {exc}', 'error')
            return

        # Keep sensor power on for the lifetime of the GUI
        try:
            GPIO.setup(O_sensors_pwr, GPIO.OUT)
            GPIO.output(O_sensors_pwr, GPIO.HIGH)
            self.sensors_powered = True
        except Exception as exc:
            self.sensors_powered = False
            self.terminal.add_message(f'Failed to power sensors: {exc}', 'error')

        # Setup solenoid output pins (held LOW until armed)
        try:
            GPIO.setup(O_plunger_solenoid, GPIO.OUT, initial=GPIO.LOW)
            GPIO.setup(O_retract_solenoid, GPIO.OUT, initial=GPIO.LOW)
            self.solenoids_ready = True
        except Exception as exc:
            self.solenoids_ready = False
            self.terminal.add_message(f'Failed to setup solenoid pins: {exc}', 'error')

        try:
            GPIO.setup(I_cryostat_sensor_sig, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            self.interlock_pin_ready = True
        except Exception as exc:
            self.status_bar.set_cryostat_status(None)
            self.terminal.add_message(f'Failed to start cryostat interlock monitor: {exc}', 'error')

        try:
            GPIO.setup(I_plunger_irsensor_sig, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            self.plunger_pin_ready = True
        except Exception as exc:
            self.status_bar.set_plunger_status('unknown')
            self.terminal.add_message(f'Failed to start plunger IR monitor: {exc}', 'error')

        if not self.interlock_pin_ready and not self.plunger_pin_ready:
            return

        self.interlock_monitor_ready = True
        if self.interlock_pin_ready and self.plunger_pin_ready:
            self.terminal.add_message('Cryostat + plunger monitor started', 'info')
        elif self.interlock_pin_ready:
            self.terminal.add_message('Cryostat interlock monitor started', 'warning')
        else:
            self.terminal.add_message('Plunger IR monitor started', 'warning')

        self.poll_interlock_state(0)
        self.interlock_poll_event = Clock.schedule_interval(
            self.poll_interlock_state,
            self.INTERLOCK_POLL_INTERVAL_S,
        )

    def poll_interlock_state(self, dt):
        if not self.interlock_monitor_ready:
            return

        if self.interlock_pin_ready:
            try:
                interlock_signal = GPIO.input(I_cryostat_sensor_sig)
                interlock_ok = interlock_signal == GPIO.LOW
                self.status_bar.set_cryostat_status(interlock_ok)

                # Gate the Ready button on interlock status
                cp = self.control_panel
                if not cp.armed:
                    if interlock_ok and cp.powerup_btn.disabled:
                        cp.powerup_btn.disabled = False
                    elif not interlock_ok and not cp.powerup_btn.disabled:
                        cp.powerup_btn.disabled = True
            except Exception as exc:
                self.status_bar.set_cryostat_status(None)
                self.control_panel.powerup_btn.disabled = True
                if not self.interlock_error_logged:
                    self.terminal.add_message(f'Cryostat interlock read error: {exc}', 'error')
                    self.interlock_error_logged = True

        if self.plunger_pin_ready:
            try:
                plunger_signal = GPIO.input(I_plunger_irsensor_sig)
                plunger_position = 'ready' if plunger_signal == GPIO.LOW else 'plunged'
                self.status_bar.set_plunger_status(plunger_position)

                # Enable Spray & Plunge only when armed and plunger is in ready position
                cp = self.control_panel
                if cp.armed and plunger_position == 'ready':
                    if cp.start_btn.disabled:
                        cp.start_btn.disabled = False
                        self.terminal.add_message('Plunger in position — ready to fire', 'success')
                elif cp.armed and plunger_position != 'ready':
                    cp.start_btn.disabled = True

                # Abort: de-energize plunger solenoid once sensor confirms plunger has retracted
                if cp.aborting and plunger_position == 'plunged':
                    cp.aborting = False
                    if GPIO:
                        try:
                            GPIO.output(O_plunger_solenoid, GPIO.LOW)
                        except Exception:
                            pass
                    cp.powerdown_btn.disabled = False
                    self.end_operation('abort')
                    self.terminal.add_message('Plunger retracted — system safe', 'info')
            except Exception as exc:
                self.status_bar.set_plunger_status('unknown')
                if not self.plunger_error_logged:
                    self.terminal.add_message(f'Plunger IR read error: {exc}', 'error')
                    self.plunger_error_logged = True

    def on_stop(self):
        if self.interlock_poll_event is not None:
            self.interlock_poll_event.cancel()
            self.interlock_poll_event = None

        if GPIO is not None and self.interlock_monitor_ready:
            try:
                if self.interlock_pin_ready:
                    GPIO.cleanup(I_cryostat_sensor_sig)
                if self.plunger_pin_ready:
                    GPIO.cleanup(I_plunger_irsensor_sig)
            except Exception:
                pass

        if GPIO is not None and getattr(self, 'sensors_powered', False):
            try:
                GPIO.output(O_sensors_pwr, GPIO.LOW)
                GPIO.cleanup(O_sensors_pwr)
            except Exception:
                pass

        if GPIO is not None and getattr(self, 'solenoids_ready', False):
            try:
                GPIO.output(O_plunger_solenoid, GPIO.LOW)
                GPIO.output(O_retract_solenoid, GPIO.LOW)
                GPIO.cleanup(O_plunger_solenoid)
                GPIO.cleanup(O_retract_solenoid)
            except Exception:
                pass


if __name__ == '__main__':
    ShakeItOffApp().run()
