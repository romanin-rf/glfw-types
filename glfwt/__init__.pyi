from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals

import collections
import ctypes
import functools
import sys
from cffi import FFI
from .library import glfw as _glfw
from PIL import Image
from typing import *

__author__: str
__copyright__: str
__license__: str
__version__: str

ERROR_REPORTING: Literal['warning', 'exception', 'ignore']='warning'
NORMALIZE_GAMMA_RAMPS: bool = True
_PREVIEW: bool
ffi: FFI
_getcwd: Any

try:
    from cffi import FFI
except ImportError:
    _cffi_to_ctypes_void_p = lambda ptr: ptr
else:
    ffi = FFI()
    def _cffi_to_ctypes_void_p(ptr):
        if isinstance(ptr, ffi.CData):
            return ctypes.cast(int(ffi.cast('uintptr_t', ptr)), ctypes.c_void_p)
        return ptr

class GLFWError(UserWarning):
    """
    Exception class used for reporting GLFW errors.
    """
    def __init__(self, message, error_code=None):
        super(GLFWError, self).__init__(message)
        self.error_code = error_code

_callback_repositories: list

class _GLFWwindow(ctypes.Structure):
    """
    Wrapper for:
        typedef struct GLFWwindow GLFWwindow;
    """
    _fields_ = [("dummy", ctypes.c_int)]


class _GLFWmonitor(ctypes.Structure):
    """
    Wrapper for:
        typedef struct GLFWmonitor GLFWmonitor;
    """
    _fields_ = [("dummy", ctypes.c_int)]


class _GLFWvidmode(ctypes.Structure):
    """
    Wrapper for:
        typedef struct GLFWvidmode GLFWvidmode;
    """
    _fields_ = [("width", ctypes.c_int),
                ("height", ctypes.c_int),
                ("red_bits", ctypes.c_int),
                ("green_bits", ctypes.c_int),
                ("blue_bits", ctypes.c_int),
                ("refresh_rate", ctypes.c_uint)]

    GLFWvidmode = collections.namedtuple('GLFWvidmode', [
        'size', 'bits', 'refresh_rate'
    ])
    Size = collections.namedtuple('Size', [
        'width', 'height'
    ])
    Bits = collections.namedtuple('Bits', [
        'red', 'green', 'blue'
    ])

    def __init__(self):
        ctypes.Structure.__init__(self)
        self.width = 0
        self.height = 0
        self.red_bits = 0
        self.green_bits = 0
        self.blue_bits = 0
        self.refresh_rate = 0

    def wrap(self, video_mode):
        """
        Wraps a nested python sequence.
        """
        size, bits, self.refresh_rate = video_mode
        self.width, self.height = size
        self.red_bits, self.green_bits, self.blue_bits = bits

    def unwrap(self):
        """
        Returns a GLFWvidmode object.
        """
        size = self.Size(self.width, self.height)
        bits = self.Bits(self.red_bits, self.green_bits, self.blue_bits)
        return self.GLFWvidmode(size, bits, self.refresh_rate)


class _GLFWgammaramp(ctypes.Structure):
    """
    Wrapper for:
        typedef struct GLFWgammaramp GLFWgammaramp;
    """
    _fields_ = [("red", ctypes.POINTER(ctypes.c_ushort)),
                ("green", ctypes.POINTER(ctypes.c_ushort)),
                ("blue", ctypes.POINTER(ctypes.c_ushort)),
                ("size", ctypes.c_uint)]

    GLFWgammaramp = collections.namedtuple('GLFWgammaramp', [
        'red', 'green', 'blue'
    ])

    def __init__(self):
        ctypes.Structure.__init__(self)
        self.red = None
        self.red_array = None
        self.green = None
        self.green_array = None
        self.blue = None
        self.blue_array = None
        self.size = 0

    def wrap(self, gammaramp):
        """
        Wraps a nested python sequence.
        """
        red, green, blue = gammaramp
        size = min(len(red), len(green), len(blue))
        array_type = ctypes.c_ushort*size
        self.size = ctypes.c_uint(size)
        self.red_array = array_type()
        self.green_array = array_type()
        self.blue_array = array_type()
        if NORMALIZE_GAMMA_RAMPS:
            red = [value * 65535 for value in red]
            green = [value * 65535 for value in green]
            blue = [value * 65535 for value in blue]
        for i in range(self.size):
            self.red_array[i] = int(red[i])
            self.green_array[i] = int(green[i])
            self.blue_array[i] = int(blue[i])
        pointer_type = ctypes.POINTER(ctypes.c_ushort)
        self.red = ctypes.cast(self.red_array, pointer_type)
        self.green = ctypes.cast(self.green_array, pointer_type)
        self.blue = ctypes.cast(self.blue_array, pointer_type)

    def unwrap(self):
        """
        Returns a GLFWgammaramp object.
        """
        red = [self.red[i] for i in range(self.size)]
        green = [self.green[i] for i in range(self.size)]
        blue = [self.blue[i] for i in range(self.size)]
        if NORMALIZE_GAMMA_RAMPS:
            red = [value / 65535.0 for value in red]
            green = [value / 65535.0 for value in green]
            blue = [value / 65535.0 for value in blue]
        return self.GLFWgammaramp(red, green, blue)


class _GLFWcursor(ctypes.Structure):
    """
    Wrapper for:
        typedef struct GLFWcursor GLFWcursor;
    """
    _fields_ = [("dummy", ctypes.c_int)]


class _GLFWimage(ctypes.Structure):
    """
    Wrapper for:
        typedef struct GLFWimage GLFWimage;
    """
    _fields_ = [("width", ctypes.c_int),
                ("height", ctypes.c_int),
                ("pixels", ctypes.POINTER(ctypes.c_ubyte))]

    GLFWimage = collections.namedtuple('GLFWimage', [
        'width', 'height', 'pixels'
    ])

    def __init__(self):
        ctypes.Structure.__init__(self)
        self.width = 0
        self.height = 0
        self.pixels = None
        self.pixels_array = None

    def wrap(self, image):
        """
        Wraps a nested python sequence or PIL/pillow Image.
        """
        if hasattr(image, 'size') and hasattr(image, 'convert'):
            # Treat image as PIL/pillow Image object
            self.width, self.height = image.size
            array_type = ctypes.c_ubyte * 4 * (self.width * self.height)
            self.pixels_array = array_type()
            pixels = image.convert('RGBA').getdata()
            for i, pixel in enumerate(pixels):
                self.pixels_array[i] = pixel
        else:
            self.width, self.height, pixels = image
            array_type = ctypes.c_ubyte * 4 * self.width * self.height
            self.pixels_array = array_type()
            for i in range(self.height):
                for j in range(self.width):
                    for k in range(4):
                        self.pixels_array[i][j][k] = pixels[i][j][k]
        pointer_type = ctypes.POINTER(ctypes.c_ubyte)
        self.pixels = ctypes.cast(self.pixels_array, pointer_type)

    def unwrap(self):
        """
        Returns a GLFWimage object.
        """
        pixels = [[[int(c) for c in p] for p in l] for l in self.pixels_array]
        return self.GLFWimage(self.width, self.height, pixels)


class _GLFWgamepadstate(ctypes.Structure):
    """
    Wrapper for:
        typedef struct GLFWgamepadstate GLFWgamepadstate;
    """
    _fields_ = [("buttons", (ctypes.c_ubyte * 15)),
                ("axes", (ctypes.c_float * 6))]

    GLFWgamepadstate = collections.namedtuple('GLFWgamepadstate', [
        'buttons', 'axes'
    ])

    def __init__(self):
        ctypes.Structure.__init__(self)
        self.buttons = (ctypes.c_ubyte * 15)(* [0] * 15)
        self.axes = (ctypes.c_float * 6)(* [0] * 6)

    def wrap(self, gamepad_state):
        """
        Wraps a nested python sequence.
        """
        buttons, axes = gamepad_state
        for i in range(15):
            self.buttons[i] = buttons[i]
        for i in range(6):
            self.axes[i] = axes[i]

    def unwrap(self):
        """
        Returns a GLFWvidmode object.
        """
        buttons = [int(button) for button in self.buttons]
        axes = [float(axis) for axis in self.axes]
        return self.GLFWgamepadstate(buttons, axes)

