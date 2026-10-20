# MSBA designer selection: research note

Generated 2026-10-20 16:07 UTC by `python -m msba_dsp.pipeline`. Figures below are computed from the local public snapshots. They are associations inside published finalist sets.

## Question

After conditioning on the published choice set, which observable firm histories are associated with being ranked first, and do those associations predict later competitions better than simple baselines?

This note does not treat a low predicted probability as evidence of improper conduct.

## Sample

The model sample contains **273** competitions and **794** finalist rows, from **2007-08-07** to **2026-09-22**. **82** firms appear. The mean choice set has **2.91** firms. **42** firms win at least once. The winner Herfindahl index is **0.045** and the five most frequent winners account for **0.348** of wins.

The in-sample logit is fit on every model competition. Out-of-sample scores for 2019 onward use a model fit only on competitions through 2018 (174 training competitions, 99 test competitions). Random splits are not used.

## Baselines and models

Choice-set log loss is the mean negative log probability of the firm that was ranked first. Lower is better. An equal-probability model on a three-firm field has a log loss near 1.10. Top-choice accuracy counts a competition only when one firm has a strictly higher probability than the others and that firm was ranked first. An equal-probability model therefore scores zero on accuracy, because it does not name a unique favorite. A baseline that piles probability on a frequent winner can have a high accuracy and a poor log loss when it is confidently wrong.

| model | sample | competitions | log_loss | top_choice_accuracy | brier |
| --- | --- | --- | --- | --- | --- |
| equal_probability | in_sample | 273 | 1.058 | 0.000 | 0.225 |
| prior_wins | in_sample | 273 | 2.426 | 0.436 | 0.288 |
| grade_wins | in_sample | 273 | 1.241 | 0.271 | 0.240 |
| shrunk_win_rate | in_sample | 273 | 1.057 | 0.392 | 0.219 |
| conditional_logit | in_sample | 273 | 0.999 | 0.491 | 0.207 |
| equal_probability | 2019_forward | 99 | 1.014 | 0.000 | 0.228 |
| prior_wins | 2019_forward | 99 | 3.158 | 0.495 | 0.314 |
| grade_wins | 2019_forward | 99 | 1.294 | 0.384 | 0.240 |
| shrunk_win_rate | 2019_forward | 99 | 0.979 | 0.424 | 0.213 |
| conditional_logit | 2019_forward | 99 | 1.077 | 0.495 | 0.227 |
| logit_plus_rating | 2019_forward | 99 | 1.048 | 0.465 | 0.224 |
| choice_normalized_gbm | 2019_forward | 99 | 1.018 | 0.455 | 0.226 |
| penalized_firm_effects | 2019_forward | 99 | 0.941 | 0.505 | 0.205 |


The conditional logit is the interpretable model. Its linear score uses prior wins, same-grade wins, prior finalist appearances, a newcomer indicator, and interactions of prior wins with field size, year, and high-school status. Project-only variables are not entered by themselves, because they do not vary among finalists.

Gradient boosting is trained through 2018 and then normalized so probabilities inside each later competition sum to one. Feature importance is not a causal effect. The Plackett-Luce rating is selection strength against other finalists. Penalized firm effects are residuals after the experience covariates, shrunk toward zero.

### Conditional-logit coefficients

Bootstrap percentile intervals, competition resample. A positive prior-wins coefficient means more earlier wins are associated with a higher selection probability inside the choice set.

| term | estimate | ci_low | ci_high | draws |
| --- | --- | --- | --- | --- |
| prior_wins | 0.087 | 0.033 | 0.150 | 35 |
| prior_grade_wins | 0.137 | 0.019 | 0.266 | 35 |
| prior_finals | -0.022 | -0.047 | -0.002 | 35 |
| newcomer | -0.412 | -1.196 | 0.209 | 35 |
| prior_wins_x_field | -0.047 | -0.157 | 0.050 | 35 |
| prior_wins_x_time | 0.005 | -0.106 | 0.078 | 35 |
| prior_wins_x_high | 0.007 | -0.091 | 0.085 | 35 |


## Hypotheses

| id | status | competitions | statement |
| --- | --- | --- | --- |
| H1 | inconclusive | 273 | Prior MSBA wins predict selection among finalists. |
| H2 | inconclusive | 24 | The association between experience and selection is stronger on larger projects. |
| H3 | supported | 273 | Same-grade experience predicts selection beyond total MSBA wins. |
| H4 | inconclusive | 204 | Firms with no observed MSBA finalist history have a different selection probability after experience counts. |
| H5 | inconclusive | 273 | The number of finalists changes the association between experience and selection. |
| H6 | supported | 99 | Some firms win more often than experience, grade history, and newcomer status predict. |
| H7 | inconclusive | 273 | The experience association changes across time. |
| H8 | inconclusive | 99 | A walk-forward competitive rating predicts later selections beyond raw experience counts. |
| H9 | inconclusive | 0 | Selection outcomes correlate with publicly measurable cost performance. |
| H10 | inconclusive | 273 | Recent firm award workload is associated with selection after total experience is included. |


