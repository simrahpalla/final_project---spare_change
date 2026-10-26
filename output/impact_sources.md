# Impact sources: every external number we use

For the report's **Motivation** and **Impact** sections. Each row: the number, where we use it, the source link, and how much to trust it. Use the hedged wording in the last column; never present a vendor blog number as an industry fact. Numbers measured by the app itself (costs, accuracy, recovery ratios) are not here: they are in `output/evidence_index.md`.

## Motivation: the problem

| Number | Used in | Source | Confidence | Say it like this |
|---|---|---|---|---|
| Unplanned downtime costs the world's 500 largest companies **~11% of revenue, ~$1.4 trillion a year** | Motivation | Siemens/Senseye, *The True Cost of Downtime 2024* ([PDF](https://assets.new.siemens.com/siemens/assets/api/uuid:1b43afb5-2d07-47f7-9eb7-893fe7d0bc59/TCOD-2024_original.pdf)) | High (primary report; 181 respondents at large industrial firms) | "Siemens estimates unplanned downtime costs the world's 500 largest companies about 11% of revenue." |
| One hour of downtime costs **at least ~$36k** (consumer goods, the lowest-cost sector in the survey) | Motivation; impact model (**$36k/hr, lower bound**, only for purchases that fill a **line-down** request, 1 hour each) | Siemens TCOD 2024, pp. 2–3 | High | "even in the lowest-cost sector, consumer goods, an hour of downtime costs about $36,000" |
| Restarting after an incident takes **81 minutes on average, up from 49 in 2019**, partly because emergency replacements are harder to source | Motivation (buyer side) | Siemens TCOD 2024, p. 11 | High | quote Siemens' reason: "emergency replacements are more challenging to source and take longer to arrive" |
| "Cost of emergency replacement parts" is part of downtime cost | Motivation | Siemens TCOD 2024, p. 4 | High | — |
| Large plants: **~27 hours of unplanned downtime a month**, 25 incidents | Motivation | Siemens TCOD 2024 | High | — |
| **~22%** of spare-parts (MRO) inventory unused for 5+ years | Motivation; impact model (idle share, mid) | SPARETECH 2025 survey of 300 manufacturing executives, via [Reliamag](https://reliamag.com/topics/guides/mro-spare-parts-inventory-statistics) | Medium (vendor survey) | "a 2025 industry survey found about a fifth of spare-parts inventory had not been used in five years" |
| **~15%** of MRO inventory obsolete | Impact model (idle share, low case) | [Reliable Plant](https://reliableplant.com/Articles/Print/3220?id=3220), practitioner experience | Low to medium | "practitioners estimate around 15%" |
| Holding inventory costs **~15–30% of its value a year** | Impact model (carrying cost 20% mid, 15–30% range) | Industry guides, e.g. [Cleverence](https://www.cleverence.com/articles/for-business/how-do-you-calculate-inventory-carrying-cost-4827/) | Medium (widely cited range, no single authority) | "commonly estimated at 15–30% of inventory value per year" |
| Scrap channels recover **~5–15%** of original cost | Impact model (scrap 10% mid, 5–15%) | Industrial liquidator benchmarks ([Maas Companies](https://maascompanies.com/blog/article/types-surplus-inventory-buyers-industrial-recovery)) | Low to medium (vendor blog) | "liquidators put scrap recovery at roughly 5–15%" |
| Auction recovers **~30–60%**, direct sale **~60–85%** of original value | Motivation (context for our measured 42–56%) | [Maas Companies](https://maascompanies.com/blog/article/how-to-sell-industrial-equipment-maximize-value) | Low to medium (vendor blog; bases differ) | "industry liquidators cite 30–60% at auction" |

## Motivation: why now and the buyer side

| Number | Used in | Source | Confidence | Say it like this |
|---|---|---|---|---|
| Siemens **SIMATIC S7-300** phase-out from **1 Oct 2023**; standard deliveries **ended 1 Oct 2025**; spare parts guaranteed only until **1 Oct 2033**; ~268 assemblies affected | Motivation ("why now"; the demo's main part family) | [Eichler](https://www.eichler-service.com/en/magazine/simatic-s7-300-et-200m-type-discontinuation-pm410-effective-october-2025), [automa.net](https://automa.net/blog/2314/siemens-automation-parts-distributors-suppliers) | Medium (resellers) | "according to industry distributors, new S7-300 parts stopped shipping in October 2025" |
| New OEM replacement part: **~16–20 weeks** (longer or never once discontinued); surplus or refurbished: **~2–10 days** | Motivation (buyer side); impact model (why hours are avoided) | [Automa: sourcing obsolete components](https://automa.net/blog/2045/how-to-source-obsolete-industrial-components) | Low to medium (marketplace operator's blog) | "a new replacement can take 4–5 months; a matching surplus part can arrive in days" |
| Main risks of emergency sourcing: wrong revision or firmware, refurbished sold as new, counterfeits | Limits and next steps (verification) | Same Automa post, plus a [practitioner forum thread](https://control.com/forums/threads/where-do-you-buy-discontinued-plcs-and-automation-parts-urgently.56040/) | Medium (consistent across sources) | — |
| **About 280,000** US manufacturing establishments (NAICS 31–33, 2023) | Tokenomics (10,000 users ≈ 3.5% of US sites) | Summary of Census County Business Patterns ([site](https://manufacturingleadgeneration.com/manufacturing-establishments-by-state/)); official release: [Census CBP 2023](https://www.census.gov/newsroom/press-releases/2025/2023-county-business-patterns.html) | Medium (not checked against the Census tables) | "about 280,000" |

## Impact: carbon factors and disposal (stored in `carbon_factors`)

| Number | Used for | Source | Confidence |
|---|---|---|---|
| Steel **1.95 kg CO2e/kg** (cradle-to-gate) | bearings, pump spares, PLC chassis/accessories, motors and drives (on total weight) | ICE database via [HKUST ECO-CM table](https://cejcheng.people.ust.hk/ec/carbonInventoryLocalized.html); cross-check worldsteel 2023: 1.92 t CO2/t crude steel ([worldsteel](https://worldsteel.org/?p=63833)) | High (standard database, cross-checked) |
| Cast iron **1.86 kg CO2e/kg** | pumps (housing) | Ecoinvent value via a [SciELO LCA paper](https://scielo.br/j/esa/a/8sZLksLQgRNPRCn9sfHPhHS/abstract/?lang=en) | Medium |
| PLC electronics **~12.4–14.4 kg CO2e per compact CPU** (cradle-to-gate); 69.3 kg for a large S7-1500 CPU (manufacturing stage) | 14 kg per PLC CPU (S7-300-class proxy); 12.4 kg per other electronic module (conservative proxy) | Siemens product carbon footprints: [S7-1500 EPD](https://cache.industry.siemens.com/dl/files/794/109983794/att_1320577/v1/SIMATIC_S7-1500_CPU_6ES7517-3FQ10-0AB0_DI_FA_EPD00083.01.pdf), [SiGREEN](https://xcelerator.siemens.com/global/en/all-offerings/products/s/sigreen.html) | High for the products measured; **the proxies are estimates** (label "est.") |
| Remanufactured industrial parts: **46–93% lower emissions** than new (turbochargers 46–50%, engines 72%, compressors 89–93%) → we credit **0.5** | reuse credit on every CO2 figure | [Energies 2024 (peer-reviewed)](https://doaj.org/article/c576efa7bafc42b8bcf8831421b0a0da); [MAN / Univ. of Bayreuth](https://www.heavyquipmag.com/2026/09/02/man-remanufacturing-engines-life-cycle-assessment/) (manufacturer-commissioned); [Curtin Univ.](https://www.curtin.edu.au/news/media-release/research-could-help-reduce-carbon-tax-for-major-industries/) | Medium; 0.5 is a deliberately conservative lower bound |
| Hazardous-waste disposal **~$242 per 55-gal drum** | chemicals (shown instead of CO2): $1.34/kg at our ~180 kg drum fill | [Alachua County FL fee schedule FY22-23](https://www.alachuacounty.us/Depts/SolidWaste/hwc/Documents/ADACompliant/HHW%20FY22-23%20Fee%20Schedule.pdf) | Medium (public rate; commercial quotes run from the low hundreds to over $1,000, so this is conservative) |

**Carbon caveats for the report:** these are cradle-to-gate manufacturing factors; shipping of the used part is not subtracted; electronics factors vary by model; part weights are our estimated shipping weights, not individually sourced.

## Not used: the "don't claim" list (from `impact_research.md`)

- **No industrial (non-aviation) MRO market size.** Only aviation figures or low-quality blogs were found. Say "a large, fragmented market" without a number.
- **No "50–60% of MRO inventory is obsolete."** No primary study supports it (debunked by Reliamag). We use the 22% survey figure instead.
- **No count of installed S7-300 PLCs.** No official number exists; say "one of the most widely installed PLC families" without a count.
- **No higher downtime rates.** The $2.3M/hr automotive figure and the ~$150k/hr small-manufacturer top end are not used anywhere; downtime is valued only at the $36k/hr lower bound, only for line-down purchases.
- **No user quotes or feedback.** No real user has tried the app yet; the pilot is planned (`output/impact_model.md`).
