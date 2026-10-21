# Phase 5 — Panel snapshots and published rankings

## Research question

Do published rank-1 patterns change across the years covered by the inferred Designer Selection Panel snapshots?

Rank 1 is the published order. It is not a signed contract. A difference between snapshot windows is a difference in published lists. It is not a record of who voted, and it is not evidence about a member's preference.

## Available evidence

The membership file is `data/processed/dsp_roster_inferred.csv`, supplied on October 20, 2026. It has 68 rows in five blocks. Each block rests on one snapshot and is carried across the other years in that block.

| Snapshot window | Named people | Confidence in the file | What the file says the snapshot is |
| --- | ---: | --- | --- |
| 2007–2009 | 12 | inferred | 2008–2009 roster, with 2007 carried backward |
| 2010–2012 | 12 | carried-forward | 2010 roster, carried through 2012 |
| 2013–2017 | 12, plus a vacant building-trades seat | carried-forward | 2013 roster, carried through 2017 |
| 2018–2024 | 13 | uncertain | 2018 voting-record snapshot, carried through 2024. The file says it may include staff or alternates, and it does not name a chair |
| 2025–2026 | 18 | mixed | 2025 voting-record notes plus the October 2026 roster page |

The local page `data/reference/panel_members.html`, saved October 20, 2026, lists the same 18 people as the public roster page on October 21, 2026. Middle initials match: Rachel E. Shanley, John S. Ferrante, and John F. Jumpe Jr. The designer-selection process page says the panel has 13 appointed members plus three local members. The roster page lists 12 people who are not labeled staff, five people labeled MSBA staff, and John F. Jumpe Jr. as a staff alternate to one of three staff seats. The page does not say which 13 of the 18 names are the appointed members for a given meeting.

The 2023–2024 and 2025 MSBA annual reports name the Board of Directors. They do not name the Designer Selection Panel. Annual reports of the state's Designer Selection Board are a different body and were not used.

No ballot, point total, roll call, or local-member name is in the result pages. No public-records request was sent.

## Sample construction

The outcome sample is the winner-model sample: 273 multi-firm rankings and 794 finalist rows, from 2007-08-07 through 2026-09-22. Every ranking falls inside one snapshot window. 2026 is partial. Experience uses earlier calendar dates only. Two rankings on the same day do not update each other.

A person is counted once per snapshot. The vacant building-trades row is a seat note, not a person. The October 2026 designation is attached to the 2025–2026 rows only. Karl Brown is labeled MSBA staff on that page and remains a member on the 2010, 2013, and 2018 snapshots.

Present-day staff bands and headquarters are the 2026 research fields from Phase 2. They describe the firm as researched in 2026. Joint ventures are left out of those two comparisons. The prose field `nationwide_operations` is not a yes/no measure, so headquarters is the location comparison.

## Method

Four descriptions are kept separate.

1. Overlap of named people between consecutive snapshots. A name missing from the next snapshot is missing from that list. The file does not give a departure date.
2. Inside each window: two-firm share, mean field size, rank-1 Herfindahl index, and the share held by the five most frequent rank-1 firms. Intervals for the two-firm share resample competitions, 2,000 draws, seed 20261020.
3. On lists that contain both a firm with an earlier rank-1 result and a firm with none, the rank-1 frequency of the firms that already have one, minus their share of the list. The same bootstrap is used. The rate on appearances that already have an earlier rank-1 result is reported beside it.
4. School-type mix from the corrected labels in Phase 3, and 2026 headquarters and staff band among firms that have a verified value.

A resampled percentile interval for the Herfindahl index sits above the estimate, because drawing the same ranking twice shrinks the set of distinct winners. Those intervals are not reported. The point estimates are.

No member-level preference is estimated. The stored winner model is not refit.

## Results

Named-person overlap:

