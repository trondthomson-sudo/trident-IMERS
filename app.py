from datetime import date
from html import escape
from io import BytesIO
from pathlib import Path
import re

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DATASET_KEYS = ["objectives", "value_drivers", "processes", "risks", "controls", "actions", "opportunities"]
UNITS = [
    ("Strategy & Business Development", "Trond V. Thomson", "Chief Strategy & Business Developer"),
    ("Finance", "Øyvind Folland", "CFO"),
    ("Commercial", "Joar Gjerde", "Chief Commercial Officer"),
    ("Vessel Operations", "Kjetil Opshaug", "Chief Operating Officer"),
    ("Technical & HSEQ", "Raymond Kaspersen", "Chief HSEQ"),
    ("Crewing", "Hanne Beate Melby", "Chief HR"),
    ("Onshore Employees & Organization", "Hanne Beate Melby", "Chief HR"),
    ("Administration", "Ida Juul-Jørgensen", "Chief Administration Officer"),
    ("ICT", "Ida Juul-Jørgensen", "Chief Administration Officer"),
    ("Legal & Compliance", "Ove Paulsen", "Chief Legal Officer"),
    ("Chile Operations", "Jorge Maluenda", "Managing Director, Chile"),
    ("Shetland Operations", "Dean Johnson", "Managing Director, Shetland"),
]
REGISTER_KEYS = {
    "Strategy & Business Development": "strategy",
    "Finance": "finance",
    "Commercial": "commercial",
    "Vessel Operations": "vessel_operations",
    "Technical & HSEQ": "technical_hseq",
    "Crewing": "crewing",
    "Onshore Employees & Organization": "onshore_employees",
    "Administration": "administration",
    "ICT": "ict",
    "Legal & Compliance": "legal_compliance",
    "Chile Operations": "chile_operations",
    "Shetland Operations": "shetland_operations",
}
ENTERPRISE_REGISTER = "Enterprise Risk Register"
UNIT_BY_NAME = {name: (owner, title) for name, owner, title in UNITS}
RISK_CATEGORIES = ["Strategy execution", "Market development", "Fleet & capacity", "Capital allocation", "M&A & integration", "Customer concentration", "Technology", "New business models", "Geographic expansion", "Competitive position", "Financing & ownership", "Organizational capacity", "Data & assumptions", "Sustainability & regulation", "Reputation & partnerships"]
APPETITE = ["Within appetite", "Approaching appetite", "Outside appetite"]
TREATMENT_DECISIONS = ["Treat", "Accept", "Monitor", "Transfer", "Avoid"]
TRENDS = ["Increasing", "Stable", "Decreasing"]
STATUSES = ["Draft", "Open", "Monitoring", "Treatment in progress", "Accepted", "Closed"]
OWNERSHIP_ROLES = ["Primary owner", "Contributor", "Informed"]
OWNERSHIP_COLUMNS = [
    "Risk ID",
    "Department",
    "Role",
    "Mitigation contribution %",
    "Mitigation focus",
    "Notes",
]
# Aliases used in Affected units / free text → canonical UNITS names
UNIT_NAME_ALIASES = {
    "Strategy & BD": "Strategy & Business Development",
    "Strategy & Business Development": "Strategy & Business Development",
    "S&BD": "Strategy & Business Development",
    "Finance": "Finance",
    "Commercial": "Commercial",
    "Vessel Operations": "Vessel Operations",
    "Technical & HSEQ": "Technical & HSEQ",
    "Crewing": "Crewing",
    "HR": "Onshore Employees & Organization",
    "Onshore Employees & Organization": "Onshore Employees & Organization",
    "Administration": "Administration",
    "ICT": "ICT",
    "Legal & Compliance": "Legal & Compliance",
    "Chile Operations": "Chile Operations",
    "Shetland Operations": "Shetland Operations",
}
COLUMNS = {
    "objectives": ["Objective ID", "Objective level", "Strategic objective", "Parent objective", "Value effect", "Executive sponsor", "Metric", "Target", "Horizon", "Status"],
    "value_drivers": ["Driver ID", "Value pillar", "Value driver", "Management intent", "Value effect", "Executive sponsor"],
    "processes": ["Process ID", "Process", "Process owner", "Purpose", "Trigger / inputs", "Main activities", "Outputs", "Interfaces", "Review frequency", "S&BD Manual section"],
    "risks": ["Risk ID", "Category", "Risk title", "Objectives", "Value pillars", "Value effects", "Level 3 drivers", "Processes", "Cause", "Risk event", "Consequences", "Accountable executive", "Risk owner", "Affected units", "Time horizon", "Velocity", "Inherent likelihood", "Inherent impact", "Residual likelihood", "Residual impact", "Target likelihood", "Target impact", "Appetite status", "Trend", "Status", "Enterprise escalation", "Treatment decision", "Current mitigation", "Evidence / rationale"],
    "controls": ["Control ID", "Risk ID", "Control", "Control type", "Control owner", "Frequency", "Effectiveness", "Evidence", "Linked processes"],
    "actions": ["Action ID", "Risk ID", "Action", "Action owner", "Due date", "Status", "Progress %", "Treatment effect", "Completion evidence"],
    "opportunities": ["Opportunity ID", "Opportunity", "Objectives", "Owner", "Strategic fit", "Probability", "Value potential", "Execution complexity", "Decision stage", "Evidence / rationale"],
}
MATERIAL_RESIDUAL_THRESHOLD = 12

VALUE_HIERARCHY_GROUPS = [
    ("2.1 · PIL-01<br>Organic EBITDA Growth", [
        ("3.1.1", "Rate uplift on existing vessels"), ("3.1.2", "Utilization and reduced off-hire"),
        ("3.1.3", "Improved commercial terms"), ("3.1.4", "Existing-fleet operating performance"),
        ("3.1.5", "Vessel and crewing cost efficiency"),
    ]),
    ("2.2 · PIL-02<br>Investment EBITDA Growth", [
        ("3.2.1", "Value-accretive newbuild EBITDA yield"), ("3.2.2", "Value-accretive reconstruction"),
        ("3.2.3", "Attractive vessel acquisitions"), ("3.2.4", "M&A and identifiable synergies"),
        ("3.2.5", "Profitable new platforms such as SFaaS"),
    ]),
    ("2.3 · PIL-03<br>Multiple Expansion", [
        ("3.3.1", "Earnings visibility"), ("3.3.2", "Long-term contract coverage"),
        ("3.3.3", "Customer and counterparty quality"), ("3.3.4", "Reduced EBITDA volatility"),
        ("3.3.5", "Fleet quality and residual-value protection"),
        ("3.3.6", "Modernize through vessel divestments and replacements"),
        ("3.3.7", "Governance and reliable reporting"), ("3.3.8", "Scalability and reduced key-person risk"),
    ]),
    ("2.4 · PIL-04<br>Cash Conversion", [
        ("3.4.1", "EBITDA-to-operating-cash conversion"), ("3.4.2", "Maintenance-capex discipline"),
        ("divider", "CFO-monitored optimization topics"),
        ("3.4.3", "Working-capital efficiency"), ("3.4.4", "DSO and collection"),
        ("3.4.5", "Cash interest"), ("3.4.6", "Cash taxes"),
    ]),
    ("2.5 · PIL-05<br>Capital Allocation & Balance-Sheet Optimization", [
        ("3.5.1", "Value-maximizing allocation of cash"), ("3.5.2", "Return on invested capital"),
        ("3.5.3", "Debt reduction versus profitable investment"), ("3.5.4", "Disposal of underperforming assets"),
        ("3.5.5", "NIBD and leverage"), ("3.5.6", "Liquidity and covenant headroom"),
        ("3.5.7", "Financing flexibility"),
    ]),
]

ISO_MATRIX_ROWS = [
    ["Context and interested parties", "ISO 9001: 4.1–4.2; ISO 14001: 4.1–4.2", "Objectives and context", "SBD-P01; SBD-P02; SBD-P10"],
    ["Scope, processes and ownership", "ISO 9001: 4.3–4.4", "Process architecture", "SBD-P01–SBD-P12"],
    ["Leadership and responsibilities", "ISO 9001: 5; ISO 14001: 5", "Accountable executive and process owners", "All processes"],
    ["Risks and opportunities", "ISO 9001: 6.1; ISO 14001: 6.1; ISO 31000 guidance", "Risk and opportunity registers", "SBD-P03; SBD-P09; SBD-P10"],
    ["Objectives and planning", "ISO 9001: 6.2", "Objectives and actions", "SBD-P01; SBD-P12"],
    ["Controlled information", "ISO 9001: 7.5; ISO 14001: 7.5", "Documents and evidence", "All processes"],
    ["Operational planning and control", "ISO 9001: 8.1", "Controls and decision gates", "SBD-P03–SBD-P08"],
    ["Performance evaluation", "ISO 9001: 9; ISO 14001: 9", "KPIs, KRIs, reviews and audits", "SBD-P09; SBD-P11; SBD-P12"],
    ["Improvement", "ISO 9001: 10; ISO 14001: 10", "Actions and findings", "All processes"],
]


def level3_driver_catalog():
    """Full Level 3 tree (3.1.1–3.5.7), excluding divider rows."""
    catalog = []
    for pillar_label, drivers in VALUE_HIERARCHY_GROUPS:
        pillar_id = "PIL-0" + pillar_label.split("PIL-0")[1][0] if "PIL-0" in pillar_label else ""
        for reference, name in drivers:
            if reference == "divider":
                continue
            catalog.append({"pillar_id": pillar_id, "pillar_label": pillar_label.replace("<br>", " "), "reference": reference, "driver": name})
    return catalog


def split_refs(value):
    return [item.strip() for item in str(value or "").replace(",", ";").split(";") if item.strip()]


def process_matches_matrix(process_id, linked_field):
    """True if an ISO matrix 'Linked S&BD processes' cell applies to this process."""
    text_val = str(linked_field or "")
    if "All processes" in text_val:
        return True
    if process_id in text_val:
        return True
    # Handle ranges like SBD-P01–SBD-P12 or SBD-P03–SBD-P08
    if "–" in text_val or "-" in text_val:
        for match in re.finditer(r"(SBD-P\d+)\s*[–-]\s*(SBD-P\d+)", text_val):
            start, end = match.group(1), match.group(2)
            try:
                n = int(process_id.split("-P")[-1])
                n0 = int(start.split("-P")[-1])
                n1 = int(end.split("-P")[-1])
                if n0 <= n <= n1:
                    return True
            except ValueError:
                pass
    return False



def files_for(register_key):
    """CSV paths for a unit register. Strategy keeps strategy_*.csv for backward compatibility."""
    return {k: DATA_DIR / f"{register_key}_{k}.csv" for k in DATASET_KEYS}


# Active register file map; Strategy is the default and migration target.
FILES = files_for("strategy")
ACTIVE_REGISTER_KEY = "strategy"


def seed(path, rows, columns):
    # Also recover blank files left on Streamlit Cloud persistent storage.
    if (not path.exists()) or path.stat().st_size == 0:
        pd.DataFrame(rows, columns=columns).to_csv(path, index=False)


def schema_columns_for(key, register_key=None):
    """Column schema for a dataset key in the active or named unit register."""
    register_key = register_key or ACTIVE_REGISTER_KEY
    columns = list(COLUMNS[key])
    if key == "objectives" and register_key != "strategy":
        columns = ["Objective ID", "Hierarchy reference", "Objective level", "Strategic objective", "Parent objective", "Value effect", "Executive sponsor", "Accountable executive(s)", "Metric", "Target", "Horizon", "Status"]
    elif key == "value_drivers" and register_key != "strategy":
        columns = ["Driver ID", "Hierarchy reference", "Value pillar", "Value driver", "Management intent", "Value effect", "Executive sponsor"]
    elif key == "processes" and register_key != "strategy":
        columns = COLUMNS["processes"] + ["Linked Level 3 drivers"]
    return columns


def safe_read_csv(path, columns=None):
    """Read a register CSV; recover empty or unreadable files without crashing."""
    columns = list(columns) if columns is not None else []
    try:
        if (not path.exists()) or path.stat().st_size == 0:
            if columns:
                pd.DataFrame(columns=columns).to_csv(path, index=False)
            return pd.DataFrame(columns=columns)
        frame = pd.read_csv(path, dtype=str, keep_default_na=False)
        if len(frame.columns) == 0:
            raise pd.errors.EmptyDataError("No columns to parse")
        return frame
    except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError, OSError):
        if columns:
            pd.DataFrame(columns=columns).to_csv(path, index=False)
        return pd.DataFrame(columns=columns)


