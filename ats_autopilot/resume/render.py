"""
Render a grounded, tailored résumé to clean HTML (and PDF where a converter is available).

HTML is always produced (zero-dependency). PDF is produced via WeasyPrint if installed;
otherwise the HTML is written and can be printed to PDF by any browser. The rendered content
is exactly the verified, grounded output of `tailor()` — rendering adds styling, never claims.
"""
from __future__ import annotations
from pathlib import Path
from html import escape

from .tailor import TailoredResume
from ..profile import Profile

_CSS = """
body{font-family:-apple-system,Segoe UI,Helvetica,Arial,sans-serif;max-width:760px;
margin:40px auto;color:#1a1a1a;line-height:1.4;padding:0 24px}
h1{margin:0;font-size:26px}
.contact{color:#555;font-size:13px;margin:4px 0 18px}
h2{font-size:13px;letter-spacing:.08em;text-transform:uppercase;color:#0b5;
border-bottom:1px solid #ddd;padding-bottom:3px;margin:20px 0 8px}
ul{margin:0;padding-left:18px}li{margin:5px 0;font-size:13.5px}
"""


def to_html(resume: TailoredResume, profile: Profile) -> str:
    contact = " · ".join(x for x in [profile.location, profile.email, profile.phone,
                                     profile.linkedin_url, profile.github_url] if x)
    parts = [f"<!doctype html><html><head><meta charset='utf-8'>",
             f"<title>{escape(profile.full_name)} — Résumé</title><style>{_CSS}</style></head><body>",
             f"<h1>{escape(profile.full_name)}</h1>",
             f"<div class='contact'>{escape(contact)}</div>"]
    for heading, lines in resume.sections:
        parts.append(f"<h2>{escape(heading)}</h2><ul>")
        parts.extend(f"<li>{escape(ln)}</li>" for ln in lines)
        parts.append("</ul>")
    parts.append("</body></html>")
    return "".join(parts)


def render(resume: TailoredResume, profile: Profile, out_path: str | Path) -> Path:
    """Write the résumé. .html always; .pdf if WeasyPrint is available, else falls back to .html."""
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    html = to_html(resume, profile)
    if out.suffix.lower() == ".pdf":
        try:
            from weasyprint import HTML  # optional dependency
            HTML(string=html).write_pdf(str(out))
            return out
        except Exception:
            out = out.with_suffix(".html")  # graceful fallback
    out.write_text(html, encoding="utf-8")
    return out
