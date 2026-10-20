# Data quality

Generated 2026-10-20 16:07 UTC.

## Coverage

| measure | value |
| --- | --- |
| archive_firm_rows | 1513 |
| projects_identified | 281 |
| selection_events_identified | 282 |
| finalist_rows | 811 |
| firms_identified | 91 |
| model_competitions | 273 |
| model_finalist_rows | 794 |
| competitions_explicit_rank | 246 |
| competitions_rank_inferred | 7 |
| records_with_budget | 29 |
| records_with_grade | 615 |
| ambiguous_medium_confidence_firms | 2 |
| joint_ventures_kept_separate | 6 |
| alias_rows | 174 |
| share_model_rows_with_grade | 0.77455919395466 |
| share_model_rows_with_budget | 0.08438287153652393 |


## How a competition enters the model

A competition is in the estimation sample only when the public record lists at least two distinct firms, the published order identifies exactly one top-ranked firm, and that firm did not decline the interview. Accelerated-repair pools, informational interviews, and applicant lists without a ranking stay out of the winner model.

Ranks printed as a bulleted "ranking" without numerals use the published order, first listed as rank 1. Those competitions are flagged `published_list_order`.

Experience features for a selection use only competitions with an earlier calendar date. Same-day selections do not update one another.

## What is not in the estimation file

- Individual panelist votes. The procedures describe a 3-2-1 point system. Vote sheets are not published here.
- Firm headquarters, founding years, and marketing language. Those are not used as quality.
- Schematic-design cost performance. The cost chart is linked by MSBA and is not in this snapshot. It would also be a post-selection measurement.
- Square footage, enrollment, and new-versus-renovation scope, except where a future ingest adds them from a parsed public table.
- The full set of firms that applied but were never listed. Historical pages usually publish the ranked or interviewed set. Only the 2025-2026 chart consistently lists applicants who were not shortlisted. Shortlist probability is therefore not estimated for the historical archive.

## Firm names

Legal suffixes, punctuation, and accents are normalized automatically. A short reviewed alias list covers published spelling and name continuity such as SMMA and successive JCJ labels. Joint ventures and "in association with" listings keep separate identifiers. Medium-confidence aliases are counted in the quality summary and listed in `data/processed/firm_alias_audit.csv`. Near-duplicate names that were not merged are in `data/processed/near_duplicate_firms.csv`.

## Left censoring

The archive starts in 2007, and 2007-2008 are thin. A firm with no earlier row is an MSBA-record newcomer, not necessarily a new practice. Tests of newcomer status emphasize selections from 2012 onward.
