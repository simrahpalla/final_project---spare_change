"""Code checks on the matching agent's answer, and a rules-only ranking to fall back on.

The matching agent scores buyers that code has already pre-filtered, but it can still mix up facts between
buyers (seen once: it gave Riverbend Foods the profile of Prairie Packaging and dropped Prairie). So every
answer is checked against the code-checked facts of each candidate before it is saved or shown:

  - every buyer must be one of the candidates, once;
  - each claim in a reason must be true FOR THAT BUYER: "4x S7-300 (18 yrs)", "need #1", "$12k/day",
    "line down", "no open need";
  - need_id must be the buyer's open need (or empty when it has none);
  - a buyer with an open need the listing fills scores 70+, an installed-base buyer below 70 (the prompt's bands);
  - every buyer with an open need is included, and the answer lists min(3, candidates) buyers.

If the check fails, the broker retries the agent once with the exact errors; if it fails again it uses
rules_ranking(): open needs first (urgency, then downtime cost), then installed base (units, then years),
with reasons written from the data. No model involved.
"""

import re

URGENCY_RANK = {"line_down": 0, "high": 1, "normal": 2, "low": 3}
_EQUIP = re.compile(r"runs (\d+)x (.+?) \((\d+) yrs\)")


def candidate_facts(c: dict) -> dict:
    """Facts the server checked for one candidate (from its `grounding` lines and `open_need`)."""
    equip = []
    for g in c.get("grounding", []):
        if m := _EQUIP.search(g):
            equip.append((int(m.group(1)), m.group(2), int(m.group(3))))
    return {"equip": equip, "need": c.get("open_need")}


def _platform_matches(text: str, platform: str) -> bool:
    words = [w for w in re.findall(r"[A-Za-z0-9\-]{2,}", platform.lower()) if w not in ("motor", "controller")]
    return any(w in text.lower() for w in words[-2:])


def reason_errors(reason: str, c: dict) -> list[str]:
    """Claims in `reason` that are not true for candidate `c`."""
    f, name, errs = candidate_facts(c), c["buyer_name"], []
    for qty, plat, yrs in re.findall(r"(\d+)\s*[x×]\s*([A-Za-z][A-Za-z0-9 \-/.]+?)\s*\((\d+)\s*(?:yrs?|years?)\)", reason):
        ok = any(e[0] == int(qty) and e[2] == int(yrs) and _platform_matches(plat, e[1]) for e in f["equip"])
        if not ok:
            real = "; ".join(f"{q}x {p} ({y} yrs)" for q, p, y in f["equip"]) or "no matching equipment"
            errs.append(f"{name}: reason says '{qty}x {plat.strip()} ({yrs} yrs)' but it runs {real}")
    need = f["need"]
    for k in re.findall(r"need\s*#\s*(\d+)", reason, re.I):
        if not need or int(k) != need["need_id"]:
            errs.append(f"{name}: reason cites need #{k}, but its open need is "
                        + (f"#{need['need_id']}" if need else "none"))
    for amt, kilo in re.findall(r"\$\s*([\d,]+(?:\.\d+)?)\s*(k)?\s*/\s*day", reason, re.I):
        v = float(amt.replace(",", "")) * (1000 if kilo else 1)
        if not need or abs(need["downtime_cost_per_day"] - v) > 1:
            errs.append(f"{name}: reason says ${v:,.0f}/day downtime, but its need says "
                        + (f"${need['downtime_cost_per_day']:,.0f}/day" if need else "no open need"))
    if re.search(r"line[\s-]*down", reason, re.I) and not (need and need["urgency"] == "line_down"):
        errs.append(f"{name}: reason says 'line down', but it has no line-down need")
    if re.search(r"\bno open need\b", reason, re.I) and need:
        errs.append(f"{name}: reason says 'no open need', but it has open need #{need['need_id']} "
                    f"({need['urgency'].replace('_', ' ')}, ${need['downtime_cost_per_day']:,.0f}/day)")
    return errs


