# MSBA Designer Selection Panel — collected records

Downloaded 2026-10-20 from the Massachusetts School Building Authority site. This folder holds the public result lists and the reference documents needed to judge whether those records can support five questions. It does not answer the questions.

## What was collected

| File | What it is |
| --- | --- |
| `raw/DSP_Meeting_Results_Chart_2025-2026.xlsx` | Official chart linked from the Designer Selection Process page. Source file name: `DSP_Meeting_Results_Chart_October9.xlsx`. |
| `raw/results_2007-2009.html` | Posted meeting results, 2007-08-07 through 2009. |
| `raw/results_2010-2014.html` | Posted meeting results. |
| `raw/results_2015-2018.html` | Posted meeting results. |
| `raw/results_2019-2024.html` | Posted meeting results through 2024-12-17. |
| `reference/DSP_Procedures_January_2026.pdf` | Designer Selection Panel procedures, revised January 2026. |
| `reference/panel_members.html` | Current panel roster page. |
| `reference/public_records.html` | How to request records, and which record types MSBA lists. |
| `reference/dsp_process.html` | DSP process page. |
| `reference/dsp_landing.html` | Designer Selection Process page, including the download links. |
| `processed/archive_firm_lists.csv` | One row per firm on a posted list. 1,513 rows, 283 meeting dates. |
| `processed/chart_projects.csv` | One row per chart block. 29 projects plus two cancelled-month notes. |
| `processed/chart_firms.csv` | Chart applicants and finalists, 224 rows. |
| `processed/panel_members.csv` | 18 names from the current roster page. |
| `processed/firms.csv` | One row per resolved firm. Includes the completed-ranking record and, where the name matched, the company profile. |
| `processed/firm_head_to_head.csv` | Pairs that shared at least five completed rankings, with who placed higher and who ranked first. |
| `processed/dsp_roster_inferred.csv` | Inferred Designer Selection Panel membership by era. Not a ballot and not a year-by-year roster. |
| `processed/firm_alias_audit.csv` | Each printed name and the firm id it resolved to. |
| `reference/firm_company.csv` | Company profile from the added firm file: staff, founding year, headquarters, geography, sources, and verification. |
| `archive/firm_info.csv` | The added firm file, kept whole, including the older list counts. |
| `archive/firm_crosswalk.csv` | Older spelling map from the 144-firm list. |
| `archive/firm_win_stats.csv` | Ranking record before it was folded into `firms.csv`. |
| `archive/source_manifest.csv` | Duplicate of `manifests/sources.csv`. |

Rebuild the processed tables with `python scripts/collect_dsp_results.py`.

The 2019–2024 page repeats the May 4 and May 18, 2021 meetings. Eight exact duplicate rows were dropped. A separate 2025 results URL now returns 404; the Excel chart is the 2025–2026 source linked from the DSP page.

## What a row actually contains

Posted results are firm names in a list. A numbered list is a final ranking. A bullet list is usually the unranked applicants invited to interview. The same school often appears twice: once as an unranked applicant list, then later as a ranking. Those are two stages of one selection, not two projects.

The 2025–2026 chart adds, for each project: application-review date, interview date, district, school, a construction-cost band, the MBE/WBE/VBE participation minimum, every applicant, a pre-interview rank, the shortlist, the final rank, and a short note. Columns labeled MBE, WBE, and V are present and empty in every row.

The chart has no final rank yet for Springfield Gerena (review 2025-08-12), Triton Regional High School (review 2026-04-07), and Milton Cunningham (review 2026-10-06). Twenty-six chart projects have a final rank of 1.

Across the HTML archive there are 731 final-ranking firm rows, of which 246 are numbered first. Eighteen of those ranking rows, from six meetings in 2010, were posted as bullets rather than numbers, so no rank number was stored. Three ranking rows are explicit ties. One hundred sixty-five rows are Accelerated Repair or Green Repair pool recommendations, not a ranking for one school. Seventy-two rows are informational interviews.

Firm names in the meeting rows are copied as printed. `processed/firms.csv` is the firm directory. Company details from the added firm file are matched onto that directory and also kept, one research row per name, in `reference/firm_company.csv`. The older list counts, which counted an applicant list and a later ranking as two tries, stay in `archive/firm_info.csv`. Teams and a few predecessor names stay separate.

`processed/dsp_roster_inferred.csv` records an inferred panel list supplied on October 20, 2026. Each era rests on one snapshot and is carried across the other years in that era. The 2007 names are inferred backward from the 2008–2009 roster. The 2018–2024 snapshot may include staff or alternates. The 2013 building-trades seat is recorded as vacant. The file does not say who voted, and it does not name the three local members on each project. The audit of those snapshots is `reports/05_panel_history.md`.

## Can these records support the five questions?

**Concentration — yes, for who the panel ranked first.** The archive plus the chart list a first-ranked firm for selections from August 2007 through 2026, except the three chart projects still open and the six 2010 rankings that were not numbered. Pool selections have to be kept out of a project count. This is the panel’s order of qualifications. Under the January 2026 procedures, the district awards the contract. If the fee was set in advance, the district takes the firms in ranked order unless it files a written justification and gets approval to do otherwise. If the fee is negotiated, the district negotiates in ranked order. A count of rank-1 firms is not yet a count of signed contracts.

**Newcomers — yes, inside this window only.** A firm can be marked as new if it has no earlier rank-1, or no earlier appearance at all, in these files. The files start in August 2007 and do not include work as a subconsultant, projects under the DSP dollar threshold, or the model-schools program. Spelling differences will look like new firms until names are reconciled.

**Voting patterns — not with these files.** The procedures say each member present signs a ballot giving 3, 2, and 1 points to a top three, the chair reads the totals, and remote participation is by roll call. The MSBA then sends the district the ranking, a record of the final vote, and a written statement of reasons. None of the posted result pages include the member, the ballot, the point total, or the roll call. The roster page is a current snapshot of 18 names, including staff and one alternate, not a record of who sat on which meeting. The three local members change with every project and are not named in the results.

**Qualifications — not with these files.** The procedures publish the criteria, including prior similar experience, past performance, workload, and the people assigned. The posted lists and the chart do not say what experience any firm offered. That information is in the application and the Master File Brochure. Those are not on the results pages.

**Decision justification — not with these files.** The procedures require a written statement explaining the ranking. The posted pages give the order and, in the chart, an occasional note such as “shortlisted all applicants” or “no interview.” They do not compare firms against the criteria.

MSBA’s public-records page lists “Designer Selection Panel information” and “Designer Selection Materials” among the records it holds. The records that would support the last three questions are that class of record. They were not collected here, and no request was sent.

## Not done

Rank-1 concentration, archive-newcomer counts, and field size are reported in `reports/01_market_structure.md`. Present-day staff, headquarters, and age are in `reports/02_firm_characteristics.md`. Earlier rank-1 results and school-type experience are in `reports/03_incumbency_specialization.md`. Applicant-to-interview rates from the 2025–2026 chart are in `reports/04_selection_stages.md`. Snapshot overlap and rankings during the years each roster snapshot covers are in `reports/05_panel_history.md`. The public cost files, and why they were not used as a performance history, are in `reports/06_project_performance.md`. District incumbents, the chart cost band, and the spelling recount are in `reports/07_local_contrasts.md`. The combined findings are in `reports/MSBA_RESEARCH_SYNTHESIS.md`. Voting, qualifications, and written justifications are not measured. No public-records request was sent. The inferred roster in `processed/dsp_roster_inferred.csv` is still not a ballot.
