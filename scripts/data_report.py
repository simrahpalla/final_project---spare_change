"""Data quality report for the Surplus Exchange database (no model calls).

    .venv\\Scripts\\python.exe scripts\\data_report.py              # report on data/exchange_new.db
    .venv\\Scripts\\python.exe scripts\\data_report.py --db PATH    # report on another copy

Prints the report and saves it to output/data_report.md. It covers:
  - row counts for every table
  - plausible buyers for each listing and the reason (installed equipment, substitute, open need)
  - listings that could fill each open need
  - negotiation pairs split into deal likely / barely overlapping / walk away
  - the planted bad records, what is wrong with each, and which check should catch it
  - 11 PASS/FAIL data-quality checks, including a consistency check of data/answer_keys.json

Exit code 0 only if every check passes.
"""

import argparse
import hashlib
import json
import re
import sqlite3
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"
ORIGINAL_DB = DATA / "exchange.db"
WORKING_DB = DATA / "exchange_new.db"
ANSWER_KEYS = DATA / "answer_keys.json"
HASH_FILE = DATA / "exchange.db.sha256"
REPORT = REPO / "output" / "data_report.md"
sys.path.insert(0, str(REPO / "scripts"))

# --------------------------------------------------------------------------- deterministic rules
# The same rules the compliance guard will run in code (Phase 3). Here they verify that each planted
# bad record trips its check and that no clean listing does.

INJECTION_PATTERNS = [
    r"ignore (all )?(previous|prior|above) instructions", r"\byou are now\b", r"system (note|prompt)",
    r"do not flag", r"rank .{0,60}#\s*1", r"set the price to",
]
PRICE_MULTIPLE_LIMIT = 3.0       # asking > 3x new price looks fraudulent
COUNTERFEIT_RATIO = 0.35         # obsolete part sold new-sealed below 35% of list: counterfeit / grey-market risk


def rules_fired(l: dict, today: str) -> list[str]:
    fired = []
    text = l["raw_text"] or ""
    if any(re.search(p, text, re.I) for p in INJECTION_PATTERNS):
        fired.append("injection_pattern")
    if l["expiry_date"] and l["expiry_date"] < today:
        fired.append("expired")
    if l["hazmat"] and l["sds_available"] != 1:
        fired.append("hazmat_no_sds")
    if l["asking_price"] and l["asking_price"] > PRICE_MULTIPLE_LIMIT * l["new_price"]:
        fired.append("price_gt_3x_new")
    if (l["obsolete"] and l["condition"] == "new_sealed" and l["asking_price"]
            and l["asking_price"] < COUNTERFEIT_RATIO * l["new_price"]):
        fired.append("counterfeit_risk")
    return fired


# Signs a real plant manager typed the listing, not a database.
ABBREVIATIONS = [r"\bea\b", r"\bqty\b", r"\bw/", r"\bpcs\b", r"\bbtls?\b", r"\bOBO\b", r"\bNIB\b", r"\basap\b",
                 r"\bfw\b", r"\bpkg\b", r"\bbatts\b", r"\brefurbed\b", r"\bctr\b", r"\bctrl\b", r"\benet\b",
                 r"\bser\b", r"\bbrgs\b", r"\bcust\b", r"\bmods\b", r"\bmfd\b", r"\bpn\b", r"~", r"\b\d+x\b",
                 r"\bx\d+\b", r"\bAB\b", r"\bPF\d", r"\bDI\b", r"\bhp\b", r"\borig\b", r"\binfo\b"]
KNOWN_TYPOS = ["wrking", "procesors", "frieght", "cartriges", "recieved", "untill", "garanteed", "seperate"]

CONDITION_ORDER = ["new_sealed", "new_open_box", "refurbished", "used_working", "used_untested", "for_parts"]


PRODUCT_LINES = {"PLC": ["S7-", "Logix", "SLC", "Modicon", "MELSEC"], "drive": ["PowerFlex", "ACS"],
                 "pump": ["Grundfos CR", "Goulds"], "motor": ["motor"], "Fanuc control": ["Fanuc"]}


def product_line(platform: str) -> str:
    return next((line for line, words in PRODUCT_LINES.items() if any(w in platform for w in words)), "other")


def norm(s: str | None) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path: Path) -> str:
    con = sqlite3.connect(path)
    try:
        return "\n".join(con.iterdump())
    finally:
        con.close()


