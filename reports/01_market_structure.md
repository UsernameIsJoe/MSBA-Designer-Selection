# Phase 1 — Market structure and historical evolution

## Research question

How has the MSBA designer-selection market evolved between 2007 and 2026?

This phase describes published rankings. It does not estimate why a firm was ranked first, and it does not treat a concentrated or a diffuse pattern as evidence about the panel's motives.

## Available evidence

The source is the existing winner-model sample: 273 multi-firm rankings, 794 finalist rows, 82 firms, and 42 firms with at least one rank-1 result. Dates run from 2007-08-07 through 2026-09-22. Rank 1 is the DSP's published order, not a signed contract.

Applicant lists, repair pools, informational interviews, unfinished rankings, and five sole-firm publications stay out of the primary counts. The sole-firm lists are added back in one sensitivity. Construction of the sample is in `reports/00_research_audit.md`.

Calendar year 2026 contains 11 rankings and ends on 2026-09-22. It is a partial year. Annual plots mark it, and the field-size contrast below stops at 2025.

## Sample construction

One observation in the concentration statistics is one model competition. The rank-1 firm is the row with `winner = 1`. There is one such row in every model competition.

A finalist appearance is one firm-row in that same sample. Participation concentration uses those rows, so a three-firm ranking contributes three appearances and one win.

An archive newcomer is a firm whose first model-sample appearance falls in the period. Every firm in 2007–2011 is an archive newcomer on that definition, because the public file starts in August 2007. That label is left-censored. It is a first observed finalist appearance, not the founding of a practice.

A firm is counted as absent from later rankings only when a later period exists and the firm has no finalist row in it. The 2022–2026 period cannot support that count. Absence from this archive is not the closing of a firm.

Head-to-head counts use pairs inside one model competition. The firm with the better published rank placed higher. A third firm can still be rank 1.

Top-k shares rank firms by rank-1 count and break ties by `firm_id`. The top-10 boundary is a tie at 10 wins between Flansburgh and Raymond Design. Either firm could sit in tenth place, and the top-10 share would be the same because both have 10 wins.

## Method

For a set of rank-1 outcomes, the Herfindahl–Hirschman index (HHI) is the sum of squared winner shares. The effective number of winning firms is 1 / HHI. The normalized HHI rescales that index against the number of firms that won at least once in the window: 0 means those winners have equal shares, and the index is undefined when one firm wins every selection in the window. A separate HHI is computed on finalist appearances.

Annual figures are reported for every calendar year and are noisy when the year has one or nine rankings. Rolling windows of five calendar years are the series used to talk about change. Uncertainty for the full-sample shares is a competition bootstrap with 1,000 draws and seed 20261020. Uncertainty for the early-versus-late contrasts is a separate 2,000-draw bootstrap of each period. These intervals describe resampling of the observed rankings. They are not causal standard errors.

Recompute the tables and figures with:

```powershell
python scripts/build_market_structure.py
```

## Results

### 1A. The rank-1 distribution is diffuse, and the same firms keep winning

Across all 273 rankings:

| Measure | Estimate | 95% bootstrap interval |
| --- | ---: | --- |
| Rankings | 273 | — |
| Unique finalist firms | 82 | — |
| Unique rank-1 firms | 42 | — |
| HHI of rank-1 shares | 0.0445 | 0.0426 to 0.0544 |
| Effective number of winners | 22.5 | 18.4 to 23.5 |
| Normalized HHI among the 42 winners | 0.0212 | — |
| Top-1 share | 7.7% | 7.3% to 11.4% |
| Top-3 share | 22.0% | — |
| Top-5 share | 34.8% | 32.2% to 41.8% |
| Top-10 share | 58.6% | 55.7% to 65.9% |
| HHI of finalist appearances | 0.0340 | — |
| Effective number of finalist firms | 29.4 | — |
| Top-5 share of finalist slots | 28.0% | — |
| Top-10 share of finalist slots | 47.9% | — |

On the 0–10,000 scale sometimes used for market shares, an HHI of 0.0445 is 445. That is below the conventional 1,000 line associated with an unconcentrated share distribution. The benchmark is a numerical comparison only. A designer-selection panel is not a product market, and these shares are counts of rankings, not revenue.

The leading rank-1 firms, and their finalist appearances in the same sample, are:

| Firm | Rank-1 results | Share of rankings | Finalist appearances | Rank-1 rate |
| --- | ---: | ---: | ---: | ---: |
| Drummey Rosane Anderson | 21 | 7.7% | 44 | 0.48 |
| Symmes Maini & McKee | 20 | 7.3% | 39 | 0.51 |
| Dore & Whittier | 19 | 7.0% | 45 | 0.42 |
| HMFH | 19 | 7.0% | 30 | 0.63 |
| DiNisco Design | 16 | 5.9% | 26 | 0.62 |
| Ai3 Architects | 15 | 5.5% | 23 | 0.65 |
| Tappé | 15 | 5.5% | 30 | 0.50 |
| Lamoureux Pagano | 14 | 5.1% | 30 | 0.47 |
| Mount Vernon Group | 11 | 4.0% | 44 | 0.25 |
| Flansburgh | 10 | 3.7% | 50 | 0.20 |