| Boundary | On both snapshots | Only the earlier snapshot | Only the later snapshot | Share of the union retained |
| --- | ---: | ---: | ---: | ---: |
| 2007–2009 to 2010–2012 | 9 | 3 | 3 | 0.60 |
| 2010–2012 to 2013–2017 | 8 | 4 | 4 | 0.50 |
| 2013–2017 to 2018–2024 | 8 | 4 | 5 | 0.47 |
| 2018–2024 to 2025–2026 | 3 | 10 | 15 | 0.11 |

The last boundary keeps Karl Brown, Russell Bartash, and John Jumpe Jr. The 2026 page labels Brown as MSBA staff and Jumpe as a staff alternate. Bartash is the Building Trades Council designee on that page. The 2013 snapshot already lists Bartash as a member and, separately, a vacant building-trades seat. Those two 2013 rows stay separate.

Bernard Feldstein is Chair on the 2007, 2010, and 2013 snapshots. The 2018 snapshot lists him as a member and does not name a chair. The October 2026 page names Beth McDougal as Chair. The file records that Jess Baccari joined in September 2025. This audit did not find a separate appointment notice for that date.

Published rankings during the years each snapshot covers:

| Window | Rankings | Two-firm lists | Mean firms | HHI | Top-five share | Unique rank-1 firms |
| --- | ---: | --- | ---: | ---: | ---: | ---: |
| 2007–2009 | 30 | 1 (3%, 0 to 10) | 3.00 | 0.089 | 57% | 16 |
| 2010–2012 | 52 | 3 (6%, 0 to 13) | 2.98 | 0.054 | 38% | 24 |
| 2013–2017 | 79 | 4 (5%, 1 to 10) | 2.99 | 0.056 | 43% | 27 |
| 2018–2024 | 88 | 20 (23%, 15 to 32) | 2.80 | 0.044 | 33% | 31 |
| 2025–2026 | 24 | 5 (21%, 8 to 38) | 2.79 | 0.073 | 46% | 16 |

The two-firm share rises by 17.7 points from the 2013–2017 window to the 2018–2024 window (interval 8.2 to 28.2). The other three boundaries have intervals that include zero. Phase 1 found the same lengthening of the short list on a nearby cut, 2009–2016 against 2018–2025. Phase 4 shows that, on the 2025–2026 chart, a two- or three-firm ranking is a cut from a median applicant pool of five. That applicant pool is not observed before the chart.

On mixed lists, firms with an earlier rank-1 result take the top place this many points more often than their share of the list:

| Window | Mixed lists | Excess | Interval | Appearances that already have a rank-1 result |
| --- | ---: | ---: | --- | --- |
| 2007–2009 | 16 | 17.2 | −8.3 to 40.1 | 14 of 33 (42%) |
| 2010–2012 | 27 | 3.4 | −14.8 to 21.0 | 41 of 120 (34%) |
| 2013–2017 | 22 | 17.4 | 0.0 to 33.4 | 73 of 207 (35%) |
| 2018–2024 | 32 | 13.5 | −1.0 to 26.8 | 80 of 209 (38%) |
| 2025–2026 | 10 | 31.7 | 13.3 to 43.3 | 23 of 55 (42%) |

The change in that excess from 2013–2017 to 2018–2024 is −3.9 points (interval −25.3 to 17.8). The 2025–2026 excess is higher, and its interval against 2018–2024 includes zero (−4.4 to 37.4) on 10 mixed lists. One rank-1 result in 2025–2026 belongs to a firm id with no earlier rank-1 result in this archive: Flansburg Architects on 2025-11-04, the same unmerged spelling identified in Phase 4.

Elementary schools are the most common stated type in every window except 2010–2012, where elementary and middle are tied at 11 of 52. Municipality-only labels, which stay unknown, are 8 of 52 in 2010–2012 and 13 of 79 in 2013–2017, then 1 of 88 in 2018–2024.