# --------------------------------------------------------------------------- loading


class Exchange:
    """Everything the report needs, read once from one database file."""

    def __init__(self, db: Path):
        con = sqlite3.connect(db)
        con.row_factory = sqlite3.Row
        self.con = con
        self.today = con.execute("SELECT value FROM exchange_meta WHERE key='today'").fetchone()[0]
        self.tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY rowid")]
        self.counts = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in self.tables}
        self.companies = {r["id"]: dict(r) for r in con.execute("SELECT * FROM companies")}
        self.catalog = {r["part_number"]: dict(r) for r in con.execute("SELECT * FROM part_catalog")}
        self.fits: dict[str, set[str]] = defaultdict(set)
        self.subs: list[tuple[str, str, str]] = []
        for r in con.execute("SELECT * FROM compatibility"):
            if r["relation"] == "fits":
                self.fits[r["part_number"]].add(r["platform"])
            else:
                self.subs.append((r["part_number"], r["substitutes_for"], r["platform"]))
        self.equipment: dict[int, set[str]] = defaultdict(set)
        for r in con.execute("SELECT company_id, platform FROM installed_equipment"):
            self.equipment[r["company_id"]].add(r["platform"])
        self.listings = {r["id"]: dict(r) for r in con.execute(
            """SELECT l.*, p.manufacturer, p.family, p.category, p.new_price, p.scrap_value, p.hazmat,
                      p.hazmat_class, p.shelf_life_months, p.obsolete
               FROM listings l LEFT JOIN part_catalog p USING (part_number) ORDER BY l.id""")}
        need_cols = {r[1] for r in con.execute("PRAGMA table_info(needs)")}
        self.needs_have_family = "family" in need_cols
        self.needs = {r["id"]: dict(r) for r in con.execute("SELECT * FROM needs ORDER BY id")}
        self.floor = {r[0]: r[1] for r in con.execute("SELECT listing_id, floor_price FROM seller_private")}
        self.ceiling = {r[0]: r[1] for r in con.execute("SELECT need_id, ceiling_price FROM buyer_private")}

    def name(self, cid: int) -> str:
        return self.companies[cid]["name"]

    # A listing can fill a need if it is the same part, a listed substitute, or (for needs that only
    # name a machine) a part of the right family that fits that machine.
    def fills(self, l: dict, n: dict) -> str | None:
        part = l["part_number"]
        if not part or l["seller_id"] == n["buyer_id"]:
            return None
        if n["part_number"]:
            if n["part_number"] == part:
                return f"same part {part}"
            for sub, replaces, platform in self.subs:
                if sub == part and replaces == n["part_number"] and (n["platform"] in (None, platform)):
                    return f"{part} is a listed substitute for {replaces} on {platform}"
            return None
        if self.needs_have_family and n["platform"] in self.fits[part] and n.get("family") == l["family"]:
            return f"need names only the machine ({n['platform']}); {part} is a {l['family'].lower()} that fits it"
        return None

    def plausible_buyers(self, l: dict) -> dict[int, list[str]]:
        out: dict[int, list[str]] = defaultdict(list)
        part = l["part_number"]
        if not part:
            return out
        for n in self.needs.values():
            if n["status"] == "open" and (why := self.fills(l, n)):
                out[n["buyer_id"]].append(f"open need #{n['id']}: {why}")
        platforms = self.fits[part] | {p for s, _, p in self.subs if s == part}
        for cid, installed in self.equipment.items():
            if cid == l["seller_id"]:
                continue
            for p in sorted(installed & platforms):
                out[cid].append(f"runs {p}")
        return dict(out)

    def decoys(self, l: dict) -> dict[int, list[str]]:
        """Buyers who run a same-brand, same-product-line platform the part does NOT fit
        (wrong platform, voltage or series), so a keyword search on brand or line would pick them."""
        fits = self.fits[l["part_number"]] if l["part_number"] else set()
        if not fits:
            return {}
        brand = l["manufacturer"].split()[0].lower()
        lines = {product_line(p) for p in fits}
        plausible = self.plausible_buyers(l)
        out = {}
        for cid, installed in self.equipment.items():
            if cid in plausible or cid == l["seller_id"]:
                continue
            wrong = sorted(p for p in installed
                           if p.lower().startswith(brand) and product_line(p) in lines and p not in fits)
            if wrong:
                out[cid] = wrong
        return out

    def is_bad(self, l: dict) -> bool:
        return l["status"] == "submitted"


