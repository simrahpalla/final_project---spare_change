# Spare Change: competitor scan

Checked on 2026-10-26 with web search and page fetches. "What it does" is based only on the pages listed in the Source column. Many company home pages returned HTTP 403 to the fetch tool. In those cases the table uses a third-party page that did open, and the row says so. "What it doesn't do" means we found no public evidence of the feature in the sources we checked. It does not prove the competitor lacks it.

Spare Change differs on four points: (1) matching on the buyer's installed base, (2) AI agents negotiating on both sides with private price limits enforced in code and a human approval step, (3) one loop from a messy seller description to an approved deal, and (4) $ recovered and estimated CO2e reported on every deal.

| Competitor | What it does | What it doesn't do that we do | Source | Checked (date 2026-10-26) |
|---|---|---|---|---|
| B-Stock | B2B liquidation marketplace. It sells surplus retail and brand inventory through wholesale auctions, fixed-price Buy Now listings and net payment terms for qualified buyers. | Sells retail returns and overstock in lots. We found no public evidence of industrial installed-base matching or agent negotiation. | https://www.fulfill.com/partners/b-stock (third-party; bstock.com returned 403) | Yes (third-party only) |
| Liquidity Services (GovDeals, AllSurplus) | Handles surplus assets end to end (valuation, marketing, buyer access, sales) across several marketplaces, including GovDeals and AllSurplus. | Its page mentions no AI or negotiation and speaks about sustainability only in general terms. No public evidence of per-deal CO2e or compatibility matching. | https://www.liquidityservices.com | Yes (govdeals.com and allsurplus.com returned 403) |
| EquipNet | Buys and resells surplus lab, pharma and biotech equipment through its MarketPlace, industry Global Auctions and an Outright Purchase Program. | Sells whole equipment by listing and auction. No public evidence of AI agents negotiating within enforced limits or of installed-base matching. | https://manufacturingchemist.com/gain-immediate-financial-return-for-your-surplus-equipment-201495 (third-party; equipnet.com returned 403) | Yes (third-party only) |
| eBay (Business & Industrial) | General marketplace. Maintenance practitioners use it to buy affordable parts for aging equipment and to sell obsolete parts. Third-party storefronts sell PLC, I/O and breaker parts there. | Keyword and part-number search. No public evidence of installed-base matching, AI agents negotiating on both sides, or impact reporting. | https://reliabilityweb.com/videos/article/buying-and-selling-machine-parts-on-ebay-case-studies ; https://www.ebay.com/str/industrialautomationcontrols | Yes (eBay category page returned 403) |
| Automa (automa.net) | Online B2B marketplace for new, surplus and discontinued automation parts. Its homepage advertises "Inventory Upload & Data Matching" (upload inventory to standardise and match it), part-number search and RFQs, "10 million unique, standardised products", 36M+ offers and "750+ Trusted Suppliers". | Matches inventory against parts and supplier catalogs (part numbers), not against the equipment buyers run; no public evidence of agent negotiation or CO2e per deal. | https://automa.net/ (homepage, fetched with a browser user agent); https://trade.gov.pl/en/?p=114066 | Yes |
| SPARETECH | Spare-parts management software for enterprises. It uses AI to standardize MRO data, right-size inventory, support sourcing across sites, and resell surplus parts through a "Surplus Seller" offering with vetted partners. | Negotiation is not mentioned. Surplus sales go through partners rather than an open two-sided marketplace with buyer "wanted" posts (unverified). No public evidence of per-deal CO2e. | https://www.sparetech.io | Yes |
| Rheaply | Lifecycle platform that lets workplace and real-estate teams track assets, reuse them internally and dispose of surplus responsibly. It links to reuse marketplaces and shows carbon-avoided data. | Focuses on workplace and real-estate assets, not industrial spares. The page mentions no AI or negotiation. | https://www.rheaply.com | Yes |
| Verusen | AI tool that analyzes MRO and spare-parts inventory through a company's existing systems and recommends stock-level changes. It also covers moving excess parts to other sites. | Optimizes stock inside one company. The page mentions no external marketplace, negotiation or sustainability metrics. | https://www.verusen.com | Yes |
| Verdantis (MRO360) | AI-based enterprise asset management and master-data software. MRO360 optimizes spare-parts inventory, and its MDM Suite cleans and governs industrial master data. | Data and inventory software. The page mentions no marketplace, negotiation or sustainability offering. | https://www.verdantis.com | Yes |
| Pactum | Sells AI "digital workers" for indirect procurement, from intake to purchase order. This includes an agent that negotiates single-source deals with suppliers, and "your team makes the final call" at award. | Negotiates for the buyer only, on new procurement. No public evidence of a surplus marketplace, matching, or agents on both sides. | https://pactum.com | Yes |
| PharmaCupboard | Exists, but as an Indian company (Vadodara), not a UK/EU one. A third-party directory calls it "India's specialized B2B marketplace for surplus pharmaceutical and chemical inventory" (APIs, excipients, solvents, according to search snippets). | Narrow pharma and chemical scope. No public evidence of AI agents, installed-base matching or CO2e reporting. | https://mtec-sc.org/life-sciences/atlas-pharmaceutical (third-party directory) | Partly. We found no own site and no UK/EU presence. |
| ChatGPT | Generative AI chatbot from OpenAI. A user could paste a messy part description into it to draft a listing, estimate a price or write a negotiation email. | Has no marketplace or buyers, no installed-base data, and no price limits enforced in code. It cannot close a deal with human approval or log impact. | https://en.wikipedia.org/wiki/ChatGPT (openai.com returned 403) | Yes (third-party) |

