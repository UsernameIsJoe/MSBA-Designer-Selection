"""Official sources used by this repository.

URLs were taken from the local snapshot of the MSBA Designer Selection Panel
page. The pipeline does not invent additional datasets.
"""

from __future__ import annotations

from msba_dsp.config import BASE_URL

SOURCES: list[dict[str, str]] = [
    {
        "source_id": "dsp_landing",
        "title": "Designer Selection Panel",
        "url": f"{BASE_URL}/building/team/dsp",
        "local_path": "data/reference/dsp_landing.html",
        "format": "html",
        "role": "Index of DSP procedures, result archives, the 2025-2026 chart, and the cost-chart link.",
    },
    {
        "source_id": "results_2007_2009",
        "title": "DSP meeting results, 2007-2009",
        "url": f"{BASE_URL}/building/team/dsp/meeting_results/2007-2009",
        "local_path": "data/raw/results_2007-2009.html",
        "format": "html",
        "role": "Historical ranked and unranked applicant lists.",
    },
    {
        "source_id": "results_2010_2014",
        "title": "DSP meeting results, 2010-2014",
        "url": f"{BASE_URL}/building/team/dsp/meeting_results/2010-2014",
        "local_path": "data/raw/results_2010-2014.html",
        "format": "html",
        "role": "Historical ranked and unranked applicant lists.",
    },
    {
        "source_id": "results_2015_2018",
        "title": "DSP meeting results, 2015-2018",
        "url": f"{BASE_URL}/building/team/dsp/meeting_results/2015-2018",
        "local_path": "data/raw/results_2015-2018.html",
        "format": "html",
        "role": "Historical ranked and unranked applicant lists.",
    },
    {
        "source_id": "results_2019_2024",
        "title": "DSP meeting results, 2019-2024",
        "url": f"{BASE_URL}/building/team/dsp/meeting_results/2019-2024",
        "local_path": "data/raw/results_2019-2024.html",
        "format": "html",
        "role": "Historical ranked and unranked applicant lists.",
    },
    {
        "source_id": "chart_2025_2026",
        "title": "DSP meeting result chart, 2025-2026",
        "url": f"{BASE_URL}/sites/default/files/edit-contentfiles/DSP/DSP_Meeting_Results_Chart_October9.xlsx",
        "local_path": "data/raw/DSP_Meeting_Results_Chart_2025-2026.xlsx",
        "format": "xlsx",
        "role": "Applicants, shortlisted firms, ranks, districts, schools, and preselection cost ranges.",
    },
    {
        "source_id": "dsp_procedures_pdf",
        "title": "Designer Selection Panel procedures, revised January 2026",
        "url": f"{BASE_URL}/sites/default/files/edit-contentfiles/DSP/DSP%20Procedures%20January%202026.pdf",
        "local_path": "data/reference/DSP_Procedures_January_2026.pdf",
        "format": "pdf",
        "role": "Stated evaluation framework. Not a results file.",
    },
    {
        "source_id": "dsp_process_html",
        "title": "Designer selection process narrative",
        "url": f"{BASE_URL}/building/team/dsp",
        "local_path": "data/reference/dsp_process.html",
        "format": "html",
        "role": "Public description of qualifications, 3-2-1 panel scoring, and interviews. Individual votes are not published.",
    },
    {
        "source_id": "panel_members",
        "title": "Designer Selection Panel membership",
        "url": f"{BASE_URL}/about/panels-dsp",
        "local_path": "data/reference/panel_members.html",
        "format": "html",
        "role": "Current appointed members. Not a vote history.",
    },
    {
        "source_id": "cost_chart_pdf",
        "title": "Designer construction cost chart",
        "url": f"{BASE_URL}/sites/default/files/edit-contentfiles/DSP/2026/DSP_Cost_Chart_2026_Annual_Update_Final.pdf",
        "local_path": "",
        "format": "pdf",
        "role": "Linked from the DSP page. Not in the local snapshot, so cost-performance models are not estimated.",
    },
    {
        "source_id": "cost_chart_tableau",
        "title": "Designer construction cost chart (Tableau)",
        "url": "https://info.massschoolbuildings.org/TabPub/DSPCostChart.aspx",
        "local_path": "",
        "format": "web",
        "role": "Interactive chart. Not ingested. Covers reconciled schematic-design budgets, which are post-selection.",
    },
    {
        "source_id": "project_info",
        "title": "Capital planning project information",
        "url": f"{BASE_URL}/building/CP_Information_Project_Info",
        "local_path": "",
        "format": "web",
        "role": "Not ingested. Grade and scope in this release come only from selection-result text and the 2025-2026 chart.",
    },
    {
        "source_id": "cost_data_portal",
        "title": "Capital planning cost data",
        "url": f"{BASE_URL}/building/CP_Information_Cost_Data",
        "local_path": "",
        "format": "web",
        "role": "Not ingested. No bid or final-construction series is in the local snapshot.",
    },
]
