# Phase 3 — Incumbency and specialization

## Research question

Once a firm has ranked first in this archive, does it rank first more often on later lists? Does experience with the same kind of school add anything beyond the total number of earlier rank-1 results?

Rank 1 is the published panel order. It is not a signed contract. A higher later rate is not evidence that the first result caused the later ones, and it is not evidence about design quality or about the panel's motives.

## Available evidence

The history is the winner-model sample from Phase 1: 273 multi-firm rankings, 794 finalist rows, 82 firms, 2007-08-07 through 2026-09-22. For a selection on a given day, every count uses only selections on earlier days. Two rankings on the same day do not update each other. The recomputed earlier rank-1 count, earlier finalist count, and wins in the previous three years match `data/processed/model_frame.csv` on every row.

School type is read from the school name. The stored category treated the substring "middle" as a middle school, so Middleborough High School was mixed, and it treated a vocational technical high school as both vocational and high, so those schools were mixed as well. This phase uses a corrected label and does not rewrite the stored category or the stored winner model.

| Stored label | Corrected label | Competitions |
| --- | --- | --- |
| Elementary, high, or middle, unchanged | Same | 212 |
| Mixed | Vocational | 16 |
| Mixed | Combined middle/high | 3 |
| Mixed | High (Middleborough High School) | 1 |
| Unspecified | High (South High Community School) | 1 |
| Unspecified, left unspecified | Unspecified | 18 |
| Unknown, left unknown | Unknown | 22 |

A name that says "school" but no grade stays unspecified. Edward Devotion School, Village School, and Essex North Shore Agricultural and Technical School stay unspecified. A municipality-only label such as "Chelsea, MA" stays unknown. Combined middle/high, vocational, elementary, middle, and high are the tracked types. That is 233 competitions. The other 40 are left out of the specialization models because a same-type count would be invented.

## Sample construction

Descriptive rates from 2012 onward count every finalist row in the 273. The 2007–2011 window is left-censored: a firm can have ranked first before the archive starts, and that history is blank here. The same contrast is also reported on the full archive so the 2012 cut is visible.

The within-list comparison keeps only competitions that contain at least one finalist with an earlier rank-1 result and at least one without. There are 68 such competitions from 2012 and 107 from the full archive.

Predictive comparisons train on known school types through 2018 and score 2019 through 2026. That test set has 93 competitions. It is smaller than the stored model's 99-competition test because competitions without a stated grade are excluded. Training drops a competition when the column being fit does not vary inside it, so the training count differs by specification. The test set does not. 2026 is partial, through 2026-09-22.

## Method

Four descriptions are kept separate.

1. On later appearances, the rank-1 rate by the number of earlier rank-1 results: 0, 1, 2, and 3 or more. Intervals are Wilson intervals. A firm's win rate before its first win is zero by construction, so that rate is not used as a before-and-after control.
2. Inside mixed fields, the share of rank-1 results going to firms that already have one, minus those firms' share of the field. The interval is a 2,000-draw bootstrap of competitions, seed 20261020.
3. Conditional logit scores on the 93 known-type competitions from 2019 on. The scores are earlier rank-1 results, earlier finalist appearances, a shrunk rank-1 rate `(wins + 0.5) / (finals + 1)`, same-type rank-1 results, same-type finalist appearances, and rank-1 results in the previous three and five years. Log loss is the average of minus the log of the probability assigned to the rank-1 firm. Lower is better. Equal probability is the reference. A difference is left minus right, so a negative number means the left score fits the test set better. Intervals resample the 93 test competitions and do not refit the coefficients.
4. A walk-forward score predicts each year from 2014 on using only earlier years, when that year has at least eight known-type competitions and at least 30 earlier training competitions. 2021 is omitted because it does not meet the test-size rule.

Present-day staff band and headquarters enter one sensitivity only. Missing staff and missing headquarters are coded as the reference group, so those coefficients are not effects. Phase 2 already found no staff-size gradient, and the Boston contrast depended on whether Cambridge and Somerville were grouped with Boston. Firm-specific residuals are the stored model result. They are not refit.

## Results

From 2012, the rank-1 rate on the current appearance rises with the number of earlier rank-1 results, then levels off.

| Earlier rank-1 results | Finalist rows | Rank-1 results | Rate | Wilson interval |
| --- | --- | --- | --- | --- |
| 0 | 82 | 16 | 19.5% | 12.4% to 29.4% |
| 1 | 51 | 16 | 31.4% | 20.3% to 45.0% |
| 2 | 43 | 17 | 39.5% | 26.4% to 54.4% |
| 3 or more | 412 | 155 | 37.6% | 33.1% to 42.4% |

The interval for zero earlier results and the interval for three or more do not overlap. The cells with one and two earlier results are small, and their intervals overlap both neighbors.

Inside the 68 mixed fields from 2012, firms that already have a rank-1 result take the top place 17.2 points more often than their share of the field (interval 7.8 to 26.0). On the full archive the excess is 14.0 points (5.7 to 22.6) across 107 competitions. Both intervals exclude zero.

On the 93 known-type competitions from 2019 on, equal probability has log loss 1.009 (0.970 to 1.045).

