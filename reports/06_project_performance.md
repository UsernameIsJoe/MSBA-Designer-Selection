# Phase 6 — Project performance feasibility

## Research question

Is a later rank-1 result associated with a measurable performance record on a firm's earlier MSBA school projects?

Rank 1 is the published order. It is not a signed contract. A cost figure is not architectural quality, and a cost figure dated after a selection cannot explain that selection.

## Available evidence

The files below were opened on 2026-10-21 from the public MSBA site. They were not copied into `data/raw`, so the pipeline manifest still records the cost chart as absent. The inspection counts are `data/processed/performance_source_inventory.csv`.

The designer construction cost chart is a one-page graphic.

| File | Window printed on the chart | Designer names in the text layer | Dollar amount for each designer |
| --- | --- | ---: | --- |
| 2026 annual update | Board approvals from 2021-01-01 through 2025-12-31 | 26 | Not text. A black line on an axis from $250 to $700 per square foot |
| 2025 update, file name `Rev2_250411` | Board approvals from 2020-01-01 through 2024-12-31 | 28, including one joint credit | Not text. Same axis |
| July 2016–June 2021 posting | Board approvals from 2016-07-01 through 2021-06-30 | 26, some names truncated in the text layer | Not text. Axis from $150 to $500. The Boston Josiah Quincy Upper School, by HMFH, is omitted from the drawing because it is above $500 per square foot |

Each chart says the line is the designer's average direct building cost for projects the Board approved in that window, from reconciled construction budgets at the end of schematic design. The average includes estimated direct building cost plus the applicable design-and-pricing contingency. It excludes special construction, demolition, hazardous-materials abatement, sitework, subcontractor bonds, insurance, general conditions, overhead and profit, the GMP fee, GMP contingency, escalation to the midpoint of construction, and alternates. The Tableau link on the DSP page is the same chart and was not downloaded.

The capital-planning cost page also posts project tables. The current schematic-design files, labeled as of the June 2026 Board meeting, have one column per project for elementary, middle, high, and middle/high schools whose estimated construction start is January 2014 or later. Counting the month-year tokens on the board-approval row gives 81, 32, 51, and 7 columns, 171 in total. The current bid files, for contracts awarded in January 2014 or later with an executed funding-agreement amendment, have 136 board-approval dates and 135 bid or GMP dates across those four school types. One elementary column has a board date and no bid date on that header row. Repair tables and the 15-page historical schematic file were not counted. A fee summary dated 04/29/2026 is a total by school type, not a firm history.

The project-information page describes pipeline status, an estimated bid schedule, and a consultant list updated for the August 26, 2026 Board meeting. Those are status reports. They were not used as a performance history.

The only cost field already inside the winner-model sample is the preselection construction-cost range on the 2025–2026 meeting chart. That range is the project's expected size before the ranking. It is not a record of how a firm's earlier project turned out.

## Sample construction

No analysis sample was built. A performance history for a selection on date T would need a project-level measure whose value was fixed before T, joined to the same firm id used in the ranking. The opened files do not provide that pair.

The model sample runs through 2026-09-22. Four of its 273 rankings fall after 2026-06-30, which is the vintage printed on the current schematic files. Eleven rankings fall in 2026.

## Method

The charts and the first page of each project table were read as text, with words grouped into visual rows so a header that sits on one line is counted once. Designer averages were not traced off the graphic. Uniformat rows were not turned into a firm score.

On the June 2026 elementary schematic file, the first column is South Hadley, Plains ES, board approval November 2012, assumed construction start May 2014, designer Jones Whitsett Architects, 63,377 square feet. That column's building subtotal is $14,664,281. Its design-and-pricing contingency is a separate row, $1,780,499. Its total construction cost, after markups and escalation, is $21,563,821. Those three numbers are different measures. The designer chart's definition matches none of them exactly: it is direct building cost plus part of the contingency, and it drops sitework and the markup rows.

The file's own note says the figures come from the MSBA's review of estimates, contracts, and other documents, are informational, and may have changed because of bids or contract amendments. Projects are omitted when the information was not available at generation. Districts may use a different school name than the report.

## Results

No association between earlier project performance and a later rank-1 result is estimated.

The public record does contain project-level cost sheets and a designer-level schematic-cost graphic. The graphic does not print the number that would be the covariate. The sheets print numbers as of June 2026, with an explicit warning that bids and amendments can change them. Schematic approval for a project comes after the designer is selected for that project, so the sheet can speak only to a later selection, and only if the sheet the panel could have seen is the sheet in hand. Four rankings in the model sample are dated after the June 2026 vintage. That is too small a window, and the vintage still mixes building type, new construction with addition and renovation, and calendar years of cost.

## Uncertainty and robustness

The column counts are layout counts. A header that wrapped onto a second line would be missed, and a footnote digit such as the "1" on one district name is not a project. The elementary bid file disagrees with itself by one column. Repair projects, the historical schematic file, and the August 2026 pipeline status reports are outside the count.

The 2025 chart's file name contains `250411`. That is not treated as a confirmed posting date.

## Alternative explanations

A firm with a lower schematic cost per square foot can be designing smaller or simpler buildings, working in a cheaper year, or sitting on a different scope. The chart's own filters for new construction versus addition and renovation, and for year, are not a project-level file. Reading a position on the graphic would not separate those factors, and it would not say how many projects sit behind the line.

Bid cost, schematic cost, and final construction cost answer different questions. A gap between them can be scope change, market escalation, or a changed design. The opened sheets keep those rows apart. Folding them into one performance score would erase that distinction.

## Interpretation

Repeated selection in this archive is not linked here to a measured record of how earlier schools performed. The designer chart is a current picture of schematic direct-building cost, drawn rather than tabulated. The project sheets are a June 2026 compilation that the publisher says can move after the bid. Either source would need a dated vintage and a project key before it could be used, without leakage, as something the panel could have known.

## Limitations

- The PDFs were read for structure and counts. They were not added to the raw snapshot.
- The Tableau workbook was not downloaded.
- Repair tables and the pre-2014 schematic file were not given project counts.
- Rank 1 remains the published order, not a contract, and a cost per square foot is not design quality.
- No public-records request was sent.

## Next research questions

A later study would need a saved copy of the project sheet as it stood before each selection, with one row per project, the designer in the same firm id used here, the board-approval date, the bid date, the final cost date, square footage, scope, and the cost row that matches the question. The synthesis of Phases 1 through 6 is `reports/MSBA_RESEARCH_SYNTHESIS.md`.