VERSION_MAJOR = 3
VERSION_MINOR = 3
VERSION_REVISION = 4
TRUE = 1
FALSE = 0
RELEASE = 0
PRESS = 1
REPEAT = 2
HAT_CENTERED = 0
HAT_UP = 1
HAT_RIGHT = 2
HAT_DOWN = 4
HAT_LEFT = 8
HAT_RIGHT_UP = HAT_RIGHT | HAT_UP
HAT_RIGHT_DOWN = HAT_RIGHT | HAT_DOWN
HAT_LEFT_UP = HAT_LEFT | HAT_UP
HAT_LEFT_DOWN = HAT_LEFT | HAT_DOWN
KEY_UNKNOWN = -1
KEY_SPACE = 32
KEY_APOSTROPHE = 39
KEY_COMMA = 44
KEY_MINUS = 45
KEY_PERIOD = 46
KEY_SLASH = 47
KEY_0 = 48
KEY_1 = 49
KEY_2 = 50
KEY_3 = 51
KEY_4 = 52
KEY_5 = 53
KEY_6 = 54
KEY_7 = 55
KEY_8 = 56
KEY_9 = 57
KEY_SEMICOLON = 59
KEY_EQUAL = 61
KEY_A = 65
KEY_B = 66
KEY_C = 67
KEY_D = 68
KEY_E = 69
KEY_F = 70
KEY_G = 71
KEY_H = 72
KEY_I = 73
KEY_J = 74
KEY_K = 75
KEY_L = 76
KEY_M = 77
KEY_N = 78
KEY_O = 79
KEY_P = 80
KEY_Q = 81
KEY_R = 82
KEY_S = 83
KEY_T = 84
KEY_U = 85
KEY_V = 86
KEY_W = 87
KEY_X = 88
KEY_Y = 89
KEY_Z = 90
KEY_LEFT_BRACKET = 91
KEY_BACKSLASH = 92
KEY_RIGHT_BRACKET = 93
KEY_GRAVE_ACCENT = 96
KEY_WORLD_1 = 161
KEY_WORLD_2 = 162
KEY_ESCAPE = 256
KEY_ENTER = 257
KEY_TAB = 258
KEY_BACKSPACE = 259
KEY_INSERT = 260
KEY_DELETE = 261
KEY_RIGHT = 262
KEY_LEFT = 263
KEY_DOWN = 264
KEY_UP = 265
KEY_PAGE_UP = 266
KEY_PAGE_DOWN = 267
KEY_HOME = 268
KEY_END = 269
KEY_CAPS_LOCK = 280
KEY_SCROLL_LOCK = 281
KEY_NUM_LOCK = 282
KEY_PRINT_SCREEN = 283
KEY_PAUSE = 284
KEY_F1 = 290
KEY_F2 = 291
KEY_F3 = 292
KEY_F4 = 293
KEY_F5 = 294
KEY_F6 = 295
KEY_F7 = 296
KEY_F8 = 297
KEY_F9 = 298
KEY_F10 = 299
KEY_F11 = 300
KEY_F12 = 301
KEY_F13 = 302
KEY_F14 = 303
KEY_F15 = 304
KEY_F16 = 305
KEY_F17 = 306
KEY_F18 = 307
KEY_F19 = 308
KEY_F20 = 309
KEY_F21 = 310
KEY_F22 = 311
KEY_F23 = 312
KEY_F24 = 313
KEY_F25 = 314
KEY_KP_0 = 320
KEY_KP_1 = 321
KEY_KP_2 = 322
KEY_KP_3 = 323
KEY_KP_4 = 324
KEY_KP_5 = 325
KEY_KP_6 = 326
KEY_KP_7 = 327
KEY_KP_8 = 328
KEY_KP_9 = 329
KEY_KP_DECIMAL = 330
KEY_KP_DIVIDE = 331
KEY_KP_MULTIPLY = 332
KEY_KP_SUBTRACT = 333
KEY_KP_ADD = 334
KEY_KP_ENTER = 335
KEY_KP_EQUAL = 336
KEY_LEFT_SHIFT = 340
KEY_LEFT_CONTROL = 341
KEY_LEFT_ALT = 342
KEY_LEFT_SUPER = 343
KEY_RIGHT_SHIFT = 344
KEY_RIGHT_CONTROL = 345
KEY_RIGHT_ALT = 346
KEY_RIGHT_SUPER = 347
KEY_MENU = 348
KEY_LAST = KEY_MENU
MOD_SHIFT = 0x0001
MOD_CONTROL = 0x0002
MOD_ALT = 0x0004
MOD_SUPER = 0x0008
MOD_CAPS_LOCK = 0x0010
MOD_NUM_LOCK = 0x0020
MOUSE_BUTTON_1 = 0
MOUSE_BUTTON_2 = 1
MOUSE_BUTTON_3 = 2
MOUSE_BUTTON_4 = 3
MOUSE_BUTTON_5 = 4
MOUSE_BUTTON_6 = 5
MOUSE_BUTTON_7 = 6
MOUSE_BUTTON_8 = 7
MOUSE_BUTTON_LAST = MOUSE_BUTTON_8
MOUSE_BUTTON_LEFT = MOUSE_BUTTON_1
MOUSE_BUTTON_RIGHT = MOUSE_BUTTON_2
MOUSE_BUTTON_MIDDLE = MOUSE_BUTTON_3
JOYSTICK_1 = 0
JOYSTICK_2 = 1
JOYSTICK_3 = 2
JOYSTICK_4 = 3
JOYSTICK_5 = 4
JOYSTICK_6 = 5
JOYSTICK_7 = 6
JOYSTICK_8 = 7
JOYSTICK_9 = 8
JOYSTICK_10 = 9
JOYSTICK_11 = 10
JOYSTICK_12 = 11
JOYSTICK_13 = 12
JOYSTICK_14 = 13
JOYSTICK_15 = 14
JOYSTICK_16 = 15
JOYSTICK_LAST = JOYSTICK_16
GAMEPAD_BUTTON_A = 0
GAMEPAD_BUTTON_B = 1
GAMEPAD_BUTTON_X = 2
GAMEPAD_BUTTON_Y = 3
GAMEPAD_BUTTON_LEFT_BUMPER = 4
GAMEPAD_BUTTON_RIGHT_BUMPER = 5
GAMEPAD_BUTTON_BACK = 6
GAMEPAD_BUTTON_START = 7
GAMEPAD_BUTTON_GUIDE = 8
GAMEPAD_BUTTON_LEFT_THUMB = 9
GAMEPAD_BUTTON_RIGHT_THUMB = 10
GAMEPAD_BUTTON_DPAD_UP = 11
GAMEPAD_BUTTON_DPAD_RIGHT = 12
GAMEPAD_BUTTON_DPAD_DOWN = 13
GAMEPAD_BUTTON_DPAD_LEFT = 14
GAMEPAD_BUTTON_LAST = GAMEPAD_BUTTON_DPAD_LEFT
GAMEPAD_BUTTON_CROSS = GAMEPAD_BUTTON_A
GAMEPAD_BUTTON_CIRCLE = GAMEPAD_BUTTON_B
GAMEPAD_BUTTON_SQUARE = GAMEPAD_BUTTON_X
GAMEPAD_BUTTON_TRIANGLE = GAMEPAD_BUTTON_Y
GAMEPAD_AXIS_LEFT_X = 0
GAMEPAD_AXIS_LEFT_Y = 1
GAMEPAD_AXIS_RIGHT_X = 2
GAMEPAD_AXIS_RIGHT_Y = 3
GAMEPAD_AXIS_LEFT_TRIGGER = 4
GAMEPAD_AXIS_RIGHT_TRIGGER = 5
GAMEPAD_AXIS_LAST = GAMEPAD_AXIS_RIGHT_TRIGGER
NO_ERROR = 0
NOT_INITIALIZED = 0x00010001
NO_CURRENT_CONTEXT = 0x00010002
INVALID_ENUM = 0x00010003
INVALID_VALUE = 0x00010004
OUT_OF_MEMORY = 0x00010005
API_UNAVAILABLE = 0x00010006
VERSION_UNAVAILABLE = 0x00010007
PLATFORM_ERROR = 0x00010008
FORMAT_UNAVAILABLE = 0x00010009
NO_WINDOW_CONTEXT = 0x0001000A
FOCUSED = 0x00020001
ICONIFIED = 0x00020002
RESIZABLE = 0x00020003
VISIBLE = 0x00020004
DECORATED = 0x00020005
AUTO_ICONIFY = 0x00020006
FLOATING = 0x00020007
MAXIMIZED = 0x00020008
CENTER_CURSOR = 0x00020009
TRANSPARENT_FRAMEBUFFER = 0x0002000A
HOVERED = 0x0002000B
FOCUS_ON_SHOW = 0x0002000C
RED_BITS = 0x00021001
GREEN_BITS = 0x00021002
BLUE_BITS = 0x00021003
ALPHA_BITS = 0x00021004
DEPTH_BITS = 0x00021005
STENCIL_BITS = 0x00021006
ACCUM_RED_BITS = 0x00021007
ACCUM_GREEN_BITS = 0x00021008
ACCUM_BLUE_BITS = 0x00021009
ACCUM_ALPHA_BITS = 0x0002100A
AUX_BUFFERS = 0x0002100B
STEREO = 0x0002100C
SAMPLES = 0x0002100D
SRGB_CAPABLE = 0x0002100E
REFRESH_RATE = 0x0002100F
DOUBLEBUFFER = 0x00021010
CLIENT_API = 0x00022001
CONTEXT_VERSION_MAJOR = 0x00022002
CONTEXT_VERSION_MINOR = 0x00022003
CONTEXT_REVISION = 0x00022004
CONTEXT_ROBUSTNESS = 0x00022005
OPENGL_FORWARD_COMPAT = 0x00022006
OPENGL_DEBUG_CONTEXT = 0x00022007
OPENGL_PROFILE = 0x00022008
CONTEXT_RELEASE_BEHAVIOR = 0x00022009
CONTEXT_NO_ERROR = 0x0002200A
CONTEXT_CREATION_API = 0x0002200B
SCALE_TO_MONITOR = 0x0002200C
COCOA_RETINA_FRAMEBUFFER = 0x00023001
COCOA_FRAME_NAME = 0x00023002
COCOA_GRAPHICS_SWITCHING = 0x00023003
X11_CLASS_NAME = 0x00024001
X11_INSTANCE_NAME = 0x00024002
NO_API = 0
OPENGL_API = 0x00030001
OPENGL_ES_API = 0x00030002
NO_ROBUSTNESS = 0
NO_RESET_NOTIFICATION = 0x00031001
LOSE_CONTEXT_ON_RESET = 0x00031002
OPENGL_ANY_PROFILE = 0
OPENGL_CORE_PROFILE = 0x00032001
OPENGL_COMPAT_PROFILE = 0x00032002
CURSOR = 0x00033001
STICKY_KEYS = 0x00033002
STICKY_MOUSE_BUTTONS = 0x00033003
LOCK_KEY_MODS = 0x00033004
RAW_MOUSE_MOTION = 0x00033005
CURSOR_NORMAL = 0x00034001
CURSOR_HIDDEN = 0x00034002
CURSOR_DISABLED = 0x00034003
ANY_RELEASE_BEHAVIOR = 0
RELEASE_BEHAVIOR_FLUSH = 0x00035001
RELEASE_BEHAVIOR_NONE = 0x00035002
NATIVE_CONTEXT_API = 0x00036001
EGL_CONTEXT_API = 0x00036002
OSMESA_CONTEXT_API = 0x00036003
ARROW_CURSOR = 0x00036001
IBEAM_CURSOR = 0x00036002
CROSSHAIR_CURSOR = 0x00036003
HAND_CURSOR = 0x00036004
HRESIZE_CURSOR = 0x00036005
VRESIZE_CURSOR = 0x00036006
CONNECTED = 0x00040001
DISCONNECTED = 0x00040002
JOYSTICK_HAT_BUTTONS = 0x00050001
COCOA_CHDIR_RESOURCES = 0x00051001
COCOA_MENUBAR = 0x00051002
DONT_CARE = -1


