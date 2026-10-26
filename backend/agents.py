"""Spare Change agents and the broker that runs them.

Design
- The BROKER is plain Python (no LLM): it routes each event through fixed steps, and runs code
  wherever code is enough (injection pre-screen, compliance rules, the SQL buyer pre-filter, price
  clamping). The model is called only where judgment is needed:
      listing_agent      messy seller text -> ListingDraft        (tools: lookup_part, get_compatibility)
      compliance_guard   edge cases the rules can't see -> GuardReview   (no tools; data in prompt)
      matching_agent     score pre-filtered candidates -> MatchResult    (no tools; data in prompt)
      pricing_agent      price facts -> PriceSuggestion                  (no tools; data in prompt)
      seller_negotiator / buyer_negotiator  one move per turn            (tools: own private terms, submit_offer, walk_away)
- Every agent uses gpt-6-luna through Portkey. All data access goes through the surplus-exchange MCP
  server: the broker's process (role "broker"), a "system" process for token logging, and one process per
  negotiation side, bound to that negotiation, so each side can read only its own limit.
- User text is wrapped in tags and labelled as data. Tags inside the text are neutralized.
- Every agent call is capped (requests, tool calls, tokens), written to token_usage with its cost, and
  logged step by step to output/audit_trail.json. A run stops when it reaches MAX_MODEL_REQUESTS or
  MAX_TOKENS_PER_RUN; a run won't start once the session has spent SESSION_BUDGET_USD.
"""

import asyncio
import json
import os
import re
import sys
import uuid
from dataclasses import dataclass, field

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

from pydantic_ai import Agent
from pydantic_ai.exceptions import ModelAPIError, ModelHTTPError, UnexpectedModelBehavior, UsageLimitExceeded
from pydantic_ai.messages import ModelRequest, ModelResponse, RetryPromptPart, ToolCallPart, ToolReturnPart
from pydantic_ai.usage import UsageLimits

import audit
import config
from llm import make_model, usage_breakdown
from match_check import (check_matches, check_reverse_matches, outreach_template, rules_ranking,
                         rules_ranking_reverse)
from mcp_pool import McpPool, McpUnavailable, RoleConnection
from models import GuardReview, ListingDraft, MatchResult, NeedDraft, NegotiatorTurn, PriceSuggestion

sys.path.insert(0, str(config.REPO_DIR / "mcp_server"))
from compliance_rules import injection_hits  # noqa: E402  (pure code, no database access)

AGENT_MAX_REQUESTS = 8     # model requests in one agent call
AGENT_MAX_TOOL_CALLS = 10  # tool calls in one agent call
OUTPUT_RETRIES = 1         # a malformed answer is retried once by pydantic-ai
FRIENDLY_ERROR = "The AI service didn't respond properly. Nothing was saved or sent. Please try again in a minute."

LISTING_TOOLS = {"lookup_part", "get_compatibility"}
NEGOTIATOR_TOOLS = {"get_my_private_terms", "submit_offer", "walk_away"}


