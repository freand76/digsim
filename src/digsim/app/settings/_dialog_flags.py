# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""The window flags of the dialogs"""

from PySide6.QtCore import Qt


# A title and a close button, no minimize or maximize. The other hints are only followed
# with CustomizeWindowHint. On Wayland the compositor draws the frame and may add buttons.
DIALOG_FLAGS = (
    Qt.WindowType.Dialog
    | Qt.WindowType.CustomizeWindowHint
    | Qt.WindowType.WindowTitleHint
    | Qt.WindowType.WindowCloseButtonHint
)
