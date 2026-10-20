# Stage 0 — Audit of the existing research platform

Audit date: 2026-10-20. This note inspects the repository as it stood after the public DSP snapshots, firm profiles, and winner models were already in place. It does not refit those models and it does not rewrite `data/raw`.

The processing code reproduces the stored selection tables. The parser, reread in memory from the HTML and Excel snapshots, returns 1,513 archive firm-rows after dropping 8 exact duplicate rows, 31 chart blocks, and 224 chart firm-rows. Those counts match the files on disk. Rebuilding the research tables from those parsed files reproduces 282 selection events, 888 competitor rows, 273 model competitions, 794 model finalist rows, and 82 model firms. `python -m pytest` reports 19 passed tests, including same-day leakage on the stored model frame and the name-resolution checks.

## What this platform already estimates

The existing question is: among the firms on one published finalist list, which firm was ranked first? The conditional logit, baselines, penalized firm effects, gradient boosting, and Plackett–Luce rating all answer that question inside the published choice set. `reports/research_report.md` is the generated model note. Experience features use earlier calendar dates only. Two selections on the same day do not update each other. A check of every firm in `data/processed/model_frame.csv` confirms that `prior_wins` equals the number of that firm's rank-1 results on strictly earlier dates.

Rank 1 is the panel's published order. It is not a signed contract. The January 2026 procedures leave the award to the district.

## Field inventory and join keys

| Table | Grain | Join key | Role |
| --- | --- | --- | --- |
| `data/raw/results_*.html` | Posted meeting page | — | Unmodified source |
| `data/raw/DSP_Meeting_Results_Chart_2025-2026.xlsx` | Chart block | — | Unmodified 2025–2026 source |
| `data/processed/archive_firm_lists.csv` | Firm on a posted list | meeting date, project, firm text | Parsed HTML |
| `data/processed/chart_projects.csv`, `chart_firms.csv` | Chart project and firm | `project_id` | Parsed Excel |
| `data/processed/selection_events.csv` | One published selection round | `selection_id`, `project_id` | 282 rounds, 2007-08-07 through 2026-10-20 |
| `data/processed/competitors.csv` | Firm within a round | `selection_id`, `firm_id` | 888 rows, with `choice_status` |
| `data/processed/model_frame.csv` | Finalist in the winner model | `selection_id`, `firm_id` | 794 rows, with pre-decision experience |
| `data/processed/firms.csv` | Resolved firm | `firm_id` | 91 directory firms, plus company fields and a separate win tally |
| `data/processed/firm_alias_audit.csv` | Printed name | `firm_id` | 174 alias rows |
| `data/reference/firm_company.csv` | Researched company profile | `firm_id` when matched | Current attributes. Unmatched rows have a blank id |
| `data/processed/dsp_roster_inferred.csv` | Inferred member in an era | era, member name | Not a ballot and not an attendance record |
| `data/processed/firm_head_to_head.csv` | Firm pair with at least five shared rankings | firm names | Earlier matchup table. Phase 1 recomputes the counts |

`firm_id` is `f_` plus the first 10 hex characters of the SHA-1 of the canonical name key. `selection_id` is the meeting date, a project slug, and the round name.

## Sample inclusion

A competition enters the winner model only when the published list has at least two firms and exactly one top-ranked firm who did not decline. The code path is `_finalize_choice_sets` in `src/msba_dsp/processing/build.py`.

| `choice_status` | Rows | In the winner model |
| --- | --- | --- |
| `model_sample` | 794 | Yes. 273 competitions |
| `applicant_pool_only` | 77 | No. Chart applicants who were not on the final list |
| `incomplete_rank` | 12 | No. A blank rank on the final list removes the whole selection |
| `single_firm` | 5 | No. A sole published firm has no opponent |

The nine events outside the model are:

- Sole published firm: Braintree South Middle (2018-06-05), North Adams Greylock (2022-07-05), Berkley Community (2023-01-03, unnumbered award list), Belchertown Jabish Brook (2023-02-14), Triton Regional High School (2026-04-07, application order with one firm and no interview).
- Unfinished final list: New Bedford Charles S. Ashley (2025-12-02), Peabody High School (2026-07-14), Pittsfield John C. Crosby (2026-08-25), Milton Cunningham (2026-10-20).

