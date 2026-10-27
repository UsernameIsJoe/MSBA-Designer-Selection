# How hard to weight a firm's history

The stored winner model learns a weight for each piece of history, then uses those weights at full strength. Full strength loses to giving every firm on the shortlist the same chance. This note asks how far the weights should be turned up from that equal chance.

The practical rule, from the checks below: weight earlier wins on the same grade of school. If you use the broader history together, use it at half strength. Do not score a firm down just for having been a finalist more often. Do not add the adjustments for list length, year, and high school.

Rank 1 is the published order, not a signed contract. The stored model was not refit, and `reports/research_report.md` was not rewritten.

## How the dial works

Dial 0 gives every firm the same chance. Dial 1 is the weight the fit produced. The grid is 0, 0.25, 0.50, 0.75, 1, 1.25, and 1.5. A tie goes to the dial closer to an equal chance.

The weights are fit on the 120 rankings through 2015. The dial is chosen on the 54 rankings in 2016–2018. Both are then frozen and scored on the 99 rankings from 2019 on, the same later window as the stored model. The later window is not used to pick the dial. Intervals resample those 99 rankings, 2,000 draws, seed 20261020.

A check that this is the same score as the stored note: the seven-term logit fit through 2018 and used at full strength has log loss 1.077 on the later window. The published note reports 1.077.

Six scores were set up before that later window was opened. Two of them beat an equal chance by a margin the later window resolves, and one is reliably worse. The intervals are not adjusted for looking at six.

## What to weight

| History used | Dial chosen on 2016–2018 | Later log loss | Gain over an equal chance |
| --- | ---: | ---: | --- |
| Nothing. Every firm equal | 0 | 1.014 | — |
| Earlier rank-1 results only | 1.50, and still falling | 0.963 | 0.051 (−0.051 to 0.147) |
| Same-grade rank-1 results only | 0.75 | 0.948 | 0.066 (0.016 to 0.120) |
| Earlier finalist appearances only | 0 | 1.014 | 0 at the chosen dial. Full strength is worse by 0.042 (0.017 to 0.066) |
| No earlier appearance in this archive | 1.50, and still falling | 1.018 | −0.004 (−0.040 to 0.029) |
| Those four together | 0.50 | 0.956 | 0.058 (0.017 to 0.102) |
| The stored seven terms, including list length, year, and high school | 0.50 | 0.970 | 0.044 (−0.082 to 0.155) |

Same-grade wins are the one item that earns a weight on its own. The 2016–2018 window puts the dial at three-quarters. Full strength also beats an equal chance on the later window, by 0.073 (0.005 to 0.140). On 69 of the 99 later lists the firms differ on this count, so the score names a firm. It names the firm that was placed first on 38 of those 69.

The four items together want half strength. At half strength the later gain is 0.058 and the interval excludes zero. At full strength the gain is 0.066 and the interval includes zero (−0.020 to 0.147). The score names a firm on every later list and is right on 48 of the 99. The weights at half strength, fit through 2015, are about 0.05 for each earlier rank-1 result, 0.10 for each same-grade rank-1 result, −0.03 for each earlier appearance, and −0.32 for a firm with no earlier appearance. The appearance term is doing work only inside that package. On its own, the dial for appearances is 0.

Appearances on their own are the weight to leave off. Turning the fitted weight up makes the later forecast worse, and that interval excludes zero. The 2016–2018 window already gets worse at every step above zero.

Earlier rank-1 results on their own, and the newcomer flag on its own, were still improving at the top of the grid. That is not an estimated optimum. Neither gain is resolved on the later window. The newcomer flag names a unique firm on 1 of the 99 later lists, because several firms on a list usually share the same flag.

The stored seven-term score at full strength is the comparison in the original note, and it loses. Fit only through 2015, full strength is 1.166 on the later window. Half strength brings it to 0.970, and that gain's interval includes zero. The three extra adjustments are what make the score fragile. Leave them out.

## What this adds

The original note compared full-strength weights with an equal chance and found the full-strength score worse. The missing step was the dial. Same-grade wins, and the four history items at half strength, are the settings that beat an equal chance on lists the dial never saw. Counting appearances, and the longer score with list length, year, and high school, are not.

## Rebuild

`python scripts/build_weight_dial.py` rewrites `data/processed/weight_dial_scores.csv`, `weight_dial_weights.csv`, `weight_dial_curve.csv`, and `weight_dial_summary.json`. It stops if the seven-term full-strength loss leaves the neighborhood of the published 1.077. `python -m pytest tests/test_weight_dial.py` checks that dial 0 is an equal chance, that a positive win weight names the firm with more wins, and that a tie on the dial stays at zero.