if _PREVIEW:
    ANGLE_PLATFORM_TYPE = 0x00050002
    ANGLE_PLATFORM_TYPE_NONE = 0x00037001
    ANGLE_PLATFORM_TYPE_OPENGL = 0x00037002
    ANGLE_PLATFORM_TYPE_OPENGLES = 0x00037003
    ANGLE_PLATFORM_TYPE_D3D9 = 0x00037004
    ANGLE_PLATFORM_TYPE_D3D11 = 0x00037005
    ANGLE_PLATFORM_TYPE_VULKAN = 0x00037007
    ANGLE_PLATFORM_TYPE_METAL = 0x00037008
    ANY_PLATFORM = 0x00060000
    CONTEXT_DEBUG = 0x00022007
    CURSOR_UNAVAILABLE = 0x0001000B
    FEATURE_UNAVAILABLE = 0x0001000C
    FEATURE_UNIMPLEMENTED = 0x0001000D
    MOUSE_PASSTHROUGH = 0x0002000D
    NOT_ALLOWED_CURSOR = 0x0003600A
    PLATFORM = 0x00050003
    PLATFORM_COCOA = 0x00060002
    PLATFORM_NULL = 0x00060005
    PLATFORM_UNAVAILABLE = 0x0001000E
    PLATFORM_WAYLAND = 0x00060003
    PLATFORM_WIN32 = 0x00060001
    PLATFORM_X11 = 0x00060004
    POINTING_HAND_CURSOR = 0x00036004
    RESIZE_ALL_CURSOR = 0x00036009
    RESIZE_EW_CURSOR = 0x00036005
    RESIZE_NESW_CURSOR = 0x00036008
    RESIZE_NS_CURSOR = 0x00036006
    RESIZE_NWSE_CURSOR = 0x00036007
    WIN32_KEYBOARD_MENU = 0x00025001
    X11_XCB_VULKAN_SURFACE = 0x00052001

    ANY_POSITION = 0x80000000
    POSITION_X = 0x0002000E
    POSITION_Y = 0x0002000F
    WAYLAND_APP_ID = 0x00026001
    CURSOR_CAPTURED = 0x00034004

_exc_info_from_callback = None

def _callback_exception_decorator(func):
    @functools.wraps(func)
    def callback_wrapper(*args, **kwargs):
        global _exc_info_from_callback
        if _exc_info_from_callback is not None:
            # We are on the way back to Python after an exception was raised.
            # Do not call further callbacks and wait for the errcheck function
            # to handle the exception first.
            return
        try:
            return func(*args, **kwargs)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            _exc_info_from_callback = sys.exc_info()
    return callback_wrapper

def _prepare_errcheck():
    """
    This function sets the errcheck attribute of all ctypes wrapped functions
    to evaluate the _exc_info_from_callback global variable and re-raise any
    exceptions that might have been raised in callbacks.
    It also modifies all callback types to automatically wrap the function
    using the _callback_exception_decorator.
    """
    def errcheck(result, *args):
        global _exc_info_from_callback
        if _exc_info_from_callback is not None:
            exc = _exc_info_from_callback
            _exc_info_from_callback = None
            _reraise(exc[1], exc[2])
        return result

    for symbol in dir(_glfw):
        if symbol.startswith('glfw'):
            getattr(_glfw, symbol).errcheck = errcheck

    _globals = globals()
    for symbol in _globals:
        if symbol.startswith('_GLFW') and symbol.endswith('fun'):
            def wrapper_cfunctype(func, cfunctype=_globals[symbol]):
                return cfunctype(_callback_exception_decorator(func))
            _globals[symbol] = wrapper_cfunctype


_GLFWerrorfun = ctypes.CFUNCTYPE(
    None, ctypes.c_int, ctypes.c_char_p
)
_GLFWwindowposfun = ctypes.CFUNCTYPE(
    None, ctypes.POINTER(_GLFWwindow), ctypes.c_int, ctypes.c_int
)
_GLFWwindowsizefun = ctypes.CFUNCTYPE(
    None, ctypes.POINTER(_GLFWwindow), ctypes.c_int, ctypes.c_int
)
_GLFWwindowclosefun = ctypes.CFUNCTYPE(
    None, ctypes.POINTER(_GLFWwindow)
)
_GLFWwindowrefreshfun = ctypes.CFUNCTYPE(
    None, ctypes.POINTER(_GLFWwindow)
)
_GLFWwindowfocusfun = ctypes.CFUNCTYPE(
    None, ctypes.POINTER(_GLFWwindow), ctypes.c_int
)
_GLFWwindowiconifyfun = ctypes.CFUNCTYPE(
    None, ctypes.POINTER(_GLFWwindow), ctypes.c_int
)
_GLFWwindowmaximizefun = ctypes.CFUNCTYPE(
    None, ctypes.POINTER(_GLFWwindow), ctypes.c_int
)
_GLFWframebuffersizefun = ctypes.CFUNCTYPE(
    None, ctypes.POINTER(_GLFWwindow), ctypes.c_int, ctypes.c_int
)
_GLFWwindowcontentscalefun = ctypes.CFUNCTYPE(
    None, ctypes.POINTER(_GLFWwindow), ctypes.c_float, ctypes.c_float
)
_GLFWmousebuttonfun = ctypes.CFUNCTYPE(
    None, ctypes.POINTER(_GLFWwindow), ctypes.c_int, ctypes.c_int, ctypes.c_int
)
_GLFWcursorposfun = ctypes.CFUNCTYPE(
    None, ctypes.POINTER(_GLFWwindow), ctypes.c_double, ctypes.c_double
)
_GLFWcursorenterfun = ctypes.CFUNCTYPE(
    None, ctypes.POINTER(_GLFWwindow), ctypes.c_int
)
_GLFWscrollfun = ctypes.CFUNCTYPE(
    None, ctypes.POINTER(_GLFWwindow), ctypes.c_double, ctypes.c_double
)
_GLFWkeyfun = ctypes.CFUNCTYPE(
    None, ctypes.POINTER(_GLFWwindow), ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int
)
_GLFWcharfun = ctypes.CFUNCTYPE(
    None, ctypes.POINTER(_GLFWwindow), ctypes.c_int
)
_GLFWmonitorfun = ctypes.CFUNCTYPE(
    None, ctypes.POINTER(_GLFWmonitor), ctypes.c_int
)
_GLFWdropfun = ctypes.CFUNCTYPE(
    None, ctypes.POINTER(_GLFWwindow), ctypes.c_int, ctypes.POINTER(ctypes.c_char_p)
)
_GLFWcharmodsfun = ctypes.CFUNCTYPE(
    None, ctypes.POINTER(_GLFWwindow), ctypes.c_uint, ctypes.c_int
)
_GLFWjoystickfun = ctypes.CFUNCTYPE(
    None, ctypes.c_int, ctypes.c_int
)