| Score, fit through 2018 | Test log loss | Coefficient on the added term |
| --- | --- | --- |
| Earlier rank-1 results | 0.958 | 0.120 |
| Earlier finalist appearances | 0.980 | 0.024 |
| Shrunk rank-1 rate | 0.980 | 1.149 |
| Rank-1 results and finalist appearances | 0.956 | appearances −0.010 |
| Rank-1 results and same-type rank-1 results | 0.952 | same-type 0.059; total wins 0.106 |
| Rank-1 results and wins in the previous five years | 0.956 | recent wins 0.007 |

The gap between earlier rank-1 results and equal probability is −0.051 (−0.150 to +0.052). The point estimate is better and the interval includes zero. The shrunk rate beats equal probability by 0.029 (0.001 to 0.057). That interval excludes zero. The margin is small.

Adding same-type rank-1 results improves the wins-only loss by 0.006 (−0.010 to +0.022). The interval includes zero. The two counts correlate 0.71, so they are not separate histories. Adding wins from the previous five years changes the loss by 0.0015, and that interval includes zero. Same-type finalist appearances have a coefficient of −0.024 and a worse test loss than wins alone. Wins from the previous three years have a coefficient of 0.025 beside a same-type term; the test loss is 0.948, still inside the range of the simpler scores.

Training only on 2012–2018, and still scoring 2019–2026, leaves the same pattern: wins-only loss 0.960 (coefficient 0.123) and wins plus same-type loss 0.954 (coefficients 0.111 and 0.049).

Among rows that already have a rank-1 result, the median time since that result is 1.21 years when the current row is rank 1 and 1.19 years when it is not.

Adding present-day staff bands and the Boston / rest-of-Massachusetts indicators moves the earlier-wins coefficient from 0.106 to 0.080. The same-type coefficient stays at 0.058. Test loss moves from 0.952 to 0.941. The improvement is 0.010 (−0.010 to +0.032) and includes zero.

The stored firm-effects model, which this phase does not refit, has out-of-sample log loss 0.941 against 1.077 for the experience logit and 0.979 for the shrunk rate, on that model's own 99-competition test. Nine firms have a residual interval that excludes zero and at least eight appearances. Those residuals are selection residuals.

Year-by-year walk-forward scores change order. Earlier wins beat equal probability in some years, including 2023 and 2025, and lose in 2019. Same-type wins help in 2017, 2023, and 2025 and hurt in 2018 and 2024. 2021 is omitted. 2026 is partial.

## Uncertainty and robustness

The within-list excess is the result whose interval excludes zero in both the 2012 cut and the full archive. The appearance-rate gradient is visible at the extremes and is imprecise in the middle. The out-of-sample gain from counting earlier wins, as opposed to giving every finalist an equal chance, is not resolved except for the shrunk rate, and that gain is about three hundredths of a log-loss point.

Same-type experience does not clear a loss comparison against total earlier wins. Recent wins do not clear a comparison against the career total. Present-day staff and headquarters do not clear a comparison against wins and same-type wins, and they are the wrong kind of variable for a historical claim. The late-start training window does not change the reading.

## Alternative explanations

Firms with several earlier rank-1 results are also the firms that keep appearing. The 3-or-more cell is 412 of 588 rows from 2012. A higher rate there can be the same firms being shortlisted again, a difference that existed before any of these rankings, or both. The within-list excess holds the field fixed and still finds a gap, so the pattern is not only "those firms show up more often." It does not say why the panel placed them first.

The archive starts in 2007. An "earlier rank-1 result" means one inside this file. A firm with a zero can have ranked first before August 2007. That is why the headline rates start in 2012, and why the full-archive excess is reported beside it rather than instead of it.

Same-type counts move with total wins. A positive same-type coefficient beside a still-positive total-win coefficient is compatible with a little extra weight on matching school type and with noise around one underlying record. The test-set comparison does not separate those readings.

## Interpretation

Firms that have already ranked first in this archive take the top place more often than the other finalists in the same list. From 2012 that excess is about 17 points, and the interval excludes zero. The rank-1 rate on later appearances is about 20% with no earlier rank-1 result in the archive and about 38% once a firm has three or more.

That association does not become a reliable out-of-sample forecast beyond a shrunk rate. Counting earlier wins beats an equal chance in the point estimate and does not beat it once the test competitions are resampled. The shrunk rate does, by a small margin. Matching the school type, counting only the last three or five years, and adding 2026 staff size and office location do not improve the forecast by a margin the test set can resolve.

The first observed win is not shown to cause the later ones. The comparison is across appearances with different histories, and across finalists in the same list. It is not a within-firm change measured against a pre-win win rate.

## Limitations

- History before August 2007 is absent. Subconsultants, under-threshold work, and model schools are absent.
- Forty competitions have no stated grade and are excluded from the specialization scores.
- Twenty-one competitions change label under the correction. The stored winner model still uses the old labels. This phase does not refit it.
- Same-type wins and total wins correlate 0.71.
- The within-list excess uses 68 competitions from 2012. Those are the lists that mix experienced and inexperienced finalists.
- Present-day staff and headquarters are 2026 fields. Missing values are coded as the reference group in the sensitivity, which mixes unlike firms.
- The inferred DSP roster is not used.
- 2026 is a partial year. 2021 is omitted from the walk-forward figure because fewer than eight competitions that year have a stated grade.
- Rank 1 is not a contract. Residuals are not quality and are not favoritism.

## Next research questions

Phase 4 can describe how applicant lists become shortlists and then final rankings, mostly from the 2025–2026 chart, with a denominator on each conversion. That is a different question from whether an earlier rank-1 result predicts the next one.
