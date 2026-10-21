# Phase 4 — Applicant, interview, and rank-1 stages

## Research question

At which stage do firms with different histories and different present-day attributes succeed or fail: getting an interview, or ranking first once interviewed?

Rank 1 is the published panel order. It is not a signed contract. A higher rate at one stage is not evidence about design quality or about the panel's motives.

## Available evidence

The 2025–2026 meeting chart is the source that lists applicants who were not interviewed. It is `data/processed/chart_projects.csv` and `data/processed/chart_firms.csv`, taken from the Excel snapshot. Each live project has an application list, sometimes with a pre-interview number, and usually a shorter interview list with a final rank.

Historical HTML pages do not support this question. `data/processed/shortlists.csv` holds 185 posted lists and 543 firm rows. Almost all of those lists are unranked bullets. The pages describe them as the firms invited to interview, or as a qualified set, and they omit whoever was not advanced. Those 185 lists are not an applicant pool, and this phase does not turn them into an application rate.

The stored pipeline matches an applicant to a finalist by the printed string. Nine interview-list names on this chart are spelled differently from the application line and still resolve to the same firm. Matching on the firm id places every interview-list firm inside the applicant list. This phase reads the chart directly and does not rewrite the stored competitor table.

## Sample construction

The chart has 31 blocks. Two are cancelled meetings and are excluded. The remaining 29 projects fall into four groups.

| Status | Projects | Used for |
| --- | --- | --- |
| Completed interview ranking | 23 | Interview rate and rank-1 rate |
| Interview list with a blank final rank | 4 | Interview rate only. Ashley, Peabody, Pittsfield, Milton |
| Application order, no interview | 1 | Described separately. Springfield Gerena, three applicants, DiNisco ranked first |
| One applicant, no interview | 1 | Excluded from the rates. Triton Regional High School |

The interview rates use 144 applicant rows on 27 projects. The rank-1 rates use the 23 completed rankings: 125 applicants and 64 interviewed firms. 2026 is partial. The last completed ranking is Memorial Elementary School on 2026-09-22. Milton, on 2026-10-20, is an unfinished interview list.

Four projects interviewed every applicant: Brockton High School, Pollard Middle School, Essex Elementary School, and Charles S. Ashley (unfinished). The chart comment "Shortlisted all applicants" is printed on Brockton and Pollard. Two applicants are marked disqualified, one at Shaw-Taylor and one at Pittsfield. Both stayed off the interview list.

Earlier rank-1 results and earlier finalist appearances come from the 273-competition winner model, using dates strictly before the decision. The interview cut uses the application-review date. The rank-1 comparison uses the interview date. A result on the same calendar day does not count. History before August 2007 is absent. Sole-firm lists, including Triton, are not in that history.

Staff size and headquarters are the 2026 profiles from Phase 2. A band or a headquarters group is used only when the profile starts with "Verified." Joint-venture rows stay in the overall rates and stay out of the staff and headquarters tables. There is one such applicant, Mount Vernon Group with Moody Nolan at Brockton.

## Method

Three rates, each with its own denominator:

1. Application to interview: interviewed firms divided by applicants, on the 27 projects with an interview list.
2. Interview to rank 1: rank-1 firms divided by interviewed firms, on the 23 completed rankings.
3. Application to rank 1: rank-1 firms divided by applicants, on those same 23 rankings.

The chart also prints a pre-interview number. That number is reported as its own step, because several comments say the panel voted to interview the top of that order. A blank number is left blank. It is not coded as zero.

Groups are earlier rank-1 results (0, 1–2, 3 or more), same-type rank-1 results on a school whose name states a grade, 2026 staff band, and 2026 headquarters. Intervals resample projects, 2,000 draws, seed 20261020. A Wilson interval is stored beside them. Cells with fewer than about 15 rows are shown and not treated as a stable rate.

No multi-factor model is fit. The chart has 23 completed rankings.

Within a project that contains both a firm with an earlier rank-1 result and a firm without one, the excess is the share of interview seats, or of the rank-1 seat, going to the firms that already have a result, minus their share of the rows in that comparison.

## Results

Interview lists are shorter than applicant lists. On the 27 projects, applicants range from 3 to 9, with a median of 5. The interview list has a median of 3. Eighteen lists have three firms, seven have two, and two unfinished lists have four. Every completed ranking is a two-firm or three-firm list: 5 of the 23 are two-firm lists and 18 are three-firm lists. In this window the short list is a cut from a larger applicant pool.

