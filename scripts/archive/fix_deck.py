import re
from pathlib import Path

path = Path("scripts/deck_builder.py")
content = path.read_text()

# 1. Imports
content = content.replace("import sys\nfrom datetime", "import sys\nfrom pathlib import Path\nsys.path.insert(0, str(Path(__file__).resolve().parent.parent))\nfrom datetime")

# 2. Colors
content = re.sub(r"AUCTUS_DARK = .*", "AUCTUS_DARK = RGBColor(0xFF, 0xFF, 0xFF)   # crisp white bg", content)
content = re.sub(r"AUCTUS_BLUE = .*", "AUCTUS_BLUE = RGBColor(0xF1, 0xF5, 0xF9)   # slate box bg", content)
content = re.sub(r"AUCTUS_GOLD = .*", "AUCTUS_GOLD = RGBColor(0x10, 0xB9, 0x81)   # emerald accent", content)
content = re.sub(r"AUCTUS_LIGHT = .*", "AUCTUS_LIGHT = RGBColor(0x0F, 0x17, 0x2A)  # dark text", content)
content = content.replace("RGBColor(0x22, 0x22, 0x40)", "RGBColor(0xE2, 0xE8, 0xF0)")
content = content.replace("RGBColor(0x88, 0x88, 0x88)", "RGBColor(0x64, 0x74, 0x8B)")

# 3. Add formatters
formatters = """
def _fmt_eur(v):
    if v is None or v == 'N/A': return 'N/A'
    try: return f"€{float(v):.2f}m"
    except: return 'N/A'

def _fmt_x(v):
    if v is None or v == 'N/A': return 'N/A'
    try: return f"{float(v):.2f}×"
    except: return 'N/A'

def _fmt_pct(v):
    if v is None or v == 'N/A': return 'N/A'
    try: return f"{float(v):.2f}%"
    except: return 'N/A'
"""
content = content.replace("def _bg(", formatters + "\ndef _bg(")

# 4. Replace inline formats
content = re.sub(r'f"€\{([^}]+)\}m"', r'_fmt_eur(\1)', content)
content = re.sub(r'f"\{([^}]+)\}×"', r'_fmt_x(\1)', content)
content = re.sub(r'f"\{([^}]+)\}%"', r'_fmt_pct(\1)', content)

path.write_text(content)
print("Updated deck_builder.py")
