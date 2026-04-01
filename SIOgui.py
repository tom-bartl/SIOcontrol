#!/usr/bin/env python3

import os
import sys
import time
from subprocess import PIPE, STDOUT, Popen
from threading import Thread

try:
    from PyQt6.QtCore import QTimer, Qt, pyqtSignal
    from PyQt6.QtGui import QFont, QIntValidator
    from PyQt6.QtWidgets import (
        QApplication,
        QCheckBox,
        QFrame,
        QGridLayout,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMainWindow,
        QPushButton,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )
except ImportError:
    from PyQt5.QtCore import QTimer, Qt, pyqtSignal
    from PyQt5.QtGui import QFont, QIntValidator
    from PyQt5.QtWidgets import (
        QApplication,
        QCheckBox,
        QFrame,
        QGridLayout,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMainWindow,
        QPushButton,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )

from SIOpinlist import (
    I_cryostat_sensor_sig,
    I_plunger_irsensor_sig,
    O_plunger_solenoid,
    O_retract_solenoid,
    O_sensors_pwr,
)

try:
    import RPi.GPIO as GPIO
except ImportError:
    GPIO = None


def bold_weight():
    if hasattr(QFont, "Weight"):
        return QFont.Weight.Bold
    return QFont.Bold


def align_left():
    if hasattr(Qt, "AlignmentFlag"):
        return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
    return Qt.AlignLeft | Qt.AlignVCenter


def button_style(enabled_bg, disabled_bg="#616161", enabled_fg="white", disabled_fg="#cfcfcf"):
    return (
        "QPushButton {"
        f"background:{enabled_bg};"
        f"color:{enabled_fg};"
        "border:none;"
        "border-radius:8px;"
        "padding:8px 14px;"
        "}"
        "QPushButton:disabled {"
        f"background:{disabled_bg};"
        f"color:{disabled_fg};"
        "}"
    )


class TouchButton(QPushButton):
    """QPushButton with debounce for noisy touchscreens."""

    def __init__(self, text, debounce_s=0.22, parent=None):
        super().__init__(text, parent)
        self.debounce_s = debounce_s
        self.last_click_ts = 0.0
        self.setMinimumHeight(70)
        self.setFont(QFont("DejaVu Sans", 18, bold_weight()))

    def mousePressEvent(self, event):
        now = time.monotonic()
        if now - self.last_click_ts < self.debounce_s:
            event.accept()
            return
        self.last_click_ts = now
        super().mousePressEvent(event)


class NumericInputRow(QWidget):
    def __init__(self, label_text, default_value="5", step=1, parent=None):
        super().__init__(parent)
        self.step = step

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        self.label = QLabel(label_text)
        self.label.setFont(QFont("DejaVu Sans", 14))
        self.label.setAlignment(align_left())

        self.minus_btn = TouchButton("-", debounce_s=0.10)
        self.minus_btn.setMinimumHeight(48)
        self.minus_btn.setMaximumWidth(64)

        self.input = QLineEdit(default_value)
        self.input.setValidator(QIntValidator(0, 999999, self))
        self.input.setFont(QFont("DejaVu Sans Mono", 14))
        self.input.setMaximumWidth(120)

        self.plus_btn = TouchButton("+", debounce_s=0.10)
        self.plus_btn.setMinimumHeight(48)
        self.plus_btn.setMaximumWidth(64)

        row.addWidget(self.label, 1)
        row.addWidget(self.minus_btn)
        row.addWidget(self.input)
        row.addWidget(self.plus_btn)

        self.minus_btn.clicked.connect(self.decrement)
        self.plus_btn.clicked.connect(self.increment)

    def get_int(self):
        try:
            return int(self.input.text())
        except ValueError:
            return 0

    def increment(self):
        self.input.setText(str(self.get_int() + self.step))

    def decrement(self):
        self.input.setText(str(max(0, self.get_int() - self.step)))


