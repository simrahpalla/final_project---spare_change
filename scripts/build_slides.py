r"""Build slides.html (reveal.js from a CDN) from slides/slides.md, with every image embedded.

    python scripts\build_slides.py

Writes slides.html at the repo root and in deliverables/. Numbers are {{key}}s from scripts/report_numbers.py.
"""

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
import make_figures  # noqa: E402
import report_numbers  # noqa: E402
from build_report import data_uri, fill  # noqa: E402

REVEAL = "https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/dist"

CSS = """
.reveal { font-family: Inter, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #0F172A; font-size: 30px; }
.reveal .slides section { text-align: left; }
.reveal h1, .reveal h2, .reveal h3 { font-family: inherit; color: #0C2340; text-transform: none; letter-spacing: -0.5px; }
.reveal h2 { font-size: 1.6em; margin-bottom: 0.5em; border-bottom: 5px solid #F97316; display: inline-block; padding-bottom: 4px; }
.reveal h3 { font-size: 0.95em; margin: 0 0 0.3em; }
.reveal p { margin: 0.25em 0; line-height: 1.3; }
.reveal a { color: #2563EB; }
.reveal ul { margin-left: 1em; } .reveal li { margin: 0.25em 0; }
.title-slide { display: flex; flex-direction: column; justify-content: center; }
.title-slide h1 { font-size: 3.2em; margin: 0.2em 0 0; }
.tag { font-size: 1.4em; font-weight: 700; color: #C2410C; }
.sub { color: #5B6575; max-width: 85%; }
.who { margin-top: 1.2em !important; font-size: 0.75em; color: #5B6575; }
.logo { width: 70px; height: 70px; border-radius: 50%; background: #F97316; color: #0C2340; font-weight: 800; font-size: 44px;
        display: flex; align-items: center; justify-content: center; }
.logo.big { width: 110px; height: 110px; font-size: 70px; }
.cols2 { display: grid; grid-template-columns: 1fr 1fr; gap: 30px; }
.cols3 { display: grid; grid-template-columns: 1.3fr 1fr 1fr; gap: 22px; font-size: 0.8em; }
.card { border: 2px solid #D5DCE5; border-radius: 12px; padding: 18px 22px; }
.card.sell { border-color: #F97316; } .card.buy { border-color: #2563EB; }
.card img { width: 100%; border: 1px solid #D5DCE5; border-radius: 6px; margin: 4px 0; }
.big-num { font-size: 1.7em; font-weight: 800; color: #0C2340; display: block; line-height: 1.1; }
.cols3 .big-num { font-size: 2.2em; }
.pass { background: #EAF3DE; color: #3B6D11; border-radius: 6px; padding: 0 8px; font-size: 0.8em; }
.src, .caption { font-size: 18px; color: #5B6575; margin-top: 0.8em !important; }
.caption { font-size: 0.6em; }
table.cmp { font-size: 0.62em; border-collapse: collapse; width: 100%; }
table.cmp th { background: #0C2340; color: #fff; padding: 8px; font-weight: 600; border: none; }
table.cmp td { border-bottom: 1px solid #D5DCE5; padding: 8px; text-align: center; }
table.cmp td:first-child { text-align: left; font-weight: 600; }
table.cmp tr.us td { background: #FFF7ED; color: #C2410C; font-weight: 800; font-size: 1.1em; }
.shots2 { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; align-items: start; }
.shots3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; align-items: start; }
.shots2 img, .shots3 img { width: 100%; border: 1px solid #D5DCE5; border-radius: 6px; margin: 0; max-height: 470px; object-fit: contain; object-position: top; }
.diagram svg { width: 100%; height: auto; max-height: 560px; }
.stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin: 0.6em 0; }
.stats div { border-top: 5px solid #F97316; padding-top: 10px; }
.stats span:last-child { font-size: 0.6em; color: #5B6575; display: block; }
.stats.teal div { border-color: #0F766E; } .stats.teal .big-num { color: #0F766E; font-size: 1.5em; }
.callout { background: #F5F7FA; border-left: 6px solid #F97316; padding: 12px 18px; font-size: 0.8em; margin-top: 0.8em !important; }
.todo { border: 3px dashed #B91C1C; color: #B91C1C; padding: 8px 14px; font-weight: 700; font-size: 0.65em; display: inline-block; }
.lab { font-size: 0.6em; font-weight: 700; margin: 0 0 4px !important; } .lab.sell { color: #C2410C; } .lab.buy { color: #2563EB; }
table.tok { margin-top: 0.5em; font-size: 22px; }
.cmp2 { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
table.cmp td span { display: block; font-size: 0.8em; font-weight: 400; color: #5B6575; }
.cmp2 table.cmp, table.us-row { font-size: 24px; }
.cmp2 table.cmp th:not(:first-child), .cmp2 table.cmp td:not(:first-child) { width: 13%; }
table.us-row { margin-top: 8px; } table.us-row td:not(:first-child) { width: 7%; font-size: 1.2em; }
table.us-row tr.us td span { color: #C2410C; font-weight: 600; }
.demo { display: grid; grid-template-columns: 1.7fr 1fr; gap: 24px; align-items: start; }
.demo img { width: 100%; border: 1px solid #D5DCE5; border-radius: 6px; margin: 0; }
.steps p { font-size: 0.8em; margin: 0.45em 0 !important; } .steps .big-num { margin-top: 0.6em !important; }
.muted { color: #5B6575; font-size: 0.6em !important; }
.closer { font-size: 1.15em; font-weight: 800; color: #C2410C; margin-top: 1.2em !important; }
.reveal .slide-number { background: #0C2340; }
.reveal .progress { color: #F97316; }
"""