def _prompt(name: str) -> str:
    return (config.PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")


def wrap(tag: str, text: str | None) -> str:
    """Wrap user text as data. Any tag-like text inside it is neutralized so it can't close the wrapper."""
    safe = re.sub(r"<\s*/?\s*([a-z_]+)", r"[\1", text or "", flags=re.I)
    return f"<{tag}>\n{safe}\n</{tag}>"


def _public(listing: dict) -> dict:
    """A listing as the UI shows it (no raw seller text, no private floor)."""
    return {k: v for k, v in (listing or {}).items() if k not in ("seller_text_untrusted", "ok")}


def _transient(e: Exception) -> bool:
    """Errors worth one retry: timeouts, dropped connections, overload / 5xx / 429."""
    if isinstance(e, ModelHTTPError):
        return e.status_code >= 500 or e.status_code == 429
    return isinstance(e, (ModelAPIError, TimeoutError, asyncio.TimeoutError, ConnectionError, OSError))


class AgentFailed(Exception):
    """A model call failed after its retry. Carries a friendly message for the user."""

    def __init__(self, agent: str, kind: str, detail: str):
        super().__init__(f"{agent} {kind}: {detail}")
        self.agent, self.kind, self.detail = agent, kind, detail


class RunLimitReached(Exception):
    def __init__(self, reason: str, detail: str):
        super().__init__(f"{reason}: {detail}")
        self.reason, self.detail = reason, detail


@dataclass
class RunState:
    """One run (a seller flow, a need flow or a negotiation): totals across all its agent calls."""

    kind: str
    subject: str
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    requests: int = 0
    input_tokens: int = 0
    cached_tokens: int = 0
    cache_write_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    agent_calls: list = field(default_factory=list)
    steps: list = field(default_factory=list)
    current: str | None = None   # the agent working right now (for the UI's live activity rail)
    status: str = "running"      # running -> done
    result: dict | None = None

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.cached_tokens + self.cache_write_tokens + self.output_tokens

    def step(self, name: str, status: str, **detail) -> dict:
        entry = {"step": name, "status": status, **detail}
        self.steps.append(entry)
        return entry

    def totals(self) -> dict:
        return {"run_id": self.run_id, "kind": self.kind, "requests": self.requests, "input_tokens": self.input_tokens,
                "cached_tokens": self.cached_tokens, "cache_write_tokens": self.cache_write_tokens,
                "output_tokens": self.output_tokens, "total_tokens": self.total_tokens, "cost_usd": round(self.cost_usd, 6)}


class Exchange:
    """Owns the MCP connections and the agents. Use as `async with Exchange() as ex:`."""

    def __init__(self, model=None, model_overrides: dict | None = None, pool: McpPool | None = None):
        # The backend passes its long-lived pool (started once at startup). The CLI and tests get their own.
        self.pool = pool or McpPool(("broker", "system"))
        self.owns_pool = pool is None
        # Test seam: tests may pass a stand-in model (e.g. to simulate a timeout) for all agents or by agent name.
        self.model = model or make_model()
        self.overrides = model_overrides or {}
        m = lambda name: self.overrides.get(name, self.model)  # noqa: E731
        self.listing_agent = Agent(
            m("listing_agent"), name="listing_agent", instructions=_prompt("listing_agent"), output_type=ListingDraft,
            toolsets=[self.pool["broker"].toolset.filtered(lambda ctx, td: td.name in LISTING_TOOLS)], retries=OUTPUT_RETRIES)
        self.need_agent = Agent(
            m("need_agent"), name="need_agent", instructions=_prompt("need_agent"), output_type=NeedDraft,
            toolsets=[self.pool["broker"].toolset.filtered(lambda ctx, td: td.name in LISTING_TOOLS)], retries=OUTPUT_RETRIES)
        self.guard = Agent(m("compliance_guard"), name="compliance_guard", instructions=_prompt("compliance_guard"),
                           output_type=GuardReview, retries=OUTPUT_RETRIES)
        self.matcher = Agent(m("matching_agent"), name="matching_agent", instructions=_prompt("matching_agent"),
                             output_type=MatchResult, retries=OUTPUT_RETRIES)
        self.pricer = Agent(m("pricing_agent"), name="pricing_agent", instructions=_prompt("pricing_agent"),
                            output_type=PriceSuggestion, retries=OUTPUT_RETRIES)

    async def __aenter__(self):
        if self.owns_pool:
            await self.pool.start()
        if self.pool.status != "ready":
            raise McpUnavailable(f"MCP tools failed to start: {self.pool.error}")
        return self

    async def __aexit__(self, *exc):
        if self.owns_pool:
            await self.pool.stop()

    # ------------------------------------------------------------------ plumbing

    async def call(self, tool: str, **args) -> dict:
        """Broker-role MCP call made by code (not by a model): shared connection, 15 s timeout, 1 reconnect."""
        return await self.pool["broker"].call(tool, args)

    async def sys_call(self, tool: str, **args) -> dict:
        return await self.pool["system"].call(tool, args)

    async def _check_session_budget(self, state: RunState) -> None:
        spent = (await self.sys_call("get_token_summary"))["total"].get("cost_usd") or 0
        if spent >= config.SESSION_BUDGET_USD:
            audit.log(state.run_id, "system", "limit_reached", subject=state.subject, stop_reason="session_budget",
                      error=f"session spend ${spent:.4f} >= budget ${config.SESSION_BUDGET_USD:.2f}")
            raise RunLimitReached("session_budget", f"session spend ${spent:.4f} reached the ${config.SESSION_BUDGET_USD:.2f} budget")

    async def _run_agent(self, state: RunState, name: str, agent: Agent, prompt: str, toolsets=None):
        """Run one agent call under the run's caps; log tokens + cost and every tool call."""
        if state.requests >= config.MAX_MODEL_REQUESTS or state.total_tokens >= config.MAX_TOKENS_PER_RUN:
            raise RunLimitReached("run_cap", f"run already used {state.requests} requests / {state.total_tokens} tokens")
        limits = UsageLimits(
            request_limit=min(AGENT_MAX_REQUESTS, config.MAX_MODEL_REQUESTS - state.requests),
            tool_calls_limit=AGENT_MAX_TOOL_CALLS,
            total_tokens_limit=config.MAX_TOKENS_PER_RUN - state.total_tokens,
        )
        audit.log(state.run_id, name, "agent_start", subject=state.subject, args={"prompt_chars": len(prompt)})
        state.current = name
        for attempt in (1, 2):
            try:
                result = await agent.run(prompt, usage_limits=limits, toolsets=toolsets)
                break
            except UsageLimitExceeded as e:
                audit.log(state.run_id, name, "limit_reached", subject=state.subject, stop_reason="agent_cap", error=str(e))
                raise RunLimitReached("agent_cap", f"{name}: {e}") from e
            except UnexpectedModelBehavior as e:  # malformed output, already retried once by pydantic-ai
                audit.log(state.run_id, name, "model_error", subject=state.subject, stop_reason="bad_output", error=str(e))
                raise AgentFailed(name, "bad_output", str(e)) from e
            except Exception as e:  # noqa: BLE001 - timeouts / outages: retry once, then give up politely
                retry = attempt == 1 and _transient(e)
                audit.log(state.run_id, name, "model_error", subject=state.subject,
                          stop_reason="retrying" if retry else "model_unavailable", error=f"{type(e).__name__}: {e}")
                if not retry:
                    raise AgentFailed(name, "model_unavailable", f"{type(e).__name__}: {e}") from e
                await asyncio.sleep(1)

        u = usage_breakdown(result.usage)
        state.requests += u["requests"]
        for k in ("input_tokens", "cached_tokens", "cache_write_tokens", "output_tokens"):
            setattr(state, k, getattr(state, k) + u[k])
        state.cost_usd += u["cost_usd"]
        state.agent_calls.append({"agent": name, **u})
        await self.sys_call("log_tokens", run_id=state.run_id, run_kind=state.kind, agent=name, model=config.MODEL_NAME,
                            requests=u["requests"], input_tokens=u["input_tokens"], cached_tokens=u["cached_tokens"],
                            cache_write_tokens=u["cache_write_tokens"], output_tokens=u["output_tokens"], cost_usd=u["cost_usd"])
        for msg in result.new_messages():
            for part in msg.parts:
                if isinstance(msg, ModelResponse) and isinstance(part, ToolCallPart):
                    if part.tool_name != "final_result":
                        audit.log(state.run_id, name, "tool_call", subject=state.subject, tool=part.tool_name, args=part.args_as_dict())
                elif isinstance(msg, ModelRequest) and isinstance(part, ToolReturnPart):
                    audit.log(state.run_id, name, "tool_result", subject=state.subject, tool=part.tool_name, result=part.content)
                elif isinstance(part, RetryPromptPart):
                    audit.log(state.run_id, name, "tool_retry", subject=state.subject, tool=part.tool_name, error=str(part.content))
        audit.log(state.run_id, name, "agent_end", subject=state.subject, result=result.output.model_dump(),
                  args={k: u[k] for k in ("requests", "input_tokens", "cached_tokens", "output_tokens", "cost_usd")})
        state.current = None
        return result.output, u

    def _start(self, state: RunState, **args) -> None:
        audit.log(state.run_id, "broker", "run_start", subject=state.subject, args={
            "kind": state.kind, "model": config.MODEL_NAME, "max_model_requests": config.MAX_MODEL_REQUESTS,
            "max_tokens_per_run": config.MAX_TOKENS_PER_RUN, "session_budget_usd": config.SESSION_BUDGET_USD, **args})

    def _finish(self, state: RunState, outcome: str, **extra) -> dict:
        audit.log(state.run_id, "broker", "run_end", subject=state.subject, stop_reason=outcome, result=state.totals())
        result = {"run_id": state.run_id, "kind": state.kind, "subject": state.subject, "outcome": outcome,
                  "steps": state.steps, "agent_calls": state.agent_calls, "totals": state.totals(), **extra}
        state.current, state.status, state.result = None, "done", result
        return result

    # ------------------------------------------------------------------ seller flow

    async def run_seller_flow(self, listing_id: int | None = None, text: str | None = None,
                              seller_id: int | None = None, state: RunState | None = None) -> dict:
        """Pasted text (or a seeded listing) -> listing -> compliance -> matches -> price -> outreach -> impact.
        Pass a RunState to watch progress live (the backend polls state.steps / state.current)."""
        state = state or RunState(kind="seller_flow", subject=f"listing:{listing_id}" if listing_id else f"seller:{seller_id}")
        self._start(state, listing_id=listing_id, seller_id=seller_id)
        try:
            await self._check_session_budget(state)
            return await self._seller_flow(state, listing_id, text, seller_id)
        except RunLimitReached as e:
            state.step("limit", "stopped", reason=e.reason, detail=e.detail)
            return self._finish(state, f"stopped: {e.reason}")
        except AgentFailed as e:
            state.step("error", e.kind, agent=e.agent, detail=e.detail)
            return self._finish(state, f"error: {FRIENDLY_ERROR}")
        except McpUnavailable as e:
            state.step("error", "tools_unavailable", detail=str(e))
            return self._finish(state, f"error: {McpUnavailable.friendly}")
        except Exception as e:  # noqa: BLE001 - never crash the caller; the audit trail keeps the details
            audit.log(state.run_id, "broker", "error", subject=state.subject, error=f"{type(e).__name__}: {e}")
            state.step("error", "unexpected", detail=f"{type(e).__name__}: {e}")
            return self._finish(state, "error: something went wrong on our side. Nothing was published. Please try again.")

    async def _seller_flow(self, state: RunState, listing_id, text, seller_id) -> dict:
        existing = None
        if listing_id:
            existing = await self.call("get_listing", listing_id=listing_id)
            if not existing.get("ok"):
                return self._finish(state, "error", error=existing.get("message"))
            text, seller_id = existing["seller_text_untrusted"], existing["seller_id"]
        seller = await self.call("get_company_profile", company_id=seller_id)
        today = (await self.call("get_exchange_date"))["today"]

        # 1. Injection pre-screen in code: zero tokens, and the model never reads the attack.
        if hits := injection_hits(text):
            state.step("prescreen", "blocked", rule="injection_pattern", patterns=hits)
            if existing and existing["status"] == "submitted":
                state.step("compliance", "blocked", result=await self.call("activate_listing", listing_id=listing_id))
            audit.log(state.run_id, "broker", "blocked", subject=state.subject, stop_reason="injection_pattern", args={"patterns": hits})
            return self._finish(state, "blocked: prompt injection (code pre-screen, no model call)")
        state.step("prescreen", "passed")

        # 1b. A listing that already has structured fields: run the code rules on them first (0 tokens).
        if existing and existing["status"] == "submitted" and existing.get("part_number"):
            rules = await self.call("check_listing_rules", listing_id=listing_id)
            if rules["status"] != "allowed":
                res = await self.call("activate_listing", listing_id=listing_id)
                state.step("rules", rules["status"], rules=rules["rules"], reasons=rules["reasons"])
                state.step("compliance", rules["status"], rules=rules["rules"], reasons=rules["reasons"], result=res,
                           listing=_public(existing), note="code rules on the stored fields, before any model call")
                return self._finish(state, f"{rules['status']}: {'; '.join(rules['reasons'])}", listing_id=listing_id)

        # 2. Listing agent: messy text -> structured fields.
        draft, _ = await self._run_agent(state, "listing_agent", self.listing_agent,
            f"Seller: {seller['name']} ({seller['location']}, {seller['industry']}). Exchange date: {today}.\n"
            + wrap("seller_text", text))
        state.step("listing_agent", "done", draft=draft.model_dump())
        if draft.other_items:
            items = [f"{draft.qty}x {draft.part_number or 'unidentified item'}"] + draft.other_items
            return self._finish(state, f"needs_clarification: this post lists {len(items)} different items "
                                f"({'; '.join(items)}). Please create one listing per item.", draft=draft.model_dump())
        if not draft.part_number:
            return self._finish(state, "needs_human: part not identified", draft=draft.model_dump())
        fields = {k: v for k, v in draft.model_dump().items()
                  if k in ("part_number", "qty", "condition", "asking_price", "expiry_date", "manufacture_date", "sds_available")}

        # 3. Save the structured listing.
        if not existing:
            saved = await self.call("create_listing", seller_id=seller_id, raw_text=text, **fields)
            if not saved.get("ok"):
                state.step("save", "refused", result=saved)
                return self._finish(state, "error: listing refused", error=saved.get("message"))
            listing_id = saved["listing_id"]
            state.subject = f"listing:{listing_id}"
            state.step("save", "created", listing_id=listing_id, expiry_date=saved.get("expiry_date"))
        elif existing["status"] == "submitted":
            upd = await self.call("update_listing_draft", listing_id=listing_id, **{k: v for k, v in fields.items() if v is not None})
            state.step("save", "updated draft" if upd.get("ok") else "refused", result=upd)
        else:
            state.step("save", "kept", note=f"listing is already '{existing['status']}'; draft used for checking only")

        # 4. Compliance, code rules first.
        rules = await self.call("check_listing_rules", listing_id=listing_id)
        state.step("rules", "passed" if rules["status"] == "allowed" else rules["status"], rules=rules["rules"],
                   reasons=rules["reasons"])
        if rules["status"] != "allowed":
            res = await self.call("activate_listing", listing_id=listing_id) if (existing or {}).get("status", "submitted") == "submitted" else rules
            listing = await self.call("get_listing", listing_id=listing_id)
            state.step("compliance", rules["status"], rules=rules["rules"], reasons=rules["reasons"], result=res,
                       listing=_public(listing))
            return self._finish(state, f"{rules['status']}: {'; '.join(rules['reasons'])}", listing_id=listing_id)
        listing = await self.call("get_listing", listing_id=listing_id)
        public = _public(listing)

        # 5. Compliance guard (LLM) for edge cases.
        review, _ = await self._run_agent(state, "compliance_guard", self.guard,
            "Structured listing (code rules passed):\n" + json.dumps(public, indent=1) + "\n" + wrap("seller_text", text))
        state.step("guard", "flagged" if review.decision == "flag" else "allowed", reasons=review.reasons)
        if review.decision == "flag":
            res = await self.call("flag_listing", listing_id=listing_id, reason="; ".join(review.reasons) or "guard flag")
            state.step("compliance", "flagged", by="compliance_guard", reasons=review.reasons, result=res, listing=public)
            return self._finish(state, "flagged by compliance guard", listing_id=listing_id)
        state.step("compliance", "allowed", rules="all code rules passed", guard="allow")
        if listing["status"] == "submitted":
            act = await self.call("activate_listing", listing_id=listing_id)
            state.step("activate", act["status"])
            listing = await self.call("get_listing", listing_id=listing_id)
        state.step("listing", "ready", listing=_public(listing))

        # 6. Matching: SQL pre-filter in code, then the model scores only those candidates.
        found = await self.call("search_buyers_for_listing", listing_id=listing_id)
        if found.get("code") == "not_active":  # sold, in negotiation, pending deal or expired: nothing to match or price
            state.step("prefilter", "skipped", reason=found.get("message"))
            return self._finish(state, f"stopped: {found.get('message')}", listing_id=listing_id)
        state.step("prefilter", "done", candidates=found.get("candidate_count", 0))
        matches = {"saved": [], "rejected": []}
        outreach = None
        if not found.get("ok") or not found["candidates"]:
            state.step("matching", "no_candidates", note="no company runs a compatible platform or needs this part; no model call")
        else:
            cands = found["candidates"]
            prompt = ("Listing:\n" + json.dumps({k: v for k, v in found["listing"].items() if k != "seller_text_untrusted"}, indent=1)
                      + "\n" + wrap("seller_text", text)
                      + f"\nCandidates ({found['candidate_count']} passed the pre-filter; top {len(cands)} shown):\n"
                      + json.dumps(cands, indent=1))
            # Fact-check the agent's answer in code; retry once with the exact errors; then fall back to rules.
            result, _ = await self._run_agent(state, "matching_agent", self.matcher, prompt)
            picked = [m.model_dump() for m in result.matches]
            errors, method, first_errors = check_matches(picked, cands), "agent", []
            if errors:
                first_errors = errors
                audit.log(state.run_id, "broker", "match_check_failed", subject=state.subject, result=errors)
                result, _ = await self._run_agent(state, "matching_agent", self.matcher, prompt + (
                    "\n\nYour previous answer failed a fact check against the candidate data:\n- " + "\n- ".join(errors)
                    + "\nAnswer again. Use only each candidate's own grounding facts and open_need."))
                picked = [m.model_dump() for m in result.matches]
                errors, method = check_matches(picked, cands), "agent_retry"
            if errors:
                audit.log(state.run_id, "broker", "match_check_failed", subject=state.subject, result=errors,
                          stop_reason="rules_fallback")
                picked, method = rules_ranking(cands), "rules_fallback"
            else:
                audit.log(state.run_id, "broker", "match_check_passed", subject=state.subject, result=method)
            matches = await self.call("record_matches", direction="seller_to_buyer", run_id=state.run_id,
                                      matches=[{**m, "listing_id": listing_id} for m in picked])
            by_id = {c["buyer_id"]: c for c in cands}
            ranked = [{**m, "buyer_name": by_id[m["buyer_id"]]["buyer_name"]} for m in picked if m["buyer_id"] in by_id]
            if ranked and method == "rules_fallback":
                subject, body = outreach_template(listing, ranked[0], by_id[ranked[0]["buyer_id"]])
                outreach = {"to": ranked[0]["buyer_name"], "subject": subject, "body": body}
            elif ranked:
                outreach = {"to": ranked[0]["buyer_name"], "subject": result.outreach_subject, "body": result.outreach_body}
            state.step("matching", "done", candidates=found["candidate_count"], ranked=ranked, method=method,
                       check_errors=first_errors, saved=len(matches.get("saved", [])), rejected=matches.get("rejected", []))
            await self._alerts(state)

        # 7. Pricing: facts from code, judgment from the model, bounds enforced in code.
        ref = await self.call("get_price_reference", part_number=listing["part_number"], exclude_listing_id=listing_id)
        price, _ = await self._run_agent(state, "pricing_agent", self.pricer, json.dumps({
            "part_number": listing["part_number"], "description": listing["description"], "condition": listing["condition"],
            "qty": listing["qty"], "seller_asking_price": listing["asking_price"], "expiry_date": listing["expiry_date"],
            "exchange_date": today, "new_price": ref["new_price"], "scrap_value": ref["scrap_value"],
            "obsolete": ref["obsolete"], "active_asks": ref["active_asks"], "approved_deals": ref["approved_deals"],
            "open_needs_matched": sum(1 for m in matches.get("saved", []) if m.get("need_id")),
        }, indent=1))
        ask = min(max(price.ask, ref["scrap_value"]), ref["new_price"])
        floor = min(max(price.floor_suggestion, ref["scrap_value"]), ask)
        await self.call("store_suggested_floor", listing_id=listing_id, floor=round(floor, 2))  # only if none yet
        state.step("pricing", "done", ask=round(ask, 2), floor_suggestion=round(floor, 2), rationale=price.rationale,
                   clamped=(ask != price.ask or floor != price.floor_suggestion), new_price=ref["new_price"], scrap_value=ref["scrap_value"])
        if outreach:
            state.step("outreach", "drafted", **outreach)

        # 8. Impact: computed in code from the catalog (weight x placeholder factor), never by the model.
        impact = await self.call("get_impact_estimate", listing_id=listing_id, price=round(ask, 2))
        state.step("impact", "done", **{k: v for k, v in impact.items() if k != "ok"})
        late = await self._recheck_listing(state, listing_id, {(c["buyer_id"], (c.get("open_need") or {}).get("need_id"))
                                                                for c in found.get("candidates") or []})
        outcome = "listed and matched" if matches.get("saved") or late else "listed (no matching buyers yet)"
        return self._finish(state, outcome, listing_id=listing_id)

    async def _recheck_listing(self, state: RunState, listing_id: int, seen: set[tuple]) -> int:
        """Race guard (Phase 5 stress test, check 9): a need saved while this flow was running was not in the first
        pre-filter. Re-run the pre-filter once, after this listing is saved; rank any NEW buyer with an open need by
        rules (code, no model call) and alert. Of two flows racing, the later re-check always sees both items."""
        again = await self.call("search_buyers_for_listing", listing_id=listing_id)
        new = [c for c in again.get("candidates") or []  # a buyer seen before WITHOUT this need counts as new
               if c.get("open_need") and (c["buyer_id"], c["open_need"]["need_id"]) not in seen]
        state.step("recheck", "done", new=len(new))
        if not new:
            return 0
        saved = await self.call("record_matches", direction="seller_to_buyer", run_id=state.run_id,
                                matches=[{**m, "listing_id": listing_id} for m in rules_ranking(new)])
        await self._alerts(state)
        return len(saved.get("saved", []))

    async def _recheck_need(self, state: RunState, need: dict, seen: set[int]) -> int:
        """Same race guard for a new need: listings activated while this flow ran, ranked by rules, then alerts."""
        again = await self.call("search_listings_for_need", need_id=need["need_id"])
        new = [c for c in again.get("listings") or [] if c["listing_id"] not in seen]
        state.step("recheck", "done", new=len(new))
        if not new:
            return 0
        saved = await self.call("record_matches", direction="buyer_to_seller", run_id=state.run_id, matches=[
            {k: m[k] for k in ("listing_id", "buyer_id", "need_id", "score", "reason")} for m in rules_ranking_reverse(new, need)])
        await self._alerts(state)
        return len(saved.get("saved", []))

    async def _alerts(self, state: RunState) -> None:
        """Alerts are decided in code (score >= 70 with an open need, top 3, never twice), not by an agent."""
        res = await self.call("send_match_alerts", run_id=state.run_id)
        state.step("alerts", "done", sent=len(res.get("sent", [])), pairs=res.get("pairs_alerted", 0),
                   duplicates=res.get("skipped_duplicates", 0), threshold=res.get("threshold"),
                   companies=sorted({a["company_id"] for a in res.get("sent", [])}))

    # ------------------------------------------------------------------ need flow (buyer side)

    async def run_need_flow(self, text: str | None = None, buyer_id: int | None = None, need_id: int | None = None,
                            max_price: float | None = None, urgency: str | None = None,
                            downtime_cost_per_day: float | None = None, state: RunState | None = None) -> dict:
        """A buyer's wanted post -> structured need -> compliance -> the SAME matching agent in reverse -> alerts.
        Pass need_id to re-match an existing need (skips extraction)."""
        state = state or RunState(kind="need_flow", subject=f"need:{need_id}" if need_id else f"buyer:{buyer_id}")
        self._start(state, need_id=need_id, buyer_id=buyer_id)
        try:
            await self._check_session_budget(state)
            return await self._need_flow(state, text, buyer_id, need_id, max_price, urgency, downtime_cost_per_day)
        except RunLimitReached as e:
            state.step("limit", "stopped", reason=e.reason, detail=e.detail)
            return self._finish(state, f"stopped: {e.reason}")
        except AgentFailed as e:
            state.step("error", e.kind, agent=e.agent, detail=e.detail)
            return self._finish(state, f"error: {FRIENDLY_ERROR}")
        except McpUnavailable as e:
            state.step("error", "tools_unavailable", detail=str(e))
            return self._finish(state, f"error: {McpUnavailable.friendly}")
        except Exception as e:  # noqa: BLE001 - never crash the caller; the audit trail keeps the details
            audit.log(state.run_id, "broker", "error", subject=state.subject, error=f"{type(e).__name__}: {e}")
            state.step("error", "unexpected", detail=f"{type(e).__name__}: {e}")
            return self._finish(state, "error: something went wrong on our side. Nothing was posted. Please try again.")

    async def _need_flow(self, state, text, buyer_id, need_id, max_price, urgency, downtime) -> dict:
        if need_id is None:
            buyer = await self.call("get_company_profile", company_id=buyer_id)
            if not buyer.get("ok"):
                return self._finish(state, f"error: {buyer.get('message', 'unknown buyer')}")
            today = (await self.call("get_exchange_date"))["today"]
            if hits := injection_hits(text):  # 1. code pre-screen: the model never reads the attack
                state.step("prescreen", "blocked", rule="injection_pattern", patterns=hits)
                audit.log(state.run_id, "broker", "blocked", subject=state.subject, stop_reason="injection_pattern")
                return self._finish(state, "blocked: prompt injection (code pre-screen, no model call)")
            state.step("prescreen", "passed")
            platforms = [e["platform"] for e in buyer["installed_equipment"]]
            draft, _ = await self._run_agent(state, "need_agent", self.need_agent,
                f"Buyer: {buyer['name']} ({buyer['location']}, {buyer['industry']}). Exchange date: {today}.\n"
                f"Buyer's installed platforms: {json.dumps(platforms)}\n" + wrap("buyer_text", text))
            d = draft.model_dump()
            state.step("need_agent", "done", draft=d)
            if draft.other_items:
                items = [f"{draft.qty}x {draft.part_number or draft.family or 'item'}"] + draft.other_items
                return self._finish(state, f"needs_clarification: this post asks for {len(items)} different items "
                                    f"({'; '.join(items)}). Please post one need per item.", draft=d)
            platform = draft.platform if draft.platform in platforms else None
            if draft.part_number and not platform:  # code: pick the buyer platform the part fits
                comp = await self.call("get_compatibility", part_number=draft.part_number)
                platform = next((p for p in comp.get("fits_platforms", []) if p in platforms), None)
            if not draft.part_number and not (platform and draft.family):
                return self._finish(state, "needs_human: couldn't tell which part or machine this need is for", draft=d)

            # 2. compliance guard (needs can carry injections or off-platform requests too)
            review, _ = await self._run_agent(state, "compliance_guard", self.guard,
                "This is a BUYER'S WANTED POST, not a listing. Structured need:\n"
                + json.dumps({"part_number": draft.part_number, "platform": platform, "family": draft.family,
                              "qty": draft.qty, "urgency": urgency or draft.urgency}, indent=1)
                + "\n" + wrap("seller_text", text))
            state.step("guard", "flagged" if review.decision == "flag" else "allowed", reasons=review.reasons)
            if review.decision == "flag":
                state.step("compliance", "flagged", by="compliance_guard", reasons=review.reasons)
                return self._finish(state, "flagged by compliance guard", draft=d)

            saved = await self.call("create_need", buyer_id=buyer_id, raw_text=text, qty=draft.qty,
                                    urgency=urgency or draft.urgency,
                                    downtime_cost_per_day=downtime if downtime is not None else (draft.downtime_cost_per_day or 0),
                                    part_number=draft.part_number, platform=platform,
                                    family=None if draft.part_number else draft.family, ceiling_price=max_price)
            if not saved.get("ok"):
                state.step("save", "refused", result=saved)
                return self._finish(state, f"needs_review: {saved.get('message')}", error=saved.get("message"))
            need_id = saved["need_id"]
            state.subject = f"need:{need_id}"
            state.step("save", "created", need_id=need_id, ceiling_recorded=saved.get("ceiling_recorded"))

        # 3. same pre-filter code (compatibility), reverse direction; no candidates -> no model call
        found = await self.call("search_listings_for_need", need_id=need_id)
        need = found.get("need") or (await self.call("get_need", need_id=need_id))
        need_public = {k: v for k, v in need.items() if k not in ("buyer_text_untrusted", "ok")}
        state.step("need", "ready", need=need_public)
        if not found.get("ok"):
            return self._finish(state, f"error: {found.get('message')}", need_id=need_id)
        cands = found["listings"]
        state.step("prefilter", "done", candidates=found["count"])
        if not cands:
            state.step("matching", "no_candidates", note="no active listing fits this need yet; no model call")
            if await self._recheck_need(state, need, set()):
                return self._finish(state, "posted and matched", need_id=need_id)
            return self._finish(state, "posted (no matching surplus yet)", need_id=need_id)

        # 4. the SAME matching agent, reverse direction; fact-checked in code, retry once, rules fallback
        prompt = ("Direction: buyer_to_seller (a new need).\nNeed:\n" + json.dumps(need_public, indent=1)
                  + "\n" + wrap("buyer_text", need.get("buyer_text_untrusted"))
                  + f"\nCandidate listings ({found['count']} fit the need):\n"
                  + json.dumps([{k: v for k, v in c.items() if k != "seller_text_untrusted"} for c in cands], indent=1))
        result, _ = await self._run_agent(state, "matching_agent", self.matcher, prompt)
        picked = [m.model_dump() for m in result.matches]
        errors, method, first_errors = check_reverse_matches(picked, cands, need), "agent", []
        if errors:
            first_errors = errors
            audit.log(state.run_id, "broker", "match_check_failed", subject=state.subject, result=errors)
            result, _ = await self._run_agent(state, "matching_agent", self.matcher, prompt + (
                "\n\nYour previous answer failed a fact check against the candidate data:\n- " + "\n- ".join(errors)
                + "\nAnswer again. Use only each listing's own fields."))
            picked = [m.model_dump() for m in result.matches]
            errors, method = check_reverse_matches(picked, cands, need), "agent_retry"
        if errors:
            audit.log(state.run_id, "broker", "match_check_failed", subject=state.subject, result=errors, stop_reason="rules_fallback")
            picked, method = rules_ranking_reverse(cands, need), "rules_fallback"
        else:
            audit.log(state.run_id, "broker", "match_check_passed", subject=state.subject, result=method)
        saved = await self.call("record_matches", direction="buyer_to_seller", run_id=state.run_id, matches=[
            {"listing_id": m["listing_id"], "buyer_id": need["buyer_id"], "need_id": need["need_id"], "score": m["score"],
             "reason": m["reason"]} for m in picked])
        by_id = {c["listing_id"]: c for c in cands}
        ranked = [{**m, "seller_name": by_id[m["listing_id"]]["seller_name"], "part_number": by_id[m["listing_id"]]["part_number"],
                   "condition": by_id[m["listing_id"]]["condition"], "asking_price": by_id[m["listing_id"]]["asking_price"],
                   "qty": by_id[m["listing_id"]]["qty"], "location": by_id[m["listing_id"]]["location"]}
                  for m in picked if m["listing_id"] in by_id]
        state.step("matching", "done", direction="buyer_to_seller", candidates=found["count"], ranked=ranked, method=method,
                   check_errors=first_errors, saved=len(saved.get("saved", [])), rejected=saved.get("rejected", []))
        if ranked and method != "rules_fallback":
            state.step("outreach", "drafted", to=ranked[0]["seller_name"], subject=result.outreach_subject, body=result.outreach_body)
        await self._alerts(state)
        await self._recheck_need(state, need, {c["listing_id"] for c in cands})
        return self._finish(state, "posted and matched", need_id=need_id)

    # ------------------------------------------------------------------ negotiation

    async def run_negotiation(self, listing_id: int, need_id: int, state: RunState | None = None,
                              negotiation_id: int | None = None, slot: asyncio.Semaphore | None = None) -> dict:
        """Seller agent vs buyer agent, each in its own MCP process that can read only its own limit.
        Ends in a deal (pending both companies' approval), a walk-away, the round cap, or a broker safety stop.
        negotiation_id: already opened by the API (units locked at once). slot: concurrency limit; while waiting
        for a free slot the run shows as 'queued'."""
        state = state or RunState(kind="negotiation", subject=f"listing:{listing_id}/need:{need_id}")
        self._start(state, listing_id=listing_id, need_id=need_id, max_rounds=config.MAX_NEGOTIATION_ROUNDS)
        try:
            await self._check_session_budget(state)
            if negotiation_id is None:
                opened = await self.call("open_negotiation", listing_id=listing_id, need_id=need_id, run_id=state.run_id)
                if not opened.get("ok"):
                    state.step("open", "refused", result=opened)
                    return self._finish(state, f"refused: {opened.get('message')}")
                negotiation_id = opened["negotiation_id"]
            nid = negotiation_id
            state.subject = f"negotiation:{nid}"
            view = await self.call("get_negotiation", negotiation_id=nid)
            state.step("open", "done", negotiation_id=nid, qty=view["qty"], max_rounds=view["max_rounds"])
            if slot is None:
                return await self._negotiate(state, nid, listing_id, need_id)
            state.current = "queued"  # until a slot is free (simultaneous starts all see a free slot before any takes one)
            t0 = asyncio.get_running_loop().time()
            async with slot:
                state.current = None
                waited = asyncio.get_running_loop().time() - t0
                if waited > 0.5:
                    state.step("queued", "waited", seconds=round(waited, 1),
                               note=f"{config.MAX_CONCURRENT_NEGOTIATIONS} negotiations were running")
                return await self._negotiate(state, nid, listing_id, need_id)
        except Exception as e:  # noqa: BLE001 - caps, model failures, anything: stop safely, never crash the caller
            if isinstance(e, RunLimitReached):
                state.step("limit", "stopped", reason=e.reason, detail=e.detail)
                outcome, why = f"stopped: {e.reason}", f"run cap: {e.reason}"
            elif isinstance(e, AgentFailed):
                state.step("error", e.kind, agent=e.agent, detail=e.detail)
                outcome, why = f"error: {FRIENDLY_ERROR}", f"{e.agent} failed: {e.kind}"
            elif isinstance(e, McpUnavailable):
                state.step("error", "tools_unavailable", detail=str(e))
                outcome, why = f"error: {McpUnavailable.friendly}", "tool server unavailable"
            else:
                audit.log(state.run_id, "broker", "error", subject=state.subject, error=f"{type(e).__name__}: {e}")
                state.step("error", "unexpected", detail=f"{type(e).__name__}: {e}")
                outcome, why = "error: something went wrong on our side. No deal was made. Please try again.", "unexpected error"
            if state.subject.startswith("negotiation:"):
                try:
                    await self.call("end_negotiation", negotiation_id=int(state.subject.split(":")[1]), reason=why)
                except Exception:  # noqa: BLE001 - best effort
                    pass
            return self._finish(state, outcome)

    async def _negotiate(self, state: RunState, nid: int, listing_id: int, need_id: int) -> dict:
        listing = await self.call("get_listing", listing_id=listing_id)
        need = await self.call("get_need", need_id=need_id)
        sides = {}
        for side in ("seller", "buyer"):
            conn = RoleConnection(f"{side}_agent", nid)
            ts = conn.toolset
            sides[side] = {"conn": conn, "agent": Agent(
                self.overrides.get(f"{side}_negotiator", self.model), name=f"{side}_negotiator", instructions=_prompt(f"{side}_negotiator"), output_type=NegotiatorTurn,
                toolsets=[ts.filtered(lambda ctx, td: td.name in NEGOTIATOR_TOOLS)], retries=OUTPUT_RETRIES)}
        for s in sides.values():
            await s["conn"].start()
        try:
            failures, turns = 0, 0
            while True:
                view = await self.call("get_negotiation", negotiation_id=nid)
                if view["status"] != "open":
                    break
                t = state.totals()
                if t["cost_usd"] > config.NEGOTIATION_MAX_COST_USD or t["total_tokens"] > config.NEGOTIATION_MAX_TOKENS:
                    stop = await self.call("end_negotiation", negotiation_id=nid, reason=(
                        f"cost cap reached (${t['cost_usd']:.4f}, {t['total_tokens']:,} tokens)"))
                    state.step("cost_cap", "stopped", result=stop, cost_usd=t["cost_usd"], tokens=t["total_tokens"])
                    break
                if failures >= 2 or turns >= view["max_rounds"] + 2:
                    stop = await self.call("end_negotiation", negotiation_id=nid,
                                           reason="an agent failed to make a valid move" if failures >= 2 else "too many turns")
                    state.step("safety_stop", "stopped", result=stop)
                    break
                side = view["next_to_move"]
                other = "buyer" if side == "seller" else "seller"
                history = "\n".join(
                    f"Round {o['round']} {o['from_side']}: {o['action']}"
                    + (f" ${o['price']:,.2f}/unit" if o["action"] != "walk_away" else "")
                    + ("\n" + wrap(f"{o['from_side']}_message", o["message_untrusted"]) if o["message_untrusted"] else "")
                    for o in view["offers"]) or "(no offers yet: you move first)"
                prompt = (
                    f"You are the {side.upper()}. Negotiation #{nid}, quantity {view['qty']}, prices per unit.\n"
                    f"Listing: {listing['part_number']} ({listing['description']}), condition {listing['condition']}, "
                    f"public ask {('$%s' % format(listing['asking_price'], ',.2f')) if listing['asking_price'] else 'none stated'}, "
                    f"seller {listing['seller_name']} ({listing['location']}).\n"
                    f"Buyer need: {need['buyer_name']} ({need['buyer_location']}), urgency {need['urgency']}.\n"
                    f"Rounds used {view['rounds_used']} of {view['max_rounds']} "
                    f"({max(view['max_rounds'] - view['rounds_used'] - 1, 0)} more offer(s) possible after yours). "
                    f"Last move from the {other} side is shown last.\n"
                    + ("ROUND CAP REACHED: the other side's last offer is FINAL. You may only accept it (if it is within "
                       "your limit) or walk_away. A counter-offer will be refused.\n" if view.get("final_offer_pending") else "")
                    + f"Offers so far:\n{history}\n"
                    "Make exactly one move now.")
                before = view["rounds_used"]
                turn, _ = await self._run_agent(state, f"{side}_negotiator", sides[side]["agent"], prompt)
                after = await self.call("get_negotiation", negotiation_id=nid)
                moved = after["rounds_used"] > before or after["status"] != "open"
                failures = 0 if moved else failures + 1
                turns += 1
                last = after["offers"][-1] if moved and after["offers"] else None
                state.step(f"{side}_turn", "moved" if moved else "no_valid_move", round=after["rounds_used"],
                           action=last and last["action"], price=last and last["price"],
                           message=last and last["message_untrusted"], reasoning=turn.reasoning)
                if moved and turn.reasoning:  # private: shown only to this side's company
                    await self.call("save_turn_note", negotiation_id=nid, side=side, round=after["rounds_used"],
                                    note=turn.reasoning)
        finally:
            for s in sides.values():
                await s["conn"].stop()

        final = await self.call("get_negotiation", negotiation_id=nid)
        deal = None
        if final["status"] == "agreed":
            deal = (await self.call("request_deal_approval", negotiation_id=nid)).get("deal")
            state.step("deal", "pending_human_approval", deal=deal)
        return self._finish(state, final["status"], negotiation=final, deal=deal)