def seed_data():
    seed(FILES["objectives"], [
        ["VAL-00", "Overall objective", "Maximize shareholder value in Trident", "", "EBITDA; Multiple; Cash/NIBD", "Executive Management", "Equity value", "Board-approved value creation plan", "2035", "Active"],
        ["PIL-01", "Value pillar", "Increase EBITDA and cash generation from the existing fleet", "VAL-00", "EBITDA; Cash/NIBD", "COO and CCO", "EBITDA and operating cash flow", "Budget and long-term plan", "2035", "Active"],
        ["PIL-02", "Value pillar", "Invest in profitable growth above Trident's return requirements", "VAL-00", "EBITDA; Multiple; Cash/NIBD", "Chief Strategy & Business Developer", "EBITDA yield, IRR and value creation", "Approved investment thresholds", "2035", "Active"],
        ["PIL-03", "Value pillar", "Increase the quality, predictability and strategic value of Trident's earnings", "VAL-00", "Multiple", "Chief Strategy & Business Developer", "Contract coverage, earnings visibility and exit multiple", "Board-approved value creation plan", "2035", "Active"],
        ["OBJ-01", "Supporting objective", "Deliver planned revenue and EBITDA development", "PIL-01", "EBITDA; Cash/NIBD", "COO and CCO", "Revenue, EBITDA and cash conversion", "Budget and long-term plan", "2035", "Active"],
        ["OBJ-02", "Supporting objective", "Improve fleet utilization and commercial returns", "PIL-01", "EBITDA; Cash/NIBD", "COO and CCO", "Utilization, off-hire, TC rate and vessel EBITDA", "Budget and long-term plan", "2035", "Active"],
        ["OBJ-03", "Supporting objective", "Allocate capital to the highest risk-adjusted returns", "PIL-02", "EBITDA; Cash/NIBD", "Chief Strategy & Business Developer and CFO", "IRR, EBITDA yield, leverage and payback", "Investment criteria", "2035", "Active"],
        ["OBJ-04", "Supporting objective", "Integrate and standardize the combined group", "PIL-01; PIL-03", "EBITDA; Multiple", "Executive Management", "Synergies, process coverage and execution milestones", "Integration plan", "2035", "Active"],
        ["OBJ-05", "Supporting objective", "Develop profitable new growth platforms and services", "PIL-02", "EBITDA; Multiple", "Chief Strategy & Business Developer", "Pipeline value, IRR and incremental EBITDA", "Strategic plan", "2035", "Active"],
        ["OBJ-06", "Supporting objective", "Maintain financing capacity, covenant headroom and exit readiness", "PIL-02; PIL-03", "Multiple; Cash/NIBD", "CFO and Chief Strategy & Business Developer", "NIBD/EBITDA, liquidity, covenant headroom and readiness", "Financing and exit plan", "2035", "Active"],
    ], ["Objective ID", "Objective level", "Strategic objective", "Parent objective", "Value effect", "Executive sponsor", "Metric", "Target", "Horizon", "Status"])
    seed(FILES["value_drivers"], [
        ["VD-01", "PIL-01", "Increase income", "Increase TC rates, utilization and contract coverage; reduce unplanned off-hire", "EBITDA; Cash/NIBD", "CCO and COO"],
        ["VD-02", "PIL-01", "Improve crewing efficiency", "Optimize crew regimes, competence, retention and sick leave", "EBITDA", "Chief HR and COO"],
        ["VD-03", "PIL-01", "Reduce other vessel costs", "Capture group purchasing benefits and improve R&M and insurance efficiency", "EBITDA; Cash/NIBD", "COO and Chief HSEQ"],
        ["VD-04", "PIL-01", "Optimize overhead", "Maintain the capabilities required for safe growth with disciplined onshore cost", "EBITDA", "Executive Management"],
        ["VD-05", "PIL-01", "Improve cash conversion", "Optimize maintenance capex, working capital, DSO, financing cost and cash taxes", "Cash/NIBD", "CFO"],
        ["VD-06", "PIL-02", "Value-accretive newbuilds", "Require adequate EBITDA yield, contract duration and downside resilience", "EBITDA; Multiple; Cash/NIBD", "Chief Strategy & Business Developer and CFO"],
        ["VD-07", "PIL-02", "Value-accretive reconstruction", "Protect existing vessel value and improve post-reconstruction earnings", "EBITDA; Multiple; Cash/NIBD", "COO and CFO"],
        ["VD-08", "PIL-02", "Value-accretive vessel acquisitions", "Acquire redeployable or contracted vessels at attractive risk-adjusted returns", "EBITDA; Cash/NIBD", "Chief Strategy & Business Developer and CFO"],
        ["VD-09", "PIL-02", "Value-accretive M&A", "Acquire businesses below value-equivalent multiples with executable synergies", "EBITDA; Multiple; Cash/NIBD", "Chief Strategy & Business Developer and CFO"],
        ["VD-10", "PIL-03", "Reduce existing earnings risk", "Increase contract duration and visibility; reduce vessel EBITDA volatility", "Multiple", "CCO and CFO"],
        ["VD-11", "PIL-03", "Improve future earnings quality", "Increase exposure to attractive jurisdictions, defensible segments and creditworthy customers", "Multiple", "Chief Strategy & Business Developer and CCO"],
        ["VD-12", "PIL-03", "Strengthen governance and scalability", "Reduce key-person risk and improve process control, auditability and integration", "Multiple", "Executive Management"],
    ], ["Driver ID", "Value pillar", "Value driver", "Management intent", "Value effect", "Executive sponsor"])
    process_names = [
        ("SBD-P01", "Long-term strategic planning", "4.2"), ("SBD-P02", "Market intelligence interpretation", "4.3"),
        ("SBD-P03", "Opportunity identification and evaluation", "4.4"), ("SBD-P04", "Business case development", "4.5"),
        ("SBD-P05", "Long-term operating agenda and rate uplift", "4.6"), ("SBD-P06", "Fleet portfolio optimization and divestment", "4.7"),
        ("SBD-P07", "Capital project governance", "4.8"), ("SBD-P08", "M&A and strategic partnerships", "4.9"),
        ("SBD-P09", "Strategic risk integration", "4.10"), ("SBD-P10", "Sustainability strategy integration", "4.11"),
        ("SBD-P11", "Sustainability Statement and CSRD", "4.12"), ("SBD-P12", "Strategy execution and monitoring", "4.13"),
        ("SBD-P13", "Value realization and strategic portfolio review", "4.14"),
    ]
    seed(FILES["processes"], [[pid, name, "Trond V. Thomson", "To be defined", "To be defined", "To be defined", "To be defined", "To be defined", "Quarterly", section] for pid, name, section in process_names],
         ["Process ID", "Process", "Process owner", "Purpose", "Trigger / inputs", "Main activities", "Outputs", "Interfaces", "Review frequency", "S&BD Manual section"])
    risk_cols = COLUMNS["risks"]
    seed(FILES["risks"], [
        ["SBD-R001", "Fleet & capacity", "Investment in fleet capacity that does not match future demand", "OBJ-02; OBJ-03", "PIL-01; PIL-02", "EBITDA; Multiple; Cash/NIBD", "3.1.2; 3.2.1; 3.2.2; 3.2.3", "SBD-P02; SBD-P04; SBD-P06; SBD-P07", "Uncertain forecasts of salmon production, customer demand and competitor capacity", "Trident commits capital to vessel segments or geographies with insufficient demand", "Low utilization, reduced returns and constrained financial flexibility", "Trond V. Thomson", "", "Finance; Commercial; Vessel Operations", "1–3 years", "Medium", 4, 5, 3, 4, 2, 3, "Outside appetite", "Increasing", "Treatment in progress", "Yes", "Illustrative – validate"],
        ["SBD-R002", "Strategy execution", "Strategic initiatives fail to translate into accountable execution", "OBJ-01; OBJ-04", "PIL-01; PIL-03", "EBITDA; Multiple", "3.3.7; 3.3.8; 3.1.1", "SBD-P01; SBD-P12", "Insufficient ownership, capacity, milestones or cross-functional alignment", "Material strategic initiatives are delayed or incompletely implemented", "Growth, integration and value-creation targets are not achieved", "Trond V. Thomson", "", "All units", "0–12 months", "Medium", 4, 4, 3, 3, 2, 2, "Approaching appetite", "Stable", "Treatment in progress", "Yes", "Illustrative – validate"],
        ["SBD-R003", "New business models", "SFaaS expansion creates exposures outside established capabilities", "OBJ-03; OBJ-05", "PIL-02; PIL-03", "EBITDA; Multiple; Cash/NIBD", "3.2.5; 3.2.4; 3.3.8", "SBD-P03; SBD-P04; SBD-P07; SBD-P08", "Expansion from vessel services into aquaculture infrastructure", "The operating model, technology or commercial structure performs below plan", "Capital loss, operational liabilities and reputational harm", "Trond V. Thomson", "", "Finance; Commercial; Technical & HSEQ; Vessel Operations", ">3 years", "Slow", 3, 5, 3, 4, 2, 3, "Approaching appetite", "Stable", "Monitoring", "Yes", "Illustrative – validate"],
        ["SBD-R004", "Data & assumptions", "Strategic decisions rely on incomplete or unreliable information", "OBJ-01; OBJ-02; OBJ-03", "PIL-01; PIL-02; PIL-03", "EBITDA; Multiple; Cash/NIBD", "3.1.1; 3.3.1; 3.3.7", "SBD-P01; SBD-P02; SBD-P04", "Group data and external intelligence are fragmented or inconsistent", "Management bases decisions on assumptions that are not sufficiently tested", "Misallocation of capital and delayed corrective decisions", "Trond V. Thomson", "", "Finance; Commercial; ICT; Vessel Operations", "0–12 months", "Fast", 4, 4, 3, 3, 2, 2, "Approaching appetite", "Stable", "Open", "No", "Illustrative – validate"],
        ["SBD-R005", "M&A & integration", "Acquisitions fail to deliver expected synergies", "OBJ-01; OBJ-04", "PIL-01; PIL-02; PIL-03", "EBITDA; Multiple; Cash/NIBD", "3.2.4; 3.3.8; 3.5.1", "SBD-P08; SBD-P12", "Due diligence, integration planning or ownership of synergies is insufficient", "An acquired business is not integrated effectively", "Synergies are delayed, costs increase and group governance remains fragmented", "Trond V. Thomson", "", "All units", "1–3 years", "Medium", 4, 4, 3, 4, 2, 3, "Outside appetite", "Stable", "Treatment in progress", "Yes", "Illustrative – validate"],
    ], risk_cols)
    seed(FILES["controls"], [
        ["SBD-C001", "SBD-R001", "Board-approved investment process and business case", "Preventive", "Trond V. Thomson", "Per investment", "Partly effective", "Approved business case and minutes", "SBD-P04; SBD-P07"],
        ["SBD-C002", "SBD-R002", "Strategy review and initiative follow-up", "Detective", "Trond V. Thomson", "Quarterly", "Partly effective", "Strategy status report", "SBD-P12"],
        ["SBD-C003", "SBD-R004", "Market intelligence and scenario analysis", "Preventive", "Trond V. Thomson", "Quarterly", "Partly effective", "Market report and model assumptions", "SBD-P02"],
    ], ["Control ID", "Risk ID", "Control", "Control type", "Control owner", "Frequency", "Effectiveness", "Evidence", "Linked processes"])
    seed(FILES["actions"], [
        ["SBD-A001", "SBD-R001", "Establish standard fleet demand and capacity scenarios", "Trond V. Thomson", "2026-12-31", "In progress", 30, "Reduce likelihood", ""],
        ["SBD-A002", "SBD-R002", "Assign executive sponsors and measurable milestones", "Trond V. Thomson", "2026-11-30", "Not started", 0, "Reduce likelihood", ""],
        ["SBD-A003", "SBD-R005", "Create a common synergy register and integration review cadence", "Trond V. Thomson", "2026-12-31", "Not started", 0, "Reduce impact", ""],
    ], ["Action ID", "Risk ID", "Action", "Action owner", "Due date", "Status", "Progress %", "Treatment effect", "Completion evidence"])
    seed(FILES["opportunities"], [
        ["SBD-O001", "Develop SFaaS and aquaculture-infrastructure ownership", "OBJ-05", "Trond V. Thomson", "High", "Medium", "High", "High", "Concept development", "Illustrative – validate"],
        ["SBD-O002", "Optimize the fleet through selective investment and divestment", "OBJ-02; OBJ-03", "Trond V. Thomson", "High", "High", "High", "Medium", "Analysis", "Illustrative – validate"],
    ], ["Opportunity ID", "Opportunity", "Objectives", "Owner", "Strategic fit", "Probability", "Value potential", "Execution complexity", "Decision stage", "Evidence / rationale"])