def slide_html(block: str) -> tuple[str, str]:
    body, notes = [], []
    for ln in block.strip().splitlines():
        if ln.startswith("Note:"):
            notes.append(ln[5:].strip())
        elif ln.startswith("<!--"):
            continue
        elif ln.strip().startswith("!svg["):
            path = re.match(r"\s*!svg\[([^\]]+)\]", ln).group(1)
            body.append(f'<div class="diagram">{(REPO / path).read_text(encoding="utf-8")}</div>')
        else:
            body.append(re.sub(r"!img\[([^|\]]+)\|?([^\]]*)\]",
                               lambda m: f'<img src="{data_uri(REPO / m.group(1), max_w=1400, quality=72)}" style="{m.group(2)}" alt="">', ln))
    return "\n".join(body), " ".join(notes)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    make_figures.write_all()
    N = report_numbers.build()
    used = {}
    raw = re.sub(r"<!--.*?-->", "", (REPO / "slides" / "slides.md").read_text(encoding="utf-8"), flags=re.S)
    src = fill(raw, N, used, "slides")
    blocks = [b for b in re.split(r"^---\s*$", src, flags=re.M) if b.strip()]
    sections = []
    for b in blocks:
        body, notes = slide_html(b)
        if not body.strip():
            continue
        sections.append(f'<section>\n{body}\n<aside class="notes">{notes}</aside>\n</section>')
    if len(sections) > 10:
        raise SystemExit(f"{len(sections)} slides: the limit is 10")
    page = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Spare Change: slides (Simrah Palla)</title>
<link rel="stylesheet" href="{REVEAL}/reveal.css">
<link rel="stylesheet" href="{REVEAL}/theme/white.css">
<style>{CSS}</style></head>
<body><div class="reveal"><div class="slides">
{chr(10).join(sections)}
</div></div>
<script src="{REVEAL}/reveal.js"></script>
<script src="{REVEAL.rsplit("/dist", 1)[0]}/plugin/notes/notes.js"></script>
<script>Reveal.initialize({{ hash: true, center: true, slideNumber: 'c/t', width: 1280, height: 720, margin: 0.05, transition: 'fade', plugins: typeof RevealNotes !== 'undefined' ? [RevealNotes] : [] }});</script>
</body></html>
"""
    (REPO / "deliverables").mkdir(exist_ok=True)
    for dest in (REPO / "slides.html", REPO / "deliverables" / "slides.html"):
        dest.write_text(page, encoding="utf-8")
    (REPO / "output" / ".numbers_used_slides.txt").write_text("\n".join(sorted(used)), encoding="utf-8")
    prev = REPO / "output" / ".numbers_used_report.txt"
    if prev.exists():
        for k in prev.read_text(encoding="utf-8").splitlines():
            used.setdefault(k, set()).add("report")
    report_numbers.write_ledger(N, used)
    print(f"slides.html: {len(sections)} slides, {len(page) / 1e6:.2f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
