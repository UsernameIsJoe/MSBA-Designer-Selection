# Phase 2 — Firm characteristics and selection outcomes

## Research question

What kinds of firms are more successful within published finalist groups?

The characteristics examined here are staff size, headquarters and Boston-office status, founding year, and a few coarse combinations of those fields. Success means rank 1 inside a published multi-firm list. It does not mean a signed contract.

## Available evidence

Company profiles live in `data/reference/firm_company.csv` and are joined onto `data/processed/firms.csv`. Every filled staff figure is marked `2026/latest available`. Headquarters and Boston-office notes are from the same present-day research pass. Founding year is a year, so age at a past selection can be calculated from it. Current staff size cannot be rolled backward into a historical headcount, and this phase does not do that.

Verification in the model sample of 82 firms: 36 profiles start with "Verified," 22 are unverified, 12 are blank, 11 are joint or tied submissions, and 1 is partial. Staff bands, headquarters groups, and ages are taken only from profiles that start with "Verified." The partial Moody Nolan row, whose Boston branch is described as "if confirmed," stays unknown.

Joint-venture rows are left out of the comparisons. That removes 6 finalist rows and leaves 788 rows, 76 firms, and the same 273 competitions. One rank-1 result in those competitions belongs to a joint venture, so the attribute tables account for 272 rank-1 results.

## Sample construction

The competitions are the Phase 1 winner-model sample: at least two firms and one top-ranked firm, from 2007-08-07 through 2026-09-22.

A staff value is placed in a band only when the recorded text falls in a non-overlapping interval. No range is replaced by its midpoint.

| Recorded text | Band used |
| --- | --- |
| 11–50, and a stated figure of about 20 | 11–50 |
| 51–200, and about 180 | 51–200 |
| 201–500, about 230, and 399 | 201–500 |
| About 1,000 | 501–1,000 |
| 1,001–5,000, and about 1,800 | 1,001+ |
| 50+, blank, or unverified | Missing |

"50+" overlaps every band above 50, so Tecton stays out of the size comparison. A sensitivity drops every point estimate and keeps only the published ranges. Another sensitivity moves "about 1,000" into 1,001+.

Headquarters, for a selection in year Y:

| Group | Rule |
| --- | --- |
| Boston headquarters | Headquarters text is Boston or Charlestown, or the role says a Boston neighborhood headquarters |
| Massachusetts outside Boston | Any other Massachusetts headquarters, including Cambridge and Somerville |
| Out-of-state, Boston branch open | The profile gives an opening year and Y is on or after that year. JCJ from 2010. LaVallee Brensinger from 2013 |
| Out-of-state, no Boston office | The profile says no Boston office was confirmed, or the dated branch had not opened yet |
| Branch timing unknown | A Boston branch is mentioned without a year. Perkins+Will, Perkins Eastman, and SLAM. They are not put in the open-branch group |
| Unknown | No verified location, or the branch is only "if confirmed" or "if active" |

Age at selection is the selection year minus the recorded founding year. A founding year after the selection is left blank. The three firms that reach age 75 inside this archive are Drummey Rosane Anderson, JCJ, and Perkins+Will.

## Method

Each comparison is inside the published choice set.

For staff size, the sample is the 219 competitions in which the rank-1 firm and at least one other finalist have a band. In 120 of those, one band is strictly the highest. The statistic is the share of those 120 in which the rank-1 firm holds that unique highest band, minus the share expected if the rank-1 firm were a random banded finalist in the same list. A second check is a conditional logit, fit only on the 124 competitions where the collapsed groups 11–50, 51–200, and 201+ are not all the same. The reference group is 11–50. The penalty is 0.0001, for numerical stability.

For headquarters, the sample is the 205 competitions with at least two finalists in the four primary groups and a rank-1 firm in one of those groups. The statistic is the rank-1 frequency of a group minus that group's share of the located finalists, averaged across those competitions.

For age, the same unique-maximum comparison asks whether the rank-1 firm is the unique oldest researched finalist. The conditional logit uses age minus the field mean, in units of 10 years, on 213 competitions where at least two finalists have a founding year and the ages differ.

Intervals are competition bootstraps with seed 20261020. Size and age contrasts use 2,000 draws. The logits use 400 draws. These intervals describe the observed lists. They are not effects of changing a firm's staff or office.

