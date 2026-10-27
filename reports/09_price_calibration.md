# Pricing the published order

## Research question

If earlier rank-1 counts are turned into a price on each published list, the way a field is priced before a race, does that price match how often the firm is actually placed first?

A price is a forecast. It is not a design score, and it is not a statement about how the panel should have voted. Rank 1 remains the published order. The district awards the contract. The stored winner model was not refit.

## The price

On a list, firm \(i\) is given strength \((\text{earlier rank-1 count}_i + 1/2)\) raised to an exponent, and the price is that strength divided by the sum of the strengths. The prices on a list add to one. Exponent 1 is proportional to the count. Exponent 0 is an equal chance, because every firm then has strength 1. The half-count is the same additive constant already used in the shrunk win rate. It was not fit.

Counts use strictly earlier calendar dates. Two rankings on the same day do not update each other. Rebuilt counts match `model_frame.csv` on all 794 finalist rows: prior wins, prior finalist appearances, published rank, and the rank-1 flag.

The description window is 2012 through 2026-09-22, 204 rankings and 588 finalist rows. The archive starts in 2007, so a count from the first years is a poor measure of who had already ranked first. The exponent is chosen on the 105 rankings from 2012 through 2018. It is scored on the 99 rankings from 2019 on, the same later window as the stored model. The grid runs from 0 to 2 in steps of 0.05. The chosen exponent is the smallest grid point with the lowest mean log loss on the earlier window. Intervals resample rankings, 2,000 draws, seed 20261020.

The equal-chance log loss on the 99 later rankings is 1.014321, and the shrunk-rate log loss is 0.978567. Both match the stored prices `p_equal` and `p_rate` in `model_frame.csv`.

## The firm with the most earlier rank-1 results

A list has a favorite when one firm has strictly more earlier rank-1 results than every other firm on that list, and that count is at least one. That is 185 of the 204 lists. The other 19 are ties, or lists on which nobody has an earlier rank-1 result in this archive.

The favorite is placed first on 94 of those 185 lists, 50.8%. Its share of the seats averages 35.8%. The excess is 15.1 points (8.0 to 21.9). On two-firm lists the favorite is first on 20 of 29, an excess of 19.0 points over one half (1.7 to 36.2). On three-firm lists it is first on 72 of 152, an excess of 14.0 points over one third (6.1 to 21.9). Four four-firm lists are too few to read.

## The proportional price is too sharp

Exponent 1, on the 588 finalist rows from 2012 on, puts too little price on the longshot and too much on the favorite. The gap is the rank-1 rate minus the average price in the bin.

| Price | Finalists | Average price | Ranked first | Gap |
| --- | ---: | ---: | ---: | --- |
| Under 20% | 170 | 10.2% | 22.9% | +12.8 points (6.8 to 18.8) |
| 20% to 35% | 149 | 27.0% | 32.2% | +5.3 points (−1.6 to 12.2) |
| 35% to 50% | 129 | 42.2% | 34.9% | −7.3 points (−14.4 to −0.2) |
| 50% to 65% | 75 | 57.3% | 41.3% | −16.0 points (−26.8 to −4.7) |
| 65% or higher | 65 | 75.7% | 63.1% | −12.7 points (−24.8 to −1.3) |

Four of the five intervals exclude zero. The 20% to 35% band includes zero. From 35% up, the firm is placed first less often than the price. The proportional price's log loss on all 204 rankings is 1.066, against 1.048 for an equal chance. The equal chance is ahead by 0.018 log-loss points, and that interval includes zero (−0.075 to 0.117). The shape is wrong even though the average score is not resolved.

Among the 185 favorites, 94 were priced at 60% or more. They were placed first 51 times, 54.3%, against an average price of 71.5%. Inside that group, a price from 60% to 75% won 30 of 65 times, and a price of 75% or more won 21 of 29. Eight of those 29 high prices lost.

Three of the losses recompute by hand from the stored counts.

- North Andover, Kittredge Elementary, 2024-03-12. Mount Vernon Group had 9 earlier rank-1 results. Machado and Silvetti and CBT/Childs Bertman Tseckares had none. Strengths 9.5, 0.5, and 0.5 sum to 10.5. The price is 9.5/10.5 = 90.5%. Mount Vernon finished second.
- Fall River, Diman Regional Vocational Technical High School, 2020-02-25. Drummey Rosane Anderson had 17. Kaestle Boos had 4. The price is 17.5/22 = 79.5% on a two-firm list. Drummey Rosane Anderson finished second.
- Boston, Dearborn School, 2013-01-08. The stored label is "Boston, MA – Dearborn School." Symmes Maini & McKee had 9, Jonathan Levi had 1, and Leers Weinzapfel had none. The price is 9.5/11.5 = 82.6%. Symmes Maini & McKee finished third.

