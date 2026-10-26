# Impact model: one mid-size plant (illustrative)

`scripts/impact_model.py` → `output/impact_model.json`. Inputs are labelled **MEASURED** (read from this app's evidence files), **SOURCED** (external; links in `output/impact_sources.md`) or **ASSUMPTION** (a stated guess with a low / mid / high range). Outputs are **ONE-TIME** (value recovered and CO2e when the idle stock is sold once) or **PER YEAR**, and are never added together. Nothing here comes from a real user: see *Planned pilot* below.

## Inputs

| Input | Mid | Low – high | Type | Basis |
|---|---|---|---|---|
| Spare-parts (MRO) inventory | $3,000,000 | $1,500,000 – $6,000,000 | ASSUMPTION | a mid-size plant's spare-parts inventory (research section 3) |
| Share unused 5+ years (idle) | 22% | 15% – 22% | SOURCED | SPARETECH 2025 survey (22% unused 5+ years); low = ~15% obsolete (Reliable Plant) |
| Annual carrying cost | 20% of value | 15% – 30% | SOURCED | industry range 15–30% of value per year |
| Scrap recovery | 10% of value | 5% – 15% | SOURCED | industrial liquidator benchmarks 5–15% |
| Recovery through Spare Change | **42%** of new price | 23% – 64% across deals | **MEASURED** | agreed price ÷ new price over every logged deal (`eval_negotiation.json`, n=31) |
| Suggested ask ÷ new price (cross-check) | 56% | 28% – 82% | **MEASURED** | pricing agent's suggested ask ÷ catalog new price (coverage runs) (`phase3_stress.json`, n=21) |
| Sell-through of idle stock | 50% | 25% – 75% | ASSUMPTION | share of the idle stock that finds a buyer (the rest is still scrapped); not measured |
| Line-down purchases filled per year | 1 | 0 – 3 | ASSUMPTION | line-down emergencies per year this plant fills with a surplus part; each counts 1 hour at $36k (lower bound). Only line-down purchases get a downtime value. Cross-check: 14% of our demo requests are line down; at the tokenomics usage of 4 requests a month that would be ~7 a year, so 1–3 is conservative. |
| Downtime cost per hour | $36,000 | — | SOURCED (lower bound) | Siemens TCOD 2024, lowest-cost sector (consumer goods). Higher sector rates are not used. |
| est. kg CO2e per $ of new value | 0.00576 | — | **MEASURED** | get_impact_estimate (sourced factors × 0.5 reuse credit) ÷ new value, over active non-chemical listings (n=18 listings) |
| App model cost per user per month | $0.024 | — | **MEASURED** | real token logs × stated usage (`tokenomics.json`) |
| Users per plant | 1 | 1 – 3 | ASSUMPTION | accounts one plant runs on the app |

## Outputs (mid case)

**One-time** (when the idle stock is sold once):

| Output | Value |
|---|---|
| Idle spare-parts inventory | $660,000 |
| Recovered if all of it is scrapped (one-time) | $66,000 |
| Recovered with Spare Change: sold share at the measured deal ratio, the rest still scrapped (one-time) | **$171,600** |
| Extra $ recovered vs. scrap (one-time) | **$105,600** |
| est. CO2e avoided by the sold share (one-time) | **1,901 kg** |

**Per year:**

| Output | Value |
|---|---|
| Carrying cost of the idle stock today | $132,000 / year |
| Carrying cost avoided (sold share, vs. keeping it) | **$66,000 / year** |
| Buyer side: downtime value (line-down purchases only, lower bound) | **$36,000 / year** |
| Spare Change model cost (model calls only; hosting and support not costed) | **$0.29 / year** |

**Reading:** at the mid case, Spare Change recovers 2.6× what scrapping does on the idle stock (one-time) and, compared with keeping it on the shelf, stops $66,000 a year of carrying cost (scrapping would stop that too, but recover only $66,000). On the buyer side, one line-down purchase filled from surplus is worth at least $36,000 of avoided downtime, against $0.29 a year of model costs.

## Our logged test deals

Of the 31 logged test deals used here (`eval_negotiation.json`; 2 more were excluded: deals on a listing or request created during a test run (not in the seed catalog, so they can't be priced)), **8** filled a request marked **line down**. Test deals repeat the same pairs, so no dollar total is given; downtime is valued only in the plant model above (line-down purchases × 1 hour × $36k). Per test deal on average: $1,889 recovered vs. $63 scrap, est. 14.0 kg CO2e (n=31).

## Scenarios

| Output | All low | Mid | All high |
|---|---|---|---|
| Extra $ recovered vs. scrap (one-time) | $20,812 | $105,600 | $267,300 |
| est. kg CO2e avoided (one-time) | 324 kg | 1,901 kg | 5,702 kg |
| Carrying cost avoided (per year) | $8,438 | $66,000 | $297,000 |
| Buyer downtime value (per year, line-down only) | $0 | $36,000 | $108,000 |
| App model cost (per year) | $0.29 | $0.29 | $0.87 |

"All low" / "all high" set every input to its low / high value at once (a high scrap rate lowers the benefit).

## Sensitivity (one input at a time, everything else at mid)

| Input | Low | Mid | High |
|---|---|---|---|
| MRO inventory | $1,500,000: extra $52,800 once · carrying $33,000/yr | $3,000,000: extra $105,600 once · carrying $66,000/yr | $6,000,000: extra $211,200 once · carrying $132,000/yr |
| Idle share | 15%: extra $72,000 once · carrying $45,000/yr | 22%: extra $105,600 once · carrying $66,000/yr | 22%: extra $105,600 once · carrying $66,000/yr |
| Carrying cost rate | 15%: extra $105,600 once · carrying $49,500/yr | 20%: extra $105,600 once · carrying $66,000/yr | 30%: extra $105,600 once · carrying $99,000/yr |
| Scrap recovery | 5%: extra $122,100 once · carrying $66,000/yr | 10%: extra $105,600 once · carrying $66,000/yr | 15%: extra $89,100 once · carrying $66,000/yr |
| Sell-through | 25%: extra $52,800 once · carrying $33,000/yr | 50%: extra $105,600 once · carrying $66,000/yr | 75%: extra $158,400 once · carrying $99,000/yr |
| Line-down purchases / year | 0: downtime $0/yr | 1: downtime $36,000/yr | 3: downtime $108,000/yr |

## Caveats

- Illustrative for one plant; inventory size, sell-through and line-down purchases are assumptions, shown with ranges.
- Recovery ratios are measured on our synthetic catalog (real part numbers and list prices, made-up companies and asks).
- CO2e comes from the app's `get_impact_estimate`: cradle-to-gate factors × a conservative 0.5 reuse credit; shipping not subtracted; chemicals excluded.
- Downtime uses $36k/hr, the lowest sector rate in Siemens TCOD 2024, only for line-down purchases, 1 hour each: a lower bound.

## Planned pilot (not done yet)

No real user has tried Spare Change yet. A planned session with a plant maintenance or MRO manager would test:
- **Time** to list one surplus part and find 3 plausible buyers: their current process vs. Spare Change.
- **Trust:** whether the suggested floor / budget, the compatibility matches and the compliance checks make sense to them.
- **A short quote** about the experience.

Until then, the only timing evidence is the author's own timed test (`output/timed_test_template.md`), labelled as such. No user quotes or feedback appear anywhere in this project.