Rebuild with:

```powershell
python scripts/build_firm_characteristics.py
```

## Results

### Coverage

Profiles are concentrated in the firms that appear often.

| Attribute | Firms | Finalist rows | Share of the 788 rows |
| --- | ---: | ---: | ---: |
| Present-day staff band | 35 | 638 | 81% |
| Primary headquarters group | 32 | 603 | 77% |
| Founding year | 33 | 622 | 79% |
| Nationwide offices recorded as "Yes" | 5 | — | — |

Thirty-five of 76 firms have a staff band, but those firms account for 638 rows. One hundred fifty-two competitions have a band for every finalist. Two hundred nineteen have a band for the rank-1 firm and at least one rival. In 17 further competitions at least two finalists have a band and the rank-1 firm's size is blank. Figure: `reports/figures/02_attribute_coverage.png`.

### 2A. Current staff size does not separate the rank-1 firm

| Present-day band | Firms | Finalist rows | Rank-1 results |
| --- | ---: | ---: | ---: |
| 11–50 | 23 | 448 | 170 |
| 51–200 | 6 | 108 | 39 |
| 201–500 | 3 | 51 | 20 |
| 501–1,000 | 1 | 13 | 6 |
| 1,001+ | 2 | 18 | 5 |

In the 120 competitions with a unique highest band, the rank-1 firm holds that band 36.7% of the time. A random banded finalist would hold it 39.4% of the time. The gap is −2.8 percentage points, with interval −11.3 to +6.0. The conditional logit agrees. Relative to a firm in the 11–50 band, the 51–200 coefficient is −0.111 (interval −0.603 to 0.359) and the 201+ coefficient is 0.023 (interval −0.486 to 0.471), on 124 competitions and 329 rows.

The gap stays near zero, with an interval that includes zero, when point estimates are dropped, when "about 1,000" is counted with 1,001+, when the six inferred-order rankings are dropped, and when 2012–2018 is estimated separately from 2019–2026. The 2019–2026 point estimate is −6.2 points (interval −18.6 to +7.0). The covariate in both periods is still the 2026 band.

By school name, the cells do not show one size gradient. Elementary lists: 72 rank-1 results out of 184 rows in the 11–50 band, 24 of 52 in 51–200, and 9 of 28 in 201+. High-school lists: 34 of 92, 5 of 22, and 13 of 28. Middle-school lists are smaller still (24 of 62, 3 of 16, and 2 of 8). The 201+ high-school cell is three firms' present-day bands, not a separate size effect.

Nineteen competitions have both a published cost range and two banded finalists, and 12 of those have a unique highest band. That subset is too small to support a claim about project budget. Figure: `reports/figures/02_staff_bands.png`.

### 2B. A Boston-city gap appears, and it depends on where Cambridge is placed

On the 205 comparable competitions, rank-1 frequency minus field share is:

| Group | Firms in the count | Finalist rows | Rank-1 results | Excess | Interval |
| --- | ---: | ---: | ---: | ---: | --- |
| Boston headquarters | 14 | 225 | 68 | −6.9 points | −11.9 to −1.9 |
| Massachusetts headquarters outside Boston | 13 | 281 | 127 | +8.5 points | +3.3 to +13.5 |
| Out-of-state, dated Boston branch already open | 2 | 36 | 11 | −1.9 points | −4.1 to +0.2 |
| Out-of-state, no Boston office | 5 | 61 | 23 | +0.2 points | −3.0 to +3.4 |

Firm counts are not a partition. JCJ and LaVallee Brensinger change groups in the year their Boston branch is recorded as opening.

The Massachusetts-outside group includes Cambridge. HMFH has 19 rank-1 results in 30 rows, and Symmes Maini & McKee has 20 in 39. Somerville adds Johnson Roberts, with one row and no rank-1 result. When Cambridge and Somerville are coded with Boston, the Boston excess becomes −1.5 points (interval −5.9 to +3.7) and the rest-of-Massachusetts excess becomes +3.1 points (interval −2.0 to +7.6). Both intervals include zero. The city-line result does not survive that boundary.

Crediting undated Boston branches does not produce a branch association. On 218 competitions the open-branch excess is −2.6 points (interval −5.5 to +0.4). Five verified firms are recorded as having nationwide offices. Their combined finalist count is small, and no nationwide coefficient is estimated. Project-reach sentences in the company file are not used as a variable. Figure: `reports/figures/02_geography_excess.png`.