The full list of favorites priced at 75% or more who were not placed first is `data/processed/price_high_losses.csv`.

## A softer exponent on the later window

The earlier window's log loss is lowest at exponent 0.35 (1.043). Exponent 0.40 is 1.044. Exponent 1 is 1.122, which is worse than the equal chance at 1.080. The fit-window gain of 0.35 over an equal chance is 0.036 log-loss points, and that interval includes zero (−0.015 to 0.087). The exponent is the point-estimate minimum. The earlier window by itself does not resolve it.

On the 99 rankings from 2019 on:

| Rule | Exponent | Log loss | Gain over an equal chance | Brier gain |
| --- | ---: | ---: | --- | --- |
| Equal chance | 0 | 1.014 | — | — |
| Proportional to the count | 1 | 1.008 | 0.007 (−0.133 to 0.142) | 0.008 (−0.024 to 0.037) |
| Shrunk win rate, the stored baseline | — | 0.979 | 0.036 (−0.039 to 0.107) | 0.014 (−0.007 to 0.034) |
| Square root | 0.5 | 0.946 | 0.068 (−0.003 to 0.138) | 0.019 (0.002 to 0.036) |
| Grid minimum from 2012–2018 | 0.35 | 0.950 | 0.064 (0.016 to 0.111) | 0.017 (0.004 to 0.030) |

The grid minimum beats an equal chance on both scores. The interval on the log-loss gain excludes zero, and so does the interval on the Brier gain. The proportional price does not beat an equal chance on either score.

The square root sits in the flat part of the earlier curve. Its later log-loss interval includes zero by a few thousandths. Its Brier interval excludes zero. The two scores do not agree on that round exponent, so it is not a second finding. Against the grid minimum, the square root is 0.004 log-loss points lower, interval −0.017 to 0.023.

The grid minimum is also 0.029 log-loss points ahead of the stored shrunk rate. That interval includes zero (−0.039 to 0.097). The shrunk rate already divides by earlier appearances, which damps a raw count in a different way. On these 99 rankings the two dampings are not separated. An earlier note found a shrunk-rate gain over an equal chance whose interval excluded zero on 93 known-type rankings. This note uses all 99 later rankings, and on that set the shrunk-rate interval includes zero. The two statements are about different sets.

The stored firm-effect log loss on this later window is 0.941. That model was not refit here. It uses firm identity. This price does not.

## The lead is not a spread

The favorite's lead is its earlier rank-1 count minus the next firm's count.

| Lead | Lists | Placed first | Excess over the seat |
| --- | ---: | --- | --- |
| 1 earlier win | 28 | 11, 39.3% | 4.8 points (−12.8 to 22.0) |
| 2 earlier wins | 34 | 19, 55.9% | 20.6 points (3.4 to 38.7) |
| 3 or 4 earlier wins | 35 | 14, 40.0% | 6.4 points (−10.0 to 21.9) |
| 5 or more earlier wins | 88 | 50, 56.8% | 19.6 points (9.5 to 29.6) |

A lead of five or more clears its seat share, on 88 lists. A lead of one does not. A lead of two clears and a lead of three or four does not, so the steps are not ordered. The number of wins in the lead is not itself a price.

## Where the favorite finishes when it is not first

On the 80 three-firm lists the favorite lost, it finished second 44 times and last 36 times. The share finished second, given that it was not first, is 55% (43.5 to 65.5). An exchangeable pair of opponents would put it second half the time. The interval includes one half. The lead shows up in the top place more than in the order underneath.

On 66 of those 80 losses, a single other firm held the next-highest earlier count. That firm was placed first 38 times, 57.6% (45.5 to 69.7), against one half for the two firms who were not the favorite. The interval includes one half. Fourteen losses had a tie for that next count and are not in the rate.

A firm sat on two lists the same day on 3 firm-days from 2012 on. That is too few for a same-day doubleheader rate.

## What the price does not say

The panel does not publish a probability. A price that is too high is a property of this forecast. Firms with long records in this archive are the ones who reach a 70% or 90% price, and the archive starts in 2007, so some of that record is left-censored. The same firms also differ in staff, office, and the schools they have already done. Those differences were tested in the earlier notes and were not resolved as separate forecasts. This note does not reopen them.

Four rankings have four firms. Near-duplicate names that were left unmerged can move a few counts. Rank 1 is still not the signed contract. No ballot or point total was used, so there is no margin of victory beyond second place and last place.

## Rebuild

`python scripts/build_price_calibration.py` rewrites the tables in `data/processed/price_*.csv` and `price_summary.json`. It checks the rebuilt counts and the two stored prices before it writes. `python -m pytest tests/test_price_calibration.py` checks the arithmetic: a nine-win favorite against two firms with none is priced at 9.5/10.5, exponent 0 is an equal chance, and a same-day rank-1 result does not change the other list that day.
