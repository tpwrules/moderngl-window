import tkinter

from moderngl_window.context.base import BaseWindow
from moderngl_window.context.tk.keys import Keys
from pyopengltk import OpenGLFrame


class Window(BaseWindow):
    #: tkinter specific key constants
    keys = Keys

    _mouse_button_map = {
        1: 1,
        3: 2,
        2: 3,
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._tk = tkinter.Tk()
        self._gl_widget = ModernglTkWindow(self._tk, width=self.width, height=self.height)
        self._gl_widget.pack(fill=tkinter.BOTH, expand=tkinter.YES)
        self._tk.resizable(self._resizable, self._resizable)

        if self._fullscreen:
            self._tk.attributes('-fullscreen', True)

        if self._cursor is False:
            self._tk.config(cursor="none")

        # Set up events
        self._gl_widget.bind('<Configure>', self.tk_resize)
        self._tk.bind('<KeyPress>', self.tk_key_press)
        self._tk.bind('<KeyRelease>', self.tk_key_release)
        self._tk.bind('<Motion>', self.tk_mouse_motion)
        self._tk.bind('<Button>', self.tk_mouse_button_press)
        self._tk.bind('<ButtonRelease>', self.tk_mouse_button_release)
        self._tk.bind('<MouseWheel>', self.tk_mouse_wheel)

        self._tk.protocol("WM_DELETE_WINDOW", self.tk_close_window)

        self._tk.title(self._title)

        # Ensure the window is opened/visible
        self._tk.update()
        self._gl_widget.tkMakeCurrent()
        self.init_mgl_context()

        self.set_default_viewport()

    def swap_buffers(self) -> None:
        """Swap buffers, set viewport, trigger events and increment frame counter"""
        err = self._ctx.error
        if err != 'GL_NO_ERROR':
            print(err)

        # Ensure we process events or tkinter will eventually stall.
        self._tk.update_idletasks()
        self._tk.update()

        self._gl_widget.tkSwapBuffers()
        self._frames += 1

    def tk_key_press(self, event: tkinter.Event) -> None:
        """Handle all queued key press events in tkinter dispatching events to standard methods"""
        keys = self.keys
        self._key_event_func(event.keysym, self.keys.ACTION_PRESS, self._modifiers)

        if event.char:
            self._unicode_char_entered_func(event.char)
        else:
            self._handle_modifiers(event, True)

        if event.keysym == keys.ESCAPE:
            self.close()

    def tk_key_release(self, event: tkinter.Event) -> None:
        """Handle all queued key release events in tkinter dispatching events to standard methods

        Args:
            event (tkinter.Event): The key release event
        """
        self._key_event_func(event.keysym, self.keys.ACTION_RELEASE, self._modifiers)

        if not event.char:
            self._handle_modifiers(event, False)

    def tk_mouse_motion(self, event: tkinter.Event) -> None:
        """Handle and translate tkinter mouse position events

        Args:
            event (tkinter.Event): The mouse motion event
        """
        if self._mouse_buttons.any:
            self._mouse_drag_event_func(event.x, event.y)
        else:
            self._mouse_position_event_func(event.x, event.y)

    def tk_mouse_button_press(self, event: tkinter.Event) -> None:
        """Handle tkinter mouse press events.

        Args:
            event (tkinter.Event): The mouse button press event
        """
        button = self._mouse_button_map.get(event.num)
        if not button:
            return

        self._handle_mouse_button_state_change(button, True)
        self._mouse_press_event_func(event.x, event.y, button)

    def tk_mouse_button_release(self, event: tkinter.Event) -> None:
        """Handle tkinter mouse press events.

        Args:
            event (tkinter.Event): The mouse button release event
        """
        button = self._mouse_button_map.get(event.num)
        if not button:
            return

        self._handle_mouse_button_state_change(button, False)
        self._mouse_release_event_func(event.x, event.y, button)

    def tk_mouse_wheel(self, event: tkinter.Event) -> None:
        """Handle mouse wheel event.

        Args:
            event (tkinter.Event): The mouse wheel event
        """
        self._mouse_scroll_event_func(0, event.delta / 120.0)

    def _handle_modifiers(self, event: tkinter.Event, press: bool) -> None:
        """Update internal key modifiers

        Args:
            event (tkinter.Event): The key event
            press (bool): Press or release event
        """
        if event.keysym in ['Shift_L', 'Shift_R']:
            self._modifiers.shift = press
        elif event.keysym in ['Control_L', 'Control_R']:
            self._modifiers.ctrl = press

    def tk_resize(self, event) -> None:
        """tkinter specific window resize event.
        Forwards resize events to the configured resize function.

        Args:
            event (tkinter.Event): The resize event
        """
        self._width, self._height = event.width, event.height
        # TODO: How do we know the actual buffer size?
        self._buffer_width, self._buffer_height = event.width, event.height

        # Race condition when going fullscreen mode.
        # The moderngl context might not be created yet.
        if not self._ctx:
            return

        self.set_default_viewport()
        self._resize_func(event.width, event.height)

    def tk_close_window(self) -> None:
        """tkinter close window callback"""
        self._close = True

    def destroy(self) -> None:
        """Destroy logic for tkinter window. Currently empty."""
        pass


class ModernglTkWindow(OpenGLFrame):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def redraw(self):
        """pyopengltk's own render method."""
        pass

    def initgl(self):
        """pyopengltk's user code for initialization."""
        pass

    def tkResize(self, event):
        """Should never be called. Event overidden."""
        raise ValueError("tkResize should never be called. The event is overriden.")

    def tkMap(self, event):
        """Called when frame goes onto the screen"""
        # Only create context once
        # In a window like this we are not likely to lose the context
        # even when window is minimized.
        if not getattr(self, '_wid', None):
            super().tkMap(event)