Springfield Gerena is the one `application_ranking_no_interview` event inside the model. The chart published an application order and no interview, and that order has a unique first firm. Triton is the other no-interview chart project; it names one firm, so it stays in the sole-firm group.

Of the 273 model competitions, 243 use printed numbers, 24 use the 2025–2026 chart rank, and 6 are 2010 lists that the source calls a ranking but prints as bullets. Those six take rank from document order and are flagged `published_list_order`. Repair pools and informational interviews never become selection events.

`data/processed/firms.csv` uses a second, wider tally. `firm_ranking_record` counts `model_sample` and `single_firm`, and it treats a sole firm at rank 1 as a win. That tally sums to 278 wins and 799 firm-rankings. The extra five wins are the sole-firm lists. Phase 1 uses the 273-competition model sample so the market figures match the winner model. The sensitivity table puts the five sole-firm lists back in. The two series answer different questions and both stay.

## Counts the existing report asked to be checked

| Published figure | Recount |
| --- | --- |
| 282 selection events | 282 |
| 273 competitions in the winner model | 273 |
| 794 finalist observations | 794 |
| 91 firms in the directory | 91 |
| 82 firms in the model sample | 82 |
| Coverage 2007–2026 | Model rankings run from 2007-08-07 through 2026-09-22. The event file also holds the unfinished Milton interview dated 2026-10-20 |
| 99 out-of-sample competitions from 2019 onward | 15+12+9+12+12+15+13+11 = 99. Training through 2018 is 174 |

The stored winner Herfindahl index, 0.045, and the top-five share, 0.348, match the Phase 1 full-sample calculation (0.0445 and 0.3480) before the report's three-decimal rounding.

The quality summary's `competitions_explicit_rank` (246) and `competitions_rank_inferred` (7) count selection events, not model competitions. The model itself contains 243 numbered HTML rankings and 6 inferred-order rankings. The labels in `reports/data_quality.md` are wider than the estimation sample.

## Names, aliases, and duplicates

Automatic matching removes case, accents, punctuation, and legal suffixes. Further matches are the reviewed list in `src/msba_dsp/processing/names.py`. Joint ventures and "in association with" lines keep their own identifiers. Six joint-venture rows are in the directory. Two aliases are medium confidence: Office of Michael Rosenfeld and DiNisco Design. Tests confirm that SMMA, Dore & Whittier, and a joint venture with Mount Vernon resolve as intended, and that Perkins & Will, Perkins Eastman, and Design Partnership of Cambridge stay apart.

`near_duplicate_firms.csv` lists 11 lookalike pairs that were deliberately left unmerged, including Symmes Maini with and without the ampersand, Perkins Eastman and Perkins Eastman DPC, and the two CBT spellings. Those splits can move a few appearances between firm ids. Phase 1 does not merge them.

One `project_id` collision is real. `_project_id` cuts the slug at 80 characters, so the year falls off the end of long district names. Monument Mountain Regional High School on 2012-03-13 and 2024-01-30 share `project_id` `p_berkshire-hills-regional-school-district-monument-mountain-regional-high-school-`. The selection ids still differ because each begins with its own date. No firm appears on both lists, so the directory's project-level dedupe does not drop a win. Five other project ids are at least 80 characters and do not collide. This should be fixed before any later analysis dedupes on `project_id`. It was left in place here because changing the slug would change stored identifiers and force a model rebuild.

## Firm profiles and the inferred roster

Company fields on `firms.csv` come from `data/reference/firm_company.csv`. They describe the firm as researched in 2026.

| Directory firms | 91 |
| --- | --- |
| Any verification status | 73 |
| Staff-size band | 39 |
| Headquarters | 40 |
| Founding year | 35 |
| Verified via a cited source | 39 |
| Unverified, no firm-specific source | 22 |
| Blank profile | 18 |
| Joint or tied submission, not one employer | 11 |
| Partial verification | 1 |

These fields are not in the conditional logit. The source inventory is right that the DSP result pages themselves do not publish offices. The company file is a separate, present-day research layer. It is not a historical panel of firm size. Phase 2 has to keep that limit.

