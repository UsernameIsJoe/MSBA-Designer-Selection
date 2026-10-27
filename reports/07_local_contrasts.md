# District history, chart cost, and spelling pairs

Three checks that use only the result lists, the 2025–2026 chart, and the near-duplicate file already in the project. Rank 1 is the published order, not a signed contract. Firm ids are not merged, and the stored winner model is not refit. Intervals resample lists or projects, 2,000 draws, seed 20261020.

## The district’s earlier designer

From 2012 through 2026-09-22 there are 204 rankings and 166 district strings. Thirty-two of those strings appear on more than one ranking. A firm is a district incumbent on a list when that same firm id ranked first for that same district string on a strictly earlier date. Two rankings on the same day do not update each other.

Thirty-one lists contain such a firm. That firm is ranked first on 22 of them, 71.0% (interval 54.8% to 87.1%). Its share of the seats on those lists averages 35.5%. The excess, the rank-1 share minus the seat share, is 35.5 points (19.4 to 50.5). The interval excludes zero. The 22 wins are spread across 12 firms. Lamoureux Pagano and DiNisco each account for four.

One of the 31 is the Springfield Gerena application ranking, which the chart records without an interview. Dropping it leaves 30 lists and an excess of 34.4 points (18.3 to 49.5). The interval still excludes zero.

This does not explain a switch toward a firm with no earlier rank-1 result. Of the 68 lists that contain both kinds of firm, only 7 also contain the district’s earlier designer. That cell is below the pre-set size of 15, so no rate was estimated for it.

Three 2016 school names place the town after a comma, and the stored district field is the fragment “MA)” for Harvard, Tisbury, and Clarksburg. Harvard and Tisbury share that fragment on 2016-12-06. None of the 31 lists uses that fragment.

## Construction-cost band and the interview

The source is the printed range on `chart_projects.csv`. The midpoint of the range is the project’s size. The cut is $100 million, a round threshold on those printed ranges. Historical HTML pages have no budget and are not in this comparison. Two disqualified applicants are excluded. The interview outcome uses the application-review date for earlier rank-1 results.

| Midpoint | No earlier rank-1 result | One or more earlier rank-1 results |
| --- | --- | --- |
| Under $100 million | 6/16, 37.5% (14.3% to 61.5%), 9 projects | 22/41, 53.7% (42.0% to 66.7%), 10 projects |
| $100 million or more | 7/20, 35.0% (17.6% to 52.9%), 13 projects | 41/65, 63.1% (52.6% to 76.2%), 17 projects |

For firms with no earlier rank-1 result, the interview rate on the larger projects minus the rate on the smaller projects is −2.5 points (−33.9 to +25.7). Four projects interviewed every applicant. Dropping them changes the difference to −5.6 points (−34.6 to +21.7). Both intervals include zero. The descriptive slice at $200 million or more is 1 interview out of 3 applicants.

Firms that already have a rank-1 result are interviewed more often in both bands. The chart’s cost band does not separate the firms that do not.

## Spelling pairs

`near_duplicate_firms.csv` has 11 pairs. Eight resolve to two firm ids and are spelling or suffix differences, including the missing ampersand in Caolo & Bieniek, the missing word in LaVallee Brensinger, and Bertman versus Bertram in the CBT name. Two are teams and stay out of the spelling pool: Miller Dyer Spears with Sasaki, and William Rawn with Arrowstreet. Perkins Eastman against Perkins Eastman DPC is ambiguous, because the DPC row’s own alias list includes the bare name “Perkins Eastman,” so that name matches two ids.

Recounting the 16 rank-1 results from 2012 that had no earlier rank-1 on their own id, 15 remain first results after the spelling pool. The exception is LaVallee Brensinger on 2023-11-21, which picks up the 2019-12-06 rank-1 result of LaVallee Brensinger Architects. Pooling the two team lines as well would also give Miller Dyer Spears / Sasaki the three earlier rank-1 results of Miller Dyer Spears, and the count would fall to 14. That pooling was not used.

Flansburg Architects, JCJ Architecture, P.C., and Jones Whitsett with SMMA are not pairs in the near-duplicate file. They stay separate ids.

## What this leaves in place

A district’s earlier designer, when that firm is back on the list, is ranked first well above its share of the seats. The printed construction-cost band on the 2025–2026 chart does not change the interview rate of firms with no earlier rank-1 result. Pooling the flagged spellings removes one of the 16 first rank-1 results. None of the three is a measure of design quality.