def migrate_existing_data():
    """Add the value-creation hierarchy without discarding existing user entries."""
    objective_path = FILES["objectives"]
    objectives = safe_read_csv(objective_path, columns=schema_columns_for("objectives"))
    # Blank Cloud volume files: restore Strategy seed rows before migration.
    if objectives.empty:
        seed_data()
        objectives = safe_read_csv(objective_path, columns=schema_columns_for("objectives"))
    if "Objective level" not in objectives.columns:
        legacy_map = {
            "OBJ-01": ("PIL-01", "EBITDA; Cash/NIBD", "COO and CCO", "Revenue, EBITDA and cash conversion", "Budget and long-term plan"),
            "OBJ-02": ("PIL-01", "EBITDA; Cash/NIBD", "COO and CCO", "Utilization, off-hire, TC rate and vessel EBITDA", "Budget and long-term plan"),
            "OBJ-03": ("PIL-02", "EBITDA; Cash/NIBD", "Chief Strategy & Business Developer and CFO", "IRR, EBITDA yield, leverage and payback", "Investment criteria"),
            "OBJ-04": ("PIL-01; PIL-03", "EBITDA; Multiple", "Executive Management", "Synergies, process coverage and execution milestones", "Integration plan"),
            "OBJ-05": ("PIL-02", "EBITDA; Multiple", "Chief Strategy & Business Developer", "Pipeline value, IRR and incremental EBITDA", "Strategic plan"),
            "OBJ-06": ("PIL-02; PIL-03", "Multiple; Cash/NIBD", "CFO and Chief Strategy & Business Developer", "NIBD/EBITDA, liquidity, covenant headroom and readiness", "Financing and exit plan"),
        }
        rows = [
            ["VAL-00", "Overall objective", "Maximize shareholder value in Trident", "", "EBITDA; Multiple; Cash/NIBD", "Executive Management", "Equity value", "Board-approved value creation plan", "2035", "Active"],
            ["PIL-01", "Value pillar", "Increase EBITDA and cash generation from the existing fleet", "VAL-00", "EBITDA; Cash/NIBD", "COO and CCO", "EBITDA and operating cash flow", "Budget and long-term plan", "2035", "Active"],
            ["PIL-02", "Value pillar", "Invest in profitable growth above Trident's return requirements", "VAL-00", "EBITDA; Multiple; Cash/NIBD", "Chief Strategy & Business Developer", "EBITDA yield, IRR and value creation", "Approved investment thresholds", "2035", "Active"],
            ["PIL-03", "Value pillar", "Increase the quality, predictability and strategic value of Trident's earnings", "VAL-00", "Multiple", "Chief Strategy & Business Developer", "Contract coverage, earnings visibility and exit multiple", "Board-approved value creation plan", "2035", "Active"],
        ]
        new_columns = ["Objective ID", "Objective level", "Strategic objective", "Parent objective", "Value effect", "Executive sponsor", "Metric", "Target", "Horizon", "Status"]
        for _, old in objectives.iterrows():
            parent, effect, sponsor, metric, target = legacy_map.get(old["Objective ID"], ("", "", old.get("Owner", ""), "", ""))
            rows.append([old["Objective ID"], "Supporting objective", old["Strategic objective"], parent, effect, sponsor, metric, target, old.get("Horizon", ""), old.get("Status", "Active")])
        pd.DataFrame(rows, columns=new_columns).to_csv(objective_path, index=False)

    # Separate CEO sponsorship from functional accountability in earlier model data.
    objectives = safe_read_csv(objective_path, columns=schema_columns_for("objectives"))
    if "Accountable executive(s)" not in objectives.columns:
        objectives = objectives.rename(columns={"Executive sponsor": "Accountable executive(s)"})
    if "Executive sponsor" not in objectives.columns:
        insert_at = list(objectives.columns).index("Value effect") + 1
        objectives.insert(insert_at, "Executive sponsor", "CEO")
    else:
        objectives["Executive sponsor"] = "CEO"
    if "Hierarchy reference" not in objectives.columns:
        objectives.insert(1, "Hierarchy reference", "")

    # Apply the agreed 2035 horizon and sole functional ownership of PIL-02.
    old_horizons = {"2028", "2029", "2030", "2026–2028", "2026–2029", "2026–2030", "2026-2028", "2026-2029", "2026-2030"}
    objectives.loc[objectives["Horizon"].isin(old_horizons), "Horizon"] = "2035"
    objectives.loc[objectives["Objective ID"] == "PIL-02", "Accountable executive(s)"] = "Chief Strategy & Business Developer"

    # Reconcile the agreed five-pillar shareholder-value framework.
    pillar_records = [
        {"Objective ID": "VAL-00", "Hierarchy reference": "0", "Objective level": "Overall objective", "Strategic objective": "Maximize shareholder value in Trident", "Parent objective": "", "Value effect": "EBITDA; Multiple; Cash/NIBD", "Executive sponsor": "CEO", "Accountable executive(s)": "Executive Management", "Metric": "Equity value", "Target": "Long-term value creation plan", "Horizon": "2035", "Status": "Active"},
        {"Objective ID": "AIP-01", "Hierarchy reference": "1.1", "Objective level": "AIP value lever", "Strategic objective": "EBITDA", "Parent objective": "VAL-00", "Value effect": "EBITDA", "Executive sponsor": "CEO", "Accountable executive(s)": "Executive Management", "Metric": "Sustainable EBITDA", "Target": "Long-term value creation plan", "Horizon": "2035", "Status": "Active"},
        {"Objective ID": "AIP-02", "Hierarchy reference": "1.2", "Objective level": "AIP value lever", "Strategic objective": "Multiple", "Parent objective": "VAL-00", "Value effect": "Multiple", "Executive sponsor": "CEO", "Accountable executive(s)": "Executive Management", "Metric": "EV/EBITDA multiple", "Target": "Long-term value creation plan", "Horizon": "2035", "Status": "Active"},
        {"Objective ID": "AIP-03", "Hierarchy reference": "1.3", "Objective level": "AIP value lever", "Strategic objective": "Cash", "Parent objective": "VAL-00", "Value effect": "Cash/NIBD", "Executive sponsor": "CEO", "Accountable executive(s)": "Executive Management", "Metric": "Free cash flow and NIBD", "Target": "Long-term value creation plan", "Horizon": "2035", "Status": "Active"},
        {"Objective ID": "PIL-01", "Hierarchy reference": "2.1", "Objective level": "Trident value pillar", "Strategic objective": "Grow organic EBITDA through rate uplift and improved existing-fleet performance", "Parent objective": "AIP-01", "Value effect": "Organic EBITDA; Cash/NIBD", "Executive sponsor": "CEO", "Accountable executive(s)": "Chief Strategy & Business Developer; CCO; COO", "Metric": "Like-for-like EBITDA, achieved rate uplift, utilization and off-hire", "Target": "Long-term value creation plan", "Horizon": "2035", "Status": "Active"},
        {"Objective ID": "PIL-02", "Hierarchy reference": "2.2", "Objective level": "Trident value pillar", "Strategic objective": "Grow investment EBITDA through value-accretive risk-adjusted returns", "Parent objective": "AIP-01", "Value effect": "Investment EBITDA; Cash/NIBD", "Executive sponsor": "CEO", "Accountable executive(s)": "Chief Strategy & Business Developer", "Metric": "Incremental EBITDA, EBITDA yield, IRR and value creation", "Target": "Approved investment thresholds", "Horizon": "2035", "Status": "Active"},
        {"Objective ID": "PIL-03", "Hierarchy reference": "2.3", "Objective level": "Trident value pillar", "Strategic objective": "Expand the valuation multiple through earnings visibility, contract quality and fleet quality", "Parent objective": "AIP-02", "Value effect": "Multiple", "Executive sponsor": "CEO", "Accountable executive(s)": "Chief Strategy & Business Developer", "Metric": "Contracted EBITDA, contract duration, earnings volatility and fleet quality", "Target": "Long-term value creation plan", "Horizon": "2035", "Status": "Active"},
        {"Objective ID": "PIL-04", "Hierarchy reference": "2.4", "Objective level": "Trident value pillar", "Strategic objective": "Maximize conversion of EBITDA into free cash flow", "Parent objective": "AIP-03", "Value effect": "Cash conversion; Cash/NIBD", "Executive sponsor": "CEO", "Accountable executive(s)": "CFO; COO", "Metric": "Operating cash flow after maintenance capex / EBITDA", "Target": "Budget and long-term cash flow plan", "Horizon": "2035", "Status": "Active"},
        {"Objective ID": "PIL-05", "Hierarchy reference": "2.5", "Objective level": "Trident value pillar", "Strategic objective": "Optimize capital allocation and the balance sheet to maximize equity value", "Parent objective": "AIP-03", "Value effect": "Capital allocation; Cash/NIBD", "Executive sponsor": "CEO", "Accountable executive(s)": "CFO; Chief Strategy & Business Developer", "Metric": "ROIC, NIBD/EBITDA, liquidity and equity value created per NOK deployed", "Target": "Capital allocation and financing plan", "Horizon": "2035", "Status": "Active"},
        {"Objective ID": "OBJ-07", "Hierarchy reference": "3.3.5", "Objective level": "Supporting objective", "Strategic objective": "Maintain and develop a high-quality, commercially relevant fleet while protecting residual value", "Parent objective": "PIL-03; PIL-05", "Value effect": "Multiple; Capital allocation; Cash/NIBD", "Executive sponsor": "CEO", "Accountable executive(s)": "Chief HSEQ; COO; Chief Strategy & Business Developer", "Metric": "Fleet quality, economic life, off-hire, maintenance backlog and residual value", "Target": "Fleet quality and portfolio plan", "Horizon": "2035", "Status": "Active"},
    ]
    for record in pillar_records:
        mask = objectives["Objective ID"] == record["Objective ID"]
        if mask.any():
            for column, value in record.items():
                if column != "Objective ID": objectives.loc[mask, column] = value
        else:
            objectives = pd.concat([objectives, pd.DataFrame([{column: record.get(column, "") for column in objectives.columns}])], ignore_index=True)

    supporting_links = {
        "OBJ-01": ("PIL-01", "Organic EBITDA; Cash/NIBD"),
        "OBJ-02": ("PIL-01; PIL-03", "Organic EBITDA; Multiple; Cash/NIBD"),
        "OBJ-03": ("PIL-02; PIL-05", "Investment EBITDA; Capital allocation; Cash/NIBD"),
        "OBJ-04": ("PIL-03", "Multiple"),
        "OBJ-05": ("PIL-02", "Investment EBITDA; Multiple"),
        "OBJ-06": ("PIL-03; PIL-04; PIL-05", "Multiple; Cash conversion; Cash/NIBD"),
    }
    for objective_id, (parent, effect) in supporting_links.items():
        mask = objectives["Objective ID"] == objective_id
        objectives.loc[mask, "Parent objective"] = parent
        objectives.loc[mask, "Value effect"] = effect
    objectives.to_csv(objective_path, index=False)

    # Replace only the canonical driver IDs; preserve any additional user-created drivers.
    driver_path = FILES["value_drivers"]
    drivers = safe_read_csv(driver_path, columns=schema_columns_for("value_drivers"))
    canonical_drivers = pd.DataFrame([
        ["VD-01", "PIL-01", "Rate uplift on existing vessels", "Increase rates and improve commercial terms on the existing fleet", "Organic EBITDA; Cash/NIBD", "Chief Strategy & Business Developer; CCO"],
        ["VD-02", "PIL-01", "Existing-fleet utilization", "Increase utilization and reduce planned and unplanned off-hire", "Organic EBITDA; Cash/NIBD", "COO; CCO; Chief HSEQ"],
        ["VD-03", "PIL-01", "Existing-fleet operating performance", "Improve contribution margins through disciplined vessel and crewing costs", "Organic EBITDA; Cash/NIBD", "COO; Chief HR; Chief HSEQ"],
        ["VD-04", "PIL-02", "Value-accretive newbuild EBITDA yield", "Add contracted EBITDA at returns exceeding Trident's approved thresholds", "Investment EBITDA; Cash/NIBD", "Chief Strategy & Business Developer"],
        ["VD-05", "PIL-02", "Value-accretive vessel investment", "Reconstruct or acquire vessels only where risk-adjusted value creation is documented", "Investment EBITDA; Multiple; Cash/NIBD", "Chief Strategy & Business Developer; COO"],
        ["VD-06", "PIL-02", "Value-accretive M&A and new platforms", "Add EBITDA through acquisitions, new geographies and services with executable synergies", "Investment EBITDA; Multiple; Cash/NIBD", "Chief Strategy & Business Developer"],
        ["VD-07", "PIL-03", "Earnings visibility and contract quality", "Increase contracted EBITDA, contract duration, customer quality and predictability", "Multiple", "Chief Strategy & Business Developer; CCO"],
        ["VD-08", "PIL-03", "Modernize through vessel divestments and replacements", "Replace or divest aging vessels in a disciplined manner to reduce avoidable OPEX and downtime, improve fleet reliability and protect residual value without overinvesting", "Multiple; Cash/NIBD", "Chief HSEQ; COO; Chief Strategy & Business Developer"],
        ["VD-09", "PIL-03", "Governance, scalability and risk control", "Reduce key-person risk and improve integration, auditability and execution confidence", "Multiple", "Executive Management"],
        ["VD-10", "PIL-04", "EBITDA-to-cash conversion", "Optimize working capital, DSO, maintenance capex, cash interest and cash taxes", "Cash conversion; Cash/NIBD", "CFO; COO"],
        ["VD-11", "PIL-05", "Value-maximizing capital deployment", "Allocate cash between organic investment, growth investment, debt reduction and distributions", "Capital allocation; Cash/NIBD", "CFO; Chief Strategy & Business Developer"],
        ["VD-12", "PIL-05", "Balance-sheet resilience", "Maintain appropriate NIBD, liquidity, covenant headroom and financing flexibility", "Capital allocation; Cash/NIBD", "CFO"],
    ], columns=["Driver ID", "Value pillar", "Value driver", "Management intent", "Value effect", "Executive sponsor"])
    driver_refs = {f"VD-{number:02d}": reference for number, reference in enumerate([
        "3.1.1", "3.1.2", "3.1.3", "3.2.1", "3.2.2", "3.2.3",
        "3.3.1", "3.3.2", "3.3.3", "3.4.1", "3.5.1", "3.5.2",
    ], start=1)}
    canonical_drivers.insert(1, "Hierarchy reference", canonical_drivers["Driver ID"].map(driver_refs))
    if "Hierarchy reference" not in drivers.columns:
        drivers.insert(1, "Hierarchy reference", "")
    custom_drivers = drivers[~drivers["Driver ID"].isin(canonical_drivers["Driver ID"])]
    pd.concat([canonical_drivers, custom_drivers], ignore_index=True).to_csv(driver_path, index=False)

    # Link each ISO-aligned S&BD process to the Level 3 value drivers it supports.
    process_path = FILES["processes"]
    processes = safe_read_csv(process_path, columns=schema_columns_for("processes"))
    if "Linked Level 3 drivers" not in processes.columns:
        processes["Linked Level 3 drivers"] = ""
    if not (processes["Process ID"] == "SBD-P13").any():
        p13 = {column: "" for column in processes.columns}
        p13.update({
            "Process ID": "SBD-P13",
            "Process": "Value realization and strategic portfolio review",
            "Process owner": "Trond V. Thomson",
            "Purpose": "Verify that approved strategic initiatives and capital decisions deliver planned EBITDA, multiple and cash outcomes",
            "Trigger / inputs": "Approved business cases; investment decisions; initiative milestones; actual financial and operating results",
            "Main activities": "Perform post-investment reviews; track synergies and value bridges; assess portfolio performance; recommend continuation, correction, expansion, divestment or termination",
            "Outputs": "Value-realization review; strategic portfolio recommendations; CEO, board and owner reporting",
            "Interfaces": "CEO; Finance; Commercial; Vessel Operations; Technical & HSEQ; Legal & Compliance; operating companies",
            "Review frequency": "Quarterly",
            "S&BD Manual section": "4.14",
        })
        processes = pd.concat([processes, pd.DataFrame([p13])], ignore_index=True)
    all_level_3 = "; ".join([
        "3.1.1", "3.1.2", "3.1.3", "3.1.4", "3.1.5",
        "3.2.1", "3.2.2", "3.2.3", "3.2.4", "3.2.5",
        "3.3.1", "3.3.2", "3.3.3", "3.3.4", "3.3.5", "3.3.6", "3.3.7", "3.3.8",
        "3.4.1", "3.4.2", "3.4.3", "3.4.4", "3.4.5", "3.4.6",
        "3.5.1", "3.5.2", "3.5.3", "3.5.4", "3.5.5", "3.5.6", "3.5.7",
    ])
    process_driver_links = {
        "SBD-P01": all_level_3,
        "SBD-P02": "3.1.1; 3.1.2; 3.2.3; 3.2.5; 3.3.2; 3.3.3; 3.3.4",
        "SBD-P03": "3.1.1; 3.2.1; 3.2.2; 3.2.3; 3.2.4; 3.2.5; 3.3.3; 3.5.1; 3.5.2; 3.5.3",
        "SBD-P04": "3.2.1; 3.2.2; 3.2.3; 3.2.4; 3.2.5; 3.3.4; 3.3.5; 3.3.6; 3.4.1; 3.5.1; 3.5.2; 3.5.3",
        "SBD-P05": "3.1.1; 3.1.2; 3.1.3; 3.1.4; 3.1.5; 3.3.1; 3.3.2; 3.3.3; 3.3.4; 3.4.1; 3.4.2; 3.4.3; 3.4.4",
        "SBD-P06": "3.1.2; 3.1.4; 3.2.2; 3.2.3; 3.3.5; 3.3.6; 3.4.2; 3.5.4",
        "SBD-P07": "3.2.1; 3.2.2; 3.2.3; 3.4.1; 3.5.1; 3.5.2; 3.5.3; 3.5.5; 3.5.6; 3.5.7",
        "SBD-P08": "3.2.3; 3.2.4; 3.2.5; 3.3.1; 3.3.3; 3.3.8; 3.5.1; 3.5.2; 3.5.3; 3.5.5",
        "SBD-P09": all_level_3,
        "SBD-P10": "3.1.4; 3.2.1; 3.2.2; 3.2.5; 3.3.3; 3.3.5; 3.3.7; 3.5.1; 3.5.2",
        "SBD-P11": "3.3.1; 3.3.3; 3.3.7; 3.5.6; 3.5.7",
        "SBD-P12": all_level_3,
        "SBD-P13": all_level_3,
    }
    for process_id, linked_drivers in process_driver_links.items():
        mask = (processes["Process ID"] == process_id) & (processes["Linked Level 3 drivers"].str.strip() == "")
        processes.loc[mask, "Linked Level 3 drivers"] = linked_drivers
    processes.to_csv(process_path, index=False)

    risk_path = FILES["risks"]
    risks = safe_read_csv(risk_path, columns=schema_columns_for("risks"))
    if "Value pillars" not in risks.columns:
        pillar_map = {"SBD-R001": "PIL-01; PIL-02", "SBD-R002": "PIL-01; PIL-03", "SBD-R003": "PIL-02; PIL-03", "SBD-R004": "PIL-01; PIL-02; PIL-03", "SBD-R005": "PIL-01; PIL-02; PIL-03"}
        effect_map = {"SBD-R001": "EBITDA; Multiple; Cash/NIBD", "SBD-R002": "EBITDA; Multiple", "SBD-R003": "EBITDA; Multiple; Cash/NIBD", "SBD-R004": "EBITDA; Multiple; Cash/NIBD", "SBD-R005": "EBITDA; Multiple; Cash/NIBD"}
        position = list(risks.columns).index("Objectives") + 1
        risks.insert(position, "Value pillars", risks["Risk ID"].map(pillar_map).fillna(""))
        risks.insert(position + 1, "Value effects", risks["Risk ID"].map(effect_map).fillna(""))
    revised_links = {
        "SBD-R001": ("PIL-01; PIL-02; PIL-03; PIL-05", "Organic EBITDA; Investment EBITDA; Multiple; Cash/NIBD"),
        "SBD-R002": ("PIL-01; PIL-03; PIL-04", "Organic EBITDA; Multiple; Cash conversion"),
        "SBD-R003": ("PIL-02; PIL-03; PIL-05", "Investment EBITDA; Multiple; Cash/NIBD"),
        "SBD-R004": ("PIL-01; PIL-02; PIL-03; PIL-04; PIL-05", "Organic EBITDA; Investment EBITDA; Multiple; Cash conversion; Cash/NIBD"),
        "SBD-R005": ("PIL-02; PIL-03; PIL-04; PIL-05", "Investment EBITDA; Multiple; Cash conversion; Cash/NIBD"),
    }
    for risk_id, (pillars, effects) in revised_links.items():
        mask = risks["Risk ID"] == risk_id
        risks.loc[mask, "Value pillars"] = pillars
        risks.loc[mask, "Value effects"] = effects
    if "Level 3 drivers" not in risks.columns:
        insert_at = list(risks.columns).index("Value effects") + 1 if "Value effects" in risks.columns else len(risks.columns)
        risks.insert(insert_at, "Level 3 drivers", "")
    seed_level3 = {
        "SBD-R001": "3.1.2; 3.2.1; 3.2.2; 3.2.3",
        "SBD-R002": "3.3.7; 3.3.8; 3.1.1",
        "SBD-R003": "3.2.5; 3.2.4; 3.3.8",
        "SBD-R004": "3.1.1; 3.3.1; 3.3.7",
        "SBD-R005": "3.2.4; 3.3.8; 3.5.1",
    }
    for risk_id, refs in seed_level3.items():
        mask = (risks["Risk ID"] == risk_id) & (risks["Level 3 drivers"].astype(str).str.strip() == "")
        risks.loc[mask, "Level 3 drivers"] = refs
    risks.to_csv(risk_path, index=False)

    # Convert existing user data to the application's American English standard.
    american_english = [
        ("Maximising", "Maximizing"), ("maximising", "maximizing"),
        ("Maximise", "Maximize"), ("maximise", "maximize"),
        ("Optimisation", "Optimization"), ("optimisation", "optimization"),
        ("Optimising", "Optimizing"), ("optimising", "optimizing"),
        ("Optimise", "Optimize"), ("optimise", "optimize"),
        ("Utilisation", "Utilization"), ("utilisation", "utilization"),
        ("Organisation", "Organization"), ("organisation", "organization"),
        ("Organisational", "Organizational"), ("organisational", "organizational"),
        ("Standardise", "Standardize"), ("standardise", "standardize"),
        ("Standardisation", "Standardization"), ("standardisation", "standardization"),
    ]
    for key, data_path in FILES.items():
        if not data_path.exists():
            continue
        frame = safe_read_csv(data_path, columns=schema_columns_for(key))
        if frame.empty and len(frame.columns) == 0:
            continue
        for column in frame.columns:
            frame[column] = frame[column].map(lambda value: _americanize(value, american_english))
        frame.to_csv(data_path, index=False)


