# A part of Braille Cell Ignorer
# Copyright (C) 2025
# This file is covered by the GNU General Public License.

"""Settings panel for configuring ignored braille cells."""

from __future__ import annotations

from typing import TYPE_CHECKING

import wx

import addonHandler
import braille
import gui
from gui import settingsDialogs, guiHelper

from . import config as cellIgnorerConfig

if TYPE_CHECKING:
	from .cellMapping import CellMappingManager

addonHandler.initTranslation()

_cellManager: "CellMappingManager | None" = None


def register(cellManager: "CellMappingManager") -> None:
	"""Register the settings panel with NVDA settings dialog.

	:param cellManager: CellMappingManager instance for refreshing after save.
	"""
	global _cellManager
	_cellManager = cellManager
	settingsDialogs.NVDASettingsDialog.categoryClasses.append(
		BrailleCellIgnorerSettingsPanel
	)


def unregister() -> None:
	"""Unregister the settings panel from NVDA settings dialog."""
	global _cellManager
	_cellManager = None
	try:
		settingsDialogs.NVDASettingsDialog.categoryClasses.remove(
			BrailleCellIgnorerSettingsPanel
		)
	except ValueError:
		pass


class BrailleCellIgnorerSettingsPanel(settingsDialogs.SettingsPanel):
	"""Settings panel for configuring ignored braille cells."""

	# Translators: Title of the Braille Cell Ignorer settings panel
	title = _("Braille Cell Ignorer")

	# Translators: Description of the Braille Cell Ignorer settings panel
	panelDescription = _(
		"Configure which braille display cells should be ignored "
		"(useful for displays with damaged cells)."
	)

	def makeSettings(self, sizer: wx.BoxSizer) -> None:
		"""Populate the panel with settings controls.

		:param sizer: The sizer to add controls to.
		"""
		helper = guiHelper.BoxSizerHelper(self, sizer=sizer)

		self._profiles: dict[str, cellIgnorerConfig.IgnoredCellsProfile] = cellIgnorerConfig.loadProfiles()
		self._pendingChanges: dict[str, list[int]] = {}
		self._currentDisplayKey: str | None = None
		self._profileKeys: list[str] = []
		self._selectedIndex: int = -1

		display = braille.handler.display if braille.handler else None
		if display and display.name != "noBraille":
			self._currentDisplayKey = f"{display.name}:{display.numCells}"

		choices = self._buildProfileList()

		# Translators: Label for the display profile selector
		profileLabel = _("&Display profile:")
		self._profileChoice = helper.addLabeledControl(
			profileLabel,
			wx.Choice,
			choices=choices,
		)
		self._profileChoice.Bind(wx.EVT_CHOICE, self._onProfileChange)

		if choices:
			self._profileChoice.SetSelection(0)
			self._selectedIndex = 0

		# Translators: Label for the ignored cells input field
		self._cellsLabel = wx.StaticText(self, label="")
		helper.addItem(self._cellsLabel)
		self._cellsEdit = helper.addItem(wx.TextCtrl(self))

		# Translators: Label for the read-only ignored cells display
		readOnlyLabel = _("Ignored cells:")
		self._cellsReadOnly = helper.addLabeledControl(
			readOnlyLabel,
			wx.TextCtrl,
			style=wx.TE_READONLY,
		)

		# Translators: Button to remove the selected historical configuration
		self._removeButton = wx.Button(self, label=_("&Remove this configuration"))
		self._removeButton.Bind(wx.EVT_BUTTON, self._onRemove)
		helper.addItem(self._removeButton)

		self._updateUIState()

	def _buildProfileList(self) -> list[str]:
		"""Build the list of profile choices for the combo box.

		:return: List of display strings for the combo box.
		"""
		self._profileKeys.clear()
		choices: list[str] = []

		if self._currentDisplayKey:
			self._profileKeys.append(self._currentDisplayKey)
			display = braille.handler.display
			# Translators: Combo box item for the currently connected display
			# {name} is the display description, {cells} is the cell count
			label = _("{name} ({cells} cells) - Connected").format(
				name=display.description,
				cells=display.numCells,
			)
			choices.append(label)
			if self._currentDisplayKey not in self._profiles:
				parts = self._currentDisplayKey.split(":", 1)
				self._profiles[self._currentDisplayKey] = cellIgnorerConfig.IgnoredCellsProfile(
					driverName=parts[0],
					numCells=int(parts[1]),
					ignoredCells=[],
				)

		for key, profile in self._profiles.items():
			if key == self._currentDisplayKey:
				continue
			if not profile.ignoredCells:
				continue
			self._profileKeys.append(key)
			# Translators: Combo box item for a historical display profile
			# {name} is the driver name, {cells} is the cell count
			label = _("{name} ({cells} cells)").format(
				name=profile.driverName,
				cells=profile.numCells,
			)
			choices.append(label)

		return choices

	def _onProfileChange(self, event: wx.CommandEvent) -> None:
		"""Handle profile selection change."""
		self._saveCurrentEdits()
		self._selectedIndex = self._profileChoice.GetSelection()
		self._updateUIState()

	def _saveCurrentEdits(self) -> None:
		"""Save current input field content to pending changes."""
		if self._selectedIndex < 0 or self._selectedIndex >= len(self._profileKeys):
			return
		key = self._profileKeys[self._selectedIndex]
		if key == self._currentDisplayKey:
			cells, _ = self._parseCellsFromInput()
			if cells is not None:
				self._pendingChanges[key] = cells

	def _updateUIState(self) -> None:
		"""Update UI controls based on current selection."""
		if self._selectedIndex < 0 or self._selectedIndex >= len(self._profileKeys):
			self._cellsEdit.Hide()
			self._cellsLabel.Hide()
			self._cellsReadOnly.Hide()
			self._removeButton.Hide()
			self.Layout()
			return

		key = self._profileKeys[self._selectedIndex]
		isCurrentDisplay = (key == self._currentDisplayKey)

		if key in self._pendingChanges:
			cells = self._pendingChanges[key]
		else:
			profile = self._profiles.get(key)
			cells = profile.ignoredCells if profile else []

		cellsStr = ", ".join(str(c) for c in cells)

		if isCurrentDisplay:
			maxCells = self._getCurrentDisplayCellCount()
			if maxCells:
				# Translators: Label for ignored cells input with valid range
				# {max} is the maximum valid cell number
				labelText = _("&Ignored cells (1-{max}, comma-separated):").format(max=maxCells)
			else:
				# Translators: Label for ignored cells input without range
				labelText = _("&Ignored cells (comma-separated):")
			self._cellsLabel.SetLabel(labelText)
			self._cellsLabel.Show()
			self._cellsEdit.SetValue(cellsStr)
			self._cellsEdit.Show()
			self._cellsReadOnly.Hide()
			self._removeButton.Hide()
		else:
			self._cellsLabel.Hide()
			self._cellsEdit.Hide()
			self._cellsReadOnly.SetValue(cellsStr)
			self._cellsReadOnly.Show()
			self._removeButton.Show()

		self.Layout()

	def _onRemove(self, event: wx.CommandEvent) -> None:
		"""Handle remove button click."""
		if self._selectedIndex < 0 or self._selectedIndex >= len(self._profileKeys):
			return
		key = self._profileKeys[self._selectedIndex]
		if key == self._currentDisplayKey:
			return
		if key in self._profiles:
			del self._profiles[key]
		if key in self._pendingChanges:
			del self._pendingChanges[key]
		self._profileKeys.pop(self._selectedIndex)
		self._profileChoice.Delete(self._selectedIndex)
		if self._profileChoice.GetCount() > 0:
			newIndex = min(self._selectedIndex, self._profileChoice.GetCount() - 1)
			self._profileChoice.SetSelection(newIndex)
			self._selectedIndex = newIndex
		else:
			self._selectedIndex = -1
		self._updateUIState()

	def _parseCellsFromInput(self) -> tuple[list[int] | None, str | None]:
		"""Parse and validate cell numbers from input field.

		:return: Tuple of (cells, error_message).
		         If valid: (sorted_cells, None)
		         If invalid: (None, error_message)
		"""
		text = self._cellsEdit.GetValue().strip()
		if not text:
			return [], None

		allowedChars = set("0123456789, ")
		if not all(c in allowedChars for c in text):
			# Translators: Error when input contains invalid characters
			return None, _("Only numbers and commas are allowed.")

		maxCells = self._getCurrentDisplayCellCount()
		cells: list[int] = []
		outOfRange: list[int] = []

		for part in text.split(","):
			part = part.strip()
			if not part:
				continue
			try:
				value = int(part)
			except ValueError:
				# Translators: Error when a value is not a valid number
				return None, _('"{value}" is not a valid number.').format(value=part)
			if value < 1:
				# Translators: Error when cell number is less than 1
				return None, _("Cell numbers must be at least 1.")
			if maxCells and value > maxCells:
				outOfRange.append(value)
			else:
				cells.append(value)

		if outOfRange:
			# Translators: Error when cell numbers exceed display size
			# {cells} is the list of invalid numbers, {max} is the maximum valid cell number
			return None, _(
				"Cell numbers {cells} exceed display size ({max} cells)."
			).format(
				cells=", ".join(str(c) for c in outOfRange),
				max=maxCells,
			)

		return sorted(set(cells)), None

	def _getCurrentDisplayCellCount(self) -> int:
		"""Get the cell count of the currently connected display.

		:return: Number of cells, or 0 if no display connected.
		"""
		if not self._currentDisplayKey:
			return 0
		profile = self._profiles.get(self._currentDisplayKey)
		return profile.numCells if profile else 0

	def isValid(self) -> bool:
		"""Validate the current settings.

		:return: True if settings are valid.
		"""
		if self._currentDisplayKey and self._selectedIndex >= 0:
			key = self._profileKeys[self._selectedIndex]
			if key == self._currentDisplayKey:
				cells, errorMsg = self._parseCellsFromInput()
				if errorMsg:
					# Translators: Title for the validation error dialog
					gui.messageBox(
						errorMsg,
						_("Ignored cells"),
						wx.OK | wx.ICON_ERROR,
						self,
					)
					return False
		return True

	def onSave(self) -> None:
		"""Save settings when OK or Apply is pressed."""
		self._saveCurrentEdits()
		for key, cells in self._pendingChanges.items():
			if key in self._profiles:
				self._profiles[key].ignoredCells = cells
			elif cells:
				parts = key.split(":", 1)
				self._profiles[key] = cellIgnorerConfig.IgnoredCellsProfile(
					driverName=parts[0],
					numCells=int(parts[1]),
					ignoredCells=cells,
				)
		profilesToSave = {
			key: profile
			for key, profile in self._profiles.items()
			if profile.ignoredCells
		}
		cellIgnorerConfig.saveProfiles(profilesToSave)
		if _cellManager:
			_cellManager.refreshIgnoredCells()

	def onDiscard(self) -> None:
		"""Handle discard when Cancel is pressed."""
		self._pendingChanges.clear()