if _PREVIEW:
    _GLFWallocatefun = ctypes.CFUNCTYPE(
        ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p
    )
    _GLFWreallocatefun = ctypes.CFUNCTYPE(
        ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p
    )
    _GLFWdeallocatefun = ctypes.CFUNCTYPE(
        None, ctypes.c_void_p, ctypes.c_void_p
    )

    class _GLFWallocator(ctypes.Structure):
        """
        Wrapper for:
            typedef struct GLFWallocator GLFWallocator;
        """
        _fields_ = [
            ("allocate", _GLFWallocatefun),
            ("reallocate", _GLFWreallocatefun),
            ("deallocate", _GLFWdeallocatefun),
        ]

def init() -> int:
    """
    Initializes the GLFW library.

    Wrapper for:
        int glfwInit(void);
    """
    ...

def terminate() -> None:
    """
    Terminates the GLFW library.

    Wrapper for:
        void glfwTerminate(void);
    """
    ...

if hasattr(_glfw, 'glfwInitHint'):
    def init_hint(hint: int, value: int) -> None:
        """
        Sets the specified init hint to the desired value.

        Wrapper for:
            void glfwInitHint(int hint, int value);
        """
        ...

def get_version() -> Tuple[int, int, int]:
    """
    Retrieves the version of the GLFW library.

    Wrapper for:
        void glfwGetVersion(int* major, int* minor, int* rev);
    """
    ...

def get_version_string() -> str:
    """
    Returns a string describing the compile-time configuration.

    Wrapper for:
        const char* glfwGetVersionString(void);
    """
    ...

if hasattr(_glfw, 'glfwGetError'):
    def get_error() -> Tuple[int, str]:
        """
        Returns and clears the last error for the calling thread.

        Wrapper for:
            int glfwGetError(const char** description);
        """
        ...

@_callback_exception_decorator
def _handle_glfw_errors(error_code: int, description: str) -> None:
    """
    Default error callback that raises GLFWError exceptions, issues GLFWError
    warnings or logs to the 'glfw' logger.
    Set an alternative error callback or set glfw.ERROR_REPORTING to False or
    'ignore' to disable this behavior.
    """
    ...

_default_error_callback = _GLFWerrorfun(_handle_glfw_errors)
_error_callback = (_handle_glfw_errors, _default_error_callback)

def set_error_callback(cbfun: _GLFWerrorfun) -> _GLFWerrorfun:
    """
    Sets the error callback.

    Wrapper for:
        GLFWerrorfun glfwSetErrorCallback(GLFWerrorfun cbfun);
    """
    ...

def get_monitors() -> _GLFWmonitor:
    """
    Returns the currently connected monitors.

    Wrapper for:
        GLFWmonitor** glfwGetMonitors(int* count);
    """
    ...

def get_primary_monitor() -> _GLFWmonitor:
    """
    Returns the primary monitor.

    Wrapper for:
        GLFWmonitor* glfwGetPrimaryMonitor(void);
    """
    ...

def get_monitor_pos(monitor: _GLFWmonitor) -> Tuple[int, int]:
    """
    Returns the position of the monitor's viewport on the virtual screen.

    Wrapper for:
        void glfwGetMonitorPos(GLFWmonitor* monitor, int* xpos, int* ypos);
    """
    ...

if hasattr(_glfw, 'glfwGetMonitorWorkarea'):
    def get_monitor_workarea(monitor: _GLFWmonitor) -> Tuple[int, int, int, int]:
        """
        Retrives the work area of the monitor.

        Wrapper for:
            void glfwGetMonitorWorkarea(GLFWmonitor* monitor, int* xpos, int* ypos, int* width, int* height);
        """
        ...

def get_monitor_physical_size(monitor: _GLFWmonitor) -> Tuple[int, int]:
    """
    Returns the physical size of the monitor.

    Wrapper for:
        void glfwGetMonitorPhysicalSize(GLFWmonitor* monitor, int* width, int* height);
    """
    ...

if hasattr(_glfw, 'glfwGetMonitorContentScale'):
    def get_monitor_content_scale(monitor: _GLFWmonitor) -> Tuple[float, float]:
        """
        Retrieves the content scale for the specified monitor.

        Wrapper for:
            void glfwGetMonitorContentScale(GLFWmonitor* monitor, float* xscale, float* yscale);
        """
        ...

def get_monitor_name(monitor: _GLFWmonitor) -> str:
    """
    Returns the name of the specified monitor.

    Wrapper for:
        const char* glfwGetMonitorName(GLFWmonitor* monitor);
    """
    ...

if hasattr(_glfw, 'glfwSetMonitorUserPointer') and hasattr(_glfw, 'glfwGetMonitorUserPointer'):
    def set_monitor_user_pointer(monitor: _GLFWmonitor, pointer: Any) -> None:
        """
        Sets the user pointer of the specified monitor. You may pass a normal
        python object into this function and it will be wrapped automatically.
        The object will be kept in existence until the pointer is set to
        something else.

        Wrapper for:
            void glfwSetMonitorUserPointer(int jid, void* pointer);
        """
        ...
    def get_monitor_user_pointer(monitor: _GLFWmonitor) -> Any:
        """
        Returns the user pointer of the specified monitor.

        Wrapper for:
            void* glfwGetMonitorUserPointer(int jid);
        """
        ...

def set_monitor_callback(cbfun: _GLFWmonitorfun) -> _GLFWmonitorfun:
    """
    Sets the monitor configuration callback.

    Wrapper for:
        GLFWmonitorfun glfwSetMonitorCallback(GLFWmonitorfun cbfun);
    """
    ...
def get_video_modes(monitor: _GLFWmonitor) -> List[_GLFWvidmode.GLFWvidmode]:
    """
    Returns the available video modes for the specified monitor.

    Wrapper for:
        const GLFWvidmode* glfwGetVideoModes(GLFWmonitor* monitor, int* count);
    """
    ...
def get_video_mode(monitor: _GLFWmonitor) -> _GLFWvidmode.GLFWvidmode:
    """
    Returns the current mode of the specified monitor.

    Wrapper for:
        const GLFWvidmode* glfwGetVideoMode(GLFWmonitor* monitor);
    """
    ...
def set_gamma(monitor: _GLFWmonitor, gamma: float) -> None:
    """
    Generates a gamma ramp and sets it for the specified monitor.

    Wrapper for:
        void glfwSetGamma(GLFWmonitor* monitor, float gamma);
    """
    ...
def get_gamma_ramp(monitor: _GLFWmonitor) -> _GLFWgammaramp.GLFWgammaramp:
    """
    Retrieves the current gamma ramp for the specified monitor.

    Wrapper for:
        const GLFWgammaramp* glfwGetGammaRamp(GLFWmonitor* monitor);
    """
    ...
def set_gamma_ramp(monitor: _GLFWmonitor, ramp: Tuple[int, int, int]) -> None:
    """
    Sets the current gamma ramp for the specified monitor.

    Wrapper for:
        void glfwSetGammaRamp(GLFWmonitor* monitor, const GLFWgammaramp* ramp);
    """
    ...
def default_window_hints() -> None:
    """
    Resets all window hints to their default values.

    Wrapper for:
        void glfwDefaultWindowHints(void);
    """
    ...
def window_hint(hint: int, value: int) -> None:
    """
    Sets the specified window hint to the desired value.

    Wrapper for:
        void glfwWindowHint(int hint, int value);
    """
    ...

if hasattr(_glfw, 'glfwWindowHintString'):
    def window_hint_string(hint: int, value: str) -> None:
        """
        Sets the specified window hint to the desired value.

        Wrapper for:
            void glfwWindowHintString(int hint, const char* value);
        """
        _glfw.glfwWindowHintString(hint, _to_char_p(value))

def create_window(width: int, height: int, title: str, monitor: _GLFWmonitor, share: _GLFWwindow) -> _GLFWwindow:
    """
    Creates a window and its associated context.

    Wrapper for:
        GLFWwindow* glfwCreateWindow(int width, int height, const char* title, GLFWmonitor* monitor, GLFWwindow* share);
    """
    ...
def destroy_window(window: _GLFWwindow) -> None:
    """
    Destroys the specified window and its context.

    Wrapper for:
        void glfwDestroyWindow(GLFWwindow* window);
    """
    ...
