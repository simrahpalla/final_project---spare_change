r"""Build report.html from report/report.md (self-contained: every image embedded, CSS inline).

    python scripts\build_report.py

Writes report.html at the repo root and in deliverables/, and refreshes output/report_numbers.md with where each
number is used. Every {{key}} must exist in scripts/report_numbers.py, or the build stops. Uses Pillow (if installed)
to re-encode screenshots as compact WebP; otherwise embeds the files as they are.
"""

import base64
import html
import io
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
import make_figures  # noqa: E402
import report_numbers  # noqa: E402

try:
    from PIL import Image
except ImportError:  # embed originals
    Image = None

COLORS = {"navy": "#0C2340", "orange": "#F97316", "orange_text": "#C2410C", "blue": "#2563EB", "green": "#3B6D11",
          "red": "#B91C1C", "teal": "#0F766E", "text": "#0F172A", "muted": "#5B6575", "border": "#D5DCE5", "fill": "#F5F7FA"}


def data_uri(path: Path, max_w=1600, quality=78) -> str:
    raw = path.read_bytes()
    if Image is not None:
        im = Image.open(io.BytesIO(raw))
        im = im.convert("RGB")
        if im.width > max_w:
            im = im.resize((max_w, round(im.height * max_w / im.width)), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, "WEBP", quality=quality, method=6)
        return "data:image/webp;base64," + base64.b64encode(buf.getvalue()).decode()
    mime = {".png": "image/png", ".webp": "image/webp", ".jpg": "image/jpeg"}[path.suffix.lower()]
    return f"data:{mime};base64," + base64.b64encode(raw).decode()


def fill(text: str, N: dict, used: dict, where: str) -> str:
    def rep(m):
        k = m.group(1)
        if k not in N:
            raise SystemExit(f"Unknown number key {{{{{k}}}}} in {where}: add it to scripts/report_numbers.py")
        used.setdefault(k, set()).add(where)
        return N[k][0]
    return re.sub(r"\{\{(\w+)\}\}", rep, text)


def inline(s: str) -> str:
    s = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r'<a href="\2">\1</a>', s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])", r"<i>\1</i>", s)
    return s


class Doc:
    def __init__(self):
        self.fig = 0

    def figure(self, line: str) -> str:
        m = re.match(r"!fig\[([^|]+)\|([^|]+)\|?([^\]]*)\]", line)
        if m:
            self.fig += 1
            src, cap, w = m.group(1), m.group(2), m.group(3) or "100%"
            return (f'<figure style="width:{w}"><img src="{data_uri(REPO / src)}" alt="{html.escape(cap)}">'
                    f'<figcaption><b>Figure {self.fig}:</b> {inline(cap)}</figcaption></figure>')
        m = re.match(r"!fig2\[([^|]+)\|([^|]+)\|([^\]]+)\]", line)
        if m:
            a, b = self.fig + 1, self.fig + 2
            self.fig += 2
            return (f'<figure class="pair"><div><img src="{data_uri(REPO / m.group(1))}" alt="Figure {a}"><span>Figure {a}</span></div>'
                    f'<div><img src="{data_uri(REPO / m.group(2))}" alt="Figure {b}"><span>Figure {b}</span></div>'
                    f'<figcaption><b>Figures {a} and {b}:</b> {inline(m.group(3))}</figcaption></figure>')
        m = re.match(r"!svgfig\[([^|]+)\|([^|]+)\|?([^\]]*)\]", line)
        if m:
            self.fig += 1
            svg = (REPO / m.group(1)).read_text(encoding="utf-8")
            return (f'<figure class="diagram" style="width:{m.group(3) or "100%"}">{svg}'
                    f'<figcaption><b>Figure {self.fig}:</b> {inline(m.group(2))}</figcaption></figure>')
        m = re.match(r"!svg\[([^|]+)\|([^\]]+)\]", line)
        if m:
            svg = (REPO / m.group(1)).read_text(encoding="utf-8")
            return f'<figure class="diagram">{svg}<figcaption><b>Diagram:</b> {inline(m.group(2))}</figcaption></figure>'
        raise SystemExit(f"Bad figure line: {line}")


def md_to_html(md: str) -> str:
    doc, out, lines, i = Doc(), [], md.splitlines(), 0
    while i < len(lines):
        ln = lines[i]
        if not ln.strip():
            i += 1
            continue
        if ln.startswith("<"):
            block = []
            while i < len(lines) and lines[i].strip():
                block.append(lines[i])
                i += 1
            out.append(inline("\n".join(block)) if not block[0].startswith("<svg") else "\n".join(block))
            continue
        if ln.startswith("!"):
            out.append(doc.figure(ln.strip()))
            i += 1
            continue
        m = re.match(r"(#{1,3}) (.*)", ln)
        if m:
            lvl, txt = len(m.group(1)), inline(m.group(2))
            out.append(f'<header class="titlebar"><div class="logo">¢</div><h1>{txt}</h1></header>' if lvl == 1 else f"<h{lvl}>{txt}</h{lvl}>")
            i += 1
            continue
        if ln.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            head, body = rows[0], [r for r in rows[2:]]
            t = "<table><thead><tr>" + "".join(f"<th>{inline(c)}</th>" for c in head) + "</tr></thead><tbody>"
            t += "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in body) + "</tbody></table>"
            out.append(t)
            continue
        if re.match(r"(- |\d+\. )", ln):
            tag = "ol" if ln[0].isdigit() else "ul"
            items = []
            while i < len(lines) and re.match(r"(- |\d+\. )", lines[i]):
                items.append(re.sub(r"^(- |\d+\. )", "", lines[i]))
                i += 1
            out.append(f"<{tag}>" + "".join(f"<li>{inline(x)}</li>" for x in items) + f"</{tag}>")
            continue
        para = []
        while i < len(lines) and lines[i].strip() and not re.match(r"(#|\||- |\d+\. |!|<)", lines[i]):
            para.append(lines[i])
            i += 1
        out.append(f"<p>{inline(' '.join(para))}</p>")
    return "\n".join(out)