def classify(floor: float, ceiling: float) -> str:
    if ceiling < floor:
        return "walk_away"
    if ceiling - floor < 0.10 * floor:
        return "barely_overlapping"
    return "deal_likely"


# --------------------------------------------------------------------------- checks


def run_checks(x: Exchange, keys: dict | None) -> list[dict]:
    checks = []

    def add(name: str, passed: bool, detail: str, fix: str = "") -> None:
        checks.append({"name": name, "passed": bool(passed), "detail": detail, "fix": "" if passed else fix})

    active = [l for l in x.listings.values() if not x.is_bad(l)]
    bad = [l for l in x.listings.values() if x.is_bad(l)]

    # 1. plausible buyer distribution (clean listings; bad ones should be blocked before matching)
    counts = {l["id"]: len(x.plausible_buyers(l)) for l in active}
    in_range = sum(1 <= c <= 3 for c in counts.values())
    zero = sum(c == 0 for c in counts.values())
    big = [lid for lid, c in counts.items() if c >= 10]
    add("1. Plausible buyers per listing: most 1-3, 2-3 with none, none with 10+",
        in_range / max(len(active), 1) >= 0.75 and 2 <= zero <= 3 and not big,
        f"{in_range}/{len(active)} clean listings have 1-3 plausible buyers, {zero} have none, "
        f"{len(big)} have 10+ {big or ''}. Distribution: {dict(sorted(Counter(counts.values()).items()))}",
        "Trim installed_equipment so each platform runs at <=3 non-seller plants; add 2-3 listings for parts no buyer runs.")

    # 2. compatibility-only matches (keyword search on the part number would miss them)
    compat_only = []
    for l in active:
        for n in x.needs.values():
            why = x.fills(l, n)
            if why and (n["part_number"] is None or n["part_number"] != l["part_number"]):
                keyword_hit = norm(l["part_number"]) in norm(n["raw_text"])
                if not keyword_hit:
                    compat_only.append((l["id"], n["id"], why))
    add("2. At least 5 matches only work through compatibility or substitutes",
        len(compat_only) >= 5,
        f"{len(compat_only)} found: " + "; ".join(f"listing {a} -> need {b}" for a, b, _ in compat_only),
        "Make several needs name only the machine (part_number NULL + platform + family), and add substitute pairs.")

    # 3. decoys
    decoy_pairs = [(l["id"], cid, p) for l in active for cid, p in x.decoys(l).items()]
    decoy_listings = sorted({lid for lid, _, _ in decoy_pairs})
    add("3. At least 3 decoys (same manufacturer, wrong platform / voltage / series)",
        len(decoy_listings) >= 3,
        f"{len(decoy_pairs)} decoy buyer-listing pairs across listings {decoy_listings}",
        "Give some buyers a same-brand platform the part does not fit (e.g. S7-1500 vs S7-300, 240V vs 480V drive).")

    # 4. price logic
    problems = []
    for p in x.catalog.values():
        if p["scrap_value"] >= 0.15 * p["new_price"]:
            problems.append(f"{p['part_number']} scrap {p['scrap_value']} not well below new {p['new_price']}")
    for l in active:
        if l["asking_price"] is not None and not (l["scrap_value"] < l["asking_price"] < l["new_price"]):
            problems.append(f"listing {l['id']} ask {l['asking_price']} not between scrap and new")
        if l["id"] in x.floor and l["asking_price"] is not None and x.floor[l["id"]] > l["asking_price"]:
            problems.append(f"listing {l['id']} floor above its own ask")
    by_cond = defaultdict(list)
    for l in active:
        if l["category"] == "spare_part" and l["asking_price"]:
            by_cond[l["condition"]].append(l["asking_price"] / l["new_price"])
    means = [(c, sum(v) / len(v)) for c in CONDITION_ORDER if (v := by_cond.get(c))]
    monotonic = all(a[1] > b[1] for a, b in zip(means, means[1:]))
    if not monotonic:
        problems.append("ask/new ratio does not fall from new_sealed to used_untested")
    prices = ([p["new_price"] for p in x.catalog.values()] + [l["asking_price"] for l in x.listings.values() if l["asking_price"]]
              + list(x.floor.values()) + list(x.ceiling.values()))
    round_share = sum(v % 50 == 0 for v in prices) / len(prices)
    if round_share > 0.25:
        problems.append(f"{round_share:.0%} of prices are multiples of $50")
    add("4. Prices are logical (scrap << ask << new, condition matters, not all round numbers)",
        not problems,
        "ask/new by condition: " + ", ".join(f"{c} {m:.2f}" for c, m in means)
        + f"; {round_share:.0%} of prices are multiples of $50"
        + (f". Problems: {'; '.join(problems[:6])}" if problems else ""),
        "Jitter catalog prices with a fixed-seed RNG, use non-round asks/floors/ceilings, and order asks by condition.")

    # 5. negotiation mix
    pairs = negotiation_pairs(x, keys)
    mix = Counter(p["type"] for p in pairs)
    add("5. Negotiation pairs mix all three types (not all easy deals)",
        all(mix[t] >= 2 for t in ("deal_likely", "barely_overlapping", "walk_away")) and mix["deal_likely"] <= 0.7 * len(pairs),
        f"{len(pairs)} pairs: {mix['deal_likely']} deal likely, {mix['barely_overlapping']} barely overlapping, {mix['walk_away']} walk away",
        "Lower some buyer ceilings below the seller floor, and set others within 10% of the floor.")

    # 6. messy raw text, clean structured fields
    lst = list(x.listings.values())
    abbrev = sum(any(re.search(a, l["raw_text"], re.I) for a in ABBREVIATIONS) for l in lst)
    typos = [l["id"] for l in lst if any(t in l["raw_text"].lower() for t in KNOWN_TYPOS)]
    no_exact_pn = sum(l["part_number"] not in l["raw_text"] for l in lst)
    no_price = sum(l["asking_price"] is None for l in lst)
    clean = all(l["part_number"] in x.catalog and l["qty"] and l["condition"] in CONDITION_ORDER for l in lst)
    add("6. Listing raw_text is messy; structured fields are the clean truth",
        abbrev >= 0.5 * len(lst) and len(typos) >= 3 and no_exact_pn >= 0.3 * len(lst) and no_price >= 3 and clean,
        f"{abbrev}/{len(lst)} use shop abbreviations, {len(typos)} have typos {typos}, {no_exact_pn} don't contain the exact "
        f"catalog part number, {no_price} state no price; structured fields valid for all: {clean}",
        "Rewrite raw_text with abbreviations, typos, partial part numbers and missing prices; keep structured fields clean.")

    # 7. bad records
    fired = {l["id"]: rules_fired(l, x.today) for l in lst}
    false_pos = {lid: r for lid, r in fired.items() if r and not x.is_bad(x.listings[lid])}
    key_bad = (keys or {}).get("bad_records", [])
    kinds = {b["check"] for b in key_bad}
    needed = {"injection_pattern", "expired", "hazmat_no_sds", "price_gt_3x_new"}
    subtle = [b for b in key_bad if b.get("subtle")]
    tagged = all(b.get("expected_outcome") for b in key_bad)
    missed = [b["listing_id"] for b in key_bad if b["check"] in RULE_CHECKS and b["check"] not in fired.get(b["listing_id"], [])]
    add("7. Bad records: injection, expired, hazmat w/o SDS, ~10x price, plus 1-2 subtle; each tagged",
        needed <= kinds and 1 <= len(subtle) <= 2 and tagged and not missed and not false_pos,
        f"{len(key_bad)} tagged bad records, checks {sorted(kinds) or 'none (no answer keys)'}, {len(subtle)} subtle; "
        f"rules that should fire but didn't: {missed or 'none'}; rules firing on clean listings: {false_pos or 'none'}",
        "Add 1-2 subtle bad records (e.g. expiry only derivable from mfg date + shelf life; counterfeit-risk pricing) "
        "and tag every bad record with its check and expected outcome in answer_keys.json.")

    # 8. private terms stay private
    leaks = []
    for table in ("listings", "needs"):
        for col in (r[1] for r in x.con.execute(f"PRAGMA table_info({table})")):
            if re.search(r"floor|ceiling|max_price|min_price|reserve|budget", col):
                leaks.append(f"{table}.{col}")
    for lid, f in x.floor.items():
        if re.search(rf"(?<![\d.]){f:g}(?![\d])|{f:,.0f}(?![\d])", x.listings[lid]["raw_text"]):
            leaks.append(f"listing {lid} text contains its floor {f:g}")
    for nid, c in x.ceiling.items():
        if re.search(rf"(?<![\d.]){c:g}(?![\d])|{c:,.0f}(?![\d])", x.needs[nid]["raw_text"]):
            leaks.append(f"need {nid} text contains its ceiling {c:g}")
    add("8. Seller floors and buyer ceilings live only in the private tables",
        not leaks, f"leaks: {leaks or 'none'}", "Move limits to seller_private / buyer_private and remove them from public text.")

    # 9. reproducible build, original untouched, reset works
    add(*reproducibility_check())

    # 10. small enough to ship
    size_kb = ORIGINAL_DB.stat().st_size / 1024
    rows = sum(x.counts.values())
    add("10. Small enough to ship in the repo as the test dataset",
        size_kb < 1024 and rows < 5000, f"exchange.db is {size_kb:.0f} KB with {rows} rows",
        "Shrink the dataset below 1 MB.")

    # 11. answer keys agree with the database
    add(*answer_key_check(x, keys))
    return checks