def window_should_close(window: _GLFWwindow) -> int:
    """
    Checks the close flag of the specified window.

    Wrapper for:
        int glfwWindowShouldClose(GLFWwindow* window);
    """
    ...
def set_window_should_close(window: _GLFWwindow, value: int) -> None:
    """
    Sets the close flag of the specified window.

    Wrapper for:
        void glfwSetWindowShouldClose(GLFWwindow* window, int value);
    """
    ...
def set_window_title(window: _GLFWwindow, title: str) -> None:
    """
    Sets the title of the specified window.

    Wrapper for:
        void glfwSetWindowTitle(GLFWwindow* window, const char* title);
    """
    _glfw.glfwSetWindowTitle(window, _to_char_p(title))

def get_window_pos(window: _GLFWwindow) -> Tuple[int, int]:
    """
    Retrieves the position of the client area of the specified window.

    Wrapper for:
        void glfwGetWindowPos(GLFWwindow* window, int* xpos, int* ypos);
    """
    ...

def set_window_pos(window: _GLFWwindow, xpos: int, ypos: int):
    """
    Sets the position of the client area of the specified window.

    Wrapper for:
        void glfwSetWindowPos(GLFWwindow* window, int xpos, int ypos);
    """
    ...

def get_window_size(window: _GLFWwindow) -> Tuple[int, int]:
    """
    Retrieves the size of the client area of the specified window.

    Wrapper for:
        void glfwGetWindowSize(GLFWwindow* window, int* width, int* height);
    """
    ...

def set_window_size(window: _GLFWwindow, width: int, height: int) -> None:
    """
    Sets the size of the client area of the specified window.

    Wrapper for:
        void glfwSetWindowSize(GLFWwindow* window, int width, int height);
    """
    ...

def get_framebuffer_size(window: _GLFWwindow) -> Tuple[int, int]:
    """
    Retrieves the size of the framebuffer of the specified window.

    Wrapper for:
        void glfwGetFramebufferSize(GLFWwindow* window, int* width, int* height);
    """
    ...

if hasattr(_glfw, 'glfwGetWindowContentScale'):
    def get_window_content_scale(window: _GLFWwindow) -> Tuple[float, float]:
        """
        Retrieves the content scale for the specified window.

        Wrapper for:
            void glfwGetWindowContentScale(GLFWwindow* window, float* xscale, float* yscale);
        """
        ...

if hasattr(_glfw, 'glfwGetWindowOpacity'):
    def get_window_opacity(window: _GLFWwindow) -> float:
        """
        Returns the opacity of the whole window.

        Wrapper for:
            float glfwGetWindowOpacity(GLFWwindow* window);
        """
        ...

if hasattr(_glfw, 'glfwSetWindowOpacity'):
    def set_window_opacity(window: _GLFWwindow, opacity: float) -> None:
        """
        Sets the opacity of the whole window.

        Wrapper for:
            void glfwSetWindowOpacity(GLFWwindow* window, float opacity);
        """
        ...

def iconify_window(window: _GLFWwindow) -> None:
    """
    Iconifies the specified window.

    Wrapper for:
        void glfwIconifyWindow(GLFWwindow* window);
    """
    ...

def restore_window(window: _GLFWwindow) -> None:
    """
    Restores the specified window.

    Wrapper for:
        void glfwRestoreWindow(GLFWwindow* window);
    """
    ...

def show_window(window: _GLFWwindow) -> None:
    """
    Makes the specified window visible.

    Wrapper for:
        void glfwShowWindow(GLFWwindow* window);
    """
    ...

def hide_window(window: _GLFWwindow) -> None:
    """
    Hides the specified window.

    Wrapper for:
        void glfwHideWindow(GLFWwindow* window);
    """
    ...

if hasattr(_glfw, 'glfwRequestWindowAttention'):
    def request_window_attention(window: _GLFWwindow) -> None:
        """
        Requests user attention to the specified window.

        Wrapper for:
            void glfwRequestWindowAttention(GLFWwindow* window);
        """
        ...

def get_window_monitor(window: _GLFWwindow) -> _GLFWmonitor:
    """
    Returns the monitor that the window uses for full screen mode.

    Wrapper for:
        GLFWmonitor* glfwGetWindowMonitor(GLFWwindow* window);
    """
    ...

def get_window_attrib(window: _GLFWwindow, attrib: int) -> int:
    """
    Returns an attribute of the specified window.

    Wrapper for:
        int glfwGetWindowAttrib(GLFWwindow* window, int attrib);
    """
    ...

if hasattr(_glfw, 'glfwSetWindowAttrib'):
    def set_window_attrib(window: _GLFWwindow, attrib: int, value: int) -> None:
        """
        Returns an attribute of the specified window.

        Wrapper for:
            void glfwSetWindowAttrib(GLFWwindow* window, int attrib, int value);
        """
        ...

def set_window_user_pointer(window: _GLFWwindow, pointer: Union[ctypes.c_void_p, Any]) -> None:
    """
    Sets the user pointer of the specified window. You may pass a normal python object into this function and it will
    be wrapped automatically. The object will be kept in existence until the pointer is set to something else or
    until the window is destroyed.

    Wrapper for:
        void glfwSetWindowUserPointer(GLFWwindow* window, void* pointer);
    """
    ...

def set_window_pos_callback(window: _GLFWwindow, cbfun: _GLFWwindowposfun) -> _GLFWwindowposfun:
    """
    Sets the position callback for the specified window.

    Wrapper for:
        GLFWwindowposfun glfwSetWindowPosCallback(GLFWwindow* window, GLFWwindowposfun cbfun);
    """
    ...

def set_window_size_callback(window: _GLFWwindow, cbfun: _GLFWwindowsizefun) -> _GLFWwindowsizefun:
    """
    Sets the size callback for the specified window.

    Wrapper for:
        GLFWwindowsizefun glfwSetWindowSizeCallback(GLFWwindow* window, GLFWwindowsizefun cbfun);
    """
    ...

def set_window_close_callback(window: _GLFWwindow, cbfun: _GLFWwindowclosefun) -> _GLFWwindowclosefun:
    """
    Sets the close callback for the specified window.

    Wrapper for:
        GLFWwindowclosefun glfwSetWindowCloseCallback(GLFWwindow* window, GLFWwindowclosefun cbfun);
    """

def set_window_refresh_callback(window: _GLFWwindow, cbfun: _GLFWwindowrefreshfun) -> _GLFWwindowrefreshfun:
    """
    Sets the refresh callback for the specified window.

    Wrapper for:
        GLFWwindowrefreshfun glfwSetWindowRefreshCallback(GLFWwindow* window, GLFWwindowrefreshfun cbfun);
    """
    ...

def set_window_focus_callback(window: _GLFWwindow, cbfun: _GLFWwindowfocusfun) -> _GLFWwindowfocusfun:
    """
    Sets the focus callback for the specified window.

    Wrapper for:
        GLFWwindowfocusfun glfwSetWindowFocusCallback(GLFWwindow* window, GLFWwindowfocusfun cbfun);
    """
    ...

def set_window_iconify_callback(window: _GLFWwindow, cbfun: _GLFWwindowiconifyfun) -> _GLFWwindowiconifyfun:
    """
    Sets the iconify callback for the specified window.

    Wrapper for:
        GLFWwindowiconifyfun glfwSetWindowIconifyCallback(GLFWwindow* window, GLFWwindowiconifyfun cbfun);
    """
    ...

if hasattr(_glfw, 'glfwSetWindowMaximizeCallback'):
    def set_window_maximize_callback(window: _GLFWwindow, cbfun: _GLFWwindowmaximizefun) -> _GLFWwindowmaximizefun:
        """
        Sets the maximize callback for the specified window.

        Wrapper for:
            GLFWwindowmaximizefun glfwSetWindowMaximizeCallback(GLFWwindow* window, GLFWwindowmaximizefun cbfun);
        """
        ...

def set_framebuffer_size_callback(window: _GLFWwindow, cbfun: _GLFWframebuffersizefun) -> _GLFWframebuffersizefun:
    """
    Sets the framebuffer resize callback for the specified window.

    Wrapper for:
        GLFWframebuffersizefun glfwSetFramebufferSizeCallback(GLFWwindow* window, GLFWframebuffersizefun cbfun);
    """
    ...

if hasattr(_glfw, 'glfwSetWindowContentScaleCallback'):
    def set_window_content_scale_callback(window: _GLFWwindow, cbfun: _GLFWwindowcontentscalefun) -> _GLFWwindowcontentscalefun:
        """
        Sets the window content scale callback for the specified window.

        Wrapper for:
            GLFWwindowcontentscalefun glfwSetWindowContentScaleCallback(GLFWwindow* window, GLFWwindowcontentscalefun cbfun);
        """
        ...

def poll_events() -> None:
    """
    Processes all pending events.

    Wrapper for:
        void glfwPollEvents(void);
    """
    ...

def wait_events() -> None:
    """
    Waits until events are pending and processes them.

    Wrapper for:
        void glfwWaitEvents(void);
    """
    ...

