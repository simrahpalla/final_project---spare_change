# Phase 10 impact consistency check

`scripts/check_impact.py` (no model calls, scratch database). **25 / 25 PASS.**

| # | Check | Result | Detail |
|---|---|---|---|
| 1 | listing 9, steel part: 20 × Bearing 6312-2Z/C3 | PASS | hand 1.7 kg × 20 × 1.95 kg CO2e/kg × 0.5 = 33.1 kg; app 33.1 kg |
| 1 | listing 18, motor: 2 × Servo motor A06B-0235-B605 | PASS | hand 18 kg × 2 × 1.95 kg CO2e/kg (steel on total weight) × 0.5 = 35.1 kg; app 35.1 kg |
| 1 | listing 2, PLC CPU: 2 × 1756-L61 | PASS | hand 2 units × 14 kg CO2e/unit × 0.5 (weight not used) = 14.0 kg; app 14.0 kg |
| 1 | electronics use the per-unit factor only (no weight term) | PASS | 7 per-unit families (PLC CPU, PLC I/O, PLC power supply, Network, VFD option, VFD control unit, Robot accessory) have kg_co2e_per_kg NULL; code uses per-unit × qty when set |
| 1 | per-unit estimate ignores weight (weight ×10 on 1756-L61) | PASS | still 14.0 kg |
| 1 | no implausibly large figure | PASS | largest per unit: {'listing': 8, 'part': '3196-STX-PE', 'family': 'Pump spare', 'qty': 1, 'weight_kg': 60.0, 'kg_co2e': 58.5, 'per_unit': 58.5}; over 50 kg/unit: listing 8 3196-STX-PE 58.5 kg/unit (60.0 kg × 1.95 × 0.5, plausible for a Pump spare) |
| 2 | every factor and source URL matches impact_research.md | PASS | 17 families: steel 1.95/kg, cast iron 1.86/kg (research §2), PLC CPU 14/unit and modules 12.4/unit (research: 12–15 kg per compact CPU), every URL found in impact_research.md |
| 2 | disposal factor = $242 per drum ÷ ~180 kg | PASS | 1.34 $/kg = 242 / 180 for Chemical and Lubricant |
| 2 | chemicals show disposal avoided, never CO2 | PASS | 6 chemical listings: CO2 None for all; disposal shown for 5 (hazardous or expiring within 12 months) |
| 2 | every URL in impact_sources.md is in impact_research.md | PASS | all present |
| 3 | the same function behind strip, deal card, Marketplace and impact_model | PASS | impact strip (seller run → get_impact_estimate): yes, deal card: yes, Marketplace summary: yes, impact_model.json: yes, frontend does no CO2 maths: yes |
| 3 | Marketplace total = sum of the individual deals (3 approved deals on a scratch DB) | PASS | board {$ 4920.0, 54.1 kg, $ 469.0 disposal} = sum {$ 4920.0, 54.1 kg, $ 469.0 disposal} |
| 3 | Reset demo clears impact totals | PASS | before reset: 2 session impacts, 3 approved deals on the board; after /api/reset: 0 and 0 |
| 4 | downtime only for line-down deals, $36k/hr lower bound | PASS | 8 of 31 logged deals were line down (count only, no summed $); plant model: 1 line-down purchase/yr × $36k |
| 4 | no $2.3M or $150k downtime rate in the model | PASS | none found |
| 5 | one-time and per-year outputs kept apart and labelled | PASS | one_time: ['recovered_if_all_scrapped_usd', 'recovered_with_spare_change_usd', 'extra_recovered_vs_scrap_usd', 'est_kg_co2e_avoided']; per_year: ['carrying_cost_of_idle_stock_usd', 'carrying_cost_avoided_usd', 'buyer_downtime_value_usd', 'app_model_cost_usd']; UI $ recovered labelled 'one-time' (strip, deal card, Marketplace, rail) |
| 5 | UI labels $ recovered as one-time | PASS | 5 labels in the frontend |
| 6 | change an evidence file → the output changes | PASS | tokenomics cost/user-month $0.02428 → $0.243: model cost $0.29/yr → $2.91/yr; one deal price ×2 in eval_negotiation: recovery ratio 0.42 → 0.436, extra recovered $105,600 → $110,880 (temp copies; real files untouched) |
| 7 | no invented user quotes, testimonials or pilot claims | PASS | no hits |
| 7 | timed test template results still empty | PASS | 20 result cells, all blank |
| 8 | don't-claim: MRO market size | PASS | only in the 'Not used' list of impact_sources.md |
| 8 | don't-claim: 50–60% obsolete | PASS | only in the 'Not used' list of impact_sources.md |
| 8 | don't-claim: S7-300 installed count | PASS | only in the 'Not used' list of impact_sources.md |
| 8 | don't-claim: $2.3M/hr | PASS | only in the 'Not used' list of impact_sources.md |
| 8 | don't-claim: $150k/hr | PASS | only in the 'Not used' list of impact_sources.md |

## est. CO2e for every listing (app values)

| Listing | Part | Family | Qty | kg/unit | kg CO2e | per unit |
|---|---|---|---|---|---|---|
| 1 | 6ES7315-2AG10-0AB0 | PLC CPU | 3 | 0.3 | 21.0 | 7.0 |
| 2 | 1756-L61 | PLC CPU | 2 | 0.3 | 14.0 | 7.0 |
| 3 | 25B-D010N104 | VFD drive | 4 | 2.0 | 7.8 | 1.9 |
| 4 | 96416889 | Pump spare | 6 | 1.2 | 7.0 | 1.2 |
| 5 | ACS580-01-039A-4 | VFD drive | 1 | 13.0 | 12.7 | 12.7 |
| 6 | 1756-IB16 | PLC I/O | 10 | 0.3 | 62.0 | 6.2 |
| 7 | 1747-L542 | PLC CPU | 1 | 0.25 | 7.0 | 7.0 |
| 8 | 3196-STX-PE | Pump spare | 1 | 60.0 | 58.5 | 58.5 |
| 9 | 6312-2Z/C3 | Bearing | 20 | 1.7 | 33.1 | 1.7 |
| 10 | A06B-6117-H209 | Servo amplifier | 1 | 3.5 | 3.4 | 3.4 |
| 11 | BMXP342020 | PLC CPU | 2 | 0.3 | 14.0 | 7.0 |
| 12 | 1756-EN2T | Network | 3 | 0.3 | 18.6 | 6.2 |
| 13 | 6ES7321-1BL00-0AA0 | PLC I/O | 12 | 0.3 | 74.4 | 6.2 |
| 16 | ZCU-14 | VFD control unit | 1 | 0.5 | 6.2 | 6.2 |
| 17 | 20F11ND022AA0NNNNN | VFD drive | 1 | 15.0 | 14.6 | 14.6 |
| 18 | A06B-0235-B605 | Servo motor | 2 | 18.0 | 35.1 | 17.6 |
| 19 | Q06UDEHCPU | PLC CPU | 1 | 0.15 | 7.0 | 7.0 |
| 20 | BMXDDI1602 | PLC I/O | 8 | 0.12 | 49.6 | 6.2 |
| 22 | 6207-2Z/C3 | Bearing | 50 | 0.29 | 14.1 | 0.3 |
| 25 | 1756-IB16 | PLC I/O | 1 | 0.3 | 6.2 | 6.2 |
| 27 | 1756-L61 | PLC CPU | 5 | 0.3 | 35.0 | 7.0 |