CSS = """
@page { size: Letter; margin: 0.6in 0.65in; }
* { box-sizing: border-box; }
body { font-family: Inter, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; font-size: 11pt; line-height: 1.45; color: %(text)s;
       max-width: 8.5in; margin: 0 auto; padding: 0 0.3in 0.4in; background: #fff; }
a { color: %(blue)s; text-decoration: none; word-break: break-word; }
.titlebar { background: %(navy)s; color: #fff; margin: 0 -0.3in 10pt; padding: 16pt 0.3in; display: flex; align-items: center; gap: 12pt; }
.titlebar h1 { margin: 0; font-size: 26pt; letter-spacing: -0.5pt; }
.logo { width: 34pt; height: 34pt; border-radius: 50%%; background: %(orange)s; color: %(navy)s; font-weight: 800; font-size: 20pt;
        display: flex; align-items: center; justify-content: center; }
.tagline { font-size: 14pt; font-weight: 700; color: %(navy)s; margin: 4pt 0; }
.tagline span { color: %(blue)s; font-weight: 600; margin-left: 6pt; }
.meta { color: %(muted)s; margin: 4pt 0 8pt; }
.oneliner { margin: 6pt 0; }
.summary { border-left: 4pt solid %(orange)s; background: %(fill)s; padding: 8pt 12pt; margin: 10pt 0 6pt; break-inside: avoid; }
h2 { color: %(navy)s; font-size: 16pt; margin: 18pt 0 6pt; padding-bottom: 3pt; border-bottom: 2pt solid %(orange)s; break-after: avoid; }
h3 { color: %(navy)s; font-size: 12.5pt; margin: 12pt 0 4pt; break-after: avoid; }
p { margin: 5pt 0; }
ul, ol { margin: 4pt 0 6pt; padding-left: 18pt; }
li { margin: 2pt 0; }
code { font-family: Consolas, 'SFMono-Regular', Menlo, monospace; font-size: 9.5pt; background: %(fill)s; padding: 0 2pt; border-radius: 3pt; }
.pn { font-family: Consolas, 'SFMono-Regular', Menlo, monospace; font-weight: 600; }
table { border-collapse: collapse; width: 100%%; margin: 6pt 0 2pt; font-size: 9.5pt; break-inside: avoid; }
th { background: %(navy)s; color: #fff; text-align: left; padding: 4pt 6pt; font-weight: 600; }
td { border: 1px solid %(border)s; padding: 3.5pt 6pt; vertical-align: top; }
tbody tr:nth-child(even) td { background: #FAFBFC; }
.caption, figcaption { font-size: 9pt; color: %(muted)s; margin: 3pt 0 8pt; }
figure { margin: 8pt auto 10pt; break-inside: avoid; text-align: center; }
figure img { width: 100%%; border: 1px solid %(border)s; border-radius: 6pt; }
figure figcaption { text-align: left; }
figure.pair { display: flex; flex-wrap: wrap; gap: 8pt; width: 100%%; }
figure.pair > div { flex: 1 1 0; text-align: center; font-size: 8.5pt; color: %(muted)s; }
figure.pair figcaption { flex-basis: 100%%; }
figure.diagram svg { width: 100%%; height: auto; }
.offers { font-family: Consolas, Menlo, monospace; font-size: 9.5pt; background: #F5F7FA; border-left: 3pt solid #F97316; padding: 5pt 9pt; }
b.teal, .teal { color: %(teal)s; }
@media print { body { padding: 0; } .titlebar { margin: 0 0 10pt; } a { color: %(navy)s; } }
""" % COLORS


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    make_figures.write_all()
    N = report_numbers.build()
    used = {}
    md = fill((REPO / "report" / "report.md").read_text(encoding="utf-8"), N, used, "report")
    body = md_to_html(md)
    page = (f'<!DOCTYPE html>\n<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
            f"<title>Spare Change: final report (Simrah Palla)</title><style>{CSS}</style></head><body>\n{body}\n</body></html>\n")
    (REPO / "deliverables").mkdir(exist_ok=True)
    for dest in (REPO / "report.html", REPO / "deliverables" / "report.html"):
        dest.write_text(page, encoding="utf-8")
    # merge usage with the slides' (if built) and refresh the ledger
    prev = REPO / "output" / ".numbers_used_slides.txt"
    if prev.exists():
        for line in prev.read_text(encoding="utf-8").splitlines():
            used.setdefault(line, set()).add("slides")
    (REPO / "output" / ".numbers_used_report.txt").write_text("\n".join(sorted(used)), encoding="utf-8")
    report_numbers.write_ledger(N, used)
    print(f"report.html: {len(page) / 1e6:.2f} MB, {len(used)} numbers used")
    return 0


if __name__ == "__main__":
    sys.exit(main())