class SIOWindow(QMainWindow):
    ui_callback_signal = pyqtSignal(object)
    INTERLOCK_POLL_INTERVAL_MS = 200

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Shake-it-off")
        self.setGeometry(0, 100, 1280, 560)

        self.active_operation = None
        self.armed = False
        self.aborting = False

        self.interlock_monitor_ready = False
        self.interlock_error_logged = False
        self.plunger_error_logged = False
        self.interlock_pin_ready = False
        self.plunger_pin_ready = False
        self.sensors_powered = False
        self.solenoids_ready = False

        self._build_ui()
        self._wire_actions()
        self.ui_callback_signal.connect(self._run_ui_callback)
        self.setup_interlock_monitor()

        self.add_message("System initialized", "success")
        self.add_message("Ready for operations", "info")
        self.update_button_states()

    def _build_ui(self):
        central = QWidget(self)
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(8)

        header = QLabel("Shake-it-off")
        header.setFont(QFont("DejaVu Sans", 30, bold_weight()))
        root.addWidget(header)

        content = QHBoxLayout()
        content.setSpacing(12)

        self.control_panel = QFrame()
        self.control_panel.setFrameShape(QFrame.Shape.StyledPanel if hasattr(QFrame, "Shape") else QFrame.StyledPanel)
        cp_layout = QVBoxLayout(self.control_panel)
        cp_layout.setSpacing(8)

        cp_title = QLabel("Run Cycle")
        cp_title.setFont(QFont("DejaVu Sans", 20, bold_weight()))
        cp_sub = QLabel("Adjust timings, power up, then start.")
        cp_sub.setFont(QFont("DejaVu Sans", 11))

        self.spray_time = NumericInputRow("Spray time (ms)", "5", 1)
        self.plunge_delay = NumericInputRow("Plunge delay (ms)", "5", 1)

        button_grid = QGridLayout()
        button_grid.setHorizontalSpacing(8)
        button_grid.setVerticalSpacing(8)

        self.ready_btn = TouchButton("Ready")
        self.abort_btn = TouchButton("Abort")
        self.spray_btn = TouchButton("Spray & Plunge")

        self.ready_btn.setStyleSheet(button_style("#2e7d32", disabled_bg="#6d8c6f"))
        self.abort_btn.setStyleSheet(button_style("#ef6c00", disabled_bg="#9a7b63"))
        self.spray_btn.setStyleSheet(button_style("#c62828", disabled_bg="#8f6a6a"))

        self.ready_btn.setEnabled(False)
        self.spray_btn.setEnabled(False)

        button_grid.addWidget(self.ready_btn, 0, 0)
        button_grid.addWidget(self.abort_btn, 0, 1)
        button_grid.addWidget(self.spray_btn, 1, 0, 1, 2)

        self.no_plunge = QCheckBox("Do not plunge")
        self.no_plunge.setFont(QFont("DejaVu Sans", 12))

        cp_layout.addWidget(cp_title)
        cp_layout.addWidget(cp_sub)
        cp_layout.addWidget(self.spray_time)
        cp_layout.addWidget(self.plunge_delay)
        cp_layout.addLayout(button_grid)
        cp_layout.addWidget(self.no_plunge)
        cp_layout.addStretch(1)

        self.clean_panel = QFrame()
        self.clean_panel.setFrameShape(QFrame.Shape.StyledPanel if hasattr(QFrame, "Shape") else QFrame.StyledPanel)
        cl_layout = QVBoxLayout(self.clean_panel)
        cl_layout.setSpacing(8)

        cl_title = QLabel("Cleaning")
        cl_title.setFont(QFont("DejaVu Sans", 20, bold_weight()))
        cl_sub = QLabel("Define pulse and cycles, then run.")
        cl_sub.setFont(QFont("DejaVu Sans", 11))

        self.clean_cycles = NumericInputRow("Cleaning cycles", "5", 1)
        self.clean_pulse = NumericInputRow("Cleaning pulse (ms)", "200", 10)

        self.clean_btn = TouchButton("Clean")
        self.clean_btn.setStyleSheet(button_style("#0277bd", disabled_bg="#607d8b"))

        cl_layout.addWidget(cl_title)
        cl_layout.addWidget(cl_sub)
        cl_layout.addWidget(self.clean_cycles)
        cl_layout.addWidget(self.clean_pulse)
        cl_layout.addWidget(self.clean_btn)
        cl_layout.addStretch(1)

        content.addWidget(self.control_panel, 3)
        content.addWidget(self.clean_panel, 2)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setFont(QFont("DejaVu Sans Mono", 11))
        self.log.setMinimumHeight(130)

        status_row = QHBoxLayout()
        status_row.setSpacing(22)

        self.cryostat_dot = QLabel("●")
        self.cryostat_dot.setFont(QFont("DejaVu Sans", 20, bold_weight()))
        self.cryostat_label = QLabel("Cryostat Interlock: N/A")
        self.cryostat_label.setFont(QFont("DejaVu Sans", 13))

        self.plunger_dot = QLabel("●")
        self.plunger_dot.setFont(QFont("DejaVu Sans", 20, bold_weight()))
        self.plunger_label = QLabel("Plunger Position: N/A")
        self.plunger_label.setFont(QFont("DejaVu Sans", 13))

        status_row.addWidget(self.cryostat_dot)
        status_row.addWidget(self.cryostat_label)
        status_row.addSpacing(30)
        status_row.addWidget(self.plunger_dot)
        status_row.addWidget(self.plunger_label)
        status_row.addStretch(1)

        root.addLayout(content, 1)
        root.addWidget(self.log)
        root.addLayout(status_row)

        self.set_cryostat_status(None)
        self.set_plunger_status("unknown")

    def _wire_actions(self):
        self.ready_btn.clicked.connect(self.power_up)
        self.abort_btn.clicked.connect(self.power_down)
        self.spray_btn.clicked.connect(self.start_process)
        self.clean_btn.clicked.connect(self.clean_process)

        self.poll_timer = QTimer(self)
        self.poll_timer.setInterval(self.INTERLOCK_POLL_INTERVAL_MS)
        self.poll_timer.timeout.connect(self.poll_interlock_state)

    def add_message(self, text, level="info"):
        ts = time.strftime("%H:%M:%S")
        self.log.append(f"[{ts}] {text}")

    def post_ui(self, callback):
        self.ui_callback_signal.emit(callback)

    def _run_ui_callback(self, callback):
        callback()

    def try_begin_operation(self, name):
        if self.active_operation is not None:
            return False
        self.active_operation = name
        return True

    def end_operation(self, name=None):
        if name is None or self.active_operation == name:
            self.active_operation = None
            self.update_button_states()

    def update_button_states(self):
        interlock_ok = self.cryostat_label.text().endswith("OK")
        plunger_ready = self.plunger_label.text().endswith("READY")
        busy = self.active_operation is not None

        self.ready_btn.setEnabled((not busy) and (not self.armed) and interlock_ok)
        self.spray_btn.setEnabled((not busy) and self.armed and plunger_ready)
        self.clean_btn.setEnabled(self.active_operation in (None, "clean"))
        self.abort_btn.setEnabled((not self.aborting) and self.active_operation in (None, "abort"))

    def set_cryostat_status(self, active):
        if active is True:
            self.cryostat_dot.setStyleSheet("color:#2e7d32;")
            self.cryostat_label.setText("Cryostat Interlock: OK")
        elif active is False:
            self.cryostat_dot.setStyleSheet("color:#b71c1c;")
            self.cryostat_label.setText("Cryostat Interlock: EMPTY")
        else:
            self.cryostat_dot.setStyleSheet("color:#757575;")
            self.cryostat_label.setText("Cryostat Interlock: N/A")

    def set_plunger_status(self, position):
        if position == "ready":
            self.plunger_dot.setStyleSheet("color:#2e7d32;")
            self.plunger_label.setText("Plunger Position: READY")
        elif position == "plunged":
            self.plunger_dot.setStyleSheet("color:#b71c1c;")
            self.plunger_label.setText("Plunger Position: PLUNGED")
        else:
            self.plunger_dot.setStyleSheet("color:#757575;")
            self.plunger_label.setText("Plunger Position: N/A")

    def power_up(self):
        if not self.try_begin_operation("ready"):
            self.add_message("System busy: finish current operation first", "warning")
            return

        self.add_message("Powering up system...", "info")
        self.update_button_states()

        if GPIO:
            try:
                GPIO.output(O_plunger_solenoid, GPIO.HIGH)
            except Exception as exc:
                self.add_message(f"Plunger solenoid error: {exc}", "error")
                self.end_operation("ready")
                return

        process = Popen(["python3", "SIOpowerupdown.py", "--updown", "up"])

        def wait_done():
            process.wait()

            def on_done():
                if process.returncode == 0:
                    self.armed = True
                    self.add_message("Plunger solenoid energized, spray armed", "success")
                    self.add_message("Waiting for plunger ready position...", "info")
                else:
                    if GPIO:
                        try:
                            GPIO.output(O_plunger_solenoid, GPIO.LOW)
                        except Exception:
                            pass
                    self.add_message("Spray arm failed", "error")
                self.update_button_states()
                self.end_operation("ready")

            self.post_ui(on_done)

        Thread(target=wait_done, daemon=True).start()

    def power_down(self):
        if not self.try_begin_operation("abort"):
            self.add_message("System busy: finish current operation first", "warning")
            return

        self.add_message("Abort - disarming spray, waiting for plunger to retract...", "warning")
        self.armed = False
        self.aborting = True
        self.update_button_states()

        if GPIO:
            try:
                GPIO.output(O_retract_solenoid, GPIO.LOW)
            except Exception:
                pass

        process = Popen(["python3", "SIOpowerupdown.py", "--updown", "down"])

        def wait_done():
            process.wait()

        Thread(target=wait_done, daemon=True).start()

    def start_process(self):
        if not self.try_begin_operation("spray_plunge"):
            self.add_message("System busy: finish current operation first", "warning")
            return

        spraytime_s = self.spray_time.get_int() / 1000.0
        plunge_delay_s = self.plunge_delay.get_int() / 1000.0
        spraytime = str(spraytime_s)
        self.add_message(
            f"Starting spray & plunge (spray: {spraytime_s}s, delay: {plunge_delay_s}s)",
            "info",
        )

        self.armed = False
        self.update_button_states()

        scripts_dir = os.path.dirname(os.path.abspath(__file__))
        script_path = os.path.join(scripts_dir, "SIOapplyandplunge.py")
        arguments = ["python3", script_path, "--stime", spraytime]
        plunge_disabled = self.no_plunge.isChecked()
        if plunge_disabled:
            self.add_message("Plunge disabled", "warning")

        def run_sequence():
            import time as _time

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
                    if msg:
                        self.post_ui(lambda text=msg: self.add_message(text, "info"))

            process.wait()

            if process.returncode != 0:
                self.post_ui(
                    lambda: self.add_message(
                        f"Spray process failed (exit {process.returncode})", "error"
                    )
                )
                self.post_ui(lambda: self.end_operation("spray_plunge"))
                return

            if plunge_disabled:
                self.post_ui(lambda: self.add_message("Spray completed (plunge disabled, retract only)", "info"))

            half_delay = max(0.0, plunge_delay_s / 2.0)
            remaining_delay = max(0.0, plunge_delay_s - half_delay)
            retract_total_hold_s = 2.0

            if half_delay > 0:
                self.post_ui(
                    lambda: self.add_message(
                        f"Waiting {half_delay:.3f}s before retract", "info"
                    )
                )
                _time.sleep(half_delay)

            if GPIO:
                try:
                    GPIO.output(O_retract_solenoid, GPIO.HIGH)
                    self.post_ui(lambda: self.add_message("Retract solenoid energized", "info"))
                except Exception as exc:
                    self.post_ui(
                        lambda err=str(exc): self.add_message(
                            f"Retract solenoid error: {err}", "error"
                        )
                    )

            # Keep plunge timing accurate: wait only the configured remaining delay
            # before firing plunge, then keep retract energized afterward if needed.
            if remaining_delay > 0:
                _time.sleep(remaining_delay)

            if GPIO:
                try:
                    if plunge_disabled:
                        self.post_ui(
                            lambda: self.add_message(
                                f"Holding retract energized for {retract_total_hold_s:.3f}s", "info"
                            )
                        )
                        _time.sleep(retract_total_hold_s)
                    else:
                        GPIO.output(O_plunger_solenoid, GPIO.LOW)
                        post_plunge_hold_s = max(0.0, retract_total_hold_s - remaining_delay)
                        if post_plunge_hold_s > 0:
                            self.post_ui(
                                lambda: self.add_message(
                                    f"Holding retract energized for {post_plunge_hold_s:.3f}s after plunge", "info"
                                )
                            )
                            _time.sleep(post_plunge_hold_s)

                    GPIO.output(O_retract_solenoid, GPIO.LOW)
                except Exception as exc:
                    self.post_ui(
                        lambda err=str(exc): self.add_message(
                            f"Plunge/retract solenoid error: {err}", "error"
                        )
                    )

            def on_done():
                if plunge_disabled:
                    self.add_message("Process completed (retract only)", "success")
                else:
                    self.add_message("Process completed", "success")
                self.update_button_states()
                self.end_operation("spray_plunge")

            self.post_ui(on_done)

        Thread(target=run_sequence, daemon=True).start()

    def clean_process(self):
        if not self.try_begin_operation("clean"):
            self.add_message("System busy: finish current operation first", "warning")
            return

        spraytime = str(self.clean_pulse.get_int() / 1000.0)
        cycles = str(self.clean_cycles.get_int())
        self.update_button_states()
        self.add_message(f"Starting cleaning ({cycles} cycles, {spraytime}s pulse)", "info")

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

        def wait_for_completion():
            if process.stdout is not None:
                for line in process.stdout:
                    msg = line.rstrip()
                    if msg:
                        self.post_ui(lambda text=msg: self.add_message(text, "info"))

            process.wait()

            def on_done():
                if process.returncode == 0:
                    self.add_message("Cleaning process completed", "success")
                else:
                    self.add_message(
                        f"Cleaning process failed (exit {process.returncode})", "error"
                    )
                self.update_button_states()
                self.end_operation("clean")

            self.post_ui(on_done)

        Thread(target=wait_for_completion, daemon=True).start()

    def setup_interlock_monitor(self):
        if GPIO is None:
            self.set_cryostat_status(None)
            self.set_plunger_status("unknown")
            self.add_message(
                "Cryostat interlock + plunger monitor unavailable (RPi.GPIO not found)",
                "warning",
            )
            return

        try:
            GPIO.setwarnings(False)
            GPIO.setmode(GPIO.BCM)
        except Exception as exc:
            self.set_cryostat_status(None)
            self.set_plunger_status("unknown")
            self.add_message(f"Failed to initialize GPIO monitor: {exc}", "error")
            return

        try:
            GPIO.setup(O_sensors_pwr, GPIO.OUT)
            GPIO.output(O_sensors_pwr, GPIO.HIGH)
            self.sensors_powered = True
        except Exception as exc:
            self.sensors_powered = False
            self.add_message(f"Failed to power sensors: {exc}", "error")

        try:
            GPIO.setup(O_plunger_solenoid, GPIO.OUT, initial=GPIO.LOW)
            GPIO.setup(O_retract_solenoid, GPIO.OUT, initial=GPIO.LOW)
            self.solenoids_ready = True
        except Exception as exc:
            self.solenoids_ready = False
            self.add_message(f"Failed to setup solenoid pins: {exc}", "error")

        try:
            GPIO.setup(I_cryostat_sensor_sig, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            self.interlock_pin_ready = True
        except Exception as exc:
            self.set_cryostat_status(None)
            self.add_message(f"Failed to start cryostat interlock monitor: {exc}", "error")

        try:
            GPIO.setup(I_plunger_irsensor_sig, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            self.plunger_pin_ready = True
        except Exception as exc:
            self.set_plunger_status("unknown")
            self.add_message(f"Failed to start plunger IR monitor: {exc}", "error")

        if not self.interlock_pin_ready and not self.plunger_pin_ready:
            return

        self.interlock_monitor_ready = True
        if self.interlock_pin_ready and self.plunger_pin_ready:
            self.add_message("Cryostat + plunger monitor started", "info")
        elif self.interlock_pin_ready:
            self.add_message("Cryostat interlock monitor started", "warning")
        else:
            self.add_message("Plunger IR monitor started", "warning")

        self.poll_interlock_state()
        self.poll_timer.start()

    def poll_interlock_state(self):
        if not self.interlock_monitor_ready:
            return

        if self.interlock_pin_ready:
            try:
                interlock_signal = GPIO.input(I_cryostat_sensor_sig)
                interlock_ok = interlock_signal == GPIO.LOW
                self.set_cryostat_status(interlock_ok)
                self.update_button_states()
            except Exception as exc:
                self.set_cryostat_status(None)
                self.update_button_states()
                if not self.interlock_error_logged:
                    self.add_message(f"Cryostat interlock read error: {exc}", "error")
                    self.interlock_error_logged = True

        if self.plunger_pin_ready:
            try:
                plunger_signal = GPIO.input(I_plunger_irsensor_sig)
                plunger_position = "ready" if plunger_signal == GPIO.LOW else "plunged"
                self.set_plunger_status(plunger_position)

                if self.armed and plunger_position == "ready":
                    if not self.spray_btn.isEnabled() and self.active_operation is None:
                        self.add_message("Plunger in position - ready to fire", "success")
                self.update_button_states()

                if self.aborting and plunger_position == "plunged":
                    self.aborting = False
                    if GPIO:
                        try:
                            GPIO.output(O_plunger_solenoid, GPIO.LOW)
                        except Exception:
                            pass
                    self.update_button_states()
                    self.end_operation("abort")
                    self.add_message("Plunger retracted - system safe", "info")
            except Exception as exc:
                self.set_plunger_status("unknown")
                self.update_button_states()
                if not self.plunger_error_logged:
                    self.add_message(f"Plunger IR read error: {exc}", "error")
                    self.plunger_error_logged = True

    def closeEvent(self, event):
        if self.poll_timer.isActive():
            self.poll_timer.stop()

        if GPIO is not None and self.interlock_monitor_ready:
            try:
                if self.interlock_pin_ready:
                    GPIO.cleanup(I_cryostat_sensor_sig)
                if self.plunger_pin_ready:
                    GPIO.cleanup(I_plunger_irsensor_sig)
            except Exception:
                pass

        if GPIO is not None and self.sensors_powered:
            try:
                GPIO.output(O_sensors_pwr, GPIO.LOW)
                GPIO.cleanup(O_sensors_pwr)
            except Exception:
                pass

        if GPIO is not None and self.solenoids_ready:
            try:
                GPIO.output(O_plunger_solenoid, GPIO.LOW)
                GPIO.output(O_retract_solenoid, GPIO.LOW)
                GPIO.cleanup(O_plunger_solenoid)
                GPIO.cleanup(O_retract_solenoid)
            except Exception:
                pass

        event.accept()


def main():
    app = QApplication(sys.argv)
    window = SIOWindow()
    window.show()
    if hasattr(app, "exec"):
        sys.exit(app.exec())
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()