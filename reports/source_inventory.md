# Source inventory and feasibility

Generated 2026-10-20 16:07 UTC.

Hashes cover the local snapshot. `local_mtime_utc` in `data/manifests/sources.csv` is the file modification time. It is not a separately logged download timestamp. Publication dates are left blank when the file does not state one.

- `dsp_landing` — Designer Selection Panel. Present: True. SHA-256: `f59146cf66990f57e3a9e6eb6f16ce286fccefeaa191c980314cbd2447f74bb5`. URL: https://www.massschoolbuildings.org/building/team/dsp
- `results_2007_2009` — DSP meeting results, 2007-2009. Present: True. SHA-256: `d978b0243ac41bb373be836b43c43a0c1c6fd5e6a0aeb563caf6745270b32032`. URL: https://www.massschoolbuildings.org/building/team/dsp/meeting_results/2007-2009
- `results_2010_2014` — DSP meeting results, 2010-2014. Present: True. SHA-256: `6a7f3a9e70788bf48c0ba6b0efc76d754e63a48aaab28ddd15e198def49aef24`. URL: https://www.massschoolbuildings.org/building/team/dsp/meeting_results/2010-2014
- `results_2015_2018` — DSP meeting results, 2015-2018. Present: True. SHA-256: `12f7beb9a654fe98f382bc1a79a8e7a21d132af434f174befc21b977f64fb50e`. URL: https://www.massschoolbuildings.org/building/team/dsp/meeting_results/2015-2018
- `results_2019_2024` — DSP meeting results, 2019-2024. Present: True. SHA-256: `8f5ae9c9ed5b766ffe45545b333c41b9782ef76f59ccc48e11b9a4fa8a160dd1`. URL: https://www.massschoolbuildings.org/building/team/dsp/meeting_results/2019-2024
- `chart_2025_2026` — DSP meeting result chart, 2025-2026. Present: True. SHA-256: `1f08420f500a606709d6fb1062970d2338904b339d64794900f58562d4e6b009`. URL: https://www.massschoolbuildings.org/sites/default/files/edit-contentfiles/DSP/DSP_Meeting_Results_Chart_October9.xlsx
- `dsp_procedures_pdf` — Designer Selection Panel procedures, revised January 2026. Present: True. SHA-256: `88c1b59cd26ed03da311a5c8f122a6e07f090511a726bf1599b1495a84419e2e`. URL: https://www.massschoolbuildings.org/sites/default/files/edit-contentfiles/DSP/DSP%20Procedures%20January%202026.pdf
- `dsp_process_html` — Designer selection process narrative. Present: True. SHA-256: `1acb2e7413101291b3ed81f180a796ca03c85bb9e5543f3ead05549a502146bf`. URL: https://www.massschoolbuildings.org/building/team/dsp
- `panel_members` — Designer Selection Panel membership. Present: True. SHA-256: `8dc8e0433d6d1ce3e5e198fd2c74d07a519fa4dfdaae37193dc9cbbcca11b9c8`. URL: https://www.massschoolbuildings.org/about/panels-dsp
- `cost_chart_pdf` — Designer construction cost chart. Present: False. SHA-256: `not hashed`. URL: https://www.massschoolbuildings.org/sites/default/files/edit-contentfiles/DSP/2026/DSP_Cost_Chart_2026_Annual_Update_Final.pdf
- `cost_chart_tableau` — Designer construction cost chart (Tableau). Present: False. SHA-256: `not hashed`. URL: https://info.massschoolbuildings.org/TabPub/DSPCostChart.aspx
- `project_info` — Capital planning project information. Present: False. SHA-256: `not hashed`. URL: https://www.massschoolbuildings.org/building/CP_Information_Project_Info
- `cost_data_portal` — Capital planning cost data. Present: False. SHA-256: `not hashed`. URL: https://www.massschoolbuildings.org/building/CP_Information_Cost_Data

## Availability

| Question | Status |
| --- | --- |
| Who was ranked, and in what order? | Available from the 2007-2024 HTML results and the 2025-2026 chart. |
| Who applied but was not interviewed? | Available for many 2025-2026 chart projects. Not consistently available before that. |
| Project district and school | Parsed from the result heading or the chart. |
| Grade level | Inferred from the school name. Unspecified when the name does not say. |
| Preselection construction-cost range | Printed on the 2025-2026 chart only. |
| Final or bid cost, cost per square foot | Not in the local snapshot. Not estimated. |
| Panelist-level votes | Not published in these files. Not invented. |
| Firm office location | Not in the DSP result files. Not estimated. |

## Feasibility

The winner-among-finalists question is feasible. Conditional probabilities sum to one inside each published choice set. The probability of being shortlisted from an unknown applicant pool is not feasible for the historical HTML. Cost-performance hypotheses are not feasible until the construction cost chart, or another public cost series, is parsed without treating post-selection costs as preselection information.