RULE_CHECKS = {"injection_pattern", "expired", "hazmat_no_sds", "price_gt_3x_new", "counterfeit_risk"}


def negotiation_pairs(x: Exchange, keys: dict | None) -> list[dict]:
    if keys and keys.get("negotiation_pairs"):
        src = [(p["listing_id"], p["need_id"]) for p in keys["negotiation_pairs"]]
    else:  # no answer keys yet: every clean listing / open need that fit together
        src = [(l["id"], n["id"]) for l in x.listings.values() if not x.is_bad(l)
               for n in x.needs.values() if x.fills(l, n)]
    out = []
    for lid, nid in src:
        f, c = x.floor[lid], x.ceiling[nid]
        out.append({"listing_id": lid, "need_id": nid, "floor": f, "ceiling": c, "type": classify(f, c)})
    return out


def reproducibility_check() -> tuple[str, bool, str, str]:
    name = "9. Reproducible seed, original never modified, reset works"
    fix = "Use a fixed random seed and deterministic timestamps; record the original's hash; add scripts/reset_db.py."
    notes, ok = [], True
    try:
        import seed_data
        from reset_db import reset
    except ImportError as e:
        return name, False, f"cannot import seed/reset: {e}", fix
    if not hasattr(seed_data, "RANDOM_SEED"):
        ok = False
        notes.append("no fixed RANDOM_SEED in seed_data.py")
    with tempfile.TemporaryDirectory() as tmp:
        a, b = Path(tmp) / "a.db", Path(tmp) / "b.db"
        seed_data.build(a)
        seed_data.build(b)
        same_twice = dump(a) == dump(b) and sha256(a) == sha256(b)
        same_as_repo = dump(a) == dump(ORIGINAL_DB)
        ok &= same_twice and same_as_repo
        notes.append(f"two fresh builds identical: {same_twice}; fresh build == data/exchange.db on disk: {same_as_repo}")
        # reset: dirty a scratch working copy, reset it, compare with the original
        scratch = Path(tmp) / "work.db"
        reset(ORIGINAL_DB, scratch)
        con = sqlite3.connect(scratch)
        con.execute("UPDATE listings SET status='sold' WHERE id=1")
        con.execute("INSERT INTO token_usage (run_id, run_kind, agent, model, input_tokens, output_tokens, cost_usd, created_at) "
                    "VALUES ('t','check','x','gpt-6-luna',1,1,0,'2026-10-25')")
        con.commit()
        con.close()
        reset(ORIGINAL_DB, scratch)
        reset_ok = dump(scratch) == dump(ORIGINAL_DB)
        ok &= reset_ok
        notes.append(f"reset restores a dirtied working copy: {reset_ok}")
    if HASH_FILE.exists():
        untouched = HASH_FILE.read_text().split()[0] == sha256(ORIGINAL_DB)
        notes.append(f"original matches its recorded SHA-256: {untouched}")
        ok &= untouched
    else:
        ok = False
        notes.append("no recorded hash of the original (data/exchange.db.sha256)")
    return name, ok, "; ".join(notes), fix


