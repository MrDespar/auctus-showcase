from pathlib import Path
path = Path("scripts/deck_builder.py")
c = path.read_text()
c = c.replace("_fmt_pct(sens[ek].get(xk, 'N/A'):.1f)", "_fmt_pct(sens[ek].get(xk, 'N/A'))")
c = c.replace("_fmt_eur(value:.1f)", "_fmt_eur(value)")
c = c.replace("_fmt_pct(pct:.1f)", "_fmt_pct(pct)")
path.write_text(c)