def get_input_mode(window: _GLFWwindow, mode: int) -> int:
    """
    Returns the value of an input option for the specified window.

    Wrapper for:
        int glfwGetInputMode(GLFWwindow* window, int mode);
    """
    ...

def set_input_mode(window: _GLFWwindow, mode: int, value: int) -> None:
    """
    Sets an input option for the specified window.
    @param[in] window The window whose input mode to set.
    @param[in] mode One of `GLFW_CURSOR`, `GLFW_STICKY_KEYS` or
    `GLFW_STICKY_MOUSE_BUTTONS`.
    @param[in] value The new value of the specified input mode.

    Wrapper for:
        void glfwSetInputMode(GLFWwindow* window, int mode, int value);
    """
    ...

if hasattr(_glfw, 'glfwRawMouseMotionSupported'):
    def raw_mouse_motion_supported() -> int:
        """
        Returns whether raw mouse motion is supported.

        Wrapper for:
            int glfwRawMouseMotionSupported(void);
        """
        ...

def get_key(window: _GLFWwindow, key: int) -> int:
    """
    Returns the last reported state of a keyboard key for the specified
    window.

    Wrapper for:
        int glfwGetKey(GLFWwindow* window, int key);
    """
    ...

def get_mouse_button(window: _GLFWwindow, button: int) -> int:
    """
    Returns the last reported state of a mouse button for the specified
    window.

    Wrapper for:
        int glfwGetMouseButton(GLFWwindow* window, int button);
    """
    ...

def get_cursor_pos(window: _GLFWwindow) -> Tuple[float, float]:
    """
    Retrieves the last reported cursor position, relative to the client
    area of the window.

    Wrapper for:
        void glfwGetCursorPos(GLFWwindow* window, double* xpos, double* ypos);
    """
    ...

def set_cursor_pos(window: _GLFWwindow, xpos: float, ypos: float):
    """
    Sets the position of the cursor, relative to the client area of the window.

    Wrapper for:
        void glfwSetCursorPos(GLFWwindow* window, double xpos, double ypos);
    """
    ...

def set_key_callback(window: _GLFWwindow, cbfun: _GLFWkeyfun) -> _GLFWkeyfun:
    """
    Sets the key callback.

    Wrapper for:
        GLFWkeyfun glfwSetKeyCallback(GLFWwindow* window, GLFWkeyfun cbfun);
    """

def set_char_callback(window: _GLFWwindow, cbfun: _GLFWcharfun) -> _GLFWcharfun:
    """
    Sets the Unicode character callback.

    Wrapper for:
        GLFWcharfun glfwSetCharCallback(GLFWwindow* window, GLFWcharfun cbfun);
    """
    ...

def set_mouse_button_callback(window: _GLFWwindow, cbfun: _GLFWmousebuttonfun) -> _GLFWmousebuttonfun:
    """
    Sets the mouse button callback.

    Wrapper for:
        GLFWmousebuttonfun glfwSetMouseButtonCallback(GLFWwindow* window, GLFWmousebuttonfun cbfun);
    """
    ...

def set_cursor_pos_callback(window: _GLFWwindow, cbfun: _GLFWcursorposfun) -> _GLFWcursorposfun:
    """
    Sets the cursor position callback.

    Wrapper for:
        GLFWcursorposfun glfwSetCursorPosCallback(GLFWwindow* window, GLFWcursorposfun cbfun);
    """
    ...

def set_cursor_enter_callback(window: _GLFWwindow, cbfun: _GLFWcursorenterfun) -> _GLFWcursorenterfun:
    """
    Sets the cursor enter/exit callback.

    Wrapper for:
        GLFWcursorenterfun glfwSetCursorEnterCallback(GLFWwindow* window, GLFWcursorenterfun cbfun);
    """
    ...

def set_scroll_callback(window: _GLFWwindow, cbfun: _GLFWscrollfun) -> _GLFWscrollfun:
    """
    Sets the scroll callback.

    Wrapper for:
        GLFWscrollfun glfwSetScrollCallback(GLFWwindow* window, GLFWscrollfun cbfun);
    """
    ...

def joystick_present(joy: int) -> int:
    """
    Returns whether the specified joystick is present.

    Wrapper for:
        int glfwJoystickPresent(int joy);
    """
    ...

def get_joystick_axes(joy: int) -> Tuple[float, int]:
    """
    Returns the values of all axes of the specified joystick.

    Wrapper for:
        const float* glfwGetJoystickAxes(int joy, int* count);
    """
    ...

def get_joystick_buttons(joy: int) -> Tuple[str, int]:
    """
    Returns the state of all buttons of the specified joystick.

    Wrapper for:
        const unsigned char* glfwGetJoystickButtons(int joy, int* count);
    """
    ...

if hasattr(_glfw, 'glfwGetJoystickHats'):
    def get_joystick_hats(joystick_id) -> Tuple[str, int]:
        """
        Returns the state of all hats of the specified joystick.

        Wrapper for:
            const unsigned char* glfwGetJoystickButtons(int joy, int* count);
        """
        ...

def get_joystick_name(joy: int) -> str:
    """
    Returns the name of the specified joystick.

    Wrapper for:
        const char* glfwGetJoystickName(int joy);
    """
    ...

if hasattr(_glfw, 'glfwGetJoystickGUID'):
    def get_joystick_guid(joystick_id: int) -> str:
        """
        Returns the SDL compatible GUID of the specified joystick.

        Wrapper for:
            const char* glfwGetJoystickGUID(int jid);
        """
        return _glfw.glfwGetJoystickGUID(joystick_id)

if hasattr(_glfw, 'glfwSetJoystickUserPointer') and hasattr(_glfw, 'glfwGetJoystickUserPointer'):
    def set_joystick_user_pointer(joystick_id: int, pointer: Union[ctypes.c_void_p, Any]) -> None:
        """
        Sets the user pointer of the specified joystick. You may pass a normal
        python object into this function and it will be wrapped automatically.
        The object will be kept in existence until the pointer is set to
        something else.

        Wrapper for:
            void glfwSetJoystickUserPointer(int jid, void* pointer);
        """
        ...

    def get_joystick_user_pointer(joystick_id: int) -> ...:
        """
        Returns the user pointer of the specified joystick.

        Wrapper for:
            void* glfwGetJoystickUserPointer(int jid);
        """
        ...

if hasattr(_glfw, 'glfwJoystickIsGamepad'):
    def joystick_is_gamepad(joystick_id: int) -> bool:
        """
        Returns whether the specified joystick has a gamepad mapping.

        Wrapper for:
            int glfwJoystickIsGamepad(int jid);
        """
        ...

if hasattr(_glfw, 'glfwGetGamepadState'):
    def get_gamepad_state(joystick_id: int) -> Optional[_GLFWgamepadstate.GLFWgamepadstate]:
        """
        Retrieves the state of the specified joystick remapped as a gamepad.

        Wrapper for:
            int glfwGetGamepadState(int jid, GLFWgamepadstate* state);
        """
        ...

def set_clipboard_string(window: _GLFWwindow, string: str) -> None:
    """
    Sets the clipboard to the specified string.

    Wrapper for:
        void glfwSetClipboardString(GLFWwindow* window, const char* string);
    """
    ...

def get_clipboard_string(window: _GLFWwindow) -> str:
    """
    Retrieves the contents of the clipboard as a string.

    Wrapper for:
        const char* glfwGetClipboardString(GLFWwindow* window);
    """

def get_time() -> float:
    """
    Returns the value of the GLFW timer.

    Wrapper for:
        double glfwGetTime(void);
    """
    ...

def set_time(time: float) -> None:
    """
    Sets the GLFW timer.

    Wrapper for:
        void glfwSetTime(double time);
    """
    ...

def make_context_current(window: _GLFWwindow) -> None:
    """
    Makes the context of the specified window current for the calling
    thread.

    Wrapper for:
        void glfwMakeContextCurrent(GLFWwindow* window);
    """
    ...

def get_current_context() -> _GLFWwindow:
    """
    Returns the window whose context is current on the calling thread.

    Wrapper for:
        GLFWwindow* glfwGetCurrentContext(void);
    """
    ...

def swap_interval(interval: int) -> None:
    """
    Sets the swap interval for the current context.

    Wrapper for:
        void glfwSwapInterval(int interval);
    """
    ...

def extension_supported(extension: str) -> int:
    """
    Returns whether the specified extension is available.

    Wrapper for:
        int glfwExtensionSupported(const char* extension);
    """
    ...

def get_proc_address(procname: str) -> Any:
    """
    Returns the address of the specified function for the current
    context.

    Wrapper for:
        GLFWglproc glfwGetProcAddress(const char* procname);
    """
    ...