def answer_key_check(x: Exchange, keys: dict | None) -> tuple[str, bool, str, str]:
    name = "11. data/answer_keys.json is consistent with the database"
    fix = "Generate answer_keys.json from the seed script and fix any field that disagrees with the DB."
    if not keys:
        return name, False, "data/answer_keys.json not found", fix
    errors = []
    for k in keys["listings"]:
        l = x.listings.get(k["listing_id"])
        if not l:
            errors.append(f"listing {k['listing_id']} missing")
            continue
        for field, want in k["expected"].items():
            have = (sorted(x.fits[l["part_number"]]) if field == "platforms"
                    else x.catalog[l["part_number"]]["manufacturer"] if field == "manufacturer" else l.get(field))
            if have != want:
                errors.append(f"listing {l['id']}.{field}: key {want!r} vs db {have!r}")
        plausible = x.plausible_buyers(l)
        if k["is_bad_record"] != x.is_bad(l):
            errors.append(f"listing {l['id']}: is_bad_record {k['is_bad_record']} vs status {l['status']}")
        if not k["is_bad_record"] and set(k["top_buyers"]) != set(plausible):
            errors.append(f"listing {l['id']}: key buyers {sorted(k['top_buyers'])} vs plausible {sorted(plausible)}")
        first = k["expected_first_buyer"]
        if first is not None and (first not in k["top_buyers"] or not any(
                n["buyer_id"] == first and x.fills(l, n) for n in x.needs.values())):
            errors.append(f"listing {l['id']}: expected first buyer {first} has no open need this listing fills")
        for d in k["decoy_buyers"]:
            if d in plausible:
                errors.append(f"listing {l['id']}: decoy {d} is actually plausible")
    for k in keys["needs"]:
        n = x.needs.get(k["need_id"])
        if not n:
            errors.append(f"need {k['need_id']} missing")
            continue
        for lid in k["top_listings"]:
            if not x.fills(x.listings[lid], n):
                errors.append(f"need {n['id']}: listing {lid} cannot fill it")
        fillable = [l["id"] for l in x.listings.values() if not x.is_bad(l) and x.fills(l, n)]
        if sorted(fillable) != sorted(k["top_listings"]):
            errors.append(f"need {n['id']}: key {k['top_listings']} vs fillable clean listings {fillable}")
    for p in keys["negotiation_pairs"]:
        f, c = x.floor[p["listing_id"]], x.ceiling[p["need_id"]]
        if p["deal_expected"] != (f <= c) or p["type"] != classify(f, c):
            errors.append(f"pair {p['listing_id']}/{p['need_id']}: outcome disagrees with floor {f} / ceiling {c}")
        if p["deal_expected"] and p["price_range"] != [f, c]:
            errors.append(f"pair {p['listing_id']}/{p['need_id']}: price range {p['price_range']} vs [{f}, {c}]")
    for b in keys["bad_records"]:
        l = x.listings.get(b["listing_id"])
        if not l or not x.is_bad(l):
            errors.append(f"bad record {b['listing_id']} missing or not status 'submitted'")
    n_items = len(keys["listings"]) + len(keys["needs"]) + len(keys["negotiation_pairs"]) + len(keys["bad_records"])
    return name, not errors, f"{n_items} answer-key entries checked; {len(errors)} disagreements" + (
        f": {'; '.join(errors[:8])}" if errors else ""), fix