def check_matches(matches: list[dict], cands: list[dict]) -> list[str]:
    """All problems with the agent's matches (empty list = passes)."""
    by_id = {c["buyer_id"]: c for c in cands}
    errs, seen = [], set()
    for m in matches:
        c = by_id.get(m["buyer_id"])
        if not c:
            errs.append(f"buyer #{m['buyer_id']} is not one of the candidates")
            continue
        if m["buyer_id"] in seen:
            errs.append(f"{c['buyer_name']} is listed twice")
        seen.add(m["buyer_id"])
        need = c.get("open_need")
        if need and m.get("need_id") != need["need_id"]:
            errs.append(f"{c['buyer_name']}: need_id should be {need['need_id']} (its open need), not {m.get('need_id')}")
        if not need and m.get("need_id") is not None:
            errs.append(f"{c['buyer_name']}: has no open need this listing fills, so need_id must be empty")
        if need and m["score"] < 70:
            errs.append(f"{c['buyer_name']}: has open need #{need['need_id']}, so its score must be 70 or more, not {m['score']}")
        if not need and m["score"] >= 70:
            errs.append(f"{c['buyer_name']}: has no open need, so its score must be below 70, not {m['score']}")
        errs += reason_errors(m.get("reason", ""), c)
    for c in cands:
        if c.get("open_need") and c["buyer_id"] not in seen and len(matches) < 3:
            errs.append(f"{c['buyer_name']} has open need #{c['open_need']['need_id']} and must be included")
    want = min(3, len(cands))
    if len(matches) < want:
        errs.append(f"list {want} buyers (there are {len(cands)} candidates), not {len(matches)}")
    return errs


def rules_ranking(cands: list[dict], limit: int = 3) -> list[dict]:
    """Rank candidates by code only: open needs (urgency, downtime), then installed base (units, years)."""
    def key(c):
        f = candidate_facts(c)
        need = f["need"]
        units = sum(q for q, _, _ in f["equip"])
        years = max((y for _, _, y in f["equip"]), default=0)
        if need:
            return (0, URGENCY_RANK.get(need["urgency"], 9), -need["downtime_cost_per_day"], -units)
        return (1, 0, -units, -years)

    out = []
    for i, c in enumerate(sorted(cands, key=key)[:limit]):
        f = candidate_facts(c)
        equip = ", ".join(f"{q}x {p} ({y} yrs)" for q, p, y in f["equip"]) or "a compatible platform"
        need = f["need"]
        if need:
            reason = (f"Open need #{need['need_id']} ({need['urgency'].replace('_', ' ')}, "
                      f"${need['downtime_cost_per_day']:,.0f}/day downtime); runs {equip}.")
            score = max(70, 95 - 5 * i)
        else:
            reason = f"No open need; runs {equip}: a likely future spare."
            score = max(35, 65 - 5 * i)
        out.append({"buyer_id": c["buyer_id"], "need_id": need["need_id"] if need else None, "score": score, "reason": reason})
    return out


def outreach_template(listing: dict, top: dict, cand: dict) -> tuple[str, str]:
    """A plain, factual outreach email built from data (used with the rules-only ranking)."""
    ask = f" at ${listing['asking_price']:,.0f} each" if listing.get("asking_price") else ""
    need = cand.get("open_need")
    why = (f"It fills your open need #{need['need_id']}." if need
           else f"Your plant runs equipment it fits ({listing['fits_platforms'][0]})." if listing.get("fits_platforms") else "")
    subject = f"{listing['description']} available ({listing['part_number']})"
    body = (f"Hello {cand['buyer_name']},\n\n"
            f"Spare Change has {listing['qty']} x {listing['part_number']} ({listing['description']}), "
            f"condition: {listing['condition'].replace('_', ' ')}{ask}, located in {listing['location']}. {why}\n\n"
            f"Would you like to discuss it?\n\nSpare Change")
    return subject, body