if hasattr(_glfw, 'glfwSetDropCallback'):
    def set_drop_callback(window: _GLFWwindow, cbfun: _GLFWdropfun) -> _GLFWdropfun:
        """
        Sets the file drop callback.

        Wrapper for:
            GLFWdropfun glfwSetDropCallback(GLFWwindow* window, GLFWdropfun cbfun);
        """
        ...

if hasattr(_glfw, 'glfwSetCharModsCallback'):
    def set_char_mods_callback(window: _GLFWwindow, cbfun: _GLFWcharmodsfun) -> _GLFWcharmodsfun:
        """
        Sets the Unicode character with modifiers callback.

        Wrapper for:
            GLFWcharmodsfun glfwSetCharModsCallback(GLFWwindow* window, GLFWcharmodsfun cbfun);
        """
        ...

if hasattr(_glfw, 'glfwVulkanSupported'):
    def vulkan_supported() -> bool:
        """
        Returns whether the Vulkan loader has been found.

        Wrapper for:
            int glfwVulkanSupported(void);
        """
        ...

if hasattr(_glfw, 'glfwGetRequiredInstanceExtensions'):
    def get_required_instance_extensions() -> List[str]:
        """
        Returns the Vulkan instance extensions required by GLFW.

        Wrapper for:
            const char** glfwGetRequiredInstanceExtensions(uint32_t* count);
        """
        ...

if hasattr(_glfw, 'glfwGetTimerValue'):
    def get_timer_value() -> int:
        """
        Returns the current value of the raw timer.

        Wrapper for:
            uint64_t glfwGetTimerValue(void);
        """
        ...

if hasattr(_glfw, 'glfwGetTimerFrequency'):
    def get_timer_frequency() -> int:
        """
        Returns the frequency, in Hz, of the raw timer.

        Wrapper for:
            uint64_t glfwGetTimerFrequency(void);
        """
        ...

if hasattr(_glfw, 'glfwSetJoystickCallback'):
    def set_joystick_callback(cbfun: _GLFWjoystickfun) -> _GLFWjoystickfun:
        """
        Sets the error callback.

        Wrapper for:
            GLFWjoystickfun glfwSetJoystickCallback(GLFWjoystickfun cbfun);
        """
        ...

if hasattr(_glfw, 'glfwUpdateGamepadMappings'):
    def update_gamepad_mappings(string: str) -> int:
        """
        Adds the specified SDL_GameControllerDB gamepad mappings.

        Wrapper for:
            int glfwUpdateGamepadMappings(const char* string);
        """
        ...

if hasattr(_glfw, 'glfwGetGamepadName'):
    def get_gamepad_name(joystick_id: int) -> Optional[str]:
        """
        Returns the human-readable gamepad name for the specified joystick.

        Wrapper for:
            const char* glfwGetGamepadName(int jid);
        """
        ...

if hasattr(_glfw, 'glfwGetKeyName'):
    def get_key_name(key: int, scancode: int) -> Optional[str]:
        """
        Returns the localized name of the specified printable key.

        Wrapper for:
            const char* glfwGetKeyName(int key, int scancode);
        """
        ...

if hasattr(_glfw, 'glfwGetKeyScancode'):
    def get_key_scancode(key: int) -> int:
        """
        Returns the platform-specific scancode of the specified key.

        Wrapper for:
            int glfwGetKeyScancode(int key);
        """
        ...

if hasattr(_glfw, 'glfwCreateCursor'):
    def create_cursor(
        image: Union[
            Image.Image,
            Tuple[int, int, Tuple[Tuple[Tuple[int, int, int, int]]]]
        ],
        xhot: int,
        yhot: int
    ) -> _GLFWcursor:
        """
        Creates a custom cursor.

        Wrapper for:
            GLFWcursor* glfwCreateCursor(const GLFWimage* image, int xhot, int yhot);
        """
        ...

if hasattr(_glfw, 'glfwCreateStandardCursor'):
    def create_standard_cursor(shape: int) -> _GLFWcursor:
        """
        Creates a cursor with a standard shape.

        Wrapper for:
            GLFWcursor* glfwCreateStandardCursor(int shape);
        """
        ...

if hasattr(_glfw, 'glfwDestroyCursor'):
    def destroy_cursor(cursor: _GLFWcursor) -> None:
        """
        Destroys a cursor.

        Wrapper for:
            void glfwDestroyCursor(GLFWcursor* cursor);
        """
        ...

if hasattr(_glfw, 'glfwSetCursor'):
    def set_cursor(window: _GLFWwindow, cursor: _GLFWcursor) -> None:
        """
        Sets the cursor for the window.

        Wrapper for:
            void glfwSetCursor(GLFWwindow* window, GLFWcursor* cursor);
        """
        ...

if hasattr(_glfw, 'glfwCreateWindowSurface'):
    def create_window_surface(instance: Any, window: _GLFWwindow, allocator: Any, surface: Any) -> ...:
        """
        Creates a Vulkan surface for the specified window.

        Wrapper for:
            VkResult glfwCreateWindowSurface(VkInstance instance, GLFWwindow* window, const VkAllocationCallbacks* allocator, VkSurfaceKHR* surface);
        """
        ...

if hasattr(_glfw, 'glfwGetPhysicalDevicePresentationSupport'):
    def get_physical_device_presentation_support(instance: Any, device: Any, queuefamily: int) -> int:
        """
        Creates a Vulkan surface for the specified window.

        Wrapper for:
            int glfwGetPhysicalDevicePresentationSupport(VkInstance instance, VkPhysicalDevice device, uint32_t queuefamily);
        """
        ...

if hasattr(_glfw, 'glfwGetInstanceProcAddress'):
    def get_instance_proc_address(instance: Any, procname: str) -> ...:
        """
        Returns the address of the specified Vulkan instance function.

        Wrapper for:
            GLFWvkproc glfwGetInstanceProcAddress(VkInstance instance, const char* procname);
        """
        ...

if hasattr(_glfw, 'glfwSetWindowIcon'):
    _glfw.glfwSetWindowIcon.restype = None
    _glfw.glfwSetWindowIcon.argtypes = [ctypes.POINTER(_GLFWwindow),
                                        ctypes.c_int,
                                        ctypes.POINTER(_GLFWimage)]


    def set_window_icon(
        window: _GLFWwindow,
        count: int,
        images: Union[_GLFWimage, Iterable[_GLFWimage]]
    ) -> None:
        """
        Sets the icon for the specified window.

        Wrapper for:
            void glfwSetWindowIcon(GLFWwindow* window, int count, const GLFWimage* images);
        """
        ...

if hasattr(_glfw, 'glfwSetWindowSizeLimits'):
    def set_window_size_limits(
        window: _GLFWwindow,
        minwidth: int,
        minheight: int,
        maxwidth: int,
        maxheight: int
    ) -> None:
        """
        Sets the size limits of the specified window.

        Wrapper for:
            void glfwSetWindowSizeLimits(GLFWwindow* window, int minwidth, int minheight, int maxwidth, int maxheight);
        """
        ...

if hasattr(_glfw, 'glfwSetWindowAspectRatio'):
    def set_window_aspect_ratio(window: _GLFWwindow, numer: int, denom: int) -> None:
        """
        Sets the aspect ratio of the specified window.

        Wrapper for:
            void glfwSetWindowAspectRatio(GLFWwindow* window, int numer, int denom);
        """
        ...

if hasattr(_glfw, 'glfwGetWindowFrameSize'):
    def get_window_frame_size(window: _GLFWwindow) -> Tuple[int, int, int, int]:
        """
        Retrieves the size of the frame of the window.

        Wrapper for:
            void glfwGetWindowFrameSize(GLFWwindow* window, int* left, int* top, int* right, int* bottom);
        """
        ...

if hasattr(_glfw, 'glfwMaximizeWindow'):
    def maximize_window(window: _GLFWwindow) -> None:
        """
        Maximizes the specified window.

        Wrapper for:
            void glfwMaximizeWindow(GLFWwindow* window);
        """
        ...

if hasattr(_glfw, 'glfwFocusWindow'):
    def focus_window(window: _GLFWwindow) -> None:
        """
        Brings the specified window to front and sets input focus.

        Wrapper for:
            void glfwFocusWindow(GLFWwindow* window);
        """
        ...

if hasattr(_glfw, 'glfwSetWindowMonitor'):
    def set_window_monitor(
        window: _GLFWwindow,
        monitor: _GLFWmonitor,
        xpos: int,
        ypos: int,
        width: int,
        height: int,
        refresh_rate: int
    ) -> None:
        """
        Sets the mode, monitor, video mode and placement of a window.

        Wrapper for:
            void glfwSetWindowMonitor(GLFWwindow* window, GLFWmonitor* monitor, int xpos, int ypos, int width, int height, int refreshRate);
        """
        ...

if hasattr(_glfw, 'glfwWaitEventsTimeout'):
    def wait_events_timeout(timeout: float) -> None:
        """
        Waits with timeout until events are queued and processes them.

        Wrapper for:
            void glfwWaitEventsTimeout(double timeout);
        """
        ...

