<!-- One slide per block, separated by a line with three dashes. Lines starting "Note:" become speaker notes.
     !img[path|css] and !svg[path] embed files; double-brace number keys come from scripts/report_numbers.py. -->
<div class="title-slide">
<div class="logo big">¢</div>
<h1>Spare Change</h1>
<p class="tag">From one plant's shelf to another plant's line.</p>
<p class="sub">AI agents match industrial surplus to the plants that run the same machines, and negotiate the deal.</p>
<p class="who">Simrah Palla · MGT 409 · <a href="{{github_url}}">{{github_url}}</a></p>
</div>
Note: One sentence: Spare Change is a marketplace where agents list a plant's surplus part, find the plants whose machines use it, and negotiate within limits enforced in code; humans approve.
---
<h2 class="long">The part one plant scraps is the part another plant is waiting for.</h2>
<div class="gap3">
<div class="card sell"><h3>Plant A: surplus on a shelf</h3><p class="big-num">{{idle_pct}}</p><p>unused 5+ years</p><p class="big-num">{{scrap_range}}</p><p>recovered as scrap</p><p class="chip teal">Scrapping wastes the carbon already spent making it.</p></div>
<div class="link"><p class="today">Today: no way to find each other</p><p class="muted2">keyword listings, broker calls, guesswork</p><div class="arrow">⟶</div><p class="connects">Spare Change connects them.</p></div>
<div class="card buy"><h3>Plant B: line down</h3><p class="big-num">≥ {{tcod_hour}}/hr</p><p>downtime (lowest-cost sector)</p><p class="big-num">{{lead_new}}</p><p>for a new part vs. {{lead_surplus}} surplus</p></div>
</div>
<p class="whynow"><b>Why now:</b> legacy PLCs retired in waves · downtime cost per hour up {{tcod_range_x}} since 2019 · an agent negotiation costs ~{{neg_cost_round}}</p>
<p class="src">Sources: SPARETECH 2025 (via Reliamag) · Maas Companies · Siemens TCOD 2024 · Automa · Rockwell, Siemens/Eichler (PLC discontinuations) · output/tokenomics.json (n={{neg_runs}} negotiations). Links: output/impact_sources.md</p>
Note: Seller plants scrap or shelve working spares after upgrades, wasting the money and the emissions spent making them. Buyer plants running the same old machines lose money every hour the line is down. Why now: Rockwell discontinued the PLC-5 in 2017 and SLC 5/01–5/03 since; Siemens ended S7-300 deliveries in {{s7_end}}; downtime per hour is {{tcod_auto_x}} its 2019 cost in automotive and {{tcod_heavy_x}} in heavy industry; and an agent negotiation costs about {{neg_cost_round}}.
---
<h2>What's new</h2>
<table class="cmx">
<tr class="band"><th></th><th colspan="4">Table stakes</th><th colspan="4" class="new">New with Spare Change</th></tr>
<tr><th>Category</th><th>List surplus</th><th>Reach buyers</th><th>Parts / catalog data</th><th>AI help</th><th class="new">Match on buyers' machines</th><th class="new">Agents negotiate both sides</th><th class="new">Limits in code</th><th class="new">$ + CO2e per deal</th></tr>
<tr><td><b>Surplus marketplaces</b><span>Automa, eBay, B-Stock, Liquidity Services, EquipNet</span></td><td class="y">✓</td><td class="y">✓</td><td class="p">◐</td><td class="n">–</td><td class="n">–</td><td class="n">–</td><td class="n">–</td><td class="n">–</td></tr>
<tr><td><b>Parts data &amp; inventory AI</b><span>SPARETECH, Verusen, Verdantis</span></td><td class="p">◐</td><td class="p">◐</td><td class="y">✓</td><td class="y">✓</td><td class="n">–</td><td class="n">–</td><td class="n">–</td><td class="n">–</td></tr>
<tr><td><b>Asset reuse</b><span>Rheaply</span></td><td class="y">✓</td><td class="p">◐</td><td class="n">–</td><td class="n">–</td><td class="n">–</td><td class="n">–</td><td class="n">–</td><td class="p">◐</td></tr>
<tr><td><b>AI negotiation</b><span>Pactum</span></td><td class="n">–</td><td class="n">–</td><td class="n">–</td><td class="y">✓</td><td class="n">–</td><td class="p">◐</td><td class="n">–</td><td class="n">–</td></tr>
<tr><td><b>General chatbot</b><span>ChatGPT</span></td><td class="n">–</td><td class="n">–</td><td class="n">–</td><td class="y">✓</td><td class="n">–</td><td class="n">–</td><td class="n">–</td><td class="n">–</td></tr>
<tr class="us"><td><b>Spare Change</b></td><td class="y">✓</td><td class="y">✓</td><td class="y">✓</td><td class="y">✓</td><td class="y">✓</td><td class="y">✓</td><td class="y">✓</td><td class="y">✓</td></tr>
</table>
<p class="src">✓ yes · ◐ partly · – no public evidence. ◐: Automa catalog matching; SPARETECH resale via partners; Rheaply carbon counter; Pactum buyer side only. Source: output/competitors.md, checked 26 Oct 2026.</p>
Note: Surplus marketplaces list and reach buyers; Automa also matches inventory against parts catalogs. Data and inventory AI tools know the parts. Pactum negotiates, but only for buyers on new procurement. Nobody we found matches on the machines buyers run, puts agents on both sides with limits enforced in code, or reports $ and CO2e per deal.
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
<p class="src">Deals: output/impact_model.json ({{pd_n}} of {{ds_logged}} logged test deals, synthetic market). Plant model: sourced inputs (Siemens, SPARETECH, Maas, ICE) + labelled assumptions. One-time and yearly values never added.</p>
Note: Deals closed at {{recovery}} of new price versus {{scrap_range}} for scrap. Downtime is counted only for line-down purchases, at the {{tcod_hour}}-an-hour lower bound. CO2e uses sourced factors and a conservative reuse credit.
---
<h2>What's next</h2>
<div class="cols2">
<div><h3>Limits today</h3><ul><li>Synthetic data, demo accounts</li><li>No company dashboard yet</li><li>No payments or part verification</li><li>No user test yet</li></ul></div>
<div><h3>Next</h3><ul><li>Timed pilot with real maintenance managers: today's way vs. Spare Change</li><li>Start with discontinued PLCs and drives</li><li>Internal exchange across one manufacturer's sites</li></ul></div>
</div>
<p class="closer">From one plant's shelf to another plant's line.</p>
Note: The company dashboard would show all of a company's listings, requests, negotiations, statuses and deal history in one view. Business challenges: getting both sides on board, scattered equipment data, trust and counterfeits, thin margins.
