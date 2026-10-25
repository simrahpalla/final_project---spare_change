"""Deterministic compliance rules for listings. Plain code, no model calls.

Used by the MCP server (check_listing_rules / activate_listing refuse a listing that trips a
rule) and by scripts/data_report.py, so the data checks and the app enforce the same rules.
The LLM compliance guard only handles edge cases these rules can't see.
"""

import re
from datetime import date

INJECTION_PATTERNS = [
    r"ignore (all )?(previous|prior|above) instructions",
    r"\byou are now\b",
    r"system (note|prompt)",
    r"do not flag",
    r"rank .{0,60}#\s*1",
    r"set the price to",
    r"(reveal|print|show).{0,40}(instructions|system prompt|floor|ceiling)",
]
PRICE_MULTIPLE_LIMIT = 3.0  # asking > 3x new price looks fraudulent
COUNTERFEIT_RATIO = 0.35    # obsolete part sold new-sealed below 35% of list: grey-market / counterfeit risk

# rule -> (outcome, plain-English reason)
RULES = {
    "injection_pattern": ("block", "Listing text contains instructions aimed at the AI (prompt injection)."),
    "expired": ("block", "Chemical is past its expiry date."),
    "hazmat_no_sds": ("block", "Hazardous material listed without a safety data sheet (SDS)."),
    "price_gt_3x_new": ("block", f"Asking price is more than {PRICE_MULTIPLE_LIMIT:g}x the new price."),
    "counterfeit_risk": ("review", "Discontinued part offered new-sealed far below list: counterfeit / grey-market risk."),
}


def injection_hits(text: str | None) -> list[str]:
    return [p for p in INJECTION_PATTERNS if re.search(p, text or "", re.I)]


def add_months(d: date, months: int) -> date:
    month = d.month - 1 + months
    year, month = d.year + month // 12, month % 12 + 1
    days = [31, 29 if year % 4 == 0 and (year % 100 or year % 400 == 0) else 28,
            31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1]
    return date(year, month, min(d.day, days))


def expiry_from_manufacture(manufacture_date: str, shelf_life_months: int | None) -> str | None:
    """Expiry = manufacture date + catalog shelf life (code, not the model, does this math)."""
    if not manufacture_date or not shelf_life_months:
        return None
    return add_months(date.fromisoformat(manufacture_date), shelf_life_months).isoformat()


def rules_fired(listing: dict, today: str) -> list[str]:
    """Rule names a listing trips. `listing` needs raw_text, expiry_date, sds_available, asking_price,
    condition, plus catalog fields hazmat, new_price, obsolete."""
    fired = []
    if injection_hits(listing.get("raw_text")):
        fired.append("injection_pattern")
    if listing.get("expiry_date") and listing["expiry_date"] < today:
        fired.append("expired")
    if listing.get("hazmat") and listing.get("sds_available") != 1:
        fired.append("hazmat_no_sds")
    ask, new = listing.get("asking_price"), listing.get("new_price")
    if ask and new and ask > PRICE_MULTIPLE_LIMIT * new:
        fired.append("price_gt_3x_new")
    if (listing.get("obsolete") and listing.get("condition") == "new_sealed" and ask and new
            and ask < COUNTERFEIT_RATIO * new):
        fired.append("counterfeit_risk")
    return fired


def verdict(fired: list[str]) -> dict:
    """allowed / blocked / needs_review, with reasons."""
    outcomes = {RULES[r][0] for r in fired}
    status = "blocked" if "block" in outcomes else "needs_review" if "review" in outcomes else "allowed"
    return {"status": status, "rules": fired, "reasons": [RULES[r][1] for r in fired]}