Of 144 applicants, 76 were interviewed, 52.8% (interval 46.2% to 60.6%). On the 23 projects that did not interview everyone, the rate is 63 of 131, 48.1% (42.9% to 53.8%). Dropping the two disqualified applicants changes the 27-project rate to 76 of 142, 53.5%.

The pre-interview number lines up with that cut.

| Pre-interview number | Applicants | Interviewed | Rate |
| --- | --- | --- | --- |
| 1 | 29 | 29 | 100% |
| 2 | 29 | 27 | 93.1% |
| 3 | 19 | 12 | 63.2% (42.1% to 84.2%) |
| 4 or lower | 2 | 2 | Two rows |
| No number | 63 | 6 | 9.5% (0% to 23.5%) |
| Disqualified | 2 | 0 | Two rows |

Firms with three or more earlier rank-1 results receive a pre-interview number of 1 or 2 on 47 of 92 applications. Firms with none receive one on 7 of 38. Every one of those 7 was interviewed, and 45 of the 47 experienced firms numbered 1 or 2 were interviewed. The two firms numbered 2 who were not interviewed both had three or more earlier results. Once a firm has a pre-interview number of 1 or 2, the interview list does not cut the inexperienced firms any further.

Among 18 completed rankings with a single pre-interview leader, that firm was also rank 1 in 12 (interval 44% to 89%). The interview changed the leader at Joseph Case, Mosier, Winter Hill, Robinson, Shaw-Taylor, and Dale Street. Three other completed rankings had two firms tied for the pre-interview first number: Medford, Burncoat, and Shrewsbury. Brockton and Pollard printed no application numbers.

Earlier rank-1 results separate the interview rate. The 1–2 cell has 14 rows.

| Earlier rank-1 results | Interviewed / applicants | Rate | Interviewed and then rank 1 |
| --- | --- | --- | --- |
| 0 | 13 / 38 | 34.2% (22.2% to 48.6%) | 1 / 10 |
| 1–2 | 6 / 14 | 42.9% (23.1% to 63.6%) | 1 / 5 |
| 3 or more | 57 / 92 | 62.0% (53.7% to 71.4%) | 21 / 49, 42.9% (36.7% to 50.0%) |

The interview-rate intervals for zero and for three or more do not overlap. Inside the 22 projects that contain both kinds of firm, firms with an earlier rank-1 result take 11.6 points more of the interview seats than their share of the applicants (4.6 to 18.5). On the 19 projects that also cut the list, the excess is 13.4 points (5.2 to 20.8).

On the completed rankings, 22 of 23 rank-1 firms have at least one earlier rank-1 result on the stored firm id. Twenty-one have three or more. The firm with two is LaVallee Brensinger Architects at Robinson. The firm with zero is the chart spelling "Flansburg Architects" at Marguerite E. Peaslee, a separate id from Flansburgh Associates. Crediting that id, and three other chart spellings, with the history of the paired name moves four applicant rows. The zero-prior interview rate moves from 13 of 38 to 11 of 34. The one completed rank-1 result in the zero cell is the Peaslee spelling. The pairs are kept separate in the primary counts: Flansburg Architects with Flansburgh Associates, Turowski 2 with Turowski2 Architecture, and Machado Silvetti with Machado and Silvetti. LaVallee Brensinger without "Architects" already has its own earlier result and is not one of the four rows.

Among interviewed firms, the rank-1 excess for firms with an earlier result is 24.8 points (13.2 to 33.0) on 19 completed lists that mix both kinds of firm. The overall rank-1 rate among interviewed firms is 23 of 64. That rate sits near one in three because the completed lists have two or three firms. The group comparison is the informative one, and the zero-prior cell is 10 interviewed firms.

Same-type experience moves with the career total. Firms with three or more earlier rank-1 results and at least one of the same school type are interviewed on 48 of 75 rows, 64%. Firms with three or more and none of the same type are interviewed on 7 of 13 rows, 54%. The second cell is small. Winter Hill Innovation School does not state a grade, so its six applicants are left out of the same-type comparison.

Present-day staff size does not line up with either stage. Interview rates are 33 of 54 for 11–50 staff (61.1%, 47.9% to 74.1%), 13 of 19 for 51–200, 14 of 29 for 201 or more (48.3%, 34.4% to 61.5%), and 15 of 41 where the band is missing. The verified bands overlap. A larger 2026 headcount is not the group most often interviewed, and it is not the group most often ranked first after the interview (4 of 12, against 12 of 27 for 11–50).

