# A part of Braille Cell Ignorer
# Copyright (C) 2025
# This file is covered by the GNU General Public License.

"""Configuration management for ignored braille cells."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import config
from logHandler import log

if TYPE_CHECKING:
	import braille

_CONFIG_SECTION = "brailleCellIgnorer"
_CONFIG_PROFILES_KEY = "profiles"


@dataclass
class IgnoredCellsProfile:
	"""Ignored cell configuration for a specific braille display.

	:ivar driverName: The braille display driver name.
	:ivar numCells: The number of cells the display has.
	:ivar ignoredCells: 1-based indices of cells to ignore.
	"""
	driverName: str
	numCells: int
	ignoredCells: list[int] = field(default_factory=list)

	@property
	def key(self) -> str:
		"""Return the configuration key for this profile."""
		return f"{self.driverName}:{self.numCells}"

	def getIgnoredCellsZeroBased(self) -> list[int]:
		"""Return the ignored cells as 0-based indices."""
		return [cell - 1 for cell in self.ignoredCells if cell > 0]


def _getConfigSection():
	"""Get or create the configuration section."""
	if _CONFIG_SECTION not in config.conf:
		config.conf[_CONFIG_SECTION] = {}
	return config.conf[_CONFIG_SECTION]


def loadProfiles() -> dict[str, IgnoredCellsProfile]:
	"""Load all ignored cell profiles from configuration.

	:return: Dictionary mapping profile keys to IgnoredCellsProfile objects.
	"""
	profiles: dict[str, IgnoredCellsProfile] = {}
	try:
		section = _getConfigSection()
		if _CONFIG_PROFILES_KEY in section:
			profilesData = section[_CONFIG_PROFILES_KEY]
			for key in profilesData:
				try:
					cellList = profilesData[key]
					profile = _parseProfileFromNewFormat(key, cellList)
					if profile:
						profiles[profile.key] = profile
				except (KeyError, TypeError):
					continue
	except Exception:
		log.error("Error loading brailleCellIgnorer config", exc_info=True)
	return profiles


def _parseProfileFromNewFormat(
	key: str,
	cellList: list[int] | str
) -> IgnoredCellsProfile | None:
	"""Parse a profile from the configuration format.

	:param key: Profile key in format "driver:numCells".
	:param cellList: List of 1-based cell indices or comma-separated string.
	:return: Parsed profile or None if invalid.
	"""
	try:
		parts = key.split(":", 1)
		if len(parts) != 2:
			return None
		driverName = parts[0].strip()
		numCells = int(parts[1].strip())
		if isinstance(cellList, str):
			cells = [int(x.strip()) for x in cellList.split(",") if x.strip()]
		elif isinstance(cellList, list):
			cells = [int(x) for x in cellList]
		else:
			return None
		return IgnoredCellsProfile(
			driverName=driverName,
			numCells=numCells,
			ignoredCells=sorted(set(cells)),
		)
	except (ValueError, AttributeError, TypeError):
		return None


def saveProfiles(profiles: dict[str, IgnoredCellsProfile]) -> None:
	"""Save all ignored cell profiles to configuration.

	:param profiles: Dictionary mapping profile keys to IgnoredCellsProfile objects.
	"""
	section = _getConfigSection()
	profilesData: dict[str, list[int]] = {}
	for key, profile in profiles.items():
		if profile.ignoredCells:
			profilesData[key] = list(profile.ignoredCells)
	section[_CONFIG_PROFILES_KEY] = profilesData


def getActiveProfile(display: "braille.BrailleDisplayDriver | None") -> IgnoredCellsProfile | None:
	"""Get the active profile for the current braille display.

	:param display: The current braille display driver, or None.
	:return: The active profile, or None if no profile applies.
	"""
	if not display or display.name == "noBraille":
		return None
	profiles = loadProfiles()
	specificKey = f"{display.name}:{display.numCells}"
	return profiles.get(specificKey)


def getIgnoredCellsForDisplay(display: "braille.BrailleDisplayDriver | None") -> list[int]:
	"""Get 0-based indices of ignored cells for the current display.

	:param display: The current braille display driver, or None.
	:return: List of 0-based cell indices to ignore.
	"""
	profile = getActiveProfile(display)
	if profile:
		return profile.getIgnoredCellsZeroBased()
	return []
