from pathlib import Path
path = Path("scripts/deck_builder.py")
c = path.read_text()
c = c.replace("_fmt_eur(float(v):.2f)", 'f"€{float(v):.2f}m"')
c = c.replace("_fmt_x(float(v):.2f)", 'f"{float(v):.2f}×"')
c = c.replace("_fmt_pct(float(v):.2f)", 'f"{float(v):.2f}%"')
path.write_text(c)