def _americanize(value, replacements):
    text = str(value)
    for british, american in replacements:
        text = text.replace(british, american)
    return text


def set_active_register(register_key):
    """Point load/save at the selected unit register."""
    global FILES, ACTIVE_REGISTER_KEY
    ACTIVE_REGISTER_KEY = register_key
    FILES = files_for(register_key)


def ensure_register_files(register_key):
    """Create empty CSVs with the correct columns when a unit register is first used."""
    paths = files_for(register_key)
    for key, path in paths.items():
        columns = schema_columns_for(key, register_key)
        if (not path.exists()) or path.stat().st_size == 0:
            pd.DataFrame(columns=columns).to_csv(path, index=False)
    return paths


def load(key):
    return safe_read_csv(FILES[key], columns=schema_columns_for(key))


def save(key, df):
    df.to_csv(FILES[key], index=False)


def ownership_path():
    """Group-level ownership matrix (shared across department registers)."""
    return DATA_DIR / "group_risk_ownership.csv"


def normalize_unit_name(raw):
    text_val = str(raw or "").strip()
    if not text_val:
        return ""
    if text_val in UNIT_NAME_ALIASES:
        return UNIT_NAME_ALIASES[text_val]
    for alias, canonical in UNIT_NAME_ALIASES.items():
        if alias.lower() == text_val.lower():
            return canonical
    for name, _owner, _title in UNITS:
        if name.lower() == text_val.lower():
            return name
    return ""


def parse_affected_departments(affected_units_value):
    raw = str(affected_units_value or "").strip()
    if not raw:
        return []
    if re.search(r"(?i)^all units$", raw) or "All units" in raw:
        return [name for name, _o, _t in UNITS]
    departments = []
    seen = set()
    for part in split_refs(raw):
        if re.search(r"(?i)^all units$", part):
            for name, _o, _t in UNITS:
                if name not in seen:
                    departments.append(name)
                    seen.add(name)
            continue
        canonical = normalize_unit_name(part)
        if canonical and canonical not in seen:
            departments.append(canonical)
            seen.add(canonical)
    return departments


def primary_department_for_risk(risk_row):
    """Heuristic primary owner from accountable executive / risk content."""
    accountable = str(risk_row.get("Accountable executive", "")).strip().lower()
    if "folland" in accountable or accountable == "cfo":
        return "Finance"
    # Default inventory steward for Strategy register risks
    return "Strategy & Business Development"


