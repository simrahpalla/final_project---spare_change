<!-- One slide per block, separated by a line with three dashes. Lines starting "Note:" become speaker notes.
     !img[path|css] and !svg[path] embed files; double-brace number keys come from scripts/report_numbers.py. -->
<div class="title-slide">
<div class="logo big">¢</div>
<h1>Spare Change</h1>
<p class="tag">Turn spare parts into spare change.</p>
<p class="sub">AI agents match industrial surplus to the plants that run the same machines, and negotiate the deal.</p>
<p class="who">Simrah Palla · MGT 409 · <a href="{{github_url}}">{{github_url}}</a></p>
</div>
Note: One sentence: Spare Change is a marketplace where agents list a plant's surplus part, find the plants whose machines use it, and negotiate within limits enforced in code; humans approve.
---
<h2>Two plants, one part</h2>
<div class="cols2">
<div class="card sell"><h3>Plant A: surplus on a shelf</h3><p class="big-num">{{idle_pct}}</p><p>of spare-parts stock unused 5+ years</p><p class="big-num">{{scrap_range}}</p><p>recovered when scrapped</p></div>
<div class="card buy"><h3>Plant B: line down</h3><p class="big-num">≥ {{tcod_hour}}</p><p>per hour of downtime (lowest-cost sector)</p><p class="big-num">{{lead_new}}</p><p>for a new part vs. {{lead_surplus}} surplus</p></div>
</div>
<p class="src">Sources: SPARETECH 2025 via Reliamag; Maas Companies; Siemens TCOD 2024; Automa.</p>
Note: Seller plants scrap or shelve working spares after upgrades. Buyer plants running the same old machines lose money every hour the line is down, and S7-300 parts stopped shipping in {{s7_end}}. Nobody connects the shelf to the stopped line.
---
<h2>What's new</h2>
<table class="cmp">
<tr><th></th><th>Matches on buyers' machines</th><th>Agents negotiate both sides</th><th>Limits enforced in code</th><th>$ + CO2e per deal</th></tr>
<tr><td>Automa</td><td>parts &amp; supplier catalogs</td><td>–</td><td>–</td><td>–</td></tr>
<tr><td>SPARETECH</td><td>parts data</td><td>–</td><td>–</td><td>–</td></tr>
<tr><td>eBay</td><td>–</td><td>–</td><td>–</td><td>–</td></tr>
<tr><td>Pactum</td><td>–</td><td>buyer only</td><td>–</td><td>–</td></tr>
<tr><td>ChatGPT</td><td>–</td><td>–</td><td>–</td><td>–</td></tr>
<tr class="us"><td>Spare Change</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td></tr>
</table>
<p class="src">"–" = no public evidence found (26 Oct 2026). Full comparison of 12 products in the report.</p>
Note: Automa sells the same goods by part number; SPARETECH has the parts data and resells via partners; Pactum negotiates for buyers on new procurement. We combine compatibility matching, two-sided agent negotiation with code-enforced limits, and a human-approved close.
---
<h2>How the agents work</h2>
!svg[report/architecture.svg]
Note: Code runs the pipeline and calls gpt-6-luna only where judgment is needed. Two human touchpoints: confirm your private limit, approve the deal. The MCP server is the only path to the data, with tools by role.
---
<h2>Demo: seller side</h2>
<div class="shots2">
!img[output/screenshots/phase11-sell-top.webp|]
!img[output/screenshots/phase11-sell-buyers.webp|]
</div>
<p class="caption">Messy text → listing → compliance → buyers ranked by their machines → price. This run: {{trace_sell_cost}}.</p>
Note: Hartwell pastes one sentence. The agents identify the S7-300 CPU, pass compliance, rank Riverbend first (score {{tr_score}}, line down) with fact-checked reasons, and suggest {{tr_ask}} plus a private floor.
---
<h2>Demo: agents negotiate, humans approve</h2>
<div class="shots2">
<div><p class="lab sell">Seller's view: only its floor</p>
!img[output/screenshots/phase11-negotiation-seller.png|]
</div>
<div><p class="lab buy">Buyer's view: only its budget</p>
!img[output/screenshots/phase11-negotiation-buyer.png|]
</div>
</div>
<p class="callout"><span class="pass">✓ Both companies approved</span> Deal at {{tr_price}} · request filled · est. {{tr_co2_deal}} kg CO2e avoided</p>
Note: Auto-negotiation started once both limits were confirmed. Seller floor {{tr_floor}}, buyer budget {{tr_budget}}: neither sees the other's. The buyer agent accepted in round {{tr_rounds}}; both companies clicked Approve; the request is filled.
---
<h2>Cost to run</h2>
<div class="stats">
<div><span class="big-num">{{sell_cost}}</span><span>per seller post (n={{sell_runs}})</span></div>
<div><span class="big-num">{{neg_cost}}</span><span>per negotiation (n={{neg_runs}})</span></div>
<div><span class="big-num">{{user_month}}</span><span>per plant per month</span></div>
<div><span class="big-num">{{u10000_year}}</span><span>a year at 10,000 users</span></div>
</div>
<table class="cmp tok"><tr><th>Measured per run (avg.)</th><th>Input</th><th>of which cached</th><th>Output</th></tr>
<tr><td>Seller post</td><td>{{sell_in}}</td><td>{{sell_cached}}</td><td>{{sell_out}}</td></tr>
<tr><td>Negotiation</td><td>{{neg_in}}</td><td>{{neg_cached}}</td><td>{{neg_out}}</td></tr></table>
<p class="callout">SQL pre-filter: <b>−{{pf_tok_cut}} tokens</b> per matching call, accuracy unchanged ({{pf_top1_with}} vs. {{pf_top1_without}}).</p>
Note: Measured from token logs, gpt-6-luna at {{price_in}} input / {{price_out}} output per million. Per-user cost assumes {{assume_sell}} posts, {{assume_buy}} requests and {{assume_neg}} negotiations a month. Caching serves {{neg_cached_pct}} of negotiation input.
---
<h2>Safety</h2>
<div class="cols3">
<div class="card"><h3>Attacks <span class="pass">{{saf_attack}}</span></h3>!img[output/screenshots/phase11-injection-blocked.webp|]<p>Injection blocked before any AI reads it: 0 tokens.</p></div>
<div class="card"><h3>Malfunction <span class="pass">{{saf_malfunction}}</span></h3><p class="big-num">{{neg_violations}}</p><p>limit violations in {{neg_n}} negotiations</p><p>Crashes under load: <b>{{crash_before}} → {{crash_after}}</b></p></div>
<div class="card"><h3>Overspending <span class="pass">{{saf_overspending}}</span></h3><p>{{cap_rounds}}-round cap · {{cap_neg_cost}} per negotiation · {{cap_session}} session budget</p><p>Blocked posts cost $0.</p></div>
</div>
Note: Attacks: prompt injection, limit extraction, tools outside a role. Malfunction: every match reason fact-checked; offers outside a limit refused in code; loops capped. Overspending: per-run, per-negotiation and session caps.
---
<h2>Impact</h2>
<div class="stats teal">
<div><span class="big-num">{{pd_value}}</span><span>avg. recovered per test deal vs. {{pd_scrap}} scrap</span></div>
<div><span class="big-num">{{imp_extra}}</span><span>extra recovered, one-time (one plant, model)</span></div>
<div><span class="big-num">{{imp_carry}}</span><span>carrying cost avoided per year</span></div>
<div><span class="big-num">{{imp_co2}} kg</span><span>est. CO2e avoided, one-time</span></div>
</div>
<p class="todo">[TODO: Simrah to fill timed test] manual vs. Spare Change, measured by the author</p>
<p class="src">Measured deals (synthetic market); plant model inputs sourced or labelled assumptions. One-time and yearly values never added.</p>
Note: Deals closed at {{recovery}} of new price versus {{scrap_range}} for scrap. Downtime counted only for line-down purchases, at the {{tcod_hour}}-an-hour lower bound. CO2e uses sourced factors and a conservative reuse credit.
---
<h2>What's next</h2>
<div class="cols2">
<div><h3>Limits today</h3><ul><li>Synthetic data, demo accounts</li><li>No payments or part verification</li><li>No independent user yet</li></ul></div>
<div><h3>Next</h3><ul><li>Pilot with a maintenance manager</li><li>Start with discontinued PLCs and drives</li><li>Internal exchange across one manufacturer's sites</li></ul></div>
</div>
<p class="closer">Your next spare part is someone's spare change.</p>
Note: Business challenges: getting both sides on board, scattered equipment data, trust and counterfeits, thin margins. The pilot measures time and trust with a real user.