Flansburgh has the most finalist appearances, 50, and 10 rank-1 results. HMFH has 19 rank-1 results from 30 appearances. Participation and first place are different distributions. The five firms with the most finalist slots account for 28% of appearances. The five firms with the most rank-1 results account for 35% of rankings. Winner shares are somewhat tighter than appearance shares, and both are spread across many firms.

Forty of the 82 finalist firms never rank first. The most appearances by a firm with no rank-1 result is 6. Thirty-four firms appear once.

Annual HHI is not comparable across years. 2007 and 2008 each have one ranking, so their HHI is 1. 2014 and 2021 have nine rankings. The rolling series is the one to read. Five-year top-5 shares move from 44.9% in 2007–2011 (69 rankings) to 32.9% in 2017–2021 (70 rankings) and 32.8% in the complete window 2021–2025 (61 rankings). Five-year HHI moves from 0.0615 to 0.0478 over the same early and middle windows. The last complete five-year window, 2020–2024, has HHI 0.0439 and a top-5 share of 33.3%. The shaded 2022–2026 window includes the partial year and is similar to the windows just before it (HHI 0.0476, top-5 share 33.3%, 63 rankings).

The point estimate is a decline. The bootstrap difference, 2007–2011 minus 2017–2021, is 12.1 percentage points for the top-5 share, with interval −5.1 to 19.4 points, and 0.014 for the HHI, with interval −0.006 to 0.037. Both intervals include zero. A lower later concentration is visible in the point estimates and is not established as a change larger than resampling noise.

Figures: `reports/figures/01_winner_concentration_curve.png`, `reports/figures/01_rolling_concentration.png`, `reports/figures/01_market_participation.png`.

### 1B. Entry continues, and later rank-1 results mostly go to firms that have already won

| Period | Rankings | Finalist firms | Rank-1 firms | First observed in this period | Not seen in a later period | Share of rank-1 results by firms that had already ranked first |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2007–2011 | 69 | 43 | 26 | 43, left-censored | 15 | — |
| 2012–2016 | 71 | 40 | 24 | 15 | 12 | 87.3% (62 of 71) |
| 2017–2021 | 70 | 43 | 28 | 13 | 14 | 90.0% (63 of 70) |
| 2022–2026 | 63 | 41 | 28 | 11 | Right-censored | 93.7% (59 of 63) |

Firms that won in the immediately previous period account for 84.3% of rank-1 results in 2017–2021 and 92.1% in 2022–2026.

Nineteen firms appear in all four periods. Forty-four appear in only one. The median span from a firm's first finalist row to its last is 1.5 years, and the mean is 6.1 years, because a minority of firms stay for the whole archive. Thirty-seven firms have a finalist row in 2024 or later, so their absence cannot yet be read as an exit. Fifteen of the 43 firms seen in 2007–2011 have no later finalist row.

Figure: `reports/figures/01_period_turnover.png`. The last period has no "not seen later" bar, because that count is not identified.

### 1C. The field is usually three firms, and two-firm rankings became more common

| Finalists | Rankings | Share | Rank-1 HHI | Top-5 share |
| ---: | ---: | ---: | ---: | ---: |
| 2 | 33 | 12.1% | 0.085 | 54.6% |
| 3 | 232 | 85.0% | 0.044 | 34.1% |
| 4 | 8 | 2.9% | 0.125 | 62.5% |

No model competition lists five or more finalists. The median field is 3 in every complete year except 2024, when it is 2 (8 of 15 rankings). The mean field in rolling windows eases from 2.99 in 2007–2011 to 2.75 in 2020–2024.

Two-firm rankings are 7 of 138 competitions in 2009–2016 (5.1%) and 23 of 101 in 2018–2025 (22.8%). The difference is 17.7 percentage points, with bootstrap interval 9.1 to 26.4. That interval excludes zero. The partial 2026 year is outside this contrast. The rise is the clearest structural change in this phase. It did not come with a demonstrated rise in winner concentration. The later windows have more two-firm lists and a lower, not higher, point estimate for the top-5 share.

The eight four-firm rankings are too few for a separate concentration claim. Their HHI of 0.125 is what equal shares across eight single wins would produce.

There are 412 distinct firm pairs across the 273 rankings. Twenty-two pairs share at least five rankings. Six meet the reporting bar used earlier (at least eight shared rankings, or one firm placing higher at least six times). Four of those six are one-sided, meaning the leader placed higher at least six times and at least twice as often as the other firm:

