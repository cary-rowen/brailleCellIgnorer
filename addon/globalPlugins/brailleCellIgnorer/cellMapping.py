# A part of Braille Cell Ignorer
# Copyright (C) 2025
# This file is covered by the GNU General Public License.

"""Core logic for mapping between logical and physical braille cells."""

from __future__ import annotations

import braille

from . import config as cellIgnorerConfig


class CellMappingManager:
	"""Manages the mapping between logical and physical braille cells.

	Registers handlers to NVDA extension points and patches necessary
	properties to handle ignored braille cells.
	"""

	def __init__(self):
		self._ignoredCells: set[int] = set()
		self._originalRoutingIndexProperty: property | None = None
		self._originalWriteCells = None
		self._originalRouteTo = None
		self._isRegistered: bool = False

	def registerHandlers(self) -> None:
		"""Register handlers to NVDA extension points and apply patches."""
		if self._isRegistered:
			return
		braille.filter_displayDimensions.register(self._filterDisplayDimensions)
		self._patchWriteCells()
		self._patchRoutingIndex()
		self._patchRouteTo()
		self._isRegistered = True
		self._refreshDisplay()

	def unregisterHandlers(self) -> None:
		"""Unregister handlers from NVDA extension points and remove patches."""
		if not self._isRegistered:
			return
		braille.filter_displayDimensions.unregister(self._filterDisplayDimensions)
		self._unpatchWriteCells()
		self._unpatchRoutingIndex()
		self._unpatchRouteTo()
		self._isRegistered = False
		self._refreshDisplay()

	def refreshIgnoredCells(self) -> None:
		"""Refresh ignored cells and trigger display update.

		The actual _ignoredCells will be updated when _filterDisplayDimensions
		is called during the display refresh cycle.
		"""
		self._refreshDisplay()

	def _refreshDisplay(self) -> None:
		"""Invalidate display dimensions cache and trigger update."""
		if not braille.handler or not braille.handler.display:
			return
		if hasattr(braille.handler, "_displayDimensions"):
			braille.handler._displayDimensions = None
		_ = braille.handler.displayDimensions
		braille.handler.update()

	def _filterDisplayDimensions(
		self,
		displayDimensions: braille.DisplayDimensions
	) -> braille.DisplayDimensions:
		"""Filter handler that reduces display size by ignored cell count.

		Registered to the filter_displayDimensions extension point.

		:param displayDimensions: The raw display dimensions.
		:return: Adjusted display dimensions accounting for ignored cells.
		"""
		display = braille.handler.display if braille.handler else None
		ignoredList = cellIgnorerConfig.getIgnoredCellsForDisplay(display)
		self._ignoredCells = set(ignoredList)
		if not self._ignoredCells or displayDimensions.numRows > 1:
			return displayDimensions
		validIgnoredCount = sum(
			1 for cell in self._ignoredCells
			if 0 <= cell < displayDimensions.numCols
		)
		newNumCols = max(0, displayDimensions.numCols - validIgnoredCount)
		return braille.DisplayDimensions(numRows=1, numCols=newNumCols)

	def _patchWriteCells(self) -> None:
		"""Patch BrailleHandler._writeCells to remap cells for ignored positions."""
		self._originalWriteCells = braille.BrailleHandler._writeCells
		manager = self

		def patchedWriteCells(handler: braille.BrailleHandler, cells: list[int]) -> None:
			"""Patched _writeCells that remaps logical cells to physical positions."""
			logicalCellCount = handler.displaySize
			braille.pre_writeCells.notify(
				cells=cells,
				rawText=handler._rawText,
				currentCellCount=logicalCellCount,
			)
			display = handler.display
			if not display or not display.numCells:
				return
			physicalCellCount = display.numCells
			ignoredCells = manager._ignoredCells
			if ignoredCells and handler.displayDimensions.numRows == 1:
				cells = handler._normalizeCellArraySize(
					cells,
					logicalCellCount,
					handler.displayDimensions.numRows,
					logicalCellCount,
					handler.displayDimensions.numRows,
				)
				cells = manager._remapCellsToPhysical(
					cells,
					physicalCellCount,
					ignoredCells,
				)
			else:
				cells = handler._normalizeCellArraySize(
					cells,
					logicalCellCount,
					handler.displayDimensions.numRows,
					physicalCellCount,
					display.numRows,
				)
			if not display.isThreadSafe:
				try:
					display.display(cells)
				except Exception:
					from logHandler import log
					log.error("Error displaying cells", exc_info=True)
					handler.handleDisplayUnavailable()
				return
			with handler.queuedWriteLock:
				handler.queuedWrite = cells
				if not display._awaitingAck:
					handler._writeCellsInBackground()

		braille.BrailleHandler._writeCells = patchedWriteCells

	def _unpatchWriteCells(self) -> None:
		"""Restore the original _writeCells method."""
		if self._originalWriteCells is not None:
			braille.BrailleHandler._writeCells = self._originalWriteCells
			self._originalWriteCells = None

	def _remapCellsToPhysical(
		self,
		logicalCells: list[int],
		physicalCellCount: int,
		ignoredCells: set[int],
	) -> list[int]:
		"""Remap logical cells to physical display positions.

		Inserts blank cells at ignored positions.

		:param logicalCells: The logical cell values from the braille buffer.
		:param physicalCellCount: The total number of physical cells on the display.
		:param ignoredCells: 0-based indices of cells to ignore.
		:return: Cell values for physical display.
		"""
		physicalCells: list[int] = []
		logicalIndex = 0
		for physicalIndex in range(physicalCellCount):
			if physicalIndex in ignoredCells:
				physicalCells.append(0)
			else:
				if logicalIndex < len(logicalCells):
					physicalCells.append(logicalCells[logicalIndex])
				else:
					physicalCells.append(0)
				logicalIndex += 1
		return physicalCells

	def _patchRoutingIndex(self) -> None:
		"""Patch BrailleDisplayGesture.routingIndex to map physical to logical positions."""
		self._originalRoutingIndexProperty = braille.BrailleDisplayGesture.routingIndex
		manager = self

		def getRoutingIndex(gesture: braille.BrailleDisplayGesture) -> int | None:
			"""Get the logical routing index from physical position."""
			rawIndex = getattr(gesture, "_routingIndex", None)
			if rawIndex is None:
				return None
			return manager._physicalToLogicalIndex(rawIndex)

		def setRoutingIndex(gesture: braille.BrailleDisplayGesture, value: int | None) -> None:
			"""Set the physical routing index."""
			gesture._routingIndex = value

		braille.BrailleDisplayGesture.routingIndex = property(
			fget=getRoutingIndex,
			fset=setRoutingIndex,
		)

	def _unpatchRoutingIndex(self) -> None:
		"""Restore the original routingIndex property."""
		if self._originalRoutingIndexProperty is not None:
			braille.BrailleDisplayGesture.routingIndex = self._originalRoutingIndexProperty
			self._originalRoutingIndexProperty = None

	def _patchRouteTo(self) -> None:
		"""Patch BrailleHandler.routeTo to handle None windowPos gracefully.

		When a routing button for an ignored cell is pressed, the routingIndex
		will be None. This patch prevents the TypeError that would occur when
		passing None to the buffer's routeTo method.
		"""
		self._originalRouteTo = braille.BrailleHandler.routeTo

		def patchedRouteTo(handler: braille.BrailleHandler, windowPos: int | None) -> None:
			"""Route to window position, ignoring None values."""
			if windowPos is None:
				# Ignored cell was pressed, do nothing
				return
			self._originalRouteTo(handler, windowPos)

		braille.BrailleHandler.routeTo = patchedRouteTo

	def _unpatchRouteTo(self) -> None:
		"""Restore the original routeTo method."""
		if self._originalRouteTo is not None:
			braille.BrailleHandler.routeTo = self._originalRouteTo
			self._originalRouteTo = None

	def _physicalToLogicalIndex(self, physicalIndex: int) -> int | None:
		"""Convert a physical routing index to logical index.

		:param physicalIndex: The physical cell index pressed.
		:return: The logical cell index, or None if the cell is ignored.
		"""
		ignoredCells = self._ignoredCells
		if physicalIndex in ignoredCells:
			return None
		ignoredBefore = sum(1 for cell in ignoredCells if cell < physicalIndex)
		return physicalIndex - ignoredBefore