Headquarters, under the city line used in Phase 2:

| Group | Interviewed / applicants | Rank 1 / interviewed |
| --- | --- | --- |
| Boston headquarters | 20 / 36, 55.6% (41.2% to 71.0%) | 5 / 17, 29.4% (14.3% to 43.8%) |
| Massachusetts outside Boston | 23 / 30, 76.7% (60.0% to 92.3%) | 11 / 19, 57.9% (40.0% to 76.5%) |

The interview intervals overlap. The rank-1 intervals meet at the edge. Grouping Cambridge and Somerville with Boston moves the rank-1 rates to 9 of 22, 40.9% (23.8% to 57.9%), and 7 of 14, 50.0% (28.6% to 72.7%). Those intervals overlap. Dated Boston branches are 4 interviewed firms out of 7 applicants. Out-of-state firms with no Boston office are 4 of 10. Those cells are too small to interpret.

## Uncertainty and robustness

The field-size description is a full count of the chart, not a sample estimate. The interview-rate gap between no earlier rank-1 result and three or more survives the project resampling, the removal of projects that interviewed everyone, and the four-row spelling sensitivity. The conditional rank-1 gap points the same way, and its zero cell is 10 firms, one of whom is the Flansburg spelling.

The pre-interview number accounts for most of the interview cut. Conditional on a number of 1 or 2, inexperienced firms are not dropped. The remaining discretion is at number 3 (12 of 19 interviewed) and among firms with no number (6 of 63).

Same-type experience, staff band, and the Boston city line do not add a stage pattern that this chart can separate from the earlier-rank-1 count or from the Cambridge boundary.

## Alternative explanations

Firms with many earlier rank-1 results are also the firms that apply often and the firms that receive a pre-interview number of 1 or 2. The interview list then follows that number. The excess inside mixed applicant pools says the gap is not only "those firms apply more." It does not say why the application order put them at the top.

A firm with no earlier result in this archive may have ranked first before August 2007. The chart window is 2025–2026, so that left censor is older here than it is for a 2012 comparison, and it is still present.

The 2026 staff band and office are current descriptions. A missing band is not a small firm. The lower interview rate in the missing group is consistent with infrequent and thinly documented names, which is the coverage pattern from Phase 2.

The city-line rank-1 gap lines up with where a few frequent practices are headquartered. Moving Cambridge and Somerville across the line removes the separation, as it did in Phase 2.

## Interpretation

On the 2025–2026 chart, the panel's interview lists are two or three firms drawn from applicant pools whose median size is five. That is the window in which a short published list can be compared with the applicant pool. It does not, by itself, explain the rise in two-firm lists in earlier years, because those years do not publish the applicants who were left off.

The stage at which earlier rank-1 results show up is the pre-interview order. Firms with three or more such results are numbered 1 or 2 on about half of their applications. Firms with none are numbered 1 or 2 on about one in five, and a firm with no number is rarely interviewed. The interview list then takes the numbered firms. After the interview, firms that already have a rank-1 result also take the top of the completed list more often than their share of the interviewed firms. Twenty-two of the 23 completed rank-1 results belong to a firm id with at least one earlier result in this archive.

Same-type school experience, 2026 staff size, and a Boston address do not mark a separate stage in this sample.

## Limitations

- The applicant pool is observed for this chart only. One hundred eighty-five earlier posted lists are interview lists, not applicant pools.
- Twenty-three completed rankings is a small set. The 1–2 win cell has 14 applications. The conditional zero-prior cell has 10 interviewed firms.
- Four chart spellings sit on a different firm id from a lookalike name. They are not merged. One of them is the only completed rank-1 result with zero stored history.
- Nine interview-list names differ in spelling from the application line. Firm-id matching keeps them in the pool.
- Same-type counts move with total rank-1 results. One project, Winter Hill, has no stated grade.
- Staff size and office location are 2026 fields. The headquarters contrast depends on the Cambridge line.
- Gerena has no interview, and Triton has one applicant. Four interview lists have a blank final rank.
- The inferred DSP roster is not used.
- Rank 1 is not a contract.

## Next research questions

The snapshot audit is `reports/05_panel_history.md`. The inferred roster is not a ballot and not an attendance record, and it was not used to explain these stage rates.
