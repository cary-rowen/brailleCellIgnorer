# Braille Cell Ignorer

An NVDA add-on that allows you to ignore damaged or malfunctioning braille display cells.

## Use Cases

- Your braille display has one or more cells with stuck pins or broken dots
- You want to continue using your display without seeing garbled output on damaged cells
- You need the remaining functional cells to shift and fill the gaps automatically

## Features

- **Ignore specific cells**: Configure which cells should be treated as non-existent
- **Automatic content shift**: Braille content flows around ignored cells seamlessly
- **Routing key handling**: Pressing a routing button on an ignored cell is silently ignored
- **Per-display profiles**: Settings are saved separately for each display model and size

## Settings

Access via: **NVDA Menu → Preferences → Settings → Braille Cell Ignorer**

| Option | Description |
|--------|-------------|
| **Display profile** | Select the display to configure (current or historical) |
| **Ignored cells** | Enter cell numbers (1-based, comma-separated, e.g., `1, 5, 40`) |
| **Remove configuration** | Delete settings for historical displays no longer in use |

## Notes

- Cell numbers are 1-based (first cell = 1, not 0)
- Only single-row displays are currently supported
- Changes take effect immediately after saving
