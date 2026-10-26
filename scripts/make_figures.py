r"""SVG figures drawn from the evidence (called by build_report.py / build_slides.py).

report/walkaway.svg: offers by round for a walk-away pair (phase3_stress.json, pair 3/3, run 1).
"""

import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def walkaway_svg() -> str:
    r = json.loads((REPO / "output" / "phase3_stress.json").read_text(encoding="utf-8"))["raw"]["neg:3/3#1"]["result"]
    offers = r["negotiation"]["offers"]
    neg = json.loads((REPO / "output" / "eval_negotiation.json").read_text(encoding="utf-8"))
    pair = next(x for x in neg["logged_negotiations"] if x["pair"] == "3/3")
    floor, budget = pair["floor"], pair["ceiling"]
    W, H, L, R, T, B = 520, 230, 60, 150, 20, 40
    rounds = len(offers)
    lo, hi = 500, 1200
    x = lambda i: L + (i - 1) * (W - L - R) / (rounds - 1)  # noqa: E731
    y = lambda v: T + (hi - v) * (H - T - B) / (hi - lo)  # noqa: E731
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="11" role="img" '
           f'aria-label="Walk-away negotiation: offers by round">']
    for v in (600, 800, 1000, 1200):
        out.append(f'<line x1="{L}" x2="{W - R}" y1="{y(v):.1f}" y2="{y(v):.1f}" stroke="#EEF1F5"/><text x="{L - 6}" y="{y(v) + 4:.1f}" text-anchor="end" fill="#8A94A6">${v:,}</text>')
    for i in range(1, rounds + 1):
        out.append(f'<text x="{x(i):.1f}" y="{H - B + 16}" text-anchor="middle" fill="#8A94A6">{i}</text>')
    out.append(f'<text x="{(L + W - R) / 2:.0f}" y="{H - 6}" text-anchor="middle" fill="#5B6575">round</text>')
    out.append(f'<line x1="{L}" x2="{W - R}" y1="{y(floor):.1f}" y2="{y(floor):.1f}" stroke="#C2410C" stroke-dasharray="5 4" stroke-width="1.5"/>'
               f'<text x="{W - R + 6}" y="{y(floor) + 4:.1f}" fill="#C2410C" font-weight="700">seller floor ${floor:,.0f}</text>')
    out.append(f'<line x1="{L}" x2="{W - R}" y1="{y(budget):.1f}" y2="{y(budget):.1f}" stroke="#2563EB" stroke-dasharray="5 4" stroke-width="1.5"/>'
               f'<text x="{W - R + 6}" y="{y(budget) + 4:.1f}" fill="#2563EB" font-weight="700">buyer budget ${budget:,.0f}</text>')
    for side, col in (("seller", "#F97316"), ("buyer", "#2563EB")):
        pts = [(o["round"], o["price"]) for o in offers if o["from_side"] == side and o["action"] == "offer"]
        out.append('<polyline fill="none" stroke="%s" stroke-width="2" points="%s"/>' % (col, " ".join(f"{x(a):.1f},{y(b):.1f}" for a, b in pts)))
        out += [f'<circle cx="{x(a):.1f}" cy="{y(b):.1f}" r="4" fill="{col}"/>' for a, b in pts]
    last = offers[-1]
    if last["action"] == "walk_away":
        out.append(f'<text x="{x(last["round"]):.1f}" y="{y(1150):.1f}" text-anchor="middle" fill="#B91C1C" font-weight="700">walks away</text>')
        out.append(f'<text x="{x(last["round"]):.1f}" y="{y(1150) + 14:.1f}" text-anchor="middle" fill="#B91C1C">no deal</text>')
    out.append(f'<text x="{W - R + 6}" y="{y(860):.1f}" fill="#5B6575">no overlap:</text><text x="{W - R + 6}" y="{y(860) + 13:.1f}" fill="#5B6575">no deal is possible</text>')
    out.append("</svg>")
    return "".join(out)


def write_all():
    (REPO / "report" / "walkaway.svg").write_text(walkaway_svg(), encoding="utf-8")


if __name__ == "__main__":
    write_all()
    print("report/walkaway.svg")