`dsp_roster_inferred.csv` has 68 rows. Confidence is `inferred` for 2007–2009 (12 names, with 2007 carried backward), `carried-forward` for 2010–2012 (12) and 2013–2017 (13, including a vacant building-trades seat), `uncertain` for 2018–2024 (13, and the file does not name a chair), and `mixed` for 2025–2026 (18, including staff and an alternate). Three local members per project are unnamed. The file is not attendance, not a ballot, and not an input to Phase 1.

## Temporal leakage

`add_decision_date_features` scores every competition on a day before it increments wins, finalist counts, or grade wins. The stored model frame passes a firm-by-firm check against that rule. Same-day selections contribute nothing to each other. Archive newcomers are firms with `prior_finals == 0`. The code and the research note both say this is an absence from the public archive, which starts in 2007, and the newcomer hypothesis is refit from 2012 before it can be called supported. That refit is inconclusive.

Current staff size, headquarters, and founding year are not pushed backward into earlier competitions. Phase 1 does not use them.

## How the winner models were validated

Out-of-sample scores for 2019 onward are fit on competitions through 2018. There is no random split across time. Choice-set log loss is the metric that includes the equal-probability baseline. Top-choice accuracy gives that baseline a zero because it never names a unique favorite.

The conditional-logit intervals in the research note rest on 35 successful competition resamples out of 40 requested draws. Failed optimizer draws are dropped. The intervals are therefore the successful draws only. The seed is `MSBA_SEED` (default 20261020). This audit did not refit the logit.

| Hypothesis | Stored status | Whether the published evidence matches that status |
| --- | --- | --- |
| H1 Prior wins predict selection | inconclusive | The in-sample coefficient on prior wins is 0.087, interval 0.033 to 0.150. Out-of-sample log loss is 1.077, which is worse than equal probability at 1.014. The status rule requires both a positive interval and a better out-of-sample loss. The status matches the rule. |
| H2 Experience matters more on larger projects | inconclusive | 24 competitions have a preselection cost range. The interval on the budget interaction includes zero. |
| H3 Same-grade wins add to total wins | supported | The grade coefficient interval, 0.019 to 0.266, excludes zero, and the code marks the hypothesis supported only if an out-of-sample loss contrast against a no-grade logit also clears zero. That contrast is not printed in `reports/research_report.md`. The printed grade-wins baseline has out-of-sample log loss 1.294, worse than equal probability. A reader of the report alone cannot see the contrast that flips the label to supported. Grade is parsed from the school name. |
| H4 Archive newcomers | inconclusive | The full-sample and 2012-onward intervals both include zero. The caution about left censoring is already in the note. |
| H5 Field size changes the experience slope | inconclusive | The interaction interval includes zero. |
| H6 Firm residuals after experience | supported | Out-of-sample log loss is 0.941 with penalized firm effects, 1.077 for the experience logit, and 0.979 for the shrunk win-rate baseline. The improvement over the logit has interval 0.027 to 0.251, and the firm-effect model also beats the shrunk baseline. Nine firms have a residual interval excluding zero and at least eight appearances. The note already treats these as selection residuals. They are not a quality score and they are not evidence of favoritism. |
| H7 The experience slope changes over time | inconclusive | The time interaction interval includes zero. |
| H8 A walk-forward rating adds to experience | inconclusive | The rating improves on the logit and loses to the shrunk win-rate baseline. The rule requires both. |
| H9 Cost performance | inconclusive | The designer construction cost chart is absent. `reports/source_inventory.md` records the PDF and Tableau links as not present. |
| H10 Recent award workload | inconclusive | The three-year win coefficient interval includes zero. |

No stored status was changed. H3 is the one place where the published report does not show the number required to audit the word "supported." Regenerating the pipeline would print that contrast if the report writer were extended. That regeneration was not run, because it would refit the models and overwrite the generated note.

## Corrections recorded, and left unchanged

1. Long `project_id` values can collide. Monument Mountain is the one collision, and it does not change the current win tally. The slug should be fixed before a later dedupe, together with a full rebuild.
2. Directory wins (278) and model wins (273) will keep their different rules. Reports have to name which series they use.
3. The quality summary's "competitions" with an explicit rank are events, not model competitions.
4. The H3 support flag needs its out-of-sample contrast printed the next time the model note is generated.
5. Near-duplicate names stay split until a reviewed alias is added. They are not merged on token overlap alone.

Phase 1, in `reports/01_market_structure.md`, uses the model sample and does not alter these rules.
