# Font Preview

A better font viewer for Linux. Preview text in all installed fonts, compare fonts side by side, and analyze Unicode coverage.

## Features

- **Browse all installed fonts** via fontconfig (`fc-list`)
- **Live preview** — type any text and see it rendered in every font
- **Compare fonts** — select 2–4 fonts for side-by-side comparison
- **Unicode coverage** — see which Unicode blocks a font supports
- **Language coverage** — test if a font has all characters for a specific language
- **Font metadata** — view family, style, weight, and file path
- **Search & filter** fonts by name
- **Favorites** — star your preferred fonts

## Installation

### Debian/Ubuntu

```bash
# Add repository (one-time)
curl -fsSL https://yeager.github.io/debian-repo/pub.gpg | sudo gpg --dearmor -o /etc/apt/keyrings/yeager.gpg
echo "deb [signed-by=/etc/apt/keyrings/yeager.gpg] https://yeager.github.io/debian-repo stable main" | sudo tee /etc/apt/sources.list.d/yeager.list
sudo apt update
sudo apt install font-preview
```

### From source

```bash
pip install .
font-preview
```

## Requirements

- Python 3.10+
- GTK 4, libadwaita
- fontconfig (`fc-list`)
- fonttools

## License

GPL-3.0-or-later — see [LICENSE](LICENSE).

## Author

Daniel Nylander <daniel@danielnylander.se>