# ------------------------------------------------------------------ reverse direction (a new need -> listings)

CONDITION_RANK = {"new_sealed": 0, "new_open_box": 1, "refurbished": 2, "used_working": 3, "used_untested": 4, "for_parts": 5}
_PART_TOKEN = re.compile(r"\b(?:[0-9][A-Z0-9]{2,}-[A-Z0-9\-/]+|[A-Z]{2,}[0-9][A-Z0-9\-/]{3,}|[0-9]{8})\b")


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def reverse_reason_errors(reason: str, c: dict, need: dict) -> list[str]:
    """Claims in a reason about listing `c` that are not true for that listing."""
    errs, name = [], f"listing #{c['listing_id']}"
    allowed = {_norm(c["part_number"]), _norm(need.get("part_number") or "")}
    for tok in _PART_TOKEN.findall(reason):
        if _norm(tok) not in allowed and not any(_norm(tok) in a or a in _norm(tok) for a in allowed if a):
            errs.append(f"{name}: reason mentions part {tok}, but the listing is {c['part_number']}")
    for amt in re.findall(r"\$\s*([\d,]+(?:\.\d+)?)\s*(?:/\s*(?:unit|ea)|per\s+unit|each\b|ea\b)", reason, re.I):
        v = float(amt.replace(",", ""))
        if not c.get("asking_price") or abs(c["asking_price"] - v) > 1:
            errs.append(f"{name}: reason says ${v:,.0f} per unit, but its ask is "
                        + (f"${c['asking_price']:,.0f}" if c.get("asking_price") else "not stated"))
    return errs


def check_reverse_matches(matches: list[dict], cands: list[dict], need: dict) -> list[str]:
    by_id = {c["listing_id"]: c for c in cands}
    errs, seen = [], set()
    for m in matches:
        c = by_id.get(m.get("listing_id"))
        if not c:
            errs.append(f"listing #{m.get('listing_id')} is not one of the candidate listings")
            continue
        if m["listing_id"] in seen:
            errs.append(f"listing #{m['listing_id']} is listed twice")
        seen.add(m["listing_id"])
        if m.get("need_id") != need["need_id"]:
            errs.append(f"listing #{m['listing_id']}: need_id must be {need['need_id']}, not {m.get('need_id')}")
        if m["score"] < 70:
            errs.append(f"listing #{m['listing_id']}: it fills the need, so its score must be 70 or more, not {m['score']}")
        errs += reverse_reason_errors(m.get("reason", ""), c, need)
    want = min(3, len(cands))
    if len(matches) < want:
        errs.append(f"list {want} listings (there are {len(cands)} candidates), not {len(matches)}")
    return errs


def rules_ranking_reverse(cands: list[dict], need: dict, limit: int = 3) -> list[dict]:
    """Rank candidate listings by code only: exact part first, then condition, quantity coverage, lower ask."""
    def key(c):
        exact = 0 if c["why_it_fits"].startswith("same part") else 1
        covers = 0 if (c.get("qty") or 0) >= need["qty"] else 1
        return (exact, CONDITION_RANK.get(c.get("condition"), 9), covers, c.get("asking_price") or 1e9)

    out = []
    for i, c in enumerate(sorted(cands, key=key)[:limit]):
        exact = c["why_it_fits"].startswith("same part") or "substitute" in c["why_it_fits"]
        ask = f" · ${c['asking_price']:,.0f}/unit" if c.get("asking_price") else " · price on request"
        reason = (f"{'Same part' if c['why_it_fits'].startswith('same part') else 'Fits'} {c['part_number']} · "
                  f"{(c.get('condition') or '').replace('_', ' ')} · {c.get('qty')} units{ask} · {c.get('location')}")
        out.append({"listing_id": c["listing_id"], "buyer_id": need["buyer_id"], "need_id": need["need_id"],
                    "score": max(70, (95 if exact else 82) - 5 * i), "reason": reason})
    return out