# --------------------------------------------------------------------------- report


def build_report(x: Exchange, keys: dict | None, checks: list[dict], db: Path) -> str:
    md = [f"# Surplus Exchange data report", "",
          f"Database: `{db.relative_to(REPO)}`. Exchange date: **{x.today}**. Generated by `scripts/data_report.py` (no model calls).", ""]
    passed = sum(c["passed"] for c in checks)
    md += [f"## Checks: {passed}/{len(checks)} PASS", "", "| Check | Result | Detail |", "|---|---|---|"]
    for c in checks:
        detail = c["detail"].replace("|", "/") + (f" **Fix:** {c['fix']}" if c["fix"] else "")
        md.append(f"| {c['name']} | **{'PASS' if c['passed'] else 'FAIL'}** | {detail} |")

    md += ["", "## Row counts", "", "| Table | Rows |", "|---|---|"]
    md += [f"| `{t}` | {n} |" for t, n in x.counts.items()]

    md += ["", "## Listings: plausible buyers", "",
           "A buyer is plausible if it has an open need the listing can fill (same part, listed substitute, or a part of the "
           "right family for the machine it named) or runs a platform the part fits. Decoys run a same-brand platform the part does not fit.", "",
           "| # | Part | Seller | Status | Plausible buyers | Why | Decoys |", "|---|---|---|---|---|---|---|"]
    for l in x.listings.values():
        pb = x.plausible_buyers(l)
        why = "<br>".join(f"{x.name(b)}: {'; '.join(r)}" for b, r in pb.items()) or "—"
        dec = "<br>".join(f"{x.name(b)} ({', '.join(p)})" for b, p in x.decoys(l).items()) or "—"
        md.append(f"| {l['id']} | {l['part_number']} | {x.name(l['seller_id'])} | {l['status']} | {len(pb)} | {why} | {dec} |")

    md += ["", "## Open needs: listings that could fill them", "", "| Need | Buyer | Asks for | Clean listings | Why |", "|---|---|---|---|---|"]
    for n in x.needs.values():
        if n["status"] != "open":
            continue
        fill = [(l, why) for l in x.listings.values() if not x.is_bad(l) and (why := x.fills(l, n))]
        asks = n["part_number"] or f"a {n.get('family') or 'part'} for {n['platform']}"
        md.append(f"| {n['id']} | {x.name(n['buyer_id'])} | {asks} | {len(fill)} | "
                  + ("<br>".join(f"listing {l['id']}: {w}" for l, w in fill) or "none yet") + " |")

    pairs = negotiation_pairs(x, keys)
    md += ["", "## Negotiation pairs", "", "Deal likely: ceiling at least 10% above floor. Barely overlapping: within 10%. Walk away: ceiling below floor.", ""]
    for t, label in (("deal_likely", "Deal likely"), ("barely_overlapping", "Barely overlapping (multiple rounds)"), ("walk_away", "Walk away")):
        group = [p for p in pairs if p["type"] == t]
        md += [f"**{label}: {len(group)}**", "", "| Listing | Need | Seller floor | Buyer ceiling | Gap |", "|---|---|---|---|---|"]
        md += [f"| {p['listing_id']} | {p['need_id']} | ${p['floor']:,.2f} | ${p['ceiling']:,.2f} | ${p['ceiling'] - p['floor']:,.2f} |" for p in group]
        md.append("")

    md += ["## Planted bad records", "", "| # | What's wrong | Check that should catch it | Expected outcome | Rules that fire now |", "|---|---|---|---|---|"]
    key_bad = {b["listing_id"]: b for b in (keys or {}).get("bad_records", [])}
    for l in x.listings.values():
        if not x.is_bad(l):
            continue
        b = key_bad.get(l["id"], {})
        md.append(f"| {l['id']} | {b.get('problem', '(no answer key)')}{' *(subtle)*' if b.get('subtle') else ''} | "
                  f"`{b.get('check', '?')}` | {b.get('expected_outcome', '?')} | {', '.join(rules_fired(l, x.today)) or 'none'} |")
    return "\n".join(md) + "\n"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--db", type=Path, default=WORKING_DB)
    p.add_argument("--brief", action="store_true", help="one line per check (fits a small terminal / screenshot)")
    args = p.parse_args()
    db = args.db.resolve()
    keys = json.loads(ANSWER_KEYS.read_text(encoding="utf-8")) if ANSWER_KEYS.exists() else None
    x = Exchange(db)
    checks = run_checks(x, keys)
    report = build_report(x, keys, checks, db)
    x.con.close()
    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text(report, encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    print(f"Surplus Exchange data report  |  {db.relative_to(REPO)}  |  exchange date {x.today}  |  no model calls\n")
    for c in checks:
        if args.brief:
            print(f"[{'PASS' if c['passed'] else 'FAIL'}] {c['name']}")
        else:
            print(f"[{'PASS' if c['passed'] else 'FAIL'}] {c['name']}\n       {c['detail']}" + (f"\n       FIX: {c['fix']}" if c["fix"] else ""))
    passed = sum(c["passed"] for c in checks)
    print(f"\n{passed}/{len(checks)} checks pass. Full report: {REPORT.relative_to(REPO)}")
    return 0 if passed == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