def seed_ownership_from_risks(risks_df):
    """Build ownership rows: one Primary owner + Contributors from Affected units."""
    rows = []
    if risks_df is None or risks_df.empty or "Risk ID" not in risks_df.columns:
        return pd.DataFrame(columns=OWNERSHIP_COLUMNS)
    for _, risk_row in risks_df.iterrows():
        risk_id = str(risk_row.get("Risk ID", "")).strip()
        if not risk_id:
            continue
        primary = primary_department_for_risk(risk_row)
        affected = parse_affected_departments(risk_row.get("Affected units", ""))
        if primary not in affected:
            affected = [primary] + affected
        # Deduplicate preserving order
        ordered = []
        seen = set()
        for dept in affected:
            if dept and dept not in seen:
                ordered.append(dept)
                seen.add(dept)
        contributors = [d for d in ordered if d != primary]
        n = max(len(contributors), 1)
        primary_share = 55 if contributors else 100
        contrib_share = max(5, (100 - primary_share) // n) if contributors else 0
        # Adjust remainder onto primary
        assigned = primary_share + contrib_share * len(contributors)
        primary_share = primary_share + (100 - assigned)
        rows.append({
            "Risk ID": risk_id,
            "Department": primary,
            "Role": "Primary owner",
            "Mitigation contribution %": str(primary_share),
            "Mitigation focus": "Lead mitigation design and follow-up",
            "Notes": "Seeded from Strategy inventory — validate",
        })
        for dept in contributors:
            rows.append({
                "Risk ID": risk_id,
                "Department": dept,
                "Role": "Contributor",
                "Mitigation contribution %": str(contrib_share),
                "Mitigation focus": "Contribute controls/actions in this unit",
                "Notes": "Seeded from Affected units — validate",
            })
    return pd.DataFrame(rows, columns=OWNERSHIP_COLUMNS)


def load_ownership(risks_df=None):
    path = ownership_path()
    if (not path.exists()) or path.stat().st_size == 0:
        seeded = seed_ownership_from_risks(risks_df if risks_df is not None else pd.DataFrame())
        seeded.to_csv(path, index=False)
        return seeded
    frame = safe_read_csv(path, columns=OWNERSHIP_COLUMNS)
    if frame.empty or "Risk ID" not in frame.columns:
        seeded = seed_ownership_from_risks(risks_df if risks_df is not None else pd.DataFrame())
        seeded.to_csv(path, index=False)
        return seeded
    for column in OWNERSHIP_COLUMNS:
        if column not in frame.columns:
            frame[column] = ""
    return frame[OWNERSHIP_COLUMNS]


def save_ownership(df):
    out = df.copy()
    for column in OWNERSHIP_COLUMNS:
        if column not in out.columns:
            out[column] = ""
    out[OWNERSHIP_COLUMNS].to_csv(ownership_path(), index=False)


def render_ownership_page(risks_df):
    """Allocate shared risks to departments with roles and mitigation contribution."""
    st.subheader("Ownership and mitigation contribution")
    st.write(
        "One risk can sit with several departments. Set a **Primary owner** and **Contributor** / **Informed** "
        "roles. Contribution % is indicative of mitigation effort share, not financial allocation. "
        "Department IMERS work (inherent → actions) should focus where this unit is Primary or Contributor."
    )
    ownership = load_ownership(risks_df)
    unit_names = [name for name, _o, _t in UNITS]
    risk_ids = (
        risks_df["Risk ID"].astype(str).tolist()
        if risks_df is not None and not risks_df.empty and "Risk ID" in risks_df.columns
        else []
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        filter_dept = st.selectbox("Filter department", ["All departments"] + unit_names, key=f"own_dept_{ACTIVE_REGISTER_KEY}")
    with c2:
        filter_role = st.selectbox("Filter role", ["All roles"] + OWNERSHIP_ROLES, key=f"own_role_{ACTIVE_REGISTER_KEY}")
    with c3:
        if st.button("Re-seed from Affected units", key=f"own_reseed_{ACTIVE_REGISTER_KEY}"):
            seeded = seed_ownership_from_risks(risks_df)
            save_ownership(seeded)
            st.success(f"Re-seeded {len(seeded)} ownership rows from the risk register.")
            st.rerun()

    view = ownership.copy()
    if filter_dept != "All departments":
        view = view[view["Department"].astype(str) == filter_dept]
    if filter_role != "All roles":
        view = view[view["Role"].astype(str) == filter_role]

    # Coverage summary
    if risk_ids:
        covered = set(ownership["Risk ID"].astype(str))
        missing = [rid for rid in risk_ids if rid not in covered]
        primaries = ownership[ownership["Role"].astype(str) == "Primary owner"]
        multi_primary = primaries.groupby("Risk ID").size()
        multi_primary = multi_primary[multi_primary > 1]
        st.caption(
            f"{len(ownership)} allocation rows · {len(set(ownership['Risk ID'].astype(str)))} risks covered · "
            f"{len(missing)} risks with no ownership row yet"
            + (f" · {len(multi_primary)} risks have multiple Primary owners (fix)" if len(multi_primary) else "")
        )
        if missing:
            st.warning("Risks without ownership rows: " + ", ".join(missing[:12]) + ("…" if len(missing) > 12 else ""))

    edited = st.data_editor(
        view,
        hide_index=True,
        use_container_width=True,
        num_rows="dynamic",
        column_config={
            "Risk ID": st.column_config.SelectboxColumn(options=risk_ids or [""], required=True),
            "Department": st.column_config.SelectboxColumn(options=unit_names, required=True),
            "Role": st.column_config.SelectboxColumn(options=OWNERSHIP_ROLES, required=True),
            "Mitigation contribution %": st.column_config.NumberColumn(min_value=0, max_value=100, step=5),
        },
        key=f"own_editor_{ACTIVE_REGISTER_KEY}_{filter_dept}_{filter_role}",
    )

    if st.button("Save ownership allocations", type="primary", key=f"own_save_{ACTIVE_REGISTER_KEY}"):
        # Replace the currently visible filter slice; keep all other rows.
        mask = pd.Series([True] * len(ownership), index=ownership.index)
        if filter_dept != "All departments":
            mask &= ownership["Department"].astype(str) == filter_dept
        if filter_role != "All roles":
            mask &= ownership["Role"].astype(str) == filter_role
        kept = ownership.loc[~mask].copy() if (filter_dept != "All departments" or filter_role != "All roles") else ownership.iloc[0:0]
        if filter_dept == "All departments" and filter_role == "All roles":
            merged = edited.copy()
        else:
            merged = pd.concat([kept, edited], ignore_index=True)
        for column in OWNERSHIP_COLUMNS:
            if column not in merged.columns:
                merged[column] = ""
        merged = merged[merged["Risk ID"].astype(str).str.strip() != ""]
        save_ownership(merged[OWNERSHIP_COLUMNS])
        st.success(f"Saved {len(merged)} ownership rows.")
        st.rerun()

    st.markdown("---")
    st.subheader("By department (read-out)")
    if ownership.empty:
        st.info("No ownership rows yet.")
    else:
        summary_rows = []
        for name, _o, _t in UNITS:
            subset = ownership[ownership["Department"].astype(str) == name]
            if subset.empty:
                continue
            summary_rows.append({
                "Department": name,
                "Primary owner": int((subset["Role"] == "Primary owner").sum()),
                "Contributor": int((subset["Role"] == "Contributor").sum()),
                "Informed": int((subset["Role"] == "Informed").sum()),
                "Total rows": len(subset),
            })
        st.dataframe(pd.DataFrame(summary_rows), hide_index=True, use_container_width=True)



def scored(df):
    out = df.copy()
    for prefix in ["Inherent", "Residual", "Target"]:
        likelihood = pd.to_numeric(out[f"{prefix} likelihood"], errors="coerce").fillna(0)
        impact = pd.to_numeric(out[f"{prefix} impact"], errors="coerce").fillna(0)
        out[f"{prefix} score"] = likelihood * impact
    return out


def material_mask(risks_df):
    """Material risks for Enterprise roll-up."""
    scored_df = risks_df if "Residual score" in risks_df.columns else scored(risks_df)
    escalated = scored_df["Enterprise escalation"].astype(str).str.strip().eq("Yes")
    outside = scored_df["Appetite status"].astype(str).str.strip().eq("Outside appetite")
    high_residual = pd.to_numeric(scored_df["Residual score"], errors="coerce").fillna(0) >= MATERIAL_RESIDUAL_THRESHOLD
    return escalated | outside | high_residual


def collect_enterprise_risks():
    """Roll up material risks from all configured unit registers with provenance."""
    frames = []
    for unit_name, _owner, _title in UNITS:
        register_key = REGISTER_KEYS[unit_name]
        ensure_register_files(register_key)
        risk_path = files_for(register_key)["risks"]
        risks_df = safe_read_csv(risk_path, columns=schema_columns_for("risks", register_key))
        if risks_df.empty or "Risk ID" not in risks_df.columns:
            continue
        scored_df = scored(risks_df)
        material = scored_df.loc[material_mask(scored_df)].copy()
        if material.empty:
            continue
        material.insert(0, "Source unit", unit_name)
        frames.append(material)
    if not frames:
        cols = ["Source unit"] + COLUMNS["risks"] + ["Inherent score", "Residual score", "Target score"]
        return pd.DataFrame(columns=cols)
    return pd.concat(frames, ignore_index=True)


def collect_enterprise_actions(enterprise_risks):
    """Treatment actions linked to rolled-up material risks, with source unit."""
    if enterprise_risks is None or enterprise_risks.empty:
        return pd.DataFrame(columns=["Source unit", "Risk ID"] + COLUMNS["actions"])
    frames = []
    risk_ids_by_unit = {
        unit: set(group["Risk ID"].astype(str))
        for unit, group in enterprise_risks.groupby("Source unit")
    }
    for unit_name, risk_ids in risk_ids_by_unit.items():
        register_key = REGISTER_KEYS[unit_name]
        action_path = files_for(register_key)["actions"]
        if not action_path.exists():
            continue
        actions_df = safe_read_csv(action_path, columns=schema_columns_for("actions", register_key))
        if actions_df.empty:
            continue
        linked = actions_df[actions_df["Risk ID"].astype(str).isin(risk_ids)].copy()
        if linked.empty:
            continue
        linked.insert(0, "Source unit", unit_name)
        frames.append(linked)
    if not frames:
        return pd.DataFrame(columns=["Source unit"] + COLUMNS["actions"])
    return pd.concat(frames, ignore_index=True)


def heatmap(df, basis):
    labels = [["" for _ in range(5)] for _ in range(5)]
    for _, r in df.iterrows():
        try:
            x, y = int(float(r[f"{basis} likelihood"] or 0)), int(float(r[f"{basis} impact"] or 0))
        except (TypeError, ValueError):
            continue
        if 1 <= x <= 5 and 1 <= y <= 5:
            label = r["Risk ID"]
            if "Source unit" in r and r["Source unit"]:
                label = f'{r["Risk ID"]} ({r["Source unit"]})'
            labels[y - 1][x - 1] += ("<br>" if labels[y - 1][x - 1] else "") + str(label)
    z = [[(x + 1) * (y + 1) for x in range(5)] for y in range(5)]
    fig = go.Figure(go.Heatmap(
        z=z, x=[1, 2, 3, 4, 5], y=[1, 2, 3, 4, 5], text=labels, texttemplate="%{text}",
        colorscale=[[0, "#cfe8cf"], [.32, "#cfe8cf"], [.33, "#ffe58f"], [.52, "#ffe58f"], [.53, "#f5ad65"], [.72, "#f5ad65"], [.73, "#dc6b57"], [1, "#a61b1b"]],
        zmin=1, zmax=25, showscale=False,
        hovertemplate="Likelihood %{x}<br>Impact %{y}<br>%{text}<extra></extra>",
    ))
    fig.update_layout(height=500, xaxis_title="Likelihood", yaxis_title="Impact", margin=dict(l=30, r=20, t=10, b=40))
    fig.update_xaxes(dtick=1, range=[.5, 5.5])
    fig.update_yaxes(dtick=1, range=[.5, 5.5])
    return fig


def editor(key, df, config=None):
    edited = st.data_editor(df, num_rows="dynamic", use_container_width=True, hide_index=True, column_config=config or {}, key=f"editor_{ACTIVE_REGISTER_KEY}_{key}")
    if st.button(f"Save {key}", type="primary", key=f"save_{ACTIVE_REGISTER_KEY}_{key}"):
        save(key, edited)
        st.success("Saved.")
        st.rerun()


def update_risks(edited, columns):
    master = load("risks").set_index("Risk ID")
    incoming = edited.set_index("Risk ID")
    master.update(incoming[columns])
    save("risks", master.reset_index())
    st.success("Saved.")
    st.rerun()


def ensure_risk_treatment_columns(df):
    """Add fast-path treatment fields used in Risks & Opportunities."""
    out = df.copy()
    changed = False
    for column, default in [("Treatment decision", ""), ("Current mitigation", "")]:
        if column not in out.columns:
            out[column] = default
            changed = True
    if changed and ACTIVE_REGISTER_KEY:
        try:
            save("risks", out)
        except Exception:
            pass
    return out


def workbook(data, *, enterprise_risks=None, enterprise_actions=None, source_label=None):
    bio = BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        for key, df in data.items():
            sheet = key.replace("_", " ").title()[:31]
            if source_label and source_label != ENTERPRISE_REGISTER:
                prefix = REGISTER_KEYS.get(source_label, source_label)[:8]
                sheet = f"{prefix}_{key}"[:31]
            df.to_excel(writer, sheet_name=sheet, index=False)
        if enterprise_risks is not None:
            display_cols = [c for c in [
                "Source unit", "Risk ID", "Risk title", "Accountable executive",
                "Residual score", "Appetite status", "Trend", "Status", "Enterprise escalation",
                "Category", "Value pillars", "Residual likelihood", "Residual impact",
            ] if c in enterprise_risks.columns]
            enterprise_risks[display_cols].to_excel(writer, sheet_name="Enterprise", index=False)
        if enterprise_actions is not None and not enterprise_actions.empty:
            enterprise_actions.to_excel(writer, sheet_name="Enterprise Actions", index=False)
        pd.DataFrame(UNITS, columns=["Risk register", "Accountable executive", "Title"]).to_excel(writer, sheet_name="ERM Structure", index=False)
    return bio.getvalue()


def render_enterprise_view():
    st.subheader("Enterprise Risk Register")
    st.info(
        "**Materiality criteria (roll-up):** a risk is included when "
        "**Enterprise escalation = Yes**, or **Appetite status = Outside appetite**, "
        f"or **Residual score ≥ {MATERIAL_RESIDUAL_THRESHOLD}** "
        f"(residual likelihood × residual impact). "
        "This view consolidates matching risks from the twelve unit registers; it does not store a separate seed register."
    )
    enterprise_risks = collect_enterprise_risks()
    enterprise_actions = collect_enterprise_actions(enterprise_risks)
    open_material = enterprise_risks[enterprise_risks["Status"].astype(str) != "Closed"] if not enterprise_risks.empty else enterprise_risks
    outside = int((enterprise_risks["Appetite status"] == "Outside appetite").sum()) if not enterprise_risks.empty else 0
    escalated = int((enterprise_risks["Enterprise escalation"] == "Yes").sum()) if not enterprise_risks.empty else 0
    if not enterprise_actions.empty and "Due date" in enterprise_actions.columns:
        due = pd.to_datetime(enterprise_actions["Due date"], errors="coerce").dt.date
        overdue = (due < date.today()) & ~enterprise_actions["Status"].isin(["Completed", "Cancelled"])
        overdue_count = int(overdue.sum())
    else:
        overdue_count = 0

    cols = st.columns(4)
    cols[0].metric("Open material risks", int(len(open_material)))
    cols[1].metric("Outside appetite", outside)
    cols[2].metric("Enterprise escalation = Yes", escalated)
    cols[3].metric("Overdue treatment actions", overdue_count)

    if enterprise_risks.empty:
        st.warning("No material risks meet the Enterprise criteria yet. Populate unit registers and mark escalation, appetite, or residual scores accordingly.")
    else:
        left, right = st.columns([1.2, 1])
        with left:
            st.subheader("Residual risk heatmap (consolidated)")
            st.plotly_chart(heatmap(enterprise_risks, "Residual"), use_container_width=True)
        with right:
            st.subheader("Material risks by source unit")
            by_unit = (
                enterprise_risks.groupby("Source unit", dropna=False)
                .size()
                .reset_index(name="Material risks")
                .sort_values("Material risks", ascending=False)
            )
            st.dataframe(by_unit, hide_index=True, use_container_width=True)

        table_cols = [c for c in [
            "Source unit", "Risk ID", "Risk title", "Accountable executive",
            "Residual score", "Appetite status", "Trend", "Status", "Enterprise escalation",
        ] if c in enterprise_risks.columns]
        st.subheader("Consolidated material risks")
        st.dataframe(
            enterprise_risks.sort_values(["Residual score", "Source unit"], ascending=[False, True])[table_cols],
            hide_index=True,
            use_container_width=True,
        )

        st.subheader("Treatment actions for material risks")
        if enterprise_actions.empty:
            st.caption("No treatment actions are linked to the current material risks.")
        else:
            action_cols = [c for c in ["Source unit", "Action ID", "Risk ID", "Action", "Action owner", "Due date", "Status", "Progress %"] if c in enterprise_actions.columns]
            st.dataframe(enterprise_actions[action_cols], hide_index=True, use_container_width=True)

    st.download_button(
        "Download Enterprise ERM workbook",
        workbook({}, enterprise_risks=enterprise_risks, enterprise_actions=enterprise_actions, source_label=ENTERPRISE_REGISTER),
        file_name=f"Trident_Enterprise_ERM_{date.today().isoformat()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
    )
    st.caption("Starter and unit entries remain illustrative until management validates them.")


def apply_brand_theme():
    st.markdown("""
    <style>
    :root{
        --trident-deep:#00191d;--trident-dark:#002228;--trident-sea:#255a64;
        --trident-mid:#397580;--trident-aqua:#90c4ce;--trident-sky:#d3e7ff;
        --trident-sky-light:#e5f1ff;--trident-signal:#00839B;
        --trident-signal-light:#b8e0e8;--trident-orange:#ff6b35;--trident-sand:#f1efeb;
    }
    html{font-size:17px}
    [data-testid="stAppViewContainer"] p,[data-testid="stAppViewContainer"] label{line-height:1.45}
    [data-testid="stAppViewContainer"]{background:#fff;color:var(--trident-deep)}
    [data-testid="stHeader"]{background:rgba(255,255,255,.92)}
    [data-testid="stSidebar"]{background:var(--trident-deep);border-right:1px solid var(--trident-sea)}
    [data-testid="stSidebar"] *{color:#fff}
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] *{color:#b9d0d4}
    [data-testid="stSidebar"] label p{font-size:.98rem}
    [data-testid="stSidebar"] details{border-color:#397580;background:#002228}
    h1,h2,h3,h4{color:var(--trident-deep)}
    [data-testid="stMetric"]{background:var(--trident-sky-light);border:1px solid #a4c4e9;border-radius:10px;padding:12px 14px}
    [data-testid="stMetricValue"]{color:var(--trident-deep)}
    div[data-baseweb="tab-list"]{border-bottom:1px solid #90c4ce}
    button[data-baseweb="tab"][aria-selected="true"]{color:var(--trident-deep);font-weight:700}
    .stButton > button[kind="primary"],.stDownloadButton > button[kind="primary"]{
        background:#00839B;border-color:#00839B;color:#fff;font-weight:700
    }
    .stButton > button[kind="primary"]:hover,.stDownloadButton > button[kind="primary"]:hover{
        background:#006677;border-color:#006677;color:#fff
    }
    [data-testid="stDataFrame"]{border:1px solid #a4c4e9;border-radius:8px;overflow:hidden}
    [data-testid="stExpander"]{border-color:#a4c4e9;background:#fff}
    [data-testid="stExpander"] summary p{font-size:.94rem;font-weight:600}
    [data-testid="stCaptionContainer"] p{font-size:.86rem}

    /* Risk library / Context shared ERM chips & panes (always available) */
    .vh-ref-badge{display:inline-block;color:#00191d;background:#caff74;border:1px solid #90c44f;border-radius:4px;padding:2px 7px;margin-right:8px;font-size:.9rem;font-weight:700;white-space:nowrap}
    .vh-process-id{display:inline-block;color:#00191d;background:#90c4ce;border:1px solid #255a64;border-radius:4px;padding:2px 7px;margin-right:8px;font-size:.9rem;font-weight:700;white-space:nowrap}
    .vh-pil-badge{display:inline-block;color:#00191d;background:#90c4ce;border:1px solid #255a64;border-radius:4px;padding:3px 8px;margin-right:8px;font-size:.9rem;font-weight:700;white-space:nowrap}
    .vh-driver-link,.vh-process-link{margin:0 0 9px 0;font-size:.96rem;line-height:1.6}
    .vh-process-pillar{margin:11px 0 8px;font-size:.98rem;font-weight:700}
    .vh-l5-erm-pane{background:rgba(255,107,53,.12);border:1px solid #d94b18;border-radius:8px;padding:12px 12px 8px;min-height:120px;margin-bottom:10px}
    .vh-l5-pane-title{font-weight:700;color:#00191d;font-size:.96rem;margin:0 0 10px 0}
    .vh-l5-risk-badge{display:inline-block;color:#00191d;background:#ffc9b0;border:1px solid #d94b18;border-radius:4px;padding:2px 7px;margin-right:8px;font-size:.9rem;font-weight:700;white-space:nowrap}
    .vh-l5-erm-coverage{font-size:.82rem;color:#8a3a18;margin:2px 0 10px 28px;line-height:1.35}
    .vh-l5-erm-coverage strong{color:#00191d}
    .vh-l5-empty-slot{color:#6b7c80;font-size:.85rem;font-style:italic;margin:0 0 9px 0;padding:4px 0}
    .vh-l5-driver-slot{margin:0 0 9px 0;min-height:1.55em}
    </style>
    """, unsafe_allow_html=True)


def render_value_hierarchy(processes=None, risks=None, controls=None, actions=None):
    st.markdown("""
    <style>
    .vh-box{border:1px solid #255a64;padding:11px 9px;text-align:center;margin-bottom:8px;background:#fff;color:#00191d;font-size:1rem;line-height:1.35}
    .vh-top{max-width:560px;margin-left:auto;margin-right:auto;font-weight:700;font-size:1.04rem;background:#00191d;color:#fff;border-color:#00191d}
    .vh-aip{background:#00839B;color:#fff;font-weight:700;min-height:52px;border-color:#006677;font-size:1.02rem}
    .vh-aip-badge{display:inline-block;color:#fff;background:#006677;border:1px solid #004d5a;border-radius:4px;padding:3px 8px;margin-right:8px;font-size:.92rem;font-weight:700;white-space:nowrap}
    .vh-pil{background:#343d40;color:#fff;font-weight:700;min-height:72px;display:flex;align-items:center;justify-content:center;border-color:#255a64;font-size:1rem}
    .vh-drivers{border:1px solid #a4c4e9;padding:9px 8px;min-height:230px;background:#fff;color:#00191d}
    .vh-drivers div{margin-bottom:7px;font-size:.86rem}
    .vh-cfo-divider{border-top:2px dotted #67a9b6;margin:12px 0 8px;padding-top:8px;color:#255a64;font-size:.78rem;font-weight:700;text-align:center;text-transform:uppercase;letter-spacing:.04em}
    .vh-support{border:1px solid #397580;padding:13px;color:#00191d;min-height:116px;font-size:.96rem;line-height:1.45}
    .vh-iso{background:#caff74;border-color:#90c44f}
    .vh-erm{background:#ff6b35;border-color:#d94b18;color:#fff}
    .vh-support strong{display:block;margin-bottom:6px}
    .vh-erm,.vh-erm strong{color:#fff}
    .vh-level{text-align:center;color:#397580;font-size:.92rem;margin:10px 0 6px;font-weight:600}
    .vh-ref-badge{display:inline-block;color:#00191d;background:#caff74;border:1px solid #90c44f;border-radius:4px;padding:2px 7px;margin-right:8px;font-size:.9rem;font-weight:700;white-space:nowrap}
    .vh-process-id{display:inline-block;color:#00191d;background:#90c4ce;border:1px solid #255a64;border-radius:4px;padding:2px 7px;margin-right:8px;font-size:.9rem;font-weight:700;white-space:nowrap}
    .vh-pil-badge{display:inline-block;color:#00191d;background:#90c4ce;border:1px solid #255a64;border-radius:4px;padding:3px 8px;margin-right:8px;font-size:.9rem;font-weight:700;white-space:nowrap}
    .vh-driver-link,.vh-process-link{margin:0 0 9px 0;font-size:.96rem;line-height:1.6}
    .vh-process-pillar{margin:11px 0 8px;font-size:.98rem;font-weight:700}
    .vh-l5-chip{border:1px solid;padding:8px 10px;border-radius:8px;font-weight:700;font-size:.92rem;margin-bottom:6px;text-align:center}
    .vh-l5-iso-chip{background:#caff74;border-color:#90c44f;color:#00191d}
    .vh-l5-erm-chip{background:#ff6b35;border-color:#d94b18;color:#00191d}
    .vh-l5-item{font-size:.92rem;line-height:1.45;margin:0 0 8px 0}
    .vh-l5-label{font-weight:700;color:#255a64}
    .vh-l5-iso-pane{background:rgba(202,255,116,.18);border:1px solid #90c44f;border-radius:8px;padding:12px 12px 8px;min-height:120px}
    .vh-l5-erm-pane{background:rgba(255,107,53,.12);border:1px solid #d94b18;border-radius:8px;padding:12px 12px 8px;min-height:120px}
    .vh-l5-pane-title{font-weight:700;color:#00191d;font-size:.96rem;margin:0 0 10px 0}
    .vh-l5-iso-coverage{font-size:.82rem;color:#255a64;margin:2px 0 10px 28px;line-height:1.35}
    .vh-l5-iso-coverage strong{color:#00191d}
    .vh-l5-risk-badge{display:inline-block;color:#00191d;background:#ffc9b0;border:1px solid #d94b18;border-radius:4px;padding:2px 7px;margin-right:8px;font-size:.9rem;font-weight:700;white-space:nowrap}
    .vh-l5-erm-coverage{font-size:.82rem;color:#8a3a18;margin:2px 0 10px 28px;line-height:1.35}
    .vh-l5-erm-coverage strong{color:#00191d}

    .vh-l5-risk-line{margin:0 0 6px 0;font-size:.9rem;line-height:1.4;padding:6px 8px;background:rgba(255,255,255,.72);border-radius:4px;border-left:3px solid #ff6b35}
    .vh-l5-risk-id{display:inline-block;font-weight:700;color:#00191d;margin-right:6px}
    .vh-l5-via-caption{display:block;font-size:.76rem;color:#6b7c80;margin-top:2px}
    .vh-l5-empty-slot{color:#6b7c80;font-size:.85rem;font-style:italic;margin:0 0 9px 0;padding:4px 0}
    .vh-l5-driver-slot{margin:0 0 9px 0;min-height:1.55em}
    div[data-testid="stPopover"] > button{
        min-height:40px;border:1px solid #a4c4e9;border-radius:8px;
        background:linear-gradient(135deg,#fff 0%,#e5f1ff 100%);
        color:#00191d;box-shadow:0 1px 2px rgba(0,25,29,.10);
        justify-content:flex-start;text-align:left;padding:7px 10px;
        transition:border-color .15s ease,box-shadow .15s ease,transform .15s ease;
    }
    div[data-testid="stPopover"] > button:hover{
        border-color:#397580;background:linear-gradient(135deg,#f8ffe9 0%,#e7ffbf 100%);
        box-shadow:0 3px 8px rgba(0,25,29,.18);transform:translateY(-1px);
    }
    div[data-testid="stPopover"] > button p{font-size:.92rem;font-weight:600;line-height:1.3}
    </style>
    <div class="vh-level">Level 0 · Overall objective</div>
    <div class="vh-box vh-top">0 · Maximize shareholder value in Trident<br><span style="font-weight:400">Equity Value ≈ (EBITDA × EV/EBITDA multiple) − NIBD</span></div>
    <div class="vh-level">Level 1 · AIP value levers</div>
    """, unsafe_allow_html=True)
    aip_cols = st.columns([2, 1, 2])
    aip_labels = [
        '<span class="vh-aip-badge">1.1</span> EBITDA',
        '<span class="vh-aip-badge">1.2</span> Multiple',
        '<span class="vh-aip-badge">1.3</span> Cash',
    ]
    for column, label in zip(aip_cols, aip_labels):
        with column:
            st.markdown(f'<div class="vh-box vh-aip">{label}</div>', unsafe_allow_html=True)

    groups = VALUE_HIERARCHY_GROUPS
    linked_processes_by_driver = {}
    if processes is not None and not processes.empty and "Linked Level 3 drivers" in processes.columns:
        for _, process in processes.iterrows():
            linked_refs = split_refs(process.get("Linked Level 3 drivers", ""))
            process_link = {
                "reference": process.get("S&BD Manual section", ""),
                "process_id": process.get("Process ID", ""),
                "process": process.get("Process", ""),
            }
            for reference in linked_refs:
                linked_processes_by_driver.setdefault(reference, []).append(process_link)

    linked_risks_by_driver = {}
    risks_for_drivers = risks if risks is not None else pd.DataFrame()
    if not risks_for_drivers.empty and "Level 3 drivers" in risks_for_drivers.columns:
        scored_for_drivers = (
            risks_for_drivers
            if "Residual score" in risks_for_drivers.columns
            else scored(risks_for_drivers)
        )
        for _, risk_row in scored_for_drivers.iterrows():
            risk_link = {
                "risk_id": str(risk_row.get("Risk ID", "")),
                "title": str(risk_row.get("Risk title", "")),
                "residual": risk_row.get("Residual score", ""),
            }
            for reference in split_refs(risk_row.get("Level 3 drivers", "")):
                linked_risks_by_driver.setdefault(reference, []).append(risk_link)

    st.markdown('<div class="vh-level">Level 2 · Trident value pillars — where Trident creates and protects value</div>', unsafe_allow_html=True)
    pillar_cols = st.columns(5)
    for column, (pillar, drivers) in zip(pillar_cols, groups):
        with column:
            st.markdown(f'<div class="vh-box vh-pil">{pillar}</div>', unsafe_allow_html=True)

    st.markdown('<div class="vh-level">Level 3 · Value drivers — how each pillar is delivered</div>', unsafe_allow_html=True)
    driver_cols = st.columns(5)
    for column, (pillar, drivers) in zip(driver_cols, groups):
        with column:
            with st.container(border=True, height=420):
                for reference, driver in drivers:
                    if reference == "divider":
                        st.markdown(f'<div class="vh-cfo-divider">{driver}</div>', unsafe_allow_html=True)
                        continue
                    linked_processes = linked_processes_by_driver.get(reference, [])
                    linked_risks = linked_risks_by_driver.get(reference, [])
                    with st.popover(f"{reference} · {driver}", use_container_width=True):
                        st.markdown("**Linked ISO-aligned S&BD processes**")
                        if linked_processes:
                            for process_link in linked_processes:
                                st.markdown(
                                    '<div class="vh-process-link">'
                                    f'<span class="vh-ref-badge">{escape(str(process_link["reference"]))}</span>'
                                    f'<span class="vh-process-id">{escape(str(process_link["process_id"]))}</span>'
                                    f'{escape(str(process_link["process"]))}</div>',
                                    unsafe_allow_html=True,
                                )
                        else:
                            st.caption("No ISO-aligned S&BD process is linked yet.")

                        st.markdown("**Linked ERM risks**")
                        if linked_risks:
                            # Deduplicate by risk id while preserving order
                            seen = set()
                            for risk_link in linked_risks:
                                rid = risk_link["risk_id"]
                                if not rid or rid in seen:
                                    continue
                                seen.add(rid)
                                residual = risk_link.get("residual", "")
                                try:
                                    score_txt = (
                                        f" · residual {int(float(residual))}"
                                        if residual is not None and str(residual).strip() != ""
                                        else ""
                                    )
                                except (TypeError, ValueError):
                                    score_txt = ""
                                st.markdown(
                                    '<div class="vh-process-link">'
                                    f'<span class="vh-l5-risk-badge">{escape(rid)}</span>'
                                    f'{escape(str(risk_link["title"]))}{escape(score_txt)}</div>',
                                    unsafe_allow_html=True,
                                )
                        else:
                            st.caption("No risks linked to this Level 3 driver yet.")

    st.markdown('<div class="vh-level">Level 4 · Applied across every pillar and value driver</div>', unsafe_allow_html=True)
    iso_col, erm_col = st.columns(2)
    with iso_col:
        st.markdown('<div class="vh-support vh-iso"><strong>4.1 · ISO-aligned delivery and follow-up</strong>Processes, owners, interfaces, procedures, controls, KPIs, documentation, evidence and continual improvement strengthen delivery of all five pillars.</div>', unsafe_allow_html=True)
    with erm_col:
        st.markdown('<div class="vh-support vh-erm"><strong>4.2 · ERM monitoring and protection</strong>Threats, risk assessments, controls, KRIs, appetite, mitigation and escalation protect all five pillars from adverse movement.</div>', unsafe_allow_html=True)

    st.markdown('<div class="vh-level">Level 5 · ISO-aligned Strategy &amp; Business Development process architecture</div>', unsafe_allow_html=True)
    if processes is None or processes.empty:
        st.caption("No processes defined for this register yet.")
        return

    driver_lookup = {
        reference: driver
        for _, drivers in groups
        for reference, driver in drivers
        if reference != "divider"
    }
    pillar_lookup = {
        "1": "PIL-01 · Organic EBITDA Growth",
        "2": "PIL-02 · Investment EBITDA Growth",
        "3": "PIL-03 · Multiple Expansion",
        "4": "PIL-04 · Cash Conversion",
        "5": "PIL-05 · Capital Allocation & Balance-Sheet Optimization",
    }
    risks_df = risks if risks is not None else pd.DataFrame(columns=COLUMNS["risks"])
    controls_df = controls if controls is not None else pd.DataFrame(columns=COLUMNS["controls"])
    actions_df = actions if actions is not None else pd.DataFrame(columns=COLUMNS["actions"])

    process_rows = processes.sort_values("Process ID")
    if risks_df.empty or "Risk ID" not in risks_df.columns:
        scored_risks_df = risks_df.copy()
    elif "Residual score" in risks_df.columns:
        scored_risks_df = risks_df
    else:
        scored_risks_df = scored(risks_df)
    st.caption(
        "Left: open a process for its Level 3 drivers (ISO). "
        "Right: open a pillar (e.g. PIL-01) to reveal its risks. "
        "Edit process links under More modules -> Processes & Process Owners."
    )
    iso_col, erm_col = st.columns(2, gap="medium")

    with iso_col:
        st.markdown(
            '<div class="vh-l5-iso-pane"><div class="vh-l5-pane-title">4.1 · ISO processes</div></div>',
            unsafe_allow_html=True,
        )
        for _, process in process_rows.iterrows():
            process_id = str(process.get("Process ID", ""))
            section = process.get("S&BD Manual section", "")
            process_name = process.get("Process", "")
            process_label = f"{section} · {process_id} · {process_name}"
            linked_refs = split_refs(process.get("Linked Level 3 drivers", ""))
            with st.expander(process_label, expanded=False):
                left_parts = [
                    '<div class="vh-l5-iso-pane">',
                    '<div class="vh-l5-pane-title">Level 3 value drivers supported by this process</div>',
                ]
                if not linked_refs:
                    left_parts.append('<div class="vh-l5-empty-slot">No Level 3 value drivers linked yet.</div>')
                else:
                    for pillar_number, pillar_name in pillar_lookup.items():
                        pillar_refs = [
                            reference
                            for reference in linked_refs
                            if reference.startswith(f"3.{pillar_number}.")
                        ]
                        if not pillar_refs:
                            continue
                        pillar_code, pillar_description = pillar_name.split(" · ", 1)
                        left_parts.append(
                            f'<div class="vh-process-pillar"><span class="vh-pil-badge">{escape(pillar_code)}</span>'
                            f'{escape(pillar_description)}</div>'
                        )
                        for reference in pillar_refs:
                            driver_name = driver_lookup.get(reference, "Value driver to be defined")
                            left_parts.append(
                                f'<div class="vh-driver-link vh-l5-driver-slot">'
                                f'<span class="vh-ref-badge">{escape(reference)}</span>{escape(driver_name)}</div>'
                            )
                left_parts.append("</div>")
                st.markdown("".join(left_parts), unsafe_allow_html=True)

    with erm_col:
        st.markdown(
            '<div class="vh-l5-erm-pane"><div class="vh-l5-pane-title">'
            "4.2 · ERM risk categories (five pillars)</div></div>",
            unsafe_allow_html=True,
        )
        st.caption("Open a pillar (e.g. PIL-01) to see risks grouped by Level 3 driver, top to bottom matching the chips above.")

        def risks_for_pillar(pillar_number, pillar_code):
            if scored_risks_df.empty:
                return pd.DataFrame()
            frames = []
            if "Level 3 drivers" in scored_risks_df.columns:
                driver_mask = scored_risks_df["Level 3 drivers"].astype(str).apply(
                    lambda value, n=pillar_number: any(
                        ref.startswith(f"3.{n}.") for ref in split_refs(value)
                    )
                )
                by_driver = scored_risks_df.loc[driver_mask]
                if not by_driver.empty:
                    frames.append(by_driver)
            if "Value pillars" in scored_risks_df.columns:
                pillar_mask = scored_risks_df["Value pillars"].astype(str).str.contains(pillar_code, na=False)
                by_pillar = scored_risks_df.loc[pillar_mask]
                if not by_pillar.empty:
                    frames.append(by_pillar)
            if not frames:
                return pd.DataFrame()
            combined = pd.concat(frames, ignore_index=True)
            if "Risk ID" in combined.columns:
                combined = combined.drop_duplicates(subset=["Risk ID"], keep="first")
            return combined

        for pillar_number, pillar_name in pillar_lookup.items():
            pillar_code, pillar_description = pillar_name.split(" · ", 1)
            pillar_risks = risks_for_pillar(pillar_number, pillar_code)
            count = 0 if pillar_risks.empty else len(pillar_risks)
            with st.expander(f"{pillar_code} · {pillar_description} ({count})", expanded=False):
                if pillar_risks.empty:
                    st.markdown(
                        '<div class="vh-l5-erm-pane"><div class="vh-l5-empty-slot">'
                        f'No risks linked to {escape(pillar_description)} yet.</div></div>',
                        unsafe_allow_html=True,
                    )
                    continue

                # ERM visual language: orange pane and risk chips (distinct from green ISO side)
                # Group by Level 3 drivers in hierarchy order (top-left to bottom-right).
                header_html = (
                    '<div class="vh-l5-erm-pane">'
                    '<div class="vh-l5-pane-title">Risks under this pillar - by Level 3 driver</div>'
                    f'<div class="vh-process-pillar"><span class="vh-pil-badge">{escape(pillar_code)}</span>'
                    f'{escape(pillar_description)}</div>'
                )
                # Map Process ID → "section · name" from ISO S&BD process definitions
                process_label_by_id = {}
                if processes is not None and not processes.empty:
                    for _, prow in processes.iterrows():
                        pid = str(prow.get("Process ID", "")).strip()
                        if not pid:
                            continue
                        section = str(prow.get("S&BD Manual section", "")).strip()
                        pname = str(prow.get("Process", "")).strip()
                        process_label_by_id[pid] = (
                            f"{section} · {pid} · {pname}" if section else f"{pid} · {pname}"
                        )

                pillar_driver_order = [
                    (reference, driver_name)
                    for reference, driver_name in groups[int(pillar_number) - 1][1]
                    if reference != "divider"
                ]

                def risk_chip_html(risk_row):
                    rid = str(risk_row.get("Risk ID", ""))
                    title = str(risk_row.get("Risk title", ""))
                    score_val = risk_row.get("Residual score", "")
                    try:
                        score_txt = (
                            f" · residual {int(float(score_val))}"
                            if pd.notna(score_val) and str(score_val).strip() != ""
                            else ""
                        )
                    except (TypeError, ValueError):
                        score_txt = ""
                    parts = [
                        f'<div class="vh-driver-link vh-l5-driver-slot">'
                        f'<span class="vh-l5-risk-badge">{escape(rid)}</span>'
                        f'{escape(title)}{escape(score_txt)}</div>'
                    ]
                    linked_procs = split_refs(risk_row.get("Processes", ""))
                    if linked_procs:
                        labels = [process_label_by_id.get(pid, pid) for pid in linked_procs]
                        coverage = "; ".join(labels)
                        parts.append(
                            '<div class="vh-l5-erm-coverage"><strong>ISO process coverage:</strong> '
                            f'{escape(coverage)}</div>'
                        )
                    else:
                        parts.append(
                            '<div class="vh-l5-erm-coverage"><strong>ISO process coverage:</strong> '
                            'Not yet linked to an S&amp;BD ISO process definition.</div>'
                        )
                    return "".join(parts)

                list_parts = [header_html]
                shown_ids = set()
                for reference, driver_name in pillar_driver_order:
                    if "Level 3 drivers" in pillar_risks.columns:
                        mask = pillar_risks["Level 3 drivers"].astype(str).apply(
                            lambda value, r=reference: r in split_refs(value)
                        )
                        driver_risks = pillar_risks.loc[mask]
                    else:
                        driver_risks = pillar_risks.iloc[0:0]
                    if "Risk ID" in driver_risks.columns and not driver_risks.empty:
                        driver_risks = driver_risks.sort_values("Risk ID")
                    list_parts.append(
                        f'<div class="vh-process-pillar" style="margin-top:10px;">'
                        f'<span class="vh-ref-badge">{escape(reference)}</span>'
                        f'{escape(driver_name)}</div>'
                    )
                    if driver_risks.empty:
                        list_parts.append(
                            '<div class="vh-l5-empty-slot">No risks linked to this Level 3 driver yet.</div>'
                        )
                    else:
                        for _, risk_row in driver_risks.iterrows():
                            rid = str(risk_row.get("Risk ID", ""))
                            shown_ids.add(rid)
                            list_parts.append(risk_chip_html(risk_row))

                # Risks tagged to the pillar but not yet to any Level 3 driver in this column
                if "Risk ID" in pillar_risks.columns:
                    orphan_mask = ~pillar_risks["Risk ID"].astype(str).isin(shown_ids)
                    orphan_risks = pillar_risks.loc[orphan_mask]
                else:
                    orphan_risks = pillar_risks.iloc[0:0]
                if not orphan_risks.empty:
                    list_parts.append(
                        '<div class="vh-process-pillar" style="margin-top:10px;">'
                        "Pillar-linked - Level 3 driver not set</div>"
                    )
                    if "Risk ID" in orphan_risks.columns:
                        orphan_risks = orphan_risks.sort_values("Risk ID")
                    for _, risk_row in orphan_risks.iterrows():
                        list_parts.append(risk_chip_html(risk_row))

                list_parts.append("</div>")
                st.markdown("".join(list_parts), unsafe_allow_html=True)


def extract_operational_questions(cause_text):
    """Pull Trident-side failure modes / numbered items from Cause for visual display."""
    import re as _re
    text_val = str(cause_text or "")
    upper = text_val.upper()
    if "TRIDENT-SIDE" in upper:
        idx = upper.find("TRIDENT-SIDE")
        chunk = text_val[idx:]
        found = _re.findall(r"\((\d+)\)\s*([^;]+?)(?=\s*\(\d+\)|$)", chunk)
        if found:
            return [item.strip(" .;") for _n, item in found if item.strip()]
        after = chunk.split(":", 1)[-1] if ":" in chunk else chunk
        parts = [p.strip(" .;") for p in after.split(";") if p.strip()]
        return parts[:8]
    bits = [b.strip() for b in text_val.replace(".", ";").split(";") if b.strip()]
    return bits[:5]




def extract_mitigation_bullets(mitigation_text):
    """Split Current mitigation into successive action bullets (numbered or semicolon lists)."""
    import re as _re
    text_val = str(mitigation_text or "").strip()
    if not text_val:
        return []
    found = _re.findall(r"\((\d+)\)\s*([^;]+?)(?=\s*\(\d+\)|$)", text_val)
    if found:
        return [item.strip(" .;") for _n, item in found if item.strip()]
    # Drop a short owner prefix like "S&BD+Commercial:" then split on semicolons
    if ":" in text_val and text_val.index(":") < 40:
        after = text_val.split(":", 1)[1].strip()
        if after:
            text_val = after
    parts = [p.strip(" .;") for p in text_val.split(";") if p.strip()]
    return parts if len(parts) > 1 else ([text_val] if text_val else [])


def render_risk_library(risks_df, processes_df=None):
    """Risk library in the same visual language as Context ERM (peach pane, chips), with ops questions."""
    # Belt-and-suspenders: ensure ERM pane classes exist even if brand theme was skipped.
    st.markdown(
        """
        <style>
        .vh-ref-badge{display:inline-block;color:#00191d;background:#caff74;border:1px solid #90c44f;border-radius:4px;padding:2px 7px;margin-right:8px;font-size:.9rem;font-weight:700;white-space:nowrap}
        .vh-pil-badge{display:inline-block;color:#00191d;background:#90c4ce;border:1px solid #255a64;border-radius:4px;padding:3px 8px;margin-right:8px;font-size:.9rem;font-weight:700;white-space:nowrap}
        .vh-driver-link{margin:0 0 9px 0;font-size:.96rem;line-height:1.6}
        .vh-process-pillar{margin:11px 0 8px;font-size:.98rem;font-weight:700}
        .vh-l5-erm-pane{background:rgba(255,107,53,.12);border:1px solid #d94b18;border-radius:8px;padding:12px 12px 8px;min-height:120px;margin-bottom:10px}
        .vh-l5-pane-title{font-weight:700;color:#00191d;font-size:.96rem;margin:0 0 10px 0}
        .vh-l5-risk-badge{display:inline-block;color:#00191d;background:#ffc9b0;border:1px solid #d94b18;border-radius:4px;padding:2px 7px;margin-right:8px;font-size:.9rem;font-weight:700;white-space:nowrap}
        .vh-l5-erm-coverage{font-size:.82rem;color:#8a3a18;margin:2px 0 10px 28px;line-height:1.35}
        .vh-l5-erm-coverage strong{color:#00191d}
        .vh-l5-empty-slot{color:#6b7c80;font-size:.85rem;font-style:italic;margin:0 0 9px 0;padding:4px 0}
        .vh-l5-driver-slot{margin:0 0 9px 0;min-height:1.55em}
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.write(
        "Same layout as **Context** Level 5 ERM: pillars → Level 3 drivers → risk chips. "
        "Under each risk: **what we can fail to do** and **what we can do** (ISO process links come later)."
    )
    catalog = level3_driver_catalog()
    scored_risks = scored(risks_df) if not risks_df.empty and "Risk ID" in risks_df.columns else risks_df.copy()
    if not scored_risks.empty and "Level 3 drivers" not in scored_risks.columns:
        scored_risks["Level 3 drivers"] = ""

    for pillar_label, _drivers in VALUE_HIERARCHY_GROUPS:
        plain = pillar_label.replace("<br>", " · ")
        pillar_id = plain.split("PIL-0")[1][:1] if "PIL-0" in plain else ""
        pillar_code = f"PIL-0{pillar_id}" if pillar_id else ""
        drivers_for_pillar = [row for row in catalog if row["pillar_id"] == pillar_code]
        # Last segment only — avoid "PIL-01 · PIL-01 · Organic EBITDA Growth"
        pillar_description = plain.rsplit(" · ", 1)[-1].strip() if " · " in plain else plain

        pillar_risk_ids = set()
        for row in drivers_for_pillar:
            ref = row["reference"]
            if scored_risks.empty:
                continue
            mask = scored_risks["Level 3 drivers"].astype(str).apply(lambda value, r=ref: r in split_refs(value))
            pillar_risk_ids.update(scored_risks.loc[mask, "Risk ID"].astype(str).tolist())
        count = len(pillar_risk_ids)

        with st.expander(f"{pillar_code} · {pillar_description} ({count})", expanded=(pillar_code == "PIL-01")):
            st.markdown(
                (
                    '<div class="vh-l5-erm-pane">'
                    '<div class="vh-l5-pane-title">Risks under this pillar - by Level 3 driver</div>'
                    f'<div class="vh-process-pillar"><span class="vh-pil-badge">{escape(pillar_code)}</span>'
                    f'{escape(pillar_description)}</div>'
                    "</div>"
                ),
                unsafe_allow_html=True,
            )

            for row in drivers_for_pillar:
                ref, driver_name = row["reference"], row["driver"]
                if scored_risks.empty:
                    linked = scored_risks
                else:
                    mask = scored_risks["Level 3 drivers"].astype(str).apply(
                        lambda value, r=ref: r in split_refs(value)
                    )
                    linked = scored_risks.loc[mask]
                if "Risk ID" in linked.columns and not linked.empty:
                    linked = linked.sort_values("Risk ID")

                # Build one self-contained peach pane for this Level 3 driver
                parts = [
                    '<div class="vh-l5-erm-pane">',
                    (
                        f'<div class="vh-process-pillar">'
                        f'<span class="vh-ref-badge">{escape(ref)}</span>'
                        f'{escape(driver_name)}</div>'
                    ),
                ]

                if linked.empty:
                    parts.append(
                        '<div class="vh-l5-empty-slot">'
                        "No risks linked to this Level 3 driver yet.</div>"
                    )
                    parts.append("</div>")
                    st.markdown("".join(parts), unsafe_allow_html=True)
                    continue

                seen = set()
                for _, risk_row in linked.iterrows():
                    rid = str(risk_row.get("Risk ID", "")).strip()
                    if not rid or rid in seen:
                        continue
                    seen.add(rid)
                    title = str(risk_row.get("Risk title", ""))
                    residual = risk_row.get("Residual score", "")
                    try:
                        score_txt = (
                            f" · residual {int(float(residual))}"
                            if residual is not None and str(residual).strip() != ""
                            else ""
                        )
                    except (TypeError, ValueError):
                        score_txt = ""

                    parts.append(
                        f'<div class="vh-driver-link vh-l5-driver-slot">'
                        f'<span class="vh-l5-risk-badge">{escape(rid)}</span>'
                        f'{escape(title)}{escape(score_txt)}</div>'
                    )

                    questions = extract_operational_questions(risk_row.get("Cause", ""))
                    if questions:
                        q_html = "".join(
                            f"<li>{escape(q.rstrip(' ?'))}?</li>" for q in questions
                        )
                        parts.append(
                            '<div class="vh-l5-erm-coverage"><strong>What we can fail to do:</strong>'
                            '<ul style="margin:4px 0 0 18px;padding:0;">'
                            f"{q_html}</ul></div>"
                        )
                    else:
                        parts.append(
                            '<div class="vh-l5-erm-coverage"><strong>What we can fail to do:</strong>'
                            '<ul style="margin:4px 0 0 18px;padding:0;">'
                            "<li>Not yet operationalized — fill Trident-side failure modes in Assess &amp; decide.</li>"
                            "</ul></div>"
                        )

                    mitigation = str(risk_row.get("Current mitigation", "") or "").strip()
                    treatment = str(risk_row.get("Treatment decision", "") or "").strip()
                    bullets = extract_mitigation_bullets(mitigation)
                    if bullets:
                        m_html = "".join(f"<li>{escape(b)}</li>" for b in bullets)
                        treat_note = (
                            f' <em>(Treatment: {escape(treatment)})</em>' if treatment else ""
                        )
                        parts.append(
                            '<div class="vh-l5-erm-coverage"><strong>What we can do:</strong>'
                            f"{treat_note}"
                            '<ul style="margin:4px 0 0 18px;padding:0;">'
                            f"{m_html}</ul></div>"
                        )
                    else:
                        parts.append(
                            '<div class="vh-l5-erm-coverage"><strong>What we can do:</strong>'
                            '<ul style="margin:4px 0 0 18px;padding:0;">'
                            "<li>No mitigation text yet — fill Current mitigation in Assess &amp; decide.</li>"
                            "</ul></div>"
                        )

                parts.append("</div>")
                st.markdown("".join(parts), unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("Add risk into a library slot")
    with st.form(key=f"add_risk_slot_{ACTIVE_REGISTER_KEY}"):
        ref_choices = [f"{row['reference']} · {row['driver']}" for row in catalog]
        chosen = st.selectbox("Level 3 driver slot", ref_choices)
        new_id = st.text_input("Risk ID", value="")
        new_title = st.text_input("Risk title", value="")
        new_category = st.selectbox("Category", RISK_CATEGORIES)
        submitted = st.form_submit_button("Create draft risk in slot", type="primary")
        if submitted:
            ref = chosen.split(" · ", 1)[0].strip()
            pillar_for_ref = next((row["pillar_id"] for row in catalog if row["reference"] == ref), "")
            if not new_id.strip() or not new_title.strip():
                st.error("Risk ID and Risk title are required.")
            else:
                master = load("risks")
                if "Level 3 drivers" not in master.columns:
                    insert_at = (
                        list(master.columns).index("Value effects") + 1
                        if "Value effects" in master.columns
                        else len(master.columns)
                    )
                    master.insert(insert_at, "Level 3 drivers", "")
                if (master["Risk ID"].astype(str) == new_id.strip()).any():
                    st.error(f"Risk ID {new_id.strip()} already exists.")
                else:
                    blank = {column: "" for column in master.columns}
                    blank.update({
                        "Risk ID": new_id.strip(),
                        "Category": new_category,
                        "Risk title": new_title.strip(),
                        "Value pillars": pillar_for_ref,
                        "Level 3 drivers": ref,
                        "Appetite status": "Within appetite",
                        "Trend": "Stable",
                        "Status": "Draft",
                        "Enterprise escalation": "No",
                        "Evidence / rationale": "Draft library entry – validate",
                        "Inherent likelihood": "1",
                        "Inherent impact": "1",
                        "Residual likelihood": "1",
                        "Residual impact": "1",
                        "Target likelihood": "1",
                        "Target impact": "1",
                    })
                    master = pd.concat([master, pd.DataFrame([blank])], ignore_index=True)
                    save("risks", master)
                    st.success(f"Created {new_id.strip()} under {ref}.")
                    st.rerun()





# Strategy retains seed + migration on strategy_*.csv (backward compatible).
set_active_register("strategy")
seed_data()
migrate_existing_data()

st.set_page_config(page_title="Trident IMS & ERM", page_icon="△", layout="wide")
apply_brand_theme()

register_options = [name for name, _owner, _title in UNITS] + [ENTERPRISE_REGISTER]
selected_register = st.sidebar.selectbox("Risk register", register_options, index=0)
with st.sidebar.expander("Configured ERM registers"):
    for unit, owner, title in UNITS:
        st.write(f"**{unit}**  \n{owner}, {title}")
    st.write("**Enterprise Risk Register**  \nConsolidated material risks from unit registers")

st.title("Trident Integrated Management & Enterprise Risk System")

if selected_register == ENTERPRISE_REGISTER:
    st.caption("Enterprise roll-up | Material risks across all unit registers")
    render_enterprise_view()
    st.stop()

owner, title = UNIT_BY_NAME[selected_register]
register_key = REGISTER_KEYS[selected_register]
set_active_register(register_key)
ensure_register_files(register_key)
st.caption(f"{selected_register} | Accountable executive: {owner} ({title})")

data = {key: load(key) for key in FILES}
risks = scored(data["risks"]) if not data["risks"].empty else scored(pd.DataFrame(columns=COLUMNS["risks"]))

def render_dashboard_heatmap(risks_df, actions_df):
    """Compact Strategy heatmap view - the near-term output."""
    basis = st.radio("Heatmap basis", ["Residual", "Inherent", "Target"], horizontal=True, key=f"hm_basis_{ACTIVE_REGISTER_KEY}")
    due = pd.to_datetime(actions_df.get("Due date", pd.Series(dtype=str)), errors="coerce").dt.date
    if not actions_df.empty and "Status" in actions_df.columns:
        overdue = (due < date.today()) & ~actions_df["Status"].isin(["Completed", "Cancelled"])
    else:
        overdue = pd.Series(False, index=actions_df.index)
    cols = st.columns(4)
    cols[0].metric("Open risks", int((risks_df["Status"] != "Closed").sum()) if not risks_df.empty and "Status" in risks_df.columns else 0)
    cols[1].metric("Outside appetite", int((risks_df["Appetite status"] == "Outside appetite").sum()) if not risks_df.empty and "Appetite status" in risks_df.columns else 0)
    cols[2].metric("Enterprise escalation", int((risks_df["Enterprise escalation"] == "Yes").sum()) if not risks_df.empty and "Enterprise escalation" in risks_df.columns else 0)
    cols[3].metric("Overdue actions", int(overdue.sum()) if hasattr(overdue, "sum") else 0)
    left, right = st.columns([1.2, 1])
    with left:
        st.subheader(f"{basis} risk heatmap")
        st.plotly_chart(heatmap(risks_df, basis), use_container_width=True)
    with right:
        st.subheader("Risks requiring attention")
        show_cols = [c for c in ["Risk ID", "Risk title", "Residual score", "Appetite status", "Trend", "Status"] if c in risks_df.columns]
        if show_cols and not risks_df.empty:
            st.dataframe(risks_df.sort_values("Residual score", ascending=False)[show_cols], hide_index=True, use_container_width=True)
        else:
            st.info("No scored risks yet.")
        st.subheader("Treatment actions")
        action_cols = [c for c in ["Action ID", "Risk ID", "Action", "Due date", "Status", "Progress %"] if c in actions_df.columns]
        if action_cols and not actions_df.empty:
            st.dataframe(actions_df[action_cols], hide_index=True, use_container_width=True)
        else:
            st.caption("No actions yet.")
    st.subheader("Exposure by shareholder-value pillar")
    pillar_rows = []
    for pillar_id, pillar_name in [
        ("PIL-01", "Organic EBITDA growth"),
        ("PIL-02", "Investment EBITDA growth"),
        ("PIL-03", "Multiple expansion"),
        ("PIL-04", "Cash conversion"),
        ("PIL-05", "Capital allocation & balance sheet"),
    ]:
        if risks_df.empty or "Value pillars" not in risks_df.columns:
            pillar_rows.append([pillar_name, 0, 0, 0])
            continue
        linked = risks_df[risks_df["Value pillars"].astype(str).str.contains(pillar_id, na=False)]
        pillar_rows.append([
            pillar_name,
            len(linked),
            int(linked["Residual score"].sum()) if "Residual score" in linked.columns and not linked.empty else 0,
            int((linked["Appetite status"] == "Outside appetite").sum()) if "Appetite status" in linked.columns and not linked.empty else 0,
        ])
    st.dataframe(
        pd.DataFrame(pillar_rows, columns=["Value pillar", "Linked risks", "Aggregate residual score", "Outside appetite"]),
        hide_index=True,
        use_container_width=True,
    )
    st.warning("Scores are drafts until Strategy & BD validates inherent/residual/appetite.")


core_pages = [
    "00 Context",
    "01 Risks & Opportunities",
    "02 Heatmap",
    "03 Ownership",
]
more_pages = [
    "(use core path above)",
    "Actions & target risk",
    "Processes & Process Owners",
    "Controls, Policies & Procedures",
    "Interfaces & Dependencies",
    "KPIs, KRIs & Process Performance",
    "Documents & Evidence",
    "Audits, Findings & Improvements",
    "Reporting & History",
    "ISO Alignment Matrix",
]

page = st.sidebar.radio("Strategy & BD path", core_pages, key=f"workflow_v4_{register_key}")
with st.sidebar.expander("More modules (later)"):
    more = st.selectbox("Open module", more_pages, key=f"workflow_more_v4_{register_key}")
    st.caption("Detailed action plans live under More modules when you need them.")
if more != "(use core path above)":
    page = more
st.sidebar.caption("Path: Context -> Risks (score, mitigate, appetite) -> Heatmap. Ownership when allocating departments.")

if page == "02 Heatmap" or page == "03 Heatmap" or str(page).startswith("01 Dashboard"):
    st.subheader("Dashboard and heatmap")
    st.caption("Default view: **Residual** score (likelihood x impact after current controls). That is the working Strategy & BD picture.")
    render_dashboard_heatmap(risks, data["actions"])
elif page == "00 Context" or str(page).startswith("00 Value"):
    st.subheader("Shareholder value framework")
    render_value_hierarchy(data["processes"], data["risks"], data["controls"], data["actions"])
    st.caption(
        "Context for Strategy & BD. Risks should link to Level 3 drivers and pillars. "
        "Score risks in **01 Risks & Opportunities**, then open **02 Heatmap**."
    )
elif page == "01 Risks & Opportunities" or str(page).startswith("02 Risks"):
    risks_work = ensure_risk_treatment_columns(data["risks"])
    data["risks"] = risks_work
    t_lib, t_reg, t_assess, t_opp = st.tabs(["Risk library", "Risk register", "Assess & decide", "Opportunities"])
    with t_lib:
        render_risk_library(risks_work, data.get("processes"))
    with t_reg:
        st.write("Shared Strategy & BD risk inventory. Use **Assess & decide** for mitigation, residual score, and appetite.")
        risk_config = {
            "Category": st.column_config.SelectboxColumn(options=RISK_CATEGORIES),
            "Appetite status": st.column_config.SelectboxColumn(options=APPETITE),
            "Trend": st.column_config.SelectboxColumn(options=TRENDS),
            "Status": st.column_config.SelectboxColumn(options=STATUSES),
            "Enterprise escalation": st.column_config.SelectboxColumn(options=["Yes", "No"]),
            "Treatment decision": st.column_config.SelectboxColumn(options=TREATMENT_DECISIONS),
        }
        editor("risks", risks_work, risk_config)
    with t_assess:
        st.markdown(
            """
**How to use this tab (Strategy & BD fast path)**

1. **Current mitigation** — what already reduces the risk (process, control, contract term, review).
2. **Residual** — score likelihood and impact **after** that mitigation (1–5 each). This feeds the heatmap.
3. **Treatment decision** — Treat / Accept / Monitor / Transfer / Avoid.
4. **Appetite** — Within / Approaching / Outside. If you **Accept**, set Status to Accepted and Appetite to Within (or Approaching with a reason).
5. Open **02 Heatmap** when residual scores are good enough to review.
            """.strip()
        )
        t_mit, t_res, t_dec = st.tabs(["1. Mitigation -> residual", "2. Residual scores", "3. Accept / appetite"])
        with t_mit:
            c = ["Risk ID", "Risk title", "Current mitigation", "Treatment decision", "Residual likelihood", "Residual impact"]
            e = st.data_editor(
                risks_work[c],
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Treatment decision": st.column_config.SelectboxColumn(options=TREATMENT_DECISIONS),
                    "Current mitigation": st.column_config.TextColumn(width="large"),
                },
                key=f"score_mit_{ACTIVE_REGISTER_KEY}",
            )
            if st.button("Save mitigation and residual", type="primary", key=f"save_mit_{ACTIVE_REGISTER_KEY}"):
                update_risks(e, ["Current mitigation", "Treatment decision", "Residual likelihood", "Residual impact"])
        with t_res:
            st.caption("Same residual fields — use if you prefer a tight scoring grid.")
            c = ["Risk ID", "Risk title", "Inherent likelihood", "Inherent impact", "Residual likelihood", "Residual impact"]
            e = st.data_editor(risks_work[c], hide_index=True, use_container_width=True, key=f"score_res2_{ACTIVE_REGISTER_KEY}")
            if st.button("Save inherent and residual scores", type="primary", key=f"save_residual_{ACTIVE_REGISTER_KEY}"):
                update_risks(e, c[-4:])
        with t_dec:
            st.caption(
                "Accept the residual: set Treatment decision = Accept, Appetite = Within appetite (or Approaching with rationale), Status = Accepted. "
                "Outside appetite usually means Treat or escalate."
            )
            c = ["Risk ID", "Risk title", "Treatment decision", "Appetite status", "Status", "Enterprise escalation", "Evidence / rationale"]
            e = st.data_editor(
                risks_work[c],
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Treatment decision": st.column_config.SelectboxColumn(options=TREATMENT_DECISIONS),
                    "Appetite status": st.column_config.SelectboxColumn(options=APPETITE),
                    "Status": st.column_config.SelectboxColumn(options=STATUSES),
                    "Enterprise escalation": st.column_config.SelectboxColumn(options=["Yes", "No"]),
                },
                key=f"score_dec_{ACTIVE_REGISTER_KEY}",
            )
            if st.button("Save acceptance and appetite", type="primary", key=f"save_appetite_{ACTIVE_REGISTER_KEY}"):
                update_risks(e, ["Treatment decision", "Appetite status", "Status", "Enterprise escalation", "Evidence / rationale"])
        st.info("Detailed multi-step action plans remain under **More modules → Actions & target risk** if you need them later.")
    with t_opp:
        editor("opportunities", data["opportunities"])
elif page == "03 Ownership" or page == "04 Ownership" or str(page).startswith("03 Ownership"):
    render_ownership_page(data["risks"])
elif page in ("04 Actions", "05 Actions", "Actions & target risk") or str(page).startswith("09 Responses"):
    st.subheader("Responses, actions and target risk")
    t1, t2 = st.tabs(["Treatment actions", "Target risk"])
    with t1:
        editor(
            "actions",
            data["actions"],
            {
                "Risk ID": st.column_config.SelectboxColumn(options=data["risks"]["Risk ID"].tolist()),
                "Status": st.column_config.SelectboxColumn(options=["Not started", "In progress", "Blocked", "Completed", "Cancelled"]),
                "Due date": st.column_config.DateColumn(format="DD.MM.YYYY"),
                "Progress %": st.column_config.NumberColumn(min_value=0, max_value=100, step=5),
            },
        )
    with t2:
        c = ["Risk ID", "Risk title", "Target likelihood", "Target impact"]
        e = st.data_editor(data["risks"][c], hide_index=True, use_container_width=True)
        if st.button("Save target risk", type="primary", key=f"save_target_{ACTIVE_REGISTER_KEY}"):
            update_risks(e, c[-2:])
elif page == "Processes & Process Owners" or str(page).startswith("04 Processes"):
    st.subheader("Processes and process owners")
    st.write("Complete a high-level plan first: purpose, inputs, main activities, outputs, interfaces and review frequency.")
    editor("processes", data["processes"])
elif page == "Controls, Policies & Procedures" or str(page).startswith("06 Controls"):
    st.subheader("Controls, policies and procedures")
    editor(
        "controls",
        data["controls"],
        {
            "Risk ID": st.column_config.SelectboxColumn(options=data["risks"]["Risk ID"].tolist()),
            "Control type": st.column_config.SelectboxColumn(options=["Preventive", "Detective", "Corrective"]),
            "Effectiveness": st.column_config.SelectboxColumn(options=["Not assessed", "Ineffective", "Partly effective", "Effective"]),
        },
    )
elif page == "Interfaces & Dependencies" or str(page).startswith("10 Interfaces"):
    st.subheader("Departmental interfaces and dependencies")
    st.caption("Process interfaces and escalation flags. Department mitigation roles are in **03 Ownership**.")
    c = ["Risk ID", "Risk title", "Processes", "Affected units", "Enterprise escalation"]
    e = st.data_editor(data["risks"][c], hide_index=True, use_container_width=True)
    if st.button("Save dependencies", type="primary", key=f"save_deps_{ACTIVE_REGISTER_KEY}"):
        update_risks(e, c[-3:])
elif page == "KPIs, KRIs & Process Performance" or str(page).startswith("11 KPIs"):
    st.subheader("KPIs, KRIs and process performance")
    st.info("Indicator register with thresholds and trend history comes later.")
    st.dataframe(data["processes"][["Process ID", "Process", "Process owner", "Review frequency"]], hide_index=True, use_container_width=True)
elif page == "Documents & Evidence" or str(page).startswith("12 Documents"):
    st.subheader("Documents and evidence")
    st.write("Evidence references are currently on controls, risks and actions.")
    st.dataframe(data["controls"][["Control ID", "Risk ID", "Control", "Evidence"]], hide_index=True, use_container_width=True)
elif page == "Audits, Findings & Improvements" or str(page).startswith("13 Audits"):
    st.subheader("Audits, findings and improvements")
    st.info("Shared IMS audit module comes later.")
    st.dataframe(data["actions"], hide_index=True, use_container_width=True)
elif page == "Reporting & History" or str(page).startswith("14 Reporting"):
    st.subheader("Reporting and history")
    ent_risks = collect_enterprise_risks()
    ent_actions = collect_enterprise_actions(ent_risks)
    export_name = selected_register.replace(" ", "_").replace("&", "and")
    st.download_button(
        f"Download {selected_register} ERM workbook",
        workbook(data, enterprise_risks=ent_risks, enterprise_actions=ent_actions, source_label=selected_register),
        file_name=f"Trident_{export_name}_ERM_{date.today().isoformat()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
        key=f"download_{ACTIVE_REGISTER_KEY}",
    )
else:
    st.subheader("ISO alignment matrix")
    st.write("Navigation aid only - not a certification conclusion.")
    matrix = pd.DataFrame(ISO_MATRIX_ROWS, columns=["Management-system element", "Reference", "Application in this model", "Linked S&BD processes"])
    st.dataframe(matrix, hide_index=True, use_container_width=True)
    st.caption("ISO 31000 and ISO 26000 provide guidance rather than certifiable requirements.")