| Pair | Shared rankings | Who placed higher | Who ranked first |
| --- | ---: | --- | --- |
| Drummey Rosane Anderson vs Kaestle Boos | 14 | Drummey 11, Kaestle Boos 3 | Drummey 8, Kaestle Boos 2, someone else 4 |
| HMFH vs Flansburgh | 8 | HMFH 7, Flansburgh 1 | HMFH 7, Flansburgh 1 |
| Symmes Maini & McKee vs Flansburgh | 8 | SMMA 7, Flansburgh 1 | SMMA 5, Flansburgh 1, someone else 2 |
| Tappé vs Flansburgh | 7 | Tappé 6, Flansburgh 1 | Tappé 4, Flansburgh 0, someone else 3 |

Design Partnership of Cambridge and Flansburgh share 11 rankings, with the place count 7–4 and rank-1 count 2–1; someone else ranked first in 8 of the 11. Dore & Whittier and Flansburgh share 8 rankings and split the higher place 4–4. Those two pairs are frequent and are not one-sided. The counts match `data/processed/firm_head_to_head.csv`. A repeated matchup is still a small slice of the archive: most pairs meet fewer than five times.

Figure: `reports/figures/01_competition_size.png`.

### Sample rules do not move the full-period concentration figures

| Sample | Rankings | Unique rank-1 firms | HHI | Top-5 share |
| --- | ---: | ---: | ---: | ---: |
| Primary multi-firm sample | 273 | 42 | 0.0445 | 34.8% |
| Drop the 6 inferred-order rankings | 267 | 42 | 0.0447 | 34.8% |
| Drop the 1 joint-venture rank-1 result | 272 | 41 | 0.0448 | 34.9% |
| Add the 5 sole published firms | 278 | 44 | 0.0439 | 34.5% |

## Uncertainty and robustness

Full-sample HHI and the top-5 share have bootstrap intervals that sit in a diffuse range. Dropping inferred ranks, the one joint-venture winner, or adding sole-firm lists changes the top-5 share by less than half a percentage point.

The decline in rolling concentration includes zero in its interval. The increase in two-firm rankings does not.

Annual shares in years with fewer than about 15 rankings swing widely and are not used as evidence of a regime change. 2024's median field of 2 is inside the later window that was tested; it is not treated as a separate break.

Head-to-head records with seven or eight meetings can be reversed by a handful of rankings. They are reported because they are the repeated meetings the archive actually contains. They are not a ranking of firm quality.

## Alternative explanations

A diffuse HHI and a stable winner set can both be true. Many firms rank first at least once, and after 2011 about nine in ten rank-1 results still go to a firm that has already ranked first in this archive. One reading is that the panel returns to a broad group of firms that have already been through the process. Another is that the firms who reach a finalist list late in the archive are the firms who were already active, so the winner set persists because the finalist pool persists. Phase 1 does not separate those readings. Phase 3 is the place to test prior wins against specialization inside the choice set.

The rise in two-firm lists may be a change in how many firms the panel advances, a change in how many firms apply, or a change in which projects are published. Historical pages usually omit applicants who were not advanced. The 2025–2026 chart is the first source that consistently lists them. This phase cannot tell a shorter shortlist from a shorter applicant pool.

Left censoring can make 2007–2011 look like an entry wave and can make the first observed wins look like the start of a career. The 15 firms who disappear after 2011 may have stopped pursuing MSBA work, may have continued below the publication threshold, or may sit in an unmerged spelling.

## Interpretation

From 2007 through September 2026, published multi-firm DSP rankings are spread across 42 rank-1 firms. The top firm accounts for under 8% of those rankings, and the top five account for about 35%. Finalist participation is at least as spread out. A core of firms appears in every five-year period and, after 2011, accounts for the large majority of rank-1 results. New finalist names continue to appear, on the order of 11 to 15 firms per five-year period after the censored opening window.

The competitive structure is a three-firm list for 85% of rankings. From 2018 through 2025, two-firm lists are about 23% of rankings, compared with about 5% in 2009–2016. That shift is the robust change in market structure. A decline in winner concentration is the direction of the five-year point estimates and is not resolved by the bootstrap.

None of these patterns identifies favoritism, misconduct, or architectural quality.

## Limitations

- The archive begins in 2007. Pre-2007 MSBA work is invisible.
- Sole-firm publications, unfinished 2025–2026 lists, repair pools, and informational interviews are outside the primary series.
- Six 2010 rankings use document order. Dropping them does not change the full-sample shares.
- Eleven near-duplicate name pairs remain split.
- 2026 is partial through 22 September.
- Head-to-head samples are small.
- The inferred DSP roster was not used. These calendar periods are not panel eras.
- Rank 1 is not a contract award.

## Next research questions

Phase 2 can ask whether present-day staff size, headquarters, and founding year line up with these participation and rank-1 patterns, with the limit that those attributes are current. Phase 3 can ask whether the persistence of the winner set is distinguishable from prior wins and school-type experience inside the choice set. The two-firm shift is a fact for that later work to condition on, not a finding about panel membership.

Before any analysis that dedupes on `project_id`, the 80-character slug should be lengthened and the tables rebuilt. Monument Mountain is the collision already found, and it did not drop a win.