## Closest competitors

**Automa** and **SPARETECH** are the closest, which matches the expected pair.

- **Automa** is closest on the marketplace side. It is a B2B marketplace for the same goods: surplus, excess and discontinued automation parts from brands such as Siemens, ABB and Allen-Bradley. Its homepage advertises inventory data-matching against 10M+ standardised products from 750+ suppliers: matching against parts and supplier catalogs, not against the equipment a buyer runs, and no evidence of agent negotiation.
- **SPARETECH** is closest on the data side. It owns clean MRO master data, which is the base installed-base matching needs, and it already resells surplus. Our sources show resale through partners, not two-sided agent negotiation.

**Pactum** is the closest match only for the negotiation feature. It works on procurement, not surplus.

## Could not verify

- **PharmaCupboard as a UK/EU company:** We found no evidence of a UK/EU business. The only PharmaCupboard we found is Indian (Vadodara). Its own site (pharmacupboard.com) did not resolve, and yourstory.com returned 403. Details about what it trades come from search snippets.
- **Own sites that would not open (HTTP 403):** bstock.com, equipnet.com, automa.net, govdeals.com, allsurplus.com, eBay's Business & Industrial category page, and openai.com. Those rows rely on the third-party pages listed in the table.
- **Automa:** the homepage opened later with a browser user agent (26 Oct 2026); the row now uses its own figures (10M+ standardised products, 750+ suppliers).

## Category-by-feature matrix (slide 3) — judgments

Each cell is based only on the rows above. ◐ = partly, or unsure (noted):
- **Surplus marketplaces** (Automa, eBay, B-Stock, Liquidity Services, EquipNet): list surplus ✓, reach buyers ✓; parts/catalog data ◐ (only Automa: inventory data-matching against its catalog); AI help – (Automa's matching is not described as AI).
- **Parts data & inventory AI** (SPARETECH, Verusen, Verdantis): parts data ✓, AI ✓; list surplus and reach buyers ◐ (SPARETECH resells via vetted partners; Verusen covers moving excess between a company's own sites).
- **Asset reuse** (Rheaply): list ✓; reach buyers ◐ (internal reuse plus linked marketplaces); $ + CO2e ◐ (a carbon-avoided counter, not per-deal $ and CO2e for industrial spares).
- **AI negotiation** (Pactum): AI ✓; agents negotiate ◐ (buyer side only, new procurement); limits in code – (no public evidence).
- **General chatbot** (ChatGPT): AI ✓; nothing else (drafting a listing is not publishing one).
