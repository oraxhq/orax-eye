"""ORAX Eye — See and control any macOS app through the Accessibility API."""

from .core import OraxEye, UIElement, AppWindow, get_eye
from ._version import __version__

__all__ = ["OraxEye", "UIElement", "AppWindow", "get_eye", "__version__"]