### 2C. Older firms do not rank first more often than the other finalists their age is known for

| Age at the selection | Firms that contribute a row | Finalist rows | Rank-1 results |
| --- | ---: | ---: | ---: |
| Under 25 | 8 | 105 | 42 |
| 25–49 | 20 | 255 | 96 |
| 50–74 | 13 | 177 | 68 |
| 75 or older | 3 | 85 | 32 |

On 211 competitions with a unique oldest researched finalist, that firm is rank 1 39.8% of the time, against a 40.3% random baseline. The gap is −0.5 points (interval −7.0 to +6.0). The rank-1 firm is older than the mean of the other researched finalists in 50.2% of 213 competitions (interval 43.7% to 56.8%). The conditional-logit coefficient is −0.013 per 10 years of age relative to the field (interval −0.096 to 0.065).

The 75-or-older rows are Drummey Rosane Anderson, JCJ, and Perkins+Will. An age gradient estimated from that bin would be a statement about three firms.

### 2D. Combined profiles repeat the headquarters split

| Profile | Firms | Finalist rows | Rank-1 results |
| --- | ---: | ---: | ---: |
| Massachusetts outside Boston, 11–50 staff | 11 | 241 | 107 |
| Boston headquarters, 11–50 staff | 11 | 197 | 60 |
| Massachusetts headquarters, including Boston, 51 or more staff | 5 | 68 | 28 |
| Out-of-state, no Boston office | 4 | 59 | 23 |
| Out-of-state, dated Boston branch | 2 | 36 | 11 |

The two large profiles are the same contrast as the headquarters result, restricted to the 11–50 band. No additional interaction model is fit. The dated-branch and 51-or-more profiles are a handful of firms.

## Uncertainty and robustness

The size and age intervals include zero under the primary rule and under the size sensitivities that were estimated. The headquarters intervals exclude zero only under the strict city boundary. Moving Cambridge and Somerville into the Boston group removes that exclusion. Branch timing, whether limited to dated openings or expanded to undated claims, does not show an association whose interval excludes zero.

The logit draws that failed to converge are omitted. The age interval uses 397 of 400 draws. The staff-band interval uses all 400.

## Alternative explanations

A null size result can mean that present-day headcount is unrelated to these rankings, or that headcount in 2026 is a poor record of headcount in 2009. Those two readings cannot be separated with this file. The same limit applies to a current office.

The Boston-city deficit lines up with who is on each side of the city line. Cambridge holds two firms with high rank-1 counts. Waltham, Worcester, Framingham, and Wakefield remain outside Boston even in the inner-core check, and after that check the interval includes zero. The pattern is consistent with a few frequent firms, not with a general penalty for a Boston address.

Firms without a profile are mostly infrequent finalists. The comparisons describe researched firms. They do not describe the firms that were left blank.

## Interpretation

Inside published finalist lists, the 2026 staff band of a firm does not identify the rank-1 firm beyond chance. Age at selection, calculated from a recorded founding year, also does not. A difference between Boston-city headquarters and other Massachusetts headquarters is visible and is sensitive to whether Cambridge is called Boston. Out-of-state firms with a documented Boston branch are too few, and their interval includes zero.

None of these associations is a historical effect of hiring, opening an office, or aging. None is evidence about design quality or about the panel's motives.

## Limitations

- Staff size and office location are 2026 descriptions.
- Forty-one firms in the comparison file have an unknown headquarters group. They contribute 149 rows.
- Eleven near-duplicate names remain split, so a few rows may sit on the wrong firm id.
- Joint ventures are excluded rather than assigned a parent firm's headcount.
- Large-staff, nationwide, and dated-branch cells contain one to five firms.
- School type is still parsed from the school name.
- Cost ranges exist for a thin slice of the archive.
- The inferred DSP roster is not used.

## Next research questions

Phase 3 can use prior rank-1 results and finalist appearances, which are dated and can be restricted to earlier competitions. Present-day staff size and office should stay out of that model, or enter only with the missingness and the Cambridge boundary shown here. Specialization by school type is the other half of Phase 3, and it has to be checked against the total prior-win count rather than treated as a new firm attribute.