if hasattr(_glfw, 'glfwPostEmptyEvent'):
    def post_empty_event() -> None:
        """
        Posts an empty event to the event queue.

        Wrapper for:
            void glfwPostEmptyEvent();
        """
        ...

if hasattr(_glfw, 'glfwGetWin32Adapter'):
    def get_win32_adapter(monitor: _GLFWmonitor) -> Optional[str]:
        """
        Returns the adapter device name of the specified monitor.

        Wrapper for:
            const char* glfwGetWin32Adapter(GLFWmonitor* monitor);
        """
        ...

if hasattr(_glfw, 'glfwGetWin32Monitor'):
    def get_win32_monitor(monitor: _GLFWmonitor) -> Optional[str]:
        """
        Returns the display device name of the specified monitor.

        Wrapper for:
            const char* glfwGetWin32Monitor(GLFWmonitor* monitor);
        """
        ...

if hasattr(_glfw, 'glfwGetWin32Window'):
    def get_win32_window(window: _GLFWwindow) -> ...:
        """
        Returns the HWND of the specified window.

        Wrapper for:
            HWND glfwGetWin32Window(GLFWwindow* window);
        """
        ...

if hasattr(_glfw, 'glfwGetWGLContext'):
    def get_wgl_context(window: _GLFWwindow) -> ...:
        """
        Returns the HGLRC of the specified window.

        Wrapper for:
            HGLRC glfwGetWGLContext(GLFWwindow* window);
        """
        ...

if hasattr(_glfw, 'glfwGetCocoaMonitor'):
    def get_cocoa_monitor(monitor: _GLFWmonitor) -> int:
        """
        Returns the CGDirectDisplayID of the specified monitor.

        Wrapper for:
            CGDirectDisplayID glfwGetCocoaMonitor(GLFWmonitor* monitor);
        """
        ...

if hasattr(_glfw, 'glfwGetCocoaWindow'):
    def get_cocoa_window(window: _GLFWwindow) -> ...:
        """
        Returns the NSWindow of the specified window.

        Wrapper for:
            id glfwGetCocoaWindow(GLFWwindow* window);
        """
        ...

if hasattr(_glfw, 'glfwGetNSGLContext'):
    def get_nsgl_context(window: _GLFWwindow) -> ...:
        """
        Returns the NSOpenGLContext of the specified window.

        Wrapper for:
            id glfwGetNSGLContext(GLFWwindow* window);
        """
        ...

if hasattr(_glfw, 'glfwGetX11Display'):
    def get_x11_display() -> ...:
        """
        Returns the Display used by GLFW.

        Wrapper for:
            Display* glfwGetX11Display(void);
        """
        ...

if hasattr(_glfw, 'glfwGetX11Adapter'):
    def get_x11_adapter(monitor: _GLFWmonitor) -> int:
        """
        Returns the RRCrtc of the specified monitor.

        Wrapper for:
            RRCrtc glfwGetX11Adapter(GLFWmonitor* monitor);
        """
        ...

if hasattr(_glfw, 'glfwGetX11Monitor'):
    def get_x11_monitor(monitor: _GLFWmonitor) -> int:
        """
        Returns the RROutput of the specified monitor.

        Wrapper for:
            RROutput glfwGetX11Monitor(GLFWmonitor* monitor);
        """
        ...

if hasattr(_glfw, 'glfwGetX11Window'):
    def get_x11_window(window: _GLFWwindow) -> int:
        """
        Returns the Window of the specified window.

        Wrapper for:
            Window glfwGetX11Window(GLFWwindow* window);
        """
        ...

if hasattr(_glfw, 'glfwSetX11SelectionString'):
    def set_x11_selection_string(string: str) -> None:
        """
        Sets the current primary selection to the specified string.

        Wrapper for:
            void glfwSetX11SelectionString(const char* string);
        """
        ...

if hasattr(_glfw, 'glfwGetX11SelectionString'):
    def get_x11_selection_string() -> Optional[str]:
        """
        Returns the contents of the current primary selection as a string.

        Wrapper for:
            const char* glfwGetX11SelectionString(void);
        """
        ...

if hasattr(_glfw, 'glfwGetGLXContext'):
    def get_glx_context(window: _GLFWwindow) -> ...:
        """
        Returns the GLXContext of the specified window.

        Wrapper for:
            GLXContext glfwGetGLXContext(GLFWwindow* window);
        """
        ...

if hasattr(_glfw, 'glfwGetGLXWindow'):
    def get_glx_window(window: _GLFWwindow) -> int:
        """
        Returns the GLXWindow of the specified window.

        Wrapper for:
            GLXWindow glfwGetGLXWindow(GLFWwindow* window);
        """
        ...

if hasattr(_glfw, 'glfwGetWaylandDisplay'):
    def get_wayland_display() -> ...:
        """
        Returns the struct wl_display* used by GLFW.

        Wrapper for:
            struct wl_display* glfwGetWaylandDisplay(void);
        """
        ...

if hasattr(_glfw, 'glfwGetWaylandMonitor'):
    def get_wayland_monitor(monitor: _GLFWmonitor) -> ...:
        """
        Returns the struct wl_output* of the specified monitor.

        Wrapper for:
            struct wl_output* glfwGetWaylandMonitor(GLFWmonitor* monitor);
        """
        ...

if hasattr(_glfw, 'glfwGetWaylandWindow'):
    def get_wayland_window(window: _GLFWwindow) -> ...:
        """
        Returns the main struct wl_surface* of the specified window.

        Wrapper for:
            struct wl_surface* glfwGetWaylandWindow(GLFWwindow* window);
        """
        ...

if hasattr(_glfw, 'glfwGetEGLDisplay'):
    def get_egl_display() -> ...:
        """
        Returns the EGLDisplay used by GLFW.

        Wrapper for:
            EGLDisplay glfwGetEGLDisplay(void);
        """
        ...

if hasattr(_glfw, 'glfwGetEGLContext'):
    def get_egl_context(window: _GLFWwindow) -> ...:
        """
        Returns the EGLContext of the specified window.

        Wrapper for:
            EGLContext glfwGetEGLContext(GLFWwindow* window);
        """
        ...

if hasattr(_glfw, 'glfwGetEGLSurface'):
    def get_egl_surface(window: _GLFWwindow) -> ...:
        """
        Returns the EGLSurface of the specified window.

        Wrapper for:
            EGLSurface glfwGetEGLSurface(GLFWwindow* window);
        """
        ...

if hasattr(_glfw, 'glfwGetOSMesaColorBuffer'):
    def get_os_mesa_color_buffer(window: _GLFWwindow) -> Optional[Tuple[int, int, int, Any]]:
        """
        Retrieves the color buffer associated with the specified window.

        Wrapper for:
            int glfwGetOSMesaColorBuffer(GLFWwindow* window, int* width, int* height, int* format, void** buffer);
        """
        ...

if hasattr(_glfw, 'glfwGetOSMesaDepthBuffer'):
    def get_os_mesa_depth_buffer(window: _GLFWwindow) -> Optional[Tuple[int, int, int, Any]]:
        """
        Retrieves the depth buffer associated with the specified window.

        Wrapper for:
            int glfwGetOSMesaDepthBuffer(GLFWwindow* window, int* width, int* height, int* bytesPerValue, void** buffer);
        """
        ...

if hasattr(_glfw, 'glfwGetOSMesaContext'):
    def get_os_mesa_context(window: _GLFWwindow) -> ...:
        """
        Returns the OSMesaContext of the specified window.

        Wrapper for:
            OSMesaContext glfwGetOSMesaContext(GLFWwindow* window);
        """
        ...

if _PREVIEW:
    if hasattr(_glfw, 'glfwInitAllocator'):
        def init_allocator(allocate: ..., reallocate: ..., deallocate: ...) -> None:
            """
            Sets the init allocator to the desired value.

            Wrapper for:
                void glfwInitAllocator(const GLFWallocator* allocator);
            """
            ...

    if hasattr(_glfw, 'glfwInitVulkanLoader'):
        def init_vulkan_loader(loader: ...) -> None:
            """
            Sets the desired Vulkan `vkGetInstanceProcAddr` function.

            Wrapper for:
                void glfwInitVulkanLoader(PFN_vkGetInstanceProcAddr loader);
            """
            ...

    if hasattr(_glfw, 'glfwGetPlatform'):
        def get_platform() -> int:
            """
            Returns the currently selected platform.

            Wrapper for:
                int glfwGetPlatform(void);
            """
            ...

    if hasattr(_glfw, 'glfwPlatformSupported'):
        _glfw.glfwPlatformSupported.restype = ctypes.c_int
        _glfw.glfwPlatformSupported.argtypes = [ctypes.c_int]
        def platform_supported(platform: int) -> int:
            """
            Returns whether the library includes support for the specified platform.

            Wrapper for:
                int glfwPlatformSupported(int platform);
            """
            ...