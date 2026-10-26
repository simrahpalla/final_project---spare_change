"""Data types for Spare Change: agent structured outputs and the audit entry."""

from typing import Literal

from pydantic import BaseModel, Field

Condition = Literal["new_sealed", "new_open_box", "refurbished", "used_working", "used_untested", "for_parts"]


# --------------------------------------------------------------------------- agent outputs


class ListingDraft(BaseModel):
    """Listing agent: the seller's messy text turned into clean fields."""

    part_number: str | None = Field(description="Exact catalog part number from lookup_part, or null if no confident match.")
    qty: int = Field(ge=1, description="Number of units offered.")
    condition: Condition
    asking_price: float | None = Field(description="Price PER UNIT the seller stated, or null if they stated none. Never invent one.")
    expiry_date: str | None = Field(None, description="YYYY-MM-DD if the text states an expiry (MM/YYYY -> last day of that month).")
    manufacture_date: str | None = Field(None, description="YYYY-MM-DD if the text gives a manufacture date instead of an expiry.")
    sds_available: Literal[0, 1] | None = Field(None, description="1 if the text says an SDS is on hand, 0 if it says there is none, else null.")
    other_items: list[str] = Field(default_factory=list, description=(
        "Other DIFFERENT products in the same post, e.g. ['2x 1756-OB16E output cards']. Empty if the post offers one "
        "product (any quantity). The fields above describe the first product only."))
    confidence: float = Field(ge=0, le=1, description="How sure you are of the part number and fields.")
    notes: str = Field("", description="One short sentence on anything ambiguous.")


class NeedDraft(BaseModel):
    """Need agent: a buyer's messy wanted post turned into clean fields. The budget is NOT extracted here:
    the buyer enters it in a private field, and code keeps it out of every public view."""

    part_number: str | None = Field(description="Exact catalog part number if the buyer named or clearly described one; else null.")
    platform: str | None = Field(description="The buyer's machine it is for, copied exactly from the buyer's installed platforms; null if unclear.")
    family: str | None = Field(description="Part family from the allowed list (e.g. 'Pump spare', 'Bearing'); null if unclear.")
    qty: int = Field(ge=1, description="Units needed (default 1 if not stated).")
    urgency: Literal["line_down", "high", "normal", "low"]
    downtime_cost_per_day: float | None = Field(None, description="USD per day of downtime if the post states it; else null.")
    other_items: list[str] = Field(default_factory=list, description="Other DIFFERENT parts asked for in the same post.")
    confidence: float = Field(ge=0, le=1)
    notes: str = Field("", description="One short sentence on anything ambiguous.")


class GuardReview(BaseModel):
    """Compliance guard (LLM): edge cases the code rules can't see."""

    decision: Literal["allow", "flag"]
    reasons: list[str] = Field(default_factory=list, description="Concrete reasons if flagged; empty if allowed.")


class ScoredMatch(BaseModel):
    buyer_id: int | None = Field(None, description="Seller-to-buyer direction: the candidate buyer.")
    listing_id: int | None = Field(None, description="Buyer-to-seller direction: the candidate listing.")
    need_id: int | None = Field(None, description="The open need the listing fills, if any.")
    score: int = Field(ge=0, le=100)
    reason: str = Field(description="Specific: name the platform/need, e.g. 'runs 4x S7-300 (18 yrs); line down at $12k/day'.")


class MatchResult(BaseModel):
    """Matching agent: the best buyers among the pre-filtered candidates, plus an outreach draft."""

    matches: list[ScoredMatch] = Field(max_length=3, description="Best first. Only buyers from the candidate list.")
    outreach_subject: str = Field(description="Email subject to the top buyer (empty if no matches).")
    outreach_body: str = Field(description="Short email to the top buyer (under 120 words; empty if no matches).")


class PriceSuggestion(BaseModel):
    """Pricing agent: a public ask and a private floor suggestion for the seller."""

    ask: float = Field(gt=0, description="Suggested public asking price per unit.")
    floor_suggestion: float = Field(gt=0, description="Suggested private minimum per unit (shown only to the seller).")
    rationale: str = Field(description="Two or three sentences citing new price, scrap value, condition and demand.")


class NegotiatorTurn(BaseModel):
    """What a negotiator did on its turn (the move itself is made through submit_offer / walk_away)."""

    move: Literal["offer", "accept", "walk_away", "none"]
    price: float | None = None
    reasoning: str = Field(description="One sentence: why this move. Never include your private limit.")


# --------------------------------------------------------------------------- audit


class AuditEntry(BaseModel):
    """One record in output/audit_trail.json (append-only)."""

    timestamp: str
    run_id: str
    subject: str | None = None  # what the run is about, e.g. "listing:12", "need:4", "negotiation:2"
    agent: str
    depth: int = 0
    step: int | None = None
    action: str  # run_start, agent_start, tool_call, tool_result, agent_end, blocked, limit_reached, run_end, ...
    delegated_to: str | None = None
    tool: str | None = None
    args: dict | None = None
    result: str | None = None
    error: str | None = None
    approval_status: str | None = None
    stop_reason: str | None = None