### H1. inconclusive

Conditional-logit coefficient on prior wins is 0.087 (bootstrap interval 0.033 to 0.150). Out-of-sample log loss is 1.077 versus 1.014 for equal probabilities.

Limitation: The archive begins in 2007, so earlier careers are unobserved. The estimate is an association inside published finalist sets.

### H2. inconclusive

On the 24 competitions with a published range, the experience × log budget coefficient is -0.066 (interval -0.516 to 0.391).

Limitation: Historical result pages do not publish construction budgets. A high-school indicator is not treated as a cost measure.

### H3. supported

Grade-specific win coefficient 0.137 (interval 0.019 to 0.266) after controlling for total wins. Correlation with total wins is 0.58.

Limitation: Grade is parsed from the school name. Unspecified names are excluded from the grade count. This is not an independent specialty certification.

### H4. inconclusive

Full-sample newcomer coefficient -0.412 (interval -1.196 to 0.209). Refit on selections from 2012 onward: -0.114 (interval -1.379 to 0.516).

Limitation: Newcomer means no earlier finalist appearance in this public archive. It does not mean the firm is a new architecture practice. Pre-2007 MSBA work is invisible, so the 2012 refit is required before calling the result supported.

### H5. inconclusive

Coefficient on prior wins × (finalists − 3) is -0.047 (interval -0.157 to 0.050).

Limitation: Finalist count is a property of the published choice set. It does not say what would happen if a firm were added or removed.

### H6. supported

Out-of-sample log loss is 0.941 with penalized firm effects, 1.077 for the experience logit, and 0.979 for the shrunk win-rate baseline. The improvement over the experience logit is 0.137 (interval 0.027 to 0.251). Firms with a residual interval excluding zero and at least eight appearances: 9.

Limitation: Firm effects are procurement-selection residuals. They are not a design-quality score. Partial pooling pulls infrequent firms toward zero.

### H7. inconclusive

Coefficient on prior wins × (year − 2016) / 10 is 0.005 (interval -0.106 to 0.078). Early and late intervals disjoint: False.

Limitation: A change in a coefficient is a change in statistical association. It is not, by itself, a change in a written policy.

### H8. inconclusive

Adding the pre-period rating changes test log loss by 0.030 relative to the experience logit (interval 0.004 to 0.062). The rating model’s own test log loss is 1.048, compared with 0.979 for the shrunk win-rate baseline. Support requires an improvement on that simple baseline, not only on the logit.

Limitation: The rating measures historical success against other finalists. It is not an architectural quality rating. Future results are not used to build the rating for a test year.

### H9. inconclusive

The designer construction cost chart is linked by MSBA but is not in the local snapshot, and schematic-design budgets would be post-selection outcomes.

Limitation: No bid, schematic, or final-cost comparison is estimated. Cost efficiency is not scored.

### H10. inconclusive

Coefficient on wins in the previous three years, controlling for total prior wins, is 0.021 (interval -0.124 to 0.176).

Limitation: Recent wins are a public-award workload proxy, not a count of all active contracts. Institutional concentration is reported descriptively and is not given a causal interpretation.

## Unexpected model outcomes

17 competitions are listed in the dashboard where the walk-forward model assigned the eventual top-ranked firm a probability of 0.15 or less and preferred someone else. The model for year Y is fit only on earlier years. These are unexpected model outcomes. They are not findings of bias, favoritism, or misconduct. Missing interview evidence is the first explanation to consider.

## Reading for firms preparing an MSBA submission

Prior MSBA wins do not yet clear the bar this project set for a stable out-of-sample claim. Firms should treat win counts as a descriptive history, not as a forecast.

The DSP's published criteria also include past performance on budget and schedule, current workload, personnel, consultants, and proximity or willingness to attend local meetings. This dataset measures the selection outcome and the firm's earlier MSBA finalist record. It does not measure those other criteria. Architectural design quality is **not directly measured**.

## Updating

Replace or add the HTML and Excel snapshots in `data/raw`, keep the source pages listed in `src/msba_dsp/ingestion/sources.py`, and rerun the pipeline. New result pages should be added as new snapshots rather than overwritten without a hash. If a source disappears, the previous hashed snapshot remains the estimation file and the manifest shows which sources are absent.