Among finalists with a verified 2026 headquarters, a Massachusetts headquarters accounts for 63 of 70 slots in 2007–2009 (90%, 84 to 96), 155 of 207 in 2018–2024 (75%, 69 to 81), and 37 of 52 in 2025–2026 (71%, 58 to 83). Adjacent windows overlap. Among rank-1 firms with a verified band, the 201-or-more band is 5 of 26, 5 of 41, 6 of 72, 11 of 79, and 4 of 22. Those rank-1 intervals overlap. The finalist-slot share in that band is 13 of 52 in the partial 2025–2026 window (25%, 15 to 35), above the 2018–2024 interval of 8 to 17. The band is a 2026 label.

## Uncertainty and robustness

The two-firm increase at the 2018 snapshot boundary is the one outcome contrast whose interval excludes zero. It matches the field-size change already measured in Phase 1, and the 2018 snapshot is the uncertain one: it may include staff, it does not name a chair, and it is carried through 2024. The incumbent excess does not move with that boundary.

The 2007–2011 zero-prior rates are left-censored. A firm can have ranked first before the archive starts. The 2025–2026 cells are small, and 2026 ends on 2026-09-22 in this sample.

Herfindahl point estimates are lower in 2018–2024 (0.044) than in 2007–2009 (0.089, 30 rankings) and the partial 2025–2026 window (0.073, 24 rankings). Without a usable interval, those differences stay descriptive. The top-five share moves with them: 57%, 38%, 43%, 33%, and 46%.

## Alternative explanations

The shorter published list can come from a shorter interview list, which Phase 4 can see only in 2025–2026, when the median applicant pool is still five firms. It can also come from a change in which projects reach a final ranking. The snapshot file does not separate those mechanisms, and it does not say who attended.

The flat rate among firms that already have a rank-1 result, about 34% to 42% in every window, is the same incumbency pattern Phase 3 measured on the pooled sample. Carrying a roster across years does not create that pattern, and the pattern does not break when the named list turns over.

A drift in the 2026 headquarters share can be a drift in which firms have a verified address. Unknown rank-1 locations are 4 of 30, 11 of 52, 7 of 79, 9 of 88, and 2 of 24.

## Interpretation

The files support a snapshot audit and a description of published rankings during the years each snapshot covers. At the first three boundaries, 9, 8, and 8 named people appear on both snapshots. Three named people remain from the 2018 snapshot to the October 2026 page, and two of those three are labeled staff or staff alternate on that page.

The published change that lines up with a snapshot boundary is the rise in two-firm rankings between the years covered by the 2013 snapshot and the years covered by the 2018 snapshot. The 2018 list is the uncertain snapshot. Firms that already have a rank-1 result in this archive take the top place at a similar rate in every window. School type, 2026 staff band, and a 2026 Massachusetts headquarters do not mark a separate break at these boundaries.

## Limitations

- Carried years are not attendance. A vacancy carried from 2013 through 2017 is not a confirmed five-year vacancy.
- Three local members sit on each project and are unnamed. Under the process page's count of 13 appointed members plus three local members, a complete standing roster would still leave out those three seats.
- The October 2026 page lists more names than the 13 appointed seats and does not say which staff seats vote.
- Former employers and earlier appointing organizations are not in the collected files. A 2026 designation is not read backward.
- No ballot is in the archive, so no member's preference is estimated.
- Rank 1 is not a contract. An unexplained difference is not a finding about favoritism or design quality.

## Next research questions

Phase 6 inspected the public cost files and did not fit a performance model. The write-up is `reports/06_project_performance.md`.

Records that would make the membership question sharper, and that were not found on the result pages, the October 2026 roster page, or the 2023–2024 and 2025 annual reports:

- A year-by-year official DSP roster, with appointment and departure dates.
- Meeting attendance or the roll call.
- The ballot, the point total, and the written statement of reasons sent to the district.
- The three local members on each project.
- Whether the 2018 voting-record names are appointed members, staff, or alternates, and who chaired from 2018 through 2024.
- A 2007 roster separate from the 2008–2009 list.

No request for those records was sent.
