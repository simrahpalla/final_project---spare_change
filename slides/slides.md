<!-- One slide per block, separated by a line with three dashes. Lines starting "Note:" become speaker notes.
     !img[path|css] and !svg[path] embed files; double-brace number keys come from scripts/report_numbers.py. -->
<div class="title-slide">
<div class="logo big">¢</div>
<h1>Spare Change</h1>
<p class="tag">Your next spare part is someone's spare change.</p>
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
<p class="src">Sources: SPARETECH 2025 survey (via Reliamag) · Maas Companies · Siemens True Cost of Downtime 2024 · Automa. Links: output/impact_sources.md</p>
Note: Seller plants scrap or shelve working spares after upgrades. Buyer plants running the same old machines lose money every hour the line is down; S7-300 parts stopped shipping in {{s7_end}}. Nobody connects the shelf to the stopped line.
---
<h2>What's new</h2>
<div class="cmp2">
<table class="cmp">
<tr><th>Product</th><th>Mach.</th><th>Agents</th><th>Limits</th><th>Impact</th></tr>
<tr><td><b>Automa</b><span>parts market, catalog matching</span></td><td>–</td><td>–</td><td>–</td><td>–</td></tr>
<tr><td><b>SPARETECH</b><span>parts data, surplus resale</span></td><td>–</td><td>–</td><td>–</td><td>–</td></tr>
<tr><td><b>eBay</b><span>general marketplace</span></td><td>–</td><td>–</td><td>–</td><td>–</td></tr>
<tr><td><b>B-Stock</b><span>retail liquidation auctions</span></td><td>–</td><td>–</td><td>–</td><td>–</td></tr>
<tr><td><b>Liquidity Services</b><span>surplus asset auctions</span></td><td>–</td><td>–</td><td>–</td><td>–</td></tr>
</table>
<table class="cmp">
<tr><th>Product</th><th>Mach.</th><th>Agents</th><th>Limits</th><th>Impact</th></tr>
<tr><td><b>EquipNet</b><span>used equipment resale</span></td><td>–</td><td>–</td><td>–</td><td>–</td></tr>
<tr><td><b>Verusen, Verdantis</b><span>in-house MRO inventory AI</span></td><td>–</td><td>–</td><td>–</td><td>–</td></tr>
<tr><td><b>Rheaply</b><span>workplace asset reuse</span></td><td>–</td><td>–</td><td>–</td><td>◐</td></tr>
<tr><td><b>Pactum</b><span>AI procurement negotiation</span></td><td>–</td><td>◐</td><td>–</td><td>–</td></tr>
<tr><td><b>ChatGPT</b><span>general chatbot</span></td><td>–</td><td>–</td><td>–</td><td>–</td></tr>
</table>
</div>
<table class="cmp us-row"><tr class="us"><td><b>Spare Change</b><span>matches on buyers' machines · agents negotiate both sides · limits in code · $ + CO2e per deal</span></td><td>✓</td><td>✓</td><td>✓</td><td>✓</td></tr></table>
<p class="src">Mach. = matches on the machines buyers run · Agents = agents negotiate on both sides · Limits = private limits enforced in code · Impact = $ + CO2e per deal. ✓ yes · ◐ partly (Rheaply: carbon counter; Pactum: buyer side only) · – no public evidence. Sources: each product's site or a third-party page, checked 26 Oct 2026 (output/competitors.md).</p>
Note: Closest: Automa sells the same goods and matches inventory against parts and supplier catalogs; SPARETECH owns the parts data and resells through partners; Pactum negotiates for buyers on new procurement. We match against the machines buyers run, agents negotiate on both sides within limits enforced in code, and humans approve.
---
<h2>How the agents work</h2>
!svg[report/architecture_simple.svg]
Note: Code runs the pipeline and calls gpt-6-luna only where judgment is needed: listing, compliance edge cases, matching, pricing, negotiating. Two human touchpoints: confirm your private limit, approve the deal. The MCP server is the only path to the data, with tools by role. The detailed diagram is in the report.
---
<h2>Seller side: turn spare parts into spare change</h2>
<div class="demo">
!img[output/screenshots/trace-sell-buyers.webp|]
<div class="steps">
<p><b>One messy sentence</b> → listing</p>
<p>Compliance <span class="pass">passed</span></p>
<p>Buyers ranked by the <b>machines they run</b></p>
<p>Price {{tr_ask}} · private floor</p>
<p class="big-num">{{trace_sell_cost}}</p><p class="muted">this run, {{trace_sell_req}} model calls</p>
</div>
</div>
<p class="src">Real run in the app, 26 Oct 2026 (run {{trace_sell_run}}, output/phase11_trace.md).</p>
Note: Hartwell pastes "12 of the SM321 32pt DI cards… open to offers". Agents identify the S7-300 input card, pass compliance, rank Prairie Packaging first (score {{tr_score}}, open request for 6) with fact-checked reasons, and suggest {{tr_ask}} plus a private floor of {{tr_floor_sugg}}; Hartwell lowers it to {{tr_floor}}.
---
<h2>Buyer side: spare yourself the downtime</h2>
<div class="shots2">
<div><p class="lab sell">Seller's view: only its {{tr_floor}} floor</p>
!img[output/screenshots/trace-neg-seller-chart.webp|]
</div>
<div><p class="lab buy">Buyer's view: only its {{tr_budget}} budget</p>
!img[output/screenshots/trace-neg-buyer-chart.webp|]
</div>
</div>
<p class="callout">{{tr_offers}} · <span class="pass">✓ Both companies approved</span></p>
<p class="src">Same real run: {{tr_rounds}} rounds, {{trace_neg_req}} model calls, {{trace_neg_cost}} (run {{trace_neg_run}}, output/phase11_trace.md).</p>
Note: Prairie Packaging starts the negotiation from its alert. The agents bargain for six rounds inside a narrow overlap ({{tr_floor}} floor, {{tr_budget}} budget) without seeing each other's limit, and the buyer accepts {{tr_price}} a unit. Each company approves its own side; the request is filled. When the limits don't overlap, the agents walk away: {{walk_deals}} deals in {{walk_n}} such tests.
---
<h2>Cost to run</h2>
<div class="stats">
<div><span class="big-num">{{sell_cost}}</span><span>per seller post (n={{sell_runs}})</span></div>
<div><span class="big-num">{{neg_cost}}</span><span>per negotiation (n={{neg_runs}})</span></div>
<div><span class="big-num">{{user_month}}</span><span>per plant per month at {{use_typical}} posts / requests / negotiations</span></div>
<div><span class="big-num">{{u10000_year}}</span><span>a year at 10,000 plants</span></div>
</div>
<table class="cmp tok"><tr><th>Per month</th><th>Light {{use_light}}</th><th>Typical {{use_typical}}</th><th>Heavy {{use_heavy}}</th></tr>
<tr><td>One plant</td><td>{{use_light_month}}</td><td>{{use_typical_month}}</td><td>{{use_heavy_month}}</td></tr>
<tr><td>10,000 plants</td><td>{{use_light_10k}}</td><td>{{use_typical_10k}}</td><td>{{use_heavy_10k}}</td></tr></table>
<p class="callout">SQL pre-filter: <b>−{{pf_tok_cut}} tokens</b> per matching call, accuracy unchanged ({{pf_top1_with}} vs. {{pf_top1_without}}).</p>
<p class="src">Measured: token_usage logs (output/tokenomics.json, n above); usage levels are assumptions; pre-filter: output/prefilter_experiment.json (n={{pf_n}} listings).</p>
Note: gpt-6-luna at {{price_in}} input / {{price_out}} output per million tokens. Caching serves {{neg_cached_pct}} of negotiation input. Model cost is not the constraint; hosting, support and sales would be.
---
<h2>Safety</h2>
<div class="cols3">
<div class="card"><h3>Attacks <span class="pass">{{saf_attack}}</span></h3>!img[output/screenshots/crop-injection-blocked.webp|]<p>Injection blocked before any AI reads it: 0 tokens.</p></div>
<div class="card"><h3>Malfunction <span class="pass">{{saf_malfunction}}</span></h3><p class="big-num">{{neg_violations}}</p><p>limit violations in {{neg_n}} negotiations</p><p>Crashes under load: <b>{{crash_before}} → {{crash_after}}</b></p></div>
<div class="card"><h3>Overspending <span class="pass">{{saf_overspending}}</span></h3><p>{{cap_rounds}}-round cap · {{cap_neg_cost}} per negotiation · {{cap_session}} session budget</p><p>Blocked posts cost $0.</p></div>
</div>
<p class="src">Tests on scratch databases: output/safety_tests.json ({{saf_total}} tests) · eval_negotiation.json (n={{neg_n}}) · concurrency_test.json ({{crash_conc}} jobs at once).</p>
Note: Attacks: prompt injection, limit extraction, tools outside a role. Malfunction: every match reason fact-checked; offers outside a limit refused in code and shown only to the agent's own company; loops capped. Overspending: per-run, per-negotiation and session caps.
---
<h2>Impact</h2>
<div class="stats teal">
<div><span class="big-num">{{pd_value}}</span><span>avg. recovered per test deal vs. {{pd_scrap}} scrap (n={{pd_n}})</span></div>
<div><span class="big-num">{{imp_extra}}</span><span>extra recovered, one-time (one plant, model)</span></div>
<div><span class="big-num">{{imp_carry}}</span><span>carrying cost avoided per year (model)</span></div>
<div><span class="big-num">{{imp_co2}} kg</span><span>est. CO2e avoided, one-time (model)</span></div>
</div>
<p class="todo">[TODO: Simrah to fill timed test] manual vs. Spare Change, measured by the author</p>
<p class="src">Deals: output/impact_model.json ({{pd_n}} of {{ds_logged}} logged test deals, synthetic market). Plant model: sourced inputs (Siemens, SPARETECH, Maas, ICE) + labelled assumptions. One-time and yearly values never added.</p>
Note: Deals closed at {{recovery}} of new price versus {{scrap_range}} for scrap. Downtime is counted only for line-down purchases, at the {{tcod_hour}}-an-hour lower bound. CO2e uses sourced factors and a conservative reuse credit.
---
<h2>What's next</h2>
<div class="cols2">
<div><h3>Limits today</h3><ul><li>Synthetic data, demo accounts</li><li>No company dashboard yet</li><li>No payments or part verification</li><li>No independent user yet</li></ul></div>
<div><h3>Next</h3><ul><li>Pilot with a maintenance manager</li><li>Start with discontinued PLCs and drives</li><li>Internal exchange across one manufacturer's sites</li></ul></div>
</div>
<p class="closer">Your next spare part is someone's spare change.</p>
Note: The company dashboard would show all of a company's listings, requests, negotiations, statuses and deal history in one view. Business challenges: getting both sides on board, scattered equipment data, trust and counterfeits, thin margins.
