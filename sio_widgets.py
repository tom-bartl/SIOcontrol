"""Shared Kivy widgets and color palette for SIO GUIs."""

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, Rectangle, Ellipse
from datetime import datetime


COLORS = {
    "bg":       (0.04, 0.07, 0.13, 1),
    "panel":    (0.07, 0.09, 0.15, 1),
    "muted":    (0.58, 0.64, 0.72, 1),
    "text":     (0.90, 0.91, 0.92, 1),
    "accent":   (0.13, 0.77, 0.37, 1),
    "warn":     (0.96, 0.62, 0.04, 1),
    "danger":   (0.94, 0.27, 0.27, 1),
    "off":      (0.25, 0.25, 0.30, 1),
    "on":       (0.13, 0.77, 0.37, 1),
    "input_hi": (0.13, 0.77, 0.37, 1),
    "input_lo": (0.35, 0.38, 0.42, 1),
}


class StatusIndicator(Widget):
    """Colored circle indicator."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (24, 24)

        with self.canvas:
            self._color_instr = Color(*COLORS["muted"])
            self._ellipse = Ellipse(pos=self.pos, size=self.size)

        self.bind(pos=self._update, size=self._update)

    def _update(self, *_):
        self._ellipse.pos = self.pos
        self._ellipse.size = self.size

    def set_color(self, rgba):
        self._color_instr.rgba = rgba


class TerminalBox(BoxLayout):
    """Terminal-style log area."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = 6
        self.spacing = 4

        with self.canvas.before:
            Color(*COLORS["bg"])
            self._rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._upd_rect, size=self._upd_rect)

        header = Label(
            text='System Messages',
            color=COLORS["accent"],
            font_size='16sp',
            size_hint_y=None,
            height=20,
            bold=True,
            halign='left',
            valign='middle',
        )
        header.bind(size=header.setter('text_size'))

        self.scroll_view = ScrollView(
            size_hint=(1, 1),
            do_scroll_x=False,
            do_scroll_y=True,
            scroll_type=['bars', 'content'],
            bar_width=10,
        )

        self.terminal_text = TextInput(
            text='',
            readonly=True,
            font_name='RobotoMono-Regular',
            font_size='12sp',
            background_color=COLORS["bg"],
            foreground_color=COLORS["text"],
            cursor_color=(0, 0, 0, 0),
            size_hint_y=None,
        )
        self.terminal_text.bind(minimum_height=self.terminal_text.setter('height'))
        self.scroll_view.add_widget(self.terminal_text)

        self.add_widget(header)
        self.add_widget(self.scroll_view)

    def _upd_rect(self, *_):
        self._rect.pos = self.pos
        self._rect.size = self.size

    def add_message(self, message, msg_type='info'):
        ts = datetime.now().strftime('%H:%M:%S')
        prefix = {'success': '[OK]', 'warning': '[WARN]', 'error': '[ERR]'}.get(msg_type, '[INFO]')
        self.terminal_text.text += f'{ts} {prefix} {message}\n'
        self.scroll_view.scroll_y = 0

    def clear(self):
        self.terminal_text.text = ''
