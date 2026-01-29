# A part of Braille Cell Ignorer
# Copyright (C) 2025
# This file is covered by the GNU General Public License.

"""Braille Cell Ignorer - A global plugin to ignore damaged braille cells.

This plugin allows users to configure specific braille display cells to be
ignored, which is useful when a display has damaged or malfunctioning cells.
The remaining functional cells will automatically shift to fill the gaps.
"""

from __future__ import annotations

import globalPluginHandler

from . import cellMapping
from . import settingsPanel


class GlobalPlugin(globalPluginHandler.GlobalPlugin):

	def __init__(self):
		super().__init__()
		self._cellManager = cellMapping.CellMappingManager()
		self._cellManager.registerHandlers()
		settingsPanel.register(self._cellManager)

	def terminate(self):
		settingsPanel.unregister()
		self._cellManager.unregisterHandlers()
		super().terminate()
