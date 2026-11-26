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
    ("CEO Office", "Arild Aasmyr", "Chief Executive Officer"),
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
    "CEO Office": "ceo",
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

# Executive functions (CEO + eight departments) used for Level III driver ownership.
FUNCTIONS = [
    ("CEO", "Arild Aasmyr"),
    ("Strategy & Business Development", "Trond V. Thomson"),
    ("Finance", "Øyvind Folland"),
    ("Commercial", "Joar Gjerde"),
    ("Vessel Operations", "Kjetil Opshaug"),
    ("Technical & HSEQ", "Raymond Kaspersen"),
    ("HR", "Hanne Beate Melby"),
    ("Administration & ICT", "Ida Juul-Jørgensen"),
    ("Legal & Compliance", "Ove Paulsen"),
]
FUNCTION_NAMES = [name for name, _head in FUNCTIONS]
FUNCTION_HEAD = dict(FUNCTIONS)
# Unit registers -> executive function. Chile and Shetland are geographies that contribute to
# the same drivers as the functions; they have no driver ownership of their own.
REGISTER_FUNCTION = {
    "CEO Office": "CEO",
    "Chile Operations": "Vessel Operations",
    "Shetland Operations": "Vessel Operations",
    "Strategy & Business Development": "Strategy & Business Development",
    "Finance": "Finance",
    "Commercial": "Commercial",
    "Vessel Operations": "Vessel Operations",
    "Technical & HSEQ": "Technical & HSEQ",
    "Crewing": "HR",
    "Onshore Employees & Organization": "HR",
    "Administration": "Administration & ICT",
    "ICT": "Administration & ICT",
    "Legal & Compliance": "Legal & Compliance",
}
# Department folders: one per executive function, plus the Enterprise roll-up.
# (folder label, function name, registers inside the folder)
FOLDERS = [
    ("CEO", "CEO", ["CEO Office"]),
    ("Strategy & BD", "Strategy & Business Development", ["Strategy & Business Development"]),
    ("Finance", "Finance", ["Finance"]),
    ("Commercial", "Commercial", ["Commercial"]),
    ("Vessel Operations", "Vessel Operations", ["Vessel Operations", "Chile Operations", "Shetland Operations"]),
    ("Technical & HSEQ", "Technical & HSEQ", ["Technical & HSEQ"]),
    ("HR", "HR", ["Crewing", "Onshore Employees & Organization"]),
    ("Admin & ICT", "Administration & ICT", ["Administration", "ICT"]),
    ("Legal & Compliance", "Legal & Compliance", ["Legal & Compliance"]),
    ("Enterprise", None, ["Enterprise Risk Register"]),
    ("Operating Agenda", None, ["Operating Agenda"]),
    ("About IMERS", None, ["About IMERS"]),
]
OPERATING_AGENDA = "Operating Agenda"
ABOUT_IMERS = "About IMERS"
EXPORTS_DIR_NAME = "exports"
IMERS_DECK_NAME = "IMERS_concept_management_group"
# Short C-level titles used on the Level III tags.
CLEVEL_TITLE = {
    "CEO": "CEO", "Strategy & Business Development": "CS&BDO", "Finance": "CFO", "Commercial": "CCO",
    "Vessel Operations": "COO", "Technical & HSEQ": "CHSEQ", "HR": "CHR",
    "Administration & ICT": "CAO", "Legal & Compliance": "CLO",
}
# Suggested main delivering process per accountable driver (to be confirmed by each executive).
MAIN_PROCESS_SUGGESTION = {
    "3.1.1": "SBD-P05 Long-term operating agenda and rate uplift",
    "3.2.1": "SBD-P04 Business case development + SBD-P07 Capital project governance",
    "3.2.3": "SBD-P08 M&A and strategic partnerships",
    "3.3.6": "SBD-P06 Fleet portfolio optimization and divestment",
    "3.5.4": "SBD-P06 Fleet portfolio optimization and divestment",
}
# Department codes for risk (R) and process (P) IDs. SBD is in use; the others are proposed.
DEPARTMENT_CODES = [
    ("CEO", "CEO Office"), ("SBD", "Strategy & Business Development"), ("FIN", "Finance"), ("COM", "Commercial"),
    ("OPS", "Vessel Operations"), ("HSQ", "Technical & HSEQ"), ("HR", "HR"), ("ADM", "Administration & ICT"),
    ("LEG", "Legal & Compliance"),
]
ABBREVIATIONS = [
    ("AIP-01–03", "AIP's three value drivers – EBITDA, multiple and cash (Level I levers 1.1–1.3)"),
    ("PIL-01–05", "PIL = pillar: the five Level II value pillars 2.1–2.5. A fixed ID, so risks and processes stay tagged even if a pillar is renamed"),
    ("3.x.y", "A Level III value driver: Level III · pillar x · driver y (35 in total)"),
    ("SBD-R001 · SBD-P04", "Department code + R (risk) or P (process) + number, e.g. Strategy & BD risk no. 001"),
    ("EBITDA", "Earnings before interest, taxes, depreciation and amortisation"),
    ("EV", "Enterprise value"), ("NIBD", "Net interest-bearing debt"),
    ("Capex", "Capital expenditure"), ("FID", "Final investment decision"),
    ("ROIC", "Return on invested capital"), ("DSO", "Days sales outstanding"),
    ("M&A", "Mergers and acquisitions"), ("SLB", "Sale-leaseback"),
    ("SFaaS", "Salmon Farming as a Service"),
    ("ISO", "International Organization for Standardization"),
    ("IMS", "Integrated Management System"), ("ERM", "Enterprise Risk Management"),
    ("IMERS", "Integrated Management & Enterprise Risk System"),
    ("KPI / KRI", "Key performance indicator / key risk indicator"),
    ("HSEQ", "Health, safety, environment and quality"),
    ("ICT", "Information and communication technology"),
    ("HR", "Human resources"), ("S&BD / SBD / BD", "Strategy & Business Development"),
    ("Ops", "Vessel Operations"),
    ("CEO", "Chief executive officer"), ("CS&BDO", "Chief strategy & business development officer"),
    ("CFO", "Chief financial officer"), ("CCO", "Chief commercial officer"), ("COO", "Chief operating officer"),
    ("CHSEQ", "Chief HSEQ officer"), ("CHR", "Chief HR officer"), ("CAO", "Chief administrative officer"),
    ("CLO", "Chief legal officer"),
]
DEFAULT_FOLDER = "Strategy & BD"
DRIVER_OWNERSHIP_COLUMNS = ["Level 3 ref", "Accountable function", "Contributing functions", "Notes"]
_SBD, _FIN, _COM, _OPS, _TEC, _HR, _ADM, _LEG = FUNCTION_NAMES[1:]
DRIVER_OWNERSHIP_SEED = [
    ("3.1.1", _SBD, [_COM, _FIN, _OPS]),
    ("3.1.2", _OPS, [_COM, _TEC, _HR]),
    ("3.1.3", _COM, [_LEG, _FIN]),
    ("3.1.4", _OPS, [_TEC, _HR]),
    ("3.1.5", _OPS, [_HR, _ADM, _TEC]),
    ("3.1.6", _SBD, [_TEC, _OPS, _FIN, _COM]),
    ("3.2.1", _SBD, [_FIN, _TEC, _COM]),
    ("3.2.2", _SBD, [_FIN, _TEC, _LEG]),
    ("3.2.3", _SBD, [_FIN, _LEG, _HR]),
    ("3.2.4", _SBD, [_FIN, _COM, _TEC]),
    ("3.3.1", _COM, [_SBD, _FIN]),
    ("3.3.2", _COM, [_LEG, _SBD]),
    ("3.3.3", _COM, [_FIN, _LEG]),
    ("3.3.4", _FIN, [_COM, _OPS]),
    ("3.3.5", _TEC, [_SBD, _OPS]),
    ("3.3.6", _SBD, [_TEC, _FIN]),
    ("3.3.7", _FIN, ["CEO", _ADM, _LEG]),
    ("3.3.8", "CEO", [_SBD, _HR, _ADM]),
    ("3.3.9", _HR, ["CEO", _OPS]),
    ("3.3.10", _TEC, [_OPS, _HR]),
    ("3.3.11", _LEG, [_TEC, _FIN]),
    ("3.3.12", _ADM, [_FIN, _OPS]),
    ("3.4.1", _FIN, [_COM, _OPS]),
    ("3.4.2", _OPS, [_TEC, _FIN]),
    ("3.4.3", _FIN, [_COM, _ADM]),
    ("3.4.4", _FIN, [_COM]),
    ("3.4.5", _FIN, []),
    ("3.4.6", _FIN, [_LEG]),
    ("3.5.1", "CEO", [_FIN, _SBD]),
    ("3.5.2", _FIN, [_SBD]),
    ("3.5.3", _FIN, [_SBD]),
    ("3.5.4", _SBD, [_FIN, _TEC]),
    ("3.5.5", _FIN, []),
    ("3.5.6", _FIN, []),
    ("3.5.7", _FIN, [_SBD]),
]
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
        ("3.1.6", "Value-accretive reconstruction of owned vessels"),
    ]),
    ("2.2 · PIL-02<br>Investment EBITDA Growth", [
        ("3.2.1", "Value-accretive newbuilds"),
        ("3.2.2", "Second-hand vessel acquisitions and sale-leasebacks"),
        ("3.2.3", "M&A and identifiable synergies"),
        ("3.2.4", "Profitable new platforms such as SFaaS"),
    ]),
    ("2.3 · PIL-03<br>Multiple Expansion", [
        ("3.3.1", "Earnings visibility"), ("3.3.2", "Long-term contract coverage"),
        ("3.3.3", "Customer and counterparty quality"), ("3.3.4", "Reduced EBITDA volatility"),
        ("3.3.5", "Fleet quality and residual-value protection"),
        ("3.3.6", "Modernize through vessel divestments and replacements"),
        ("divider", "Strong operating platform"),
        ("3.3.7", "Governance and reliable reporting"),
        ("3.3.8", "Scalable operating model and integration capability"),
        ("3.3.9", "People, competence, leadership and succession"),
        ("3.3.10", "HSEQ performance: safety, environment, quality and ESG"),
        ("3.3.11", "Regulatory compliance and legal robustness"),
        ("3.3.12", "Plug-and-play administrative platform and cyber resilience"),
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
    """Full Level III tree (3.1.1–3.5.7), excluding divider rows."""
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
        ("SBD-P01", "Long-term strategic planning", "4.1"), ("SBD-P02", "Market intelligence interpretation", "4.2"),
        ("SBD-P03", "Opportunity identification and evaluation", "4.3"), ("SBD-P04", "Business case development", "4.4"),
        ("SBD-P05", "Long-term operating agenda and rate uplift", "4.5"), ("SBD-P06", "Fleet portfolio optimization and divestment", "4.6"),
        ("SBD-P07", "Capital project governance", "4.7"), ("SBD-P08", "M&A and strategic partnerships", "4.8"),
        ("SBD-P09", "Strategic risk integration", "4.9"), ("SBD-P10", "Sustainability strategy integration", "4.10"),
        ("SBD-P11", "Sustainability Statement and CSRD", "4.11"), ("SBD-P12", "Strategy execution and monitoring", "4.12"),
        ("SBD-P13", "Value realization and strategic portfolio review", "4.13"),
    ]
    seed(FILES["processes"], [[pid, name, "Trond V. Thomson", "To be defined", "To be defined", "To be defined", "To be defined", "To be defined", "Quarterly", section] for pid, name, section in process_names],
         ["Process ID", "Process", "Process owner", "Purpose", "Trigger / inputs", "Main activities", "Outputs", "Interfaces", "Review frequency", "S&BD Manual section"])
    risk_cols = COLUMNS["risks"]
    seed(FILES["risks"], [
        ["SBD-R001", "Fleet & capacity", "Investment in fleet capacity that does not match future demand", "OBJ-02; OBJ-03", "PIL-01; PIL-02", "EBITDA; Multiple; Cash/NIBD", "3.1.2; 3.2.1; 3.1.6; 3.2.2", "SBD-P02; SBD-P04; SBD-P06; SBD-P07", "Uncertain forecasts of salmon production, customer demand and competitor capacity", "Trident commits capital to vessel segments or geographies with insufficient demand", "Low utilization, reduced returns and constrained financial flexibility", "Trond V. Thomson", "", "Finance; Commercial; Vessel Operations", "1–3 years", "Medium", 4, 5, 3, 4, 2, 3, "Outside appetite", "Increasing", "Treatment in progress", "Yes", "Illustrative – validate"],
        ["SBD-R002", "Strategy execution", "Strategic initiatives fail to translate into accountable execution", "OBJ-01; OBJ-04", "PIL-01; PIL-03", "EBITDA; Multiple", "3.3.7; 3.3.8; 3.1.1", "SBD-P01; SBD-P12", "Insufficient ownership, capacity, milestones or cross-functional alignment", "Material strategic initiatives are delayed or incompletely implemented", "Growth, integration and value-creation targets are not achieved", "Trond V. Thomson", "", "All units", "0–12 months", "Medium", 4, 4, 3, 3, 2, 2, "Approaching appetite", "Stable", "Treatment in progress", "Yes", "Illustrative – validate"],
        ["SBD-R003", "New business models", "SFaaS expansion creates exposures outside established capabilities", "OBJ-03; OBJ-05", "PIL-02; PIL-03", "EBITDA; Multiple; Cash/NIBD", "3.2.4; 3.2.3; 3.3.8", "SBD-P03; SBD-P04; SBD-P07; SBD-P08", "Expansion from vessel services into aquaculture infrastructure", "The operating model, technology or commercial structure performs below plan", "Capital loss, operational liabilities and reputational harm", "Trond V. Thomson", "", "Finance; Commercial; Technical & HSEQ; Vessel Operations", ">3 years", "Slow", 3, 5, 3, 4, 2, 3, "Approaching appetite", "Stable", "Monitoring", "Yes", "Illustrative – validate"],
        ["SBD-R004", "Data & assumptions", "Strategic decisions rely on incomplete or unreliable information", "OBJ-01; OBJ-02; OBJ-03", "PIL-01; PIL-02; PIL-03", "EBITDA; Multiple; Cash/NIBD", "3.1.1; 3.3.1; 3.3.7", "SBD-P01; SBD-P02; SBD-P04", "Group data and external intelligence are fragmented or inconsistent", "Management bases decisions on assumptions that are not sufficiently tested", "Misallocation of capital and delayed corrective decisions", "Trond V. Thomson", "", "Finance; Commercial; ICT; Vessel Operations", "0–12 months", "Fast", 4, 4, 3, 3, 2, 2, "Approaching appetite", "Stable", "Open", "No", "Illustrative – validate"],
        ["SBD-R005", "M&A & integration", "Acquisitions fail to deliver expected synergies", "OBJ-01; OBJ-04", "PIL-01; PIL-02; PIL-03", "EBITDA; Multiple; Cash/NIBD", "3.2.3; 3.3.8; 3.5.1", "SBD-P08; SBD-P12", "Due diligence, integration planning or ownership of synergies is insufficient", "An acquired business is not integrated effectively", "Synergies are delayed, costs increase and group governance remains fragmented", "Trond V. Thomson", "", "All units", "1–3 years", "Medium", 4, 4, 3, 4, 2, 3, "Outside appetite", "Stable", "Treatment in progress", "Yes", "Illustrative – validate"],
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

    # Link each ISO-aligned S&BD process to the Level III value drivers it supports.
    process_path = FILES["processes"]
    processes = safe_read_csv(process_path, columns=schema_columns_for("processes"))
    if "Linked Level 3 drivers" not in processes.columns:
        processes["Linked Level 3 drivers"] = ""
    # Recover S&BD processes missing from a blank or header-only file (e.g. on Streamlit Cloud).
    sbd_seed = [
        ("SBD-P01", "Long-term strategic planning", "4.1"), ("SBD-P02", "Market intelligence interpretation", "4.2"),
        ("SBD-P03", "Opportunity identification and evaluation", "4.3"), ("SBD-P04", "Business case development", "4.4"),
        ("SBD-P05", "Long-term operating agenda and rate uplift", "4.5"), ("SBD-P06", "Fleet portfolio optimization and divestment", "4.6"),
        ("SBD-P07", "Capital project governance", "4.7"), ("SBD-P08", "M&A and strategic partnerships", "4.8"),
        ("SBD-P09", "Strategic risk integration", "4.9"), ("SBD-P10", "Sustainability strategy integration", "4.10"),
        ("SBD-P11", "Sustainability Statement and CSRD", "4.11"), ("SBD-P12", "Strategy execution and monitoring", "4.12"),
    ]
    existing_ids = set(processes["Process ID"].astype(str))
    missing_rows = []
    for pid, pname, sec in sbd_seed:
        if pid not in existing_ids:
            row = {column: "" for column in processes.columns}
            row.update({"Process ID": pid, "Process": pname, "Process owner": "Trond V. Thomson",
                        "Purpose": "To be defined", "Trigger / inputs": "To be defined", "Main activities": "To be defined",
                        "Outputs": "To be defined", "Interfaces": "To be defined", "Review frequency": "Quarterly",
                        "S&BD Manual section": sec})
            missing_rows.append(row)
    if missing_rows:
        processes = pd.concat([pd.DataFrame(missing_rows), processes], ignore_index=True)
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
            "S&BD Manual section": "4.13",
        })
        processes = pd.concat([processes, pd.DataFrame([p13])], ignore_index=True)
    all_level_3 = "; ".join([
        "3.1.1", "3.1.2", "3.1.3", "3.1.4", "3.1.5", "3.1.6",
        "3.2.1", "3.2.2", "3.2.3", "3.2.4",
        "3.3.1", "3.3.2", "3.3.3", "3.3.4", "3.3.5", "3.3.6", "3.3.7", "3.3.8",
        "3.3.9", "3.3.10", "3.3.11", "3.3.12",
        "3.4.1", "3.4.2", "3.4.3", "3.4.4", "3.4.5", "3.4.6",
        "3.5.1", "3.5.2", "3.5.3", "3.5.4", "3.5.5", "3.5.6", "3.5.7",
    ])
    process_driver_links = {
        "SBD-P01": all_level_3,
        "SBD-P02": "3.1.1; 3.1.2; 3.2.2; 3.2.4; 3.3.2; 3.3.3; 3.3.4",
        "SBD-P03": "3.1.1; 3.2.1; 3.1.6; 3.2.2; 3.2.3; 3.2.4; 3.3.3; 3.5.1; 3.5.2; 3.5.3",
        "SBD-P04": "3.2.1; 3.1.6; 3.2.2; 3.2.3; 3.2.4; 3.3.4; 3.3.5; 3.3.6; 3.4.1; 3.5.1; 3.5.2; 3.5.3",
        "SBD-P05": "3.1.1; 3.1.2; 3.1.3; 3.1.4; 3.1.5; 3.3.1; 3.3.2; 3.3.3; 3.3.4; 3.4.1; 3.4.2; 3.4.3; 3.4.4",
        "SBD-P06": "3.1.2; 3.1.4; 3.1.6; 3.2.2; 3.3.5; 3.3.6; 3.4.2; 3.5.4",
        "SBD-P07": "3.2.1; 3.1.6; 3.2.2; 3.4.1; 3.5.1; 3.5.2; 3.5.3; 3.5.5; 3.5.6; 3.5.7",
        "SBD-P08": "3.2.2; 3.2.3; 3.2.4; 3.3.1; 3.3.3; 3.3.8; 3.5.1; 3.5.2; 3.5.3; 3.5.5",
        "SBD-P09": all_level_3,
        "SBD-P10": "3.1.4; 3.2.1; 3.1.6; 3.2.4; 3.3.3; 3.3.5; 3.3.7; 3.5.1; 3.5.2",
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
        "SBD-R001": "3.1.2; 3.2.1; 3.1.6; 3.2.2",
        "SBD-R002": "3.3.7; 3.3.8; 3.1.1",
        "SBD-R003": "3.2.4; 3.2.3; 3.3.8",
        "SBD-R004": "3.1.1; 3.3.1; 3.3.7",
        "SBD-R005": "3.2.3; 3.3.8; 3.5.1",
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


def driver_ownership_path():
    """Group-level Level III driver ownership (shared across all registers)."""
    return DATA_DIR / "driver_ownership.csv"


def load_driver_ownership():
    """Load driver ownership; seed it and add any Level III drivers missing from the file."""
    path = driver_ownership_path()
    seed(
        path,
        [[ref, acc, "; ".join(contrib), "Proposed - validate with function head"] for ref, acc, contrib in DRIVER_OWNERSHIP_SEED],
        DRIVER_OWNERSHIP_COLUMNS,
    )
    df = safe_read_csv(path, columns=DRIVER_OWNERSHIP_COLUMNS)
    for col in DRIVER_OWNERSHIP_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    known = set(df["Level 3 ref"].astype(str))
    seed_lookup = {ref: (acc, contrib) for ref, acc, contrib in DRIVER_OWNERSHIP_SEED}
    missing = []
    for item in level3_driver_catalog():
        ref = item["reference"]
        if ref not in known:
            acc, contrib = seed_lookup.get(ref, ("", []))
            missing.append({"Level 3 ref": ref, "Accountable function": acc, "Contributing functions": "; ".join(contrib), "Notes": "Added with hierarchy update - validate"})
    if missing:
        df = pd.concat([df, pd.DataFrame(missing)], ignore_index=True)
        df[DRIVER_OWNERSHIP_COLUMNS].to_csv(path, index=False)
    return df[DRIVER_OWNERSHIP_COLUMNS]


def driver_ownership_with_names(df=None):
    """Ownership table in hierarchy order, with pillar and driver names attached."""
    df = load_driver_ownership() if df is None else df
    catalog = level3_driver_catalog()
    order = {item["reference"]: i for i, item in enumerate(catalog)}
    names = {item["reference"]: item["driver"] for item in catalog}
    pillars = {item["reference"]: item["pillar_id"] for item in catalog}
    out = df.copy()
    out.insert(1, "Pillar", out["Level 3 ref"].map(pillars).fillna("Not in hierarchy"))
    out.insert(2, "Value driver", out["Level 3 ref"].map(names).fillna("(not in current hierarchy)"))
    out.insert(out.columns.get_loc("Accountable function") + 1, "Accountable executive", out["Accountable function"].map(FUNCTION_HEAD).fillna(""))
    out["_order"] = out["Level 3 ref"].map(order).fillna(999)
    return out.sort_values("_order").drop(columns="_order").reset_index(drop=True)


def drivers_for_function(function_name, ownership=None):
    """Return (accountable_refs, contributing_refs) for one executive function."""
    ownership = driver_ownership_with_names(ownership)
    acc = ownership[ownership["Accountable function"].astype(str).str.strip() == function_name]
    contrib = ownership[ownership["Contributing functions"].map(lambda v: function_name in split_refs(v))]
    return acc, contrib


def function_scope(function_name, ownership=None):
    """Level III refs a function is accountable for or contributes to."""
    if not function_name:
        return set()
    acc, contrib = drivers_for_function(function_name, ownership)
    return set(acc["Level 3 ref"]).union(set(contrib["Level 3 ref"]))


def out_of_scope_tags(risks_df, function_name):
    """Risk ID -> Level III refs tagged outside the function's scope."""
    scope = function_scope(function_name)
    result = {}
    if not scope or risks_df is None or risks_df.empty or "Level 3 drivers" not in risks_df.columns:
        return result
    for _, row in risks_df.iterrows():
        outside = [ref for ref in split_refs(row.get("Level 3 drivers", "")) if ref not in scope]
        if outside:
            result[str(row.get("Risk ID", ""))] = outside
    return result


def collect_all_register_rows(dataset):
    """All rows of one dataset across unit registers, with source unit."""
    frames = []
    for unit_name, _owner, _title in UNITS:
        register_key = REGISTER_KEYS[unit_name]
        ensure_register_files(register_key)
        df = safe_read_csv(files_for(register_key)[dataset], columns=schema_columns_for(dataset, register_key))
        if df.empty:
            continue
        df = df.copy()
        df.insert(0, "Source unit", unit_name)
        frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def value_coverage(ownership=None):
    """Per Level III driver: ownership, linked processes and risks across all registers, and gaps."""
    table = driver_ownership_with_names(ownership)
    risks = collect_all_register_rows("risks")
    processes = collect_all_register_rows("processes")
    risk_refs, risk_units, risk_resid = {}, {}, {}
    if not risks.empty and "Level 3 drivers" in risks.columns:
        risks = scored(risks)
        for _, row in risks.iterrows():
            for ref in split_refs(row.get("Level 3 drivers", "")):
                risk_refs[ref] = risk_refs.get(ref, 0) + 1
                risk_units.setdefault(ref, set()).add(row["Source unit"])
                risk_resid[ref] = max(risk_resid.get(ref, 0), int(pd.to_numeric(row.get("Residual score", 0), errors="coerce") or 0))
    proc_refs = {}
    if not processes.empty and "Linked Level 3 drivers" in processes.columns:
        for _, row in processes.iterrows():
            for ref in split_refs(row.get("Linked Level 3 drivers", "")):
                proc_refs[ref] = proc_refs.get(ref, 0) + 1
    rows = []
    for _, row in table.iterrows():
        ref = row["Level 3 ref"]
        acc = str(row["Accountable function"]).strip()
        gaps = []
        if not acc:
            gaps.append("No accountable function")
        elif acc not in FUNCTION_NAMES:
            gaps.append("Accountable function not recognised")
        if proc_refs.get(ref, 0) == 0:
            gaps.append("No processes")
        if risk_refs.get(ref, 0) == 0:
            gaps.append("No risks")
        rows.append({
            "Level 3 ref": ref,
            "Pillar": row["Pillar"],
            "Value driver": row["Value driver"],
            "Accountable function": acc,
            "Contributing functions": row["Contributing functions"],
            "Processes": proc_refs.get(ref, 0),
            "Risks": risk_refs.get(ref, 0),
            "Registers with risks": "; ".join(sorted(risk_units.get(ref, set()))),
            "Highest residual": risk_resid.get(ref, 0),
            "Gaps": "; ".join(gaps) if gaps else "Covered",
        })
    return pd.DataFrame(rows)


def function_driver_matrix(ownership=None):
    """Drivers x functions grid with A (accountable) / C (contributing)."""
    table = driver_ownership_with_names(ownership)
    rows = []
    for _, row in table.iterrows():
        contributors = split_refs(row["Contributing functions"])
        rec = {"Level 3 ref": row["Level 3 ref"], "Value driver": row["Value driver"]}
        for fn in FUNCTION_NAMES:
            rec[fn] = "A" if str(row["Accountable function"]).strip() == fn else ("C" if fn in contributors else "")
        rows.append(rec)
    return pd.DataFrame(rows)


def function_summary(ownership=None):
    """Per function: number of accountable and contributing drivers, and pillars touched."""
    table = driver_ownership_with_names(ownership)
    rows = []
    for fn, head in FUNCTIONS:
        acc, contrib = drivers_for_function(fn, table[DRIVER_OWNERSHIP_COLUMNS])
        pillars = sorted(set(acc["Pillar"]).union(set(contrib["Pillar"])))
        rows.append({
            "Function": fn,
            "Head": head,
            "Accountable drivers": len(acc),
            "Contributing drivers": len(contrib),
            "Pillars touched": ", ".join(pillars),
            "Status": "OK" if len(acc) > 0 else "No accountable driver - check mapping",
        })
    return pd.DataFrame(rows)


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



def input_zone_banner(label="Editable inputs"):
    """Visual cue: grey panel around data editors that accept user input."""
    st.markdown(
        f'<div class="vh-input-banner">{label} — grey panel is the editable grid. Type or pick values, then Save below.</div>',
        unsafe_allow_html=True,
    )

def editor(key, df, config=None, height=700):
    with st.container(key=f"vh_input_{ACTIVE_REGISTER_KEY}_{key}"):
        edited = st.data_editor(
            df,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            column_config=config or {},
            height=height,
            key=f"editor_{ACTIVE_REGISTER_KEY}_{key}",
        )
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
        driver_ownership_with_names().to_excel(writer, sheet_name="Driver Ownership", index=False)
        function_driver_matrix().to_excel(writer, sheet_name="Function x Driver", index=False)
        if source_label == ENTERPRISE_REGISTER:
            value_coverage().to_excel(writer, sheet_name="Value Coverage", index=False)
    return bio.getvalue()



# ---------------------------------------------------------------------------
# Operating Agenda folder: meeting running order, presenters and Level III topics
# ---------------------------------------------------------------------------
AGENDA_COLUMNS = ["Order", "Section", "Level 1 lever", "Level 2 pillar", "Item", "Level 3 refs", "Presenter function", "Co-presenter function", "Minutes", "Key exhibits", "Notes"]
AGENDA_CHAPTERS = [
    ('1 Welcome and introduction to Trident Aqua Services', '#00191d'),
    ('2 IMERS: our purpose and how we put strategy into action through ISO and ERM', '#255a64'),
    ('3 Life at sea', '#00839B'),
    ('4 Customers and how we provide competitive service platforms', '#006677'),
    ('5 The business plan for our existing fleet', '#397580'),
    ('6 One Trident: a bolt-on platform built to more than double Trident in size', '#255a64'),
    ('7 Growth and financing: building the future', '#00839B'),
    ('8 Our north star', '#00191d'),
]
AGENDA_SECTIONS = [c for c, _ in AGENDA_CHAPTERS] + ["Break"]
AGENDA_LEVERS = ["", "0 Shareholder value", "Context", "1.1 EBITDA", "1.2 Multiple", "1.3 Cash",
                 "1.1 EBITDA · 1.3 Cash", "1.2 Multiple · 1.3 Cash", "1.1 EBITDA · 1.2 Multiple"]
AGENDA_PILLARS = ["", "2.1 Organic EBITDA Growth", "2.2 Investment EBITDA Growth", "2.3 Multiple Expansion",
                  "2.4 Cash Conversion", "2.5 Capital Allocation & Balance Sheet",
                  "2.1 Organic EBITDA Growth · 2.3 Multiple Expansion", "2.3 Multiple Expansion · 2.4 Cash Conversion",
                  "2.3 Multiple Expansion · 2.5 Capital Allocation & Balance Sheet"]
_C = [c for c, _ in AGENDA_CHAPTERS]
_AGENDA_SEED = [
    # chapter, lever, pillar, item, refs, presenter, co-presenter, minutes, exhibits, notes
    (_C[0], '0 Shareholder value', '', 'Welcome and purpose of the day', '', 'CEO', '', 5,
     'Why we are here; how the day is built',
     'Start easy – for people meeting Trident for the first time'),
    (_C[0], 'Context', '', 'The big picture: food demand, a growing middle class, aquaculture vs wild catch – and Atlantic salmon production and demand worldwide', '', 'Strategy & Business Development', '', 15,
     'Global protein demand and middle-class growth; wild catch plateau vs aquaculture growth; Atlantic salmon supply by region and outlook; salmon demand, consumption per capita and market penetration outlook by region',
     'Funnel from the world to the salmon industry'),
    (_C[0], '0 Shareholder value', '', "Trident today and tomorrow: our services, platform, geographies and customers – and our ambition to be the world's leading aquaculture service company", '', 'CEO', '', 15,
     'High level only: what we do, where we operate, and where we want to be – the details follow in the sessions later in the day',
     'A short trailer for the day'),
    (_C[1], '0 Shareholder value', '', "IMERS: one strategy – how we all work towards maximizing shareholder value in full alignment with our stakeholders' interests", '', 'Strategy & Business Development', '', 20,
     "one value tree from Level 0 (shareholder value) to every department, so all functions pull towards the same goal; each department's ISO processes (IV-A) turn strategy into daily execution and its ERM register (IV-B) protects the value it is responsible for; one accountable executive per Level III driver; material risks rolled up to the enterprise level; every driver linked to the stakeholders it serves (Sustainability Statement 2025)",
     'The strategic frame for the day – every session that follows is one part of this value tree'),
    (_C[2], '1.1 EBITDA', '2.1 Organic EBITDA Growth', 'Our value proposition: vessels as service platforms – what they deliver to farmers, and how we operate them', '3.1.2; 3.1.4; 3.1.5', 'Vessel Operations', '', 25,
     'Vessel segments – wellboats, harvest and stun & bleed vessels, premium and standard service vessels, feed carriers; what each does for the farmer through the production cycle; the fleet by region; how Vessel Operations runs the fleet – organisation, crews, planning and day-to-day follow-up',
     'No economics here – introduce the vessels and the services. Consider a short vessel film'),
    (_C[2], '1.2 Multiple', '2.3 Multiple Expansion', 'Safety, fish welfare, environment and the technical standard of our fleet', '3.3.10; 3.3.5', 'Technical & HSEQ', '', 20,
     'LTIF/TRIF/SIF; fish welfare; emissions; technical standard and condition of the fleet',
     ''),
    ('Break', '', '', 'Break', '', '', '', 15,
     '',
     ''),
    (_C[3], '1.1 EBITDA · 1.2 Multiple', '2.1 Organic EBITDA Growth · 2.3 Multiple Expansion', 'Our customers: contracts, coverage, counterparties and commercial terms', '3.3.1; 3.3.2; 3.3.3; 3.1.3', 'Commercial', '', 30,
     'Customer map; contracted EBITDA and duration; concentration; key terms and indexation',
     ''),
    (_C[3], '1.1 EBITDA', '2.2 Investment EBITDA Growth', "Trident's expansion yard strategy: a global yard footprint to deliver newbuilds on time, on budget and at the most competitive prices", '', 'Vessel Operations', '', 15,
     'Why newbuilding uses a global yard footprint; how we select and work with newbuild yards; contract structure, supervision and follow-up to secure on-time, on-budget delivery; track record; how we secure competitive prices for the 19-vessel program',
     'Expansion only – newbuild yards worldwide. Maintenance and local yards are covered separately later in this chapter'),
    (_C[3], '1.1 EBITDA', '2.1 Organic EBITDA Growth', 'Global yard outlook: capacity, prices and the China option – the framework for newbuild prices and TC re-rating', '', 'Strategy & Business Development', '', 15,
     'Answer to the yard-price challenge: global yard capacity and price benchmarks by region; the China construction plan and its effect on newbuild prices; yard comparison (e.g. China vs Zamakona NB809, incl. finance and guarantees); newbuild-parity TC under different yard prices and yard indexation',
     'Sets the newbuild price used for TC re-rating in chapter 5 and the newbuild program in Growth'),
    (_C[3], '1.3 Cash', '2.4 Cash Conversion', 'Maintenance capex and our local maintenance yard strategy: keeping the fleet available and cost-efficient', '3.4.2', 'Vessel Operations', '', 15,
     'Maintenance capex by vessel and year; docking and survey plan; why maintenance uses local yards close to where the vessels operate; availability and off-hire around dockings',
     'A different strategy from newbuilding: local yards for maintenance vs a global footprint for expansion. Same capex source as the long-term vessel plan'),
    (_C[4], '1.2 Multiple · 1.3 Cash', '2.3 Multiple Expansion · 2.4 Cash Conversion', 'Setting the stage: earnings quality, reporting and how our EBITDA turns into cash', '3.3.4; 3.3.7; 3.4.1; 3.4.3; 3.4.4; 3.4.5; 3.4.6', 'Finance', '', 10,
     'EBITDA quality and volatility; reporting; EBITDA to free cash flow bridge',
     'Introduction before the 2027 budget'),
    (_C[4], 'Context', '', 'The 2027 budget', '', 'Finance', '', 20,
     'Budget 2027: revenue, EBITDA, capex and cash by region',
     'Near-term starting point for the long-term plan'),
    (_C[4], '1.1 EBITDA', '2.1 Organic EBITDA Growth', "TC fleet uplift: from today's rates to newbuild-parity pricing, vessel by vessel – benchmarked against comparable vessels by size and segment", '3.1.1', 'Strategy & Business Development', 'Commercial', 30,
     'Segment yardsticks: each vessel compared with similar vessels by size and segment (own fleet and competitors) – why and at which level each vessel should trade; fleet waterfall of real uplift above CPI indexation; renewal calendar and uplift steps per vessel; gap to newbuild-parity TC (from the yard outlook); commercial path to get there – renewals, terms and customers',
     'Co-hosted: Trond (model and pricing level) and Joar (commercial execution)'),
    (_C[4], '1.1 EBITDA · 1.2 Multiple', '2.1 Organic EBITDA Growth · 2.3 Multiple Expansion', 'Long-term implications for organic EBITDA (vessels in place) – and the conclusion on fleet renewal, replacement and divestment', '3.1.6; 3.3.6; 3.5.4', 'Strategy & Business Development', '', 15,
     '10-year EBITDA for the vessels in place, CPI-indexed vs with uplift; reconstructions with capex and yield; which vessels to keep, reconstruct, replace or divest – with timing and cash effect',
     'The conclusion of the TC fleet uplift session with Joar: what the uplift means for long-term EBITDA and for the fleet'),
    ('Break', '', '', 'Lunch', '', '', '', 45,
     '',
     ''),
    (_C[5], '1.2 Multiple', '2.3 Multiple Expansion', 'One Trident: a bolt-on platform ready to integrate acquisitions – and more than double in vessels, people and value', '3.3.8', 'CEO', '', 10,
     'How three companies became one; the integration playbook; what makes the platform scalable – common processes (ISO), one risk system (ERM), shared HSEQ platform; capacity to absorb companies of our own size',
     'Introduces the chapter: why Trident can integrate acquisitions and grow beyond twice its size'),
    (_C[5], '1.2 Multiple', '2.3 Multiple Expansion', 'Our people: competence, crew and leadership capacity to integrate and grow', '3.3.9', 'HR', '', 15,
     '1,001 employees (897 at sea); crew pool and recruitment; competence and training; succession and key-person map; how we onboard acquired crews and teams',
     ''),
    (_C[5], '1.2 Multiple', '2.3 Multiple Expansion', 'Compliance and legal: one framework that acquired companies plug into', '3.3.11', 'Legal & Compliance', '', 15,
     'Code of Conduct, anti-corruption, sanctions and due diligence; legal entity structure; how compliance is rolled out to acquired companies',
     ''),
    (_C[5], '1.2 Multiple', '2.3 Multiple Expansion', 'Our administrative platform: shared services, systems and data across Trident worldwide', '3.3.12', 'Administration & ICT', '', 15,
     'How administration is organised across regions and companies – shared services, common routines and document control; one system landscape and data model, with cyber resilience as part of it; how acquired companies are onboarded onto our administration and systems',
     'Focus on the administrative platform as part of the bolt-on system – ICT is one part of it'),
    ('Break', '', '', 'Break', '', '', '', 15,
     '',
     ''),
    (_C[6], 'Context', '', "The Norwegian Salmon Leap 2050: how Norway's salmon industry will develop – and what it means for the vessels, newbuilds and M&A ahead", '', 'Strategy & Business Development', '', 10,
     "Not a forecast – today's government decisions and industry plans added up: Norway from 1.84 m t (2025) towards ≈5 m t, ≈3 m t more salmon (2 m t offshore in the three areas opened Feb 2026, 1 m t in closed containment); ≈USD 75 bn of infrastructure; sea-phase volume >2.5×; ≈600,000 m³ new wellboat capacity and ≈USD 13 bn of vessel investment (wellboats USD 10 bn; service, feed and harvest USD 3 bn)",
     "Trond presents an analysis of Norway's plans, built on public information and government targets. Sets the stage for the newbuild program and the M&A plan. Source: 'The Salmon Leap 2050' (11 Nov 2026) with its source list"),
    (_C[6], '1.1 EBITDA', '2.2 Investment EBITDA Growth', 'Organic newbuild growth: newbuild program, yards and EBITDA ramp', '3.2.1', 'CEO', '', 20,
     'Newbuild pipeline by type and region; yard slots; EBITDA yield vs hurdle; capex and delivery timing',
     'Arild presents; Trond moderates and leads the Q&A to help the audience follow. Builds on the yard analysis in chapter 4; assets Trident does not own today'),
    (_C[6], '1.1 EBITDA', '2.2 Investment EBITDA Growth', 'The M&A plan: acquisitions, sale-leasebacks and new platforms', '3.2.2; 3.2.3; 3.2.4', 'Strategy & Business Development', '', 20,
     'Target universe and priorities; SLB cases; synergies; new platforms (SFaaS)',
     ''),
    (_C[6], '1.3 Cash', '2.5 Capital Allocation & Balance Sheet', "Today's financing: capital structure, returns, leverage and headroom", '3.5.2; 3.5.3; 3.5.5; 3.5.6', 'Finance', '', 10,
     'Current debt and capital structure; ROIC; NIBD/EBITDA; liquidity and covenant headroom',
     'Øyvind sets the starting point for how we finance the future'),
    (_C[6], '1.3 Cash', '2.5 Capital Allocation & Balance Sheet', 'Financing the future: paving the way for new capital to fund growth', '3.5.7', 'Strategy & Business Development', 'Finance', 10,
     'Funding need from the newbuild and M&A plans; financing structures and sources (bank, bond, equity, sale-leaseback, green/sustainability-linked); sequencing with the balance sheet',
     "Trond builds on Øyvind's starting point"),
    (_C[7], '1.3 Cash', '2.5 Capital Allocation & Balance Sheet', 'Our north star: where Trident is going – maximizing shareholder value in full alignment with our stakeholders', '3.5.1', 'CEO', '', 15,
     "The day in one picture – back to the ambition from the morning; the north star: the world's leading aquaculture service company, creating long-term shareholder value by creating value for customers, our people, communities, fish welfare and the ocean; how we allocate capital to get there; thank you and Q&A",
     'Close the circle from the opening – leave the audience with one picture of where we are going, not a list of decisions'),
]
AGENDA_SECTION_STYLE = {c: (col, "#ffffff") for c, col in AGENDA_CHAPTERS}
AGENDA_SECTION_STYLE["Break"] = ("#eef2f3", "#4a5a5e")


def agenda_path():
    return DATA_DIR / "operating_agenda.csv"


def agenda_meta_path():
    return DATA_DIR / "operating_agenda_meta.json"


def load_agenda():
    seed(agenda_path(), [[i + 1, *row] for i, row in enumerate(_AGENDA_SEED)], AGENDA_COLUMNS)
    df = safe_read_csv(agenda_path(), columns=AGENDA_COLUMNS)
    for col in AGENDA_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    df["Order"] = pd.to_numeric(df["Order"], errors="coerce")
    df["Minutes"] = pd.to_numeric(df["Minutes"], errors="coerce").fillna(0).astype(int)
    return df[AGENDA_COLUMNS].sort_values("Order", na_position="last").reset_index(drop=True)


def load_agenda_meta():
    import json
    default = {"title": "Trident Operating Agenda 2026 - management review", "date": "", "start": "08:30"}
    try:
        if agenda_meta_path().exists():
            default.update(json.loads(agenda_meta_path().read_text(encoding="utf-8")))
    except (OSError, ValueError):
        pass
    return default


def save_agenda_meta(meta):
    import json
    agenda_meta_path().write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")


def agenda_with_times(df, start="08:30"):
    out = df.copy()
    try:
        h, m = [int(x) for x in str(start).split(":")[:2]]
    except ValueError:
        h, m = 8, 30
    t = h * 60 + m
    starts, ends = [], []
    for minutes in out["Minutes"]:
        starts.append(f"{t // 60:02d}:{t % 60:02d}")
        t += int(minutes)
        ends.append(f"{t // 60:02d}:{t % 60:02d}")
    out.insert(1, "Start", starts)
    out.insert(2, "End", ends)
    def _who(f):
        f = str(f or "").strip()
        return f"{FUNCTION_HEAD.get(f, '')} ({f})" if f and FUNCTION_HEAD.get(f, f) != f else f
    co = out["Co-presenter function"] if "Co-presenter function" in out.columns else pd.Series([""] * len(out), index=out.index)
    out["Presenter"] = [(_who(f) + (" & " + _who(c) if str(c).strip() else "")) for f, c in zip(out["Presenter function"], co)]
    return out


def agenda_checks(df):
    """Every Level III driver on the agenda exactly once, presented by its accountable function."""
    ownership = driver_ownership_with_names()
    accountable = dict(zip(ownership["Level 3 ref"], ownership["Accountable function"]))
    names = dict(zip(ownership["Level 3 ref"], ownership["Value driver"]))
    seen = {}
    for _, row in df.iterrows():
        for ref in split_refs(row["Level 3 refs"]):
            seen.setdefault(ref, []).append((row["Item"], str(row["Presenter function"]).strip(),
                                             str(row.get("Co-presenter function", "")).strip()))
    rows = []
    for item in level3_driver_catalog():
        ref = item["reference"]
        hits = seen.get(ref, [])
        presenters = sorted({p for _, p, _c in hits})
        hosts = {p for _, p, _c in hits} | {c for _, _p, c in hits if c}
        acc = str(accountable.get(ref, "")).strip()
        if not hits:
            status = "Not on the agenda"
        elif len(hits) > 1:
            status = "On the agenda more than once"
        elif acc not in hosts and "CEO" in hosts:
            status = "OK"  # the CEO may present any driver on behalf of the accountable executive
        elif acc not in hosts:
            status = "Accountable executive is neither presenter nor co-presenter"
        else:
            status = "OK"
        rows.append({"Level 3 ref": ref, "Value driver": names.get(ref, item["driver"]), "Accountable function": acc,
                     "Presented by": "; ".join(presenters), "Agenda item": "; ".join(i for i, _p, _c in hits), "Check": status})
    unknown = sorted(set(seen) - {i["reference"] for i in level3_driver_catalog()})
    return pd.DataFrame(rows), unknown


def risks_for_refs(refs, limit=5):
    risks = collect_all_register_rows("risks")
    if risks.empty or "Level 3 drivers" not in risks.columns or not refs:
        return pd.DataFrame()
    risks = scored(risks)
    mask = risks["Level 3 drivers"].map(lambda v: bool(set(split_refs(v)) & set(refs)))
    cols = [c for c in ["Source unit", "Risk ID", "Risk title", "Level 3 drivers", "Residual score", "Appetite status"] if c in risks.columns]
    return risks.loc[mask, cols].sort_values("Residual score", ascending=False).head(limit)



# ---------------------------------------------------------------------------
# Stakeholder alignment: Level III drivers -> stakeholders in society (ESRS / SDG)
# ---------------------------------------------------------------------------
STAKEHOLDERS = [
    # name, short, VSME/DMA topics (Sustainability Statement 2025), SDGs, what they expect, colour, 2025 statement data
    ("Owners & investors", "Owners", "G1 Business conduct (double material)", "SDG 8",
     "Long-term value creation, transparency and sound governance", "#00191d",
     "Shareholder dialogue (statement 5.4)"),
    ("Banks & financial stakeholders", "Banks", "G1 Business conduct (double material)", "SDG 8",
     "Resilience, risk management and sustainability information; increasingly linked to financing conditions", "#343d40",
     "Banks, lenders and insurers request ESG and risk information (statement 5.4.2)"),
    ("Customers & industry partners", "Customers", "Fish welfare (cross-cutting) · E3 · E4", "SDG 12, 14",
     "Operational quality, fish welfare, transparency and environmental performance", "#00839B",
     "Customer dialogue on performance, HSEQ and sustainability (statement 5.4.1)"),
    ("Employees & management", "Employees", "S1 Own workforce (double material)", "SDG 8",
     "Safe workplaces, competence, fair conditions and a respectful culture", "#d08a2e",
     "1,001 employees (897 at sea); turnover 16.7%; LTIF/TRIF/SIF and sick leave tracked"),
    ("Vessel yards & suppliers", "Suppliers", "G1 supplier due diligence · S2 (lower materiality)", "SDG 8",
     "Predictable orders, fair terms and responsible supply-chain standards", "#7a5c99",
     "Integrity due diligence and supplier expectations (statement 4.2, 6.3)"),
    ("Authorities & local communities", "Society", "G1 Business conduct · S3 (lower materiality)", "SDG 8",
     "Compliance, transparency, licence to operate and a responsible local presence", "#5a6570",
     "Code of Conduct, ABC, sanctions, whistleblowing policies (statement 5, 6.3)"),
    ("Fish welfare", "Fish welfare", "Cross-cutting: E3 · E4 · S1 · G1", "SDG 14",
     "Gentle handling, oxygen and water-quality control, biosecurity, fewer welfare incidents", "#2f8f5b",
     "Group fish-health role established 2025; welfare incident follow-up (statement 3.5)"),
    ("Marine environment & biodiversity", "Marine", "E3 · E4 (double material) · E2 Pollution (impact material)", "SDG 14",
     "Protect water, marine ecosystems and biodiversity; prevent spills, discharges and pollution", "#1f6f9f",
     "NOx 2,341 t and SOx 72.36 t in 2025; ballast-water and discharge controls"),
    ("Climate", "Climate", "E1 Climate change (double material)", "SDG 13",
     "Lower fuel use and emissions; hybrid and lower-emission vessel technology", "#90c44f",
     "144,072 tCO₂e in 2025, 83% Scope 1 from vessel fuel"),
]
STAKEHOLDER_NAMES = [s[0] for s in STAKEHOLDERS]
STAKEHOLDER_INFO = {s[0]: s for s in STAKEHOLDERS}
CAPITAL_STAKEHOLDERS = {"Owners & investors", "Banks & financial stakeholders"}
NATURE_STAKEHOLDERS = {"Fish welfare", "Marine environment & biodiversity", "Climate"}
STAKEHOLDER_GROUPS = [("People", "#d08a2e"), ("Nature", "#2f8f5b"), ("Capital", "#00191d")]


def stakeholder_group(name):
    return "Capital" if name in CAPITAL_STAKEHOLDERS else ("Nature" if name in NATURE_STAKEHOLDERS else "People")


def stakeholder_stats(table):
    """Link counts behind the headline: driver-stakeholder links by group, by lever and by stakeholder."""
    lever_of = {"PIL-01": "1.1 EBITDA", "PIL-02": "1.1 EBITDA", "PIL-03": "1.2 Multiple", "PIL-04": "1.3 Cash", "PIL-05": "1.3 Cash"}
    links = []
    for _, row in table.iterrows():
        for sh in split_refs(row["Stakeholders"]):
            if sh in STAKEHOLDER_INFO:
                links.append({"ref": row["Level 3 ref"], "lever": lever_of.get(row["Pillar"], ""), "stakeholder": sh, "group": stakeholder_group(sh)})
    df = pd.DataFrame(links, columns=["ref", "lever", "stakeholder", "group"])
    total = len(df)
    by_group = df["group"].value_counts().to_dict()
    societal = by_group.get("People", 0) + by_group.get("Nature", 0)
    lever_share = {}
    for lever in ["1.1 EBITDA", "1.2 Multiple", "1.3 Cash"]:
        sub = df[df["lever"] == lever]
        lever_share[lever] = round(100 * (sub["group"] != "Capital").mean()) if len(sub) else 0
    by_stake = df["stakeholder"].value_counts().reindex(STAKEHOLDER_NAMES, fill_value=0).to_dict()
    return {"total": total, "by_group": by_group, "societal": societal,
            "societal_pct": round(100 * societal / total) if total else 0, "lever_share": lever_share, "by_stake": by_stake}
STAKEHOLDER_COLUMNS = ["Level 3 ref", "Stakeholders", "Shared value"]
_OW, _BK, _CU, _EM, _YS, _AC, _FW, _MA, _CL = STAKEHOLDER_NAMES
STAKEHOLDER_SEED = [
    ("3.1.1", [_OW, _CU], "Prices at newbuild parity fund reinvestment in the modern, reliable capacity customers depend on."),
    ("3.1.2", [_CU, _FW, _OW], "Vessels available when treatments and harvests are due, so fish are handled on time."),
    ("3.1.3", [_CU, _OW], "Clear, balanced terms and indexation that make long partnerships work for both sides."),
    ("3.1.4", [_CU, _FW, _CL, _EM], "Well-run vessels: fewer incidents, lower fuel use and better fish handling."),
    ("3.1.5", [_OW, _EM, _CL, _YS], "Efficiency through planning, procurement, fuel management and lower sick leave, never by cutting safe manning."),
    ("3.1.6", [_CL, _FW, _CU, _YS, _EM], "Reconstruction extends vessel life and adds modern fish-handling, safety and energy-saving technology."),
    ("3.2.1", [_CL, _FW, _CU, _EM, _YS], "Newbuilds bring hybrid and lower-emission vessels, gentler fish handling and work for yards."),
    ("3.2.2", [_CU, _OW, _BK], "Sale-leasebacks free customers' capital for their core business; acquired vessels are brought up to Trident standards."),
    ("3.2.3", [_OW, _CU, _EM], "Consolidation gives customers one accountable operator and employees wider career paths."),
    ("3.2.4", [_CU, _FW, _MA], "New platforms (SFaaS) help farmers grow with lower biological risk."),
    ("3.3.1", [_OW, _BK, _EM, _CU], "Predictable earnings secure jobs and long-term customer partnerships."),
    ("3.3.2", [_OW, _BK, _CU, _EM, _YS], "Long contracts give customers secured capacity, employees stable work and yards predictable orders."),
    ("3.3.3", [_OW, _BK, _CU, _AC], "We work with financially sound, responsible producers."),
    ("3.3.4", [_OW, _BK, _EM], "Stable earnings protect employment through the cycle."),
    ("3.3.5", [_EM, _FW, _CL, _OW, _BK], "A modern fleet is safer, cleaner and better for fish, and holds its value."),
    ("3.3.6", [_CL, _FW, _MA, _EM, _AC], "Retiring old tonnage cuts emissions and risk; divested vessels go to responsible owners or certified recycling."),
    ("3.3.7", [_OW, _BK, _AC], "Transparent, reliable reporting, including the VSME sustainability statement and its KPIs."),
    ("3.3.8", [_EM, _CU, _AC], "One Trident Aqua Services: shared ISO 9001/14001 management system and common processes, with local presence."),
    ("3.3.9", [_EM, _AC], "Competence, leadership and succession; a stable workforce and local recruitment."),
    ("3.3.10", [_EM, _FW, _MA, _CL, _AC, _CU], "Safety, fish welfare, biosecurity and environmental care: the core of the licence to operate."),
    ("3.3.11", [_AC, _OW, _BK, _YS], "Code of Conduct, anti-corruption, sanctions compliance and supplier due diligence in every country."),
    ("3.3.12", [_CU, _AC, _EM], "A plug-and-play platform – shared services, common systems and data – lets acquired companies join fast and safely; secure systems protect customers, employees and operations."),
    ("3.4.1", [_OW, _BK, _YS], "Cash discipline without pushing the burden onto suppliers."),
    ("3.4.2", [_EM, _FW, _MA, _CL, _YS], "Planned maintenance keeps vessels safe, efficient and free of spills, and gives yards steady work."),
    ("3.4.3", [_OW, _YS], "Efficient working capital with suppliers paid on agreed terms."),
    ("3.4.4", [_OW, _CU], "Clear invoicing and collection agreed with customers."),
    ("3.4.5", [_OW, _BK], "Lower financing cost leaves more cash for fleet renewal."),
    ("3.4.6", [_AC, _OW], "Taxes paid where value is created, within the law in each country."),
    ("3.5.1", [_OW, _CU, _CL, _EM], "Cash goes where it creates the most value, including fleet renewal and safer, cleaner vessels."),
    ("3.5.2", [_OW, _BK], "Returns above the cost of capital keep the company able to invest."),
    ("3.5.3", [_OW, _BK], "Balanced choice between paying down debt and investing."),
    ("3.5.4", [_CL, _MA, _OW, _AC], "Disposals done responsibly, including certified ship recycling where relevant."),
    ("3.5.5", [_BK, _OW], "Leverage within limits that protect all stakeholders through a downturn."),
    ("3.5.6", [_BK, _YS, _EM], "Liquidity to pay employees and suppliers through any cycle."),
    ("3.5.7", [_BK, _OW, _CL], "Access to financing, including green or sustainability-linked loans that reward ESG performance."),
]


def stakeholder_path():
    return DATA_DIR / "stakeholder_alignment.csv"


def load_stakeholder_alignment():
    path = stakeholder_path()
    seed(path, [[ref, "; ".join(st_), txt] for ref, st_, txt in STAKEHOLDER_SEED], STAKEHOLDER_COLUMNS)
    df = safe_read_csv(path, columns=STAKEHOLDER_COLUMNS)
    for col in STAKEHOLDER_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    known = set(df["Level 3 ref"].astype(str))
    lookup = {ref: (st_, txt) for ref, st_, txt in STAKEHOLDER_SEED}
    missing = [{"Level 3 ref": i["reference"], "Stakeholders": "; ".join(lookup.get(i["reference"], ([], ""))[0]),
                "Shared value": lookup.get(i["reference"], ([], ""))[1]}
               for i in level3_driver_catalog() if i["reference"] not in known]
    if missing:
        df = pd.concat([df, pd.DataFrame(missing)], ignore_index=True)
        df[STAKEHOLDER_COLUMNS].to_csv(path, index=False)
    return df[STAKEHOLDER_COLUMNS]


def stakeholder_table():
    df = load_stakeholder_alignment()
    catalog = level3_driver_catalog()
    order = {i["reference"]: n for n, i in enumerate(catalog)}
    names = {i["reference"]: i["driver"] for i in catalog}
    pillars = {i["reference"]: i["pillar_id"] for i in catalog}
    ownership = driver_ownership_with_names()
    acc = dict(zip(ownership["Level 3 ref"], ownership["Accountable executive"]))
    out = df.copy()
    out.insert(1, "Pillar", out["Level 3 ref"].map(pillars).fillna(""))
    out.insert(2, "Value driver", out["Level 3 ref"].map(names).fillna("(not in hierarchy)"))
    out["Accountable executive"] = out["Level 3 ref"].map(acc).fillna("")
    out["_o"] = out["Level 3 ref"].map(order).fillna(999)
    return out.sort_values("_o").drop(columns="_o").reset_index(drop=True)


def stakeholder_sankey(table, reverse=False):
    import plotly.graph_objects as go
    levers = [("1.1 EBITDA", ["PIL-01", "PIL-02"]), ("1.2 Multiple", ["PIL-03"]), ("1.3 Cash", ["PIL-04", "PIL-05"])]
    pillar_labels = {"PIL-01": "2.1 Organic EBITDA growth", "PIL-02": "2.2 Investment EBITDA growth", "PIL-03": "2.3 Multiple expansion",
                     "PIL-04": "2.4 Cash conversion", "PIL-05": "2.5 Capital allocation & balance sheet"}
    stake_order = [n for n in STAKEHOLDER_NAMES if n not in CAPITAL_STAKEHOLDERS] + [n for n in STAKEHOLDER_NAMES if n in CAPITAL_STAKEHOLDERS]
    group_names = [g for g, _ in STAKEHOLDER_GROUPS]
    nodes = ["0 · Maximize<br>shareholder value"] + [l for l, _ in levers] + list(pillar_labels.values()) + stake_order + group_names
    idx = {n: i for i, n in enumerate(nodes)}
    colors = ["#00191d"] + ["#00839B"] * 3 + ["#343d40"] * 5 + [STAKEHOLDER_INFO[n][5] for n in stake_order] + [c for _, c in STAKEHOLDER_GROUPS]

    def spread(n, lo=0.04, hi=0.96):
        return [lo + (hi - lo) * i / max(n - 1, 1) for i in range(n)]
    node_x = [0.001] + [0.19] * 3 + [0.40] * 5 + [0.72] * len(stake_order) + [0.999] * 3
    node_y = [0.5] + spread(3, 0.15, 0.85) + spread(5, 0.08, 0.92) + spread(len(stake_order), 0.03, 0.97) + [0.22, 0.55, 0.86]
    src, tgt, val, lcol, hover = [], [], [], [], []
    pil_stake = {}
    for _, row in table.iterrows():
        for sh in split_refs(row["Stakeholders"]):
            if sh in idx and row["Pillar"] in pillar_labels:
                pil_stake.setdefault((row["Pillar"], sh), []).append(row["Level 3 ref"])
    pil_total = {p: sum(len(v) for (pp, _), v in pil_stake.items() if pp == p) for p in pillar_labels}
    for lever, pils in levers:
        tot = sum(pil_total[p] for p in pils)
        src.append(idx[nodes[0]]); tgt.append(idx[lever]); val.append(tot); lcol.append("rgba(0,131,155,.25)"); hover.append(lever)
        for p in pils:
            src.append(idx[lever]); tgt.append(idx[pillar_labels[p]]); val.append(pil_total[p]); lcol.append("rgba(52,61,64,.22)"); hover.append(pillar_labels[p])
    for (p, sh), refs in pil_stake.items():
        c = STAKEHOLDER_INFO[sh][5].lstrip("#")
        rgba = f"rgba({int(c[0:2],16)},{int(c[2:4],16)},{int(c[4:6],16)},.45)"
        src.append(idx[pillar_labels[p]]); tgt.append(idx[sh]); val.append(len(refs)); lcol.append(rgba)
        hover.append(f"{len(refs)} driver(s): {', '.join(refs)}")
    for sh in stake_order:
        n = sum(len(v) for (p, s_), v in pil_stake.items() if s_ == sh)
        if not n:
            continue
        g = stakeholder_group(sh)
        c = dict(STAKEHOLDER_GROUPS)[g].lstrip("#")
        src.append(idx[sh]); tgt.append(idx[g]); val.append(n)
        lcol.append(f"rgba({int(c[0:2],16)},{int(c[2:4],16)},{int(c[4:6],16)},.30)")
        hover.append(f"{sh} → {g}: {n} link(s)")
    title_text = ("Level 0  →  I Levers  →  II Pillars  →  Stakeholders  →  People · Nature · Capital"
                  "<br><sup>Flow width = number of Level III driver links</sup>")
    if reverse:
        src, tgt = tgt, src
        node_x = [min(max(1 - x, 0.001), 0.999) for x in node_x]
        title_text = ("People · Nature · Capital  →  Stakeholders  →  II Pillars  →  I Levers  →  Level 0"
                      "<br><sup>What each stakeholder group needs, and where it builds shareholder value · flow width = number of Level III driver links</sup>")
    fig = go.Figure(go.Sankey(
        arrangement="fixed",
        node=dict(label=nodes, color=colors, x=node_x, y=node_y, pad=18, thickness=26, line=dict(color="#ffffff", width=0.5),
                  hovertemplate="%{label}<extra></extra>"),
        link=dict(source=src, target=tgt, value=val, color=lcol, customdata=hover, hovertemplate="%{customdata}<extra></extra>"),
    ))
    fig.update_layout(height=900, margin=dict(l=10, r=10, t=56, b=10),
                      font=dict(size=20, color="#00191d", family="Source Sans Pro, Arial, sans-serif"),
                      title=dict(text=title_text, font=dict(size=20, color="#255a64"), x=0.0, xanchor="left"))
    return fig


def stakeholder_lever_grid(table):
    import plotly.graph_objects as go
    lever_of = {"PIL-01": "1.1 EBITDA", "PIL-02": "1.1 EBITDA", "PIL-03": "1.2 Multiple", "PIL-04": "1.3 Cash", "PIL-05": "1.3 Cash"}
    levers = ["1.1 EBITDA", "1.2 Multiple", "1.3 Cash"]
    order = [n for n in STAKEHOLDER_NAMES if n not in CAPITAL_STAKEHOLDERS] + [n for n in STAKEHOLDER_NAMES if n in CAPITAL_STAKEHOLDERS]
    z, text = [], []
    for sh in order:
        row, trow = [], []
        for lv in levers:
            refs = [r["Level 3 ref"] for _, r in table.iterrows() if lever_of.get(r["Pillar"]) == lv and sh in split_refs(r["Stakeholders"])]
            row.append(len(refs)); trow.append(", ".join(refs))
        z.append(row); text.append(trow)
    fig = go.Figure(go.Heatmap(
        z=z, x=levers, y=[f"{sh}  ({stakeholder_group(sh)})" for sh in order], customdata=text,
        colorscale=[[0, "#f3f7f8"], [0.35, "#90c4ce"], [1, "#00839B"]], showscale=False, xgap=4, ygap=4,
        texttemplate="%{z}", textfont=dict(size=22, color="#00191d"),
        hovertemplate="%{y} · %{x}<br>Drivers: %{customdata}<extra></extra>",
    ))
    fig.update_layout(height=640, margin=dict(l=10, r=10, t=10, b=10), font=dict(size=18, color="#00191d"),
                      yaxis=dict(autorange="reversed", tickfont=dict(size=18)), xaxis=dict(side="top", tickfont=dict(size=20)))
    return fig


def stakeholder_drilldown(table, stakeholder):
    import plotly.graph_objects as go
    pillar_labels = {"PIL-01": "2.1 Organic EBITDA growth", "PIL-02": "2.2 Investment EBITDA growth", "PIL-03": "2.3 Multiple expansion",
                     "PIL-04": "2.4 Cash conversion", "PIL-05": "2.5 Capital allocation & balance sheet"}
    lever_of = {"PIL-01": "1.1 EBITDA", "PIL-02": "1.1 EBITDA", "PIL-03": "1.2 Multiple", "PIL-04": "1.3 Cash", "PIL-05": "1.3 Cash"}
    rows = table[table["Stakeholders"].map(lambda v: stakeholder in split_refs(v))]
    if rows.empty:
        return None
    drivers = [f'{r["Level 3 ref"]} · {r["Value driver"]}' for _, r in rows.iterrows()]
    pils = [p for p in pillar_labels if p in set(rows["Pillar"])]
    levs = [l for l in ["1.1 EBITDA", "1.2 Multiple", "1.3 Cash"] if l in {lever_of[p] for p in pils}]
    nodes = [STAKEHOLDER_INFO[stakeholder][1]] + drivers + [pillar_labels[p] for p in pils] + levs + ["0 · Maximize<br>shareholder value"]
    idx = {n: i for i, n in enumerate(nodes)}
    color = STAKEHOLDER_INFO[stakeholder][5]
    c = color.lstrip("#"); rgba = f"rgba({int(c[0:2],16)},{int(c[2:4],16)},{int(c[4:6],16)},.35)"
    src, tgt, val, lc, hov = [], [], [], [], []
    for (_, r), d in zip(rows.iterrows(), drivers):
        src.append(0); tgt.append(idx[d]); val.append(1); lc.append(rgba); hov.append(str(r["Shared value"]))
        src.append(idx[d]); tgt.append(idx[pillar_labels[r["Pillar"]]]); val.append(1); lc.append("rgba(52,61,64,.22)"); hov.append(d)
    for p in pils:
        n = int((rows["Pillar"] == p).sum())
        src.append(idx[pillar_labels[p]]); tgt.append(idx[lever_of[p]]); val.append(n); lc.append("rgba(52,61,64,.22)"); hov.append(f"{n} driver(s)")
    for l in levs:
        n = int(rows["Pillar"].map(lever_of).eq(l).sum())
        src.append(idx[l]); tgt.append(idx[nodes[-1]]); val.append(n); lc.append("rgba(0,131,155,.25)"); hov.append(f"{n} driver(s)")

    def spread(n, lo=0.04, hi=0.96):
        return [lo + (hi - lo) * i / max(n - 1, 1) for i in range(n)] if n > 1 else [0.5]
    node_x = [0.001] + [0.17] * len(drivers) + [0.56] * len(pils) + [0.76] * len(levs) + [0.999]
    node_y = [0.5] + spread(len(drivers), 0.02, 0.98) + spread(len(pils), 0.1, 0.9) + spread(len(levs), 0.2, 0.8) + [0.5]
    colors = [color] + ["#90c4ce"] * len(drivers) + ["#343d40"] * len(pils) + ["#00839B"] * len(levs) + ["#00191d"]
    fig = go.Figure(go.Sankey(
        arrangement="fixed",
        node=dict(label=nodes, color=colors, x=node_x, y=node_y, pad=12, thickness=24, line=dict(color="#fff", width=0.5),
                  hovertemplate="%{label}<extra></extra>"),
        link=dict(source=src, target=tgt, value=val, color=lc, customdata=hov, hovertemplate="%{customdata}<extra></extra>"),
    ))
    fig.update_layout(height=max(520, 46 * len(drivers) + 120), margin=dict(l=10, r=10, t=10, b=10),
                      font=dict(size=16, color="#00191d", family="Source Sans Pro, Arial, sans-serif"))
    return fig


def render_stakeholder_alignment():
    from html import escape as _esc
    table = stakeholder_table()
    st.subheader("Stakeholder alignment – shareholder value in context")
    st.write(
        "Trident's value hierarchy maximizes long-term shareholder value **by** creating value for the people and the environment "
        "the business depends on. Each Level III driver is linked to the stakeholder groups and material topics in Trident's "
        "Sustainability Statement 2025 (VSME, double materiality assessment) and the SDGs Trident has committed to (8, 12, 13, 14)."
    )
    beyond = table["Stakeholders"].map(lambda v: any(s not in CAPITAL_STAKEHOLDERS for s in split_refs(v)))
    fin_only = table.loc[~beyond, "Level 3 ref"].tolist()
    cols = st.columns(3)
    cols[0].metric("Level III drivers serving stakeholders beyond owners and banks", f"{int(beyond.sum())} / {len(table)}")
    cols[1].metric("Stakeholder groups", len(STAKEHOLDERS))
    cols[2].metric("Purely financial drivers", len(fin_only))
    if fin_only:
        _names = dict(zip(driver_ownership_with_names()["Level 3 ref"], driver_ownership_with_names()["Value driver"]))
        st.info(f"Only **{len(fin_only)} of {len(table)}** value-tree drivers serve owners and banks alone – and all are financing: "
                + " · ".join(f"{r} {_names.get(r, '')}" for r in fin_only)
                + ". Even these keep the balance sheet strong enough to fund fleet renewal, safety and environmental investment.")

    t_flow, t_st, t_matrix, t_edit = st.tabs(["Illustration", "By stakeholder", "Driver × stakeholder matrix", "Edit mapping"])
    with t_flow:
        stats = stakeholder_stats(table)
        bg = stats["by_group"]
        ls = stats["lever_share"]
        bs = stats["by_stake"]
        cust, emp, own = bs.get("Customers & industry partners", 0), bs.get("Employees & management", 0), bs.get("Owners & investors", 0)
        marine = bs.get("Marine environment & biodiversity", 0)
        top_lever = max(ls, key=ls.get)
        st.markdown(
            f'''
            <div style="background:#00191d;color:#fff;border-radius:10px;padding:26px 30px 22px;margin:6px 0 16px">
              <div style="font-size:2.5rem;font-weight:800;line-height:1.15">Creating shareholder value at Trident means creating value for people and nature</div>
              <div style="font-size:1.35rem;margin-top:12px;color:#caff74;font-weight:600">
                {stats["societal_pct"]}% of the links in our value model ({stats["societal"]} of {stats["total"]}) go to customers, employees, suppliers,
                communities, fish welfare, the ocean and climate – {100 - stats["societal_pct"]}% to owners and banks.</div>
            </div>
            <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-bottom:12px">
              <div style="border-top:5px solid #00839B;background:#f5f9fa;padding:14px 16px;border-radius:6px">
                <div style="font-size:2.2rem;font-weight:800;color:#00839B">{ls[top_lever]}%</div>
                <div style="font-size:1.08rem;color:#00191d">of <b>{top_lever}</b> links reach people and nature – growth means newer, cleaner vessels, reliable capacity and better fish handling.
                (Multiple {ls["1.2 Multiple"]}% · Cash {ls["1.3 Cash"]}%)</div></div>
              <div style="border-top:5px solid #d08a2e;background:#f5f9fa;padding:14px 16px;border-radius:6px">
                <div style="font-size:2.2rem;font-weight:800;color:#d08a2e">{cust} &amp; {emp}</div>
                <div style="font-size:1.08rem;color:#00191d">Level III drivers serve <b>customers</b> and <b>employees</b> – close to owners ({own}).
                What is good for value is good for the people who deliver it.</div></div>
              <div style="border-top:5px solid #1f6f9f;background:#f5f9fa;padding:14px 16px;border-radius:6px">
                <div style="font-size:2.2rem;font-weight:800;color:#1f6f9f">{marine}</div>
                <div style="font-size:1.08rem;color:#00191d">drivers link to the <b>marine environment &amp; biodiversity</b> – although E3/E4 are double material.
                Our clearest area to strengthen.</div></div>
            </div>''',
            unsafe_allow_html=True,
        )
        st.plotly_chart(stakeholder_sankey(table), use_container_width=True, key="sankey_forward")
        st.caption("Hover a flow to see which Level III drivers create the link.")
        st.markdown(
            '''<div style="border-left:8px solid #00839B;padding:10px 18px;margin:30px 0 8px;background:#f5f9fa">
            <div style="font-size:2rem;font-weight:800;color:#00191d;line-height:1.2">Seen from the stakeholders' side: where each group fits in shareholder value</div>
            <div style="font-size:1.2rem;color:#255a64;margin-top:6px">Number of Level III drivers linking each stakeholder group to each value lever.
            Hover a cell to see the drivers.</div></div>''',
            unsafe_allow_html=True,
        )
        st.plotly_chart(stakeholder_lever_grid(table), use_container_width=True, key="stakeholder_grid")
        lever_of = {"PIL-01": "1.1 EBITDA", "PIL-02": "1.1 EBITDA", "PIL-03": "1.2 Multiple", "PIL-04": "1.3 Cash", "PIL-05": "1.3 Cash"}
        strongest = []
        for sh in STAKEHOLDER_NAMES:
            counts = {}
            for _, r in table.iterrows():
                if sh in split_refs(r["Stakeholders"]):
                    lv = lever_of.get(r["Pillar"], "")
                    counts[lv] = counts.get(lv, 0) + 1
            if counts:
                top = max(counts.values())
                strongest.append(f"**{STAKEHOLDER_INFO[sh][1]}** → " + " / ".join(k for k in ["1.1 EBITDA", "1.2 Multiple", "1.3 Cash"] if counts.get(k) == top))
        st.markdown("Where each group connects most strongly: " + " · ".join(strongest))
        st.markdown(
            '''<div style="font-size:1.6rem;font-weight:800;color:#00191d;margin:26px 0 4px">Follow one stakeholder group to shareholder value</div>
            <div style="font-size:1.1rem;color:#255a64;margin-bottom:6px">Stakeholder → the Level III drivers that serve them → pillar → lever → Level 0.
            Hover a flow to read the shared-value statement.</div>''',
            unsafe_allow_html=True,
        )
        pick = st.selectbox("Stakeholder group", [n for n in STAKEHOLDER_NAMES if n not in CAPITAL_STAKEHOLDERS] + sorted(CAPITAL_STAKEHOLDERS),
                            key="stakeholder_drill_pick")
        info = STAKEHOLDER_INFO[pick]
        st.markdown(f"**What they expect:** {info[4]}  \n**Sustainability Statement 2025:** {info[2]} · {info[3]} · {info[6]}")
        fig = stakeholder_drilldown(table, pick)
        if fig is None:
            st.caption("No Level III drivers linked to this group yet.")
        else:
            st.plotly_chart(fig, use_container_width=True, key="stakeholder_drill")
    with t_st:
        for name, short, esrs, sdg, need, color, fact in STAKEHOLDERS:
            rows = table[table["Stakeholders"].map(lambda v, n=name: n in split_refs(v))]
            st.markdown(
                f'<div style="border-left:6px solid {color};padding:6px 12px;margin:14px 0 4px;background:#f7fafb">'
                f'<div style="font-weight:700;font-size:1.05rem;color:#00191d">{_esc(name)} '
                f'<span style="font-weight:400;color:#4a5a5e">· {len(rows)} Level III drivers</span></div>'
                f'<div style="font-size:.86rem;color:#255a64">{_esc(esrs)} · {_esc(sdg)}</div>'
                f'<div style="font-size:.9rem;color:#00191d;margin-top:2px">What they expect: {_esc(need)}</div>'
                f'<div style="font-size:.82rem;color:#4a5a5e;margin-top:2px">Sustainability Statement 2025: {_esc(fact)}</div></div>',
                unsafe_allow_html=True,
            )
            if not rows.empty:
                st.dataframe(rows[["Level 3 ref", "Value driver", "Shared value", "Accountable executive"]], hide_index=True, use_container_width=True)
    with t_matrix:
        grid = table[["Level 3 ref", "Value driver"]].copy()
        for name, short, *_ in STAKEHOLDERS:
            grid[short] = table["Stakeholders"].map(lambda v, n=name: "●" if n in split_refs(v) else "")
        st.dataframe(grid, hide_index=True, use_container_width=True, height=760)
        st.caption("Columns: " + " · ".join(f"{s[1]} = {s[0]}" for s in STAKEHOLDERS))
    with t_edit:
        st.caption("Stakeholders: separate with semicolons, using these names exactly: " + "; ".join(STAKEHOLDER_NAMES))
        input_zone_banner("Stakeholder mapping — editable fields")
        edited = st.data_editor(table, hide_index=True, use_container_width=True, height=760,
                                disabled=["Level 3 ref", "Pillar", "Value driver", "Accountable executive"],
                                column_config={"Stakeholders": st.column_config.TextColumn(width="large"),
                                               "Shared value": st.column_config.TextColumn(width="large")},
                                key="stakeholder_editor")
        if st.button("Save stakeholder mapping", type="primary", key="save_stakeholders"):
            unknown = sorted({x for v in edited["Stakeholders"] for x in split_refs(v) if x not in STAKEHOLDER_NAMES})
            if unknown:
                st.error("Unknown stakeholder name(s): " + ", ".join(unknown))
            else:
                edited[STAKEHOLDER_COLUMNS].to_csv(stakeholder_path(), index=False)
                st.success("Saved.")
                st.rerun()


def render_operating_agenda():
    from html import escape as _esc
    meta = load_agenda_meta()
    agenda = load_agenda()
    timed = agenda_with_times(agenda, meta.get("start", "08:30"))
    driver_names = {i["reference"]: i["driver"] for i in level3_driver_catalog()}

    st.subheader(meta.get("title") or "Operating Agenda")
    total = int(agenda["Minutes"].sum())
    talk = int(agenda.loc[agenda["Section"] != "Break", "Minutes"].sum())
    cols = st.columns(4)
    cols[0].metric("Date", meta.get("date") or "Not set")
    cols[1].metric("Time", f"{timed['Start'].iloc[0]}–{timed['End'].iloc[-1]}" if len(timed) else "-")
    cols[2].metric("Presentation time", f"{talk // 60} h {talk % 60:02d} min")
    _pp = set(agenda["Presenter function"].astype(str).str.strip()) | set(agenda["Co-presenter function"].astype(str).str.strip())
    cols[3].metric("Presenters", len(_pp - {""}))
    st.caption("The day runs from the big picture to the details, so participants who are new to Trident can follow. "
               "Switch on IMERS references in the running order to see how each item maps to the value tree; the Checks tab tests coverage.")

    t_run, t_stake, t_pres, t_check, t_edit = st.tabs(["Running order", "Stakeholder alignment", "By presenter", "Checks", "Edit agenda"])
    show_refs = False
    with t_stake:
        render_stakeholder_alignment()

    with t_run:
        show_refs = st.toggle("Show IMERS references (levers, pillars, Level III drivers and risks)", value=False, key="agenda_show_refs",
                              help="Off: the audience view. On: shows how each item maps to the IMERS value tree.")
        st.markdown("""
        <style>
        .oa-sec{padding:8px 12px;border-radius:6px 6px 0 0;font-weight:700;margin-top:14px;font-size:1rem}
        .oa-row{display:grid;grid-template-columns:105px 1fr 260px;gap:14px;padding:9px 12px;border:1px solid #d5e3e6;border-top:none;background:#fff}
        .oa-row.break{background:#f5f8f9;color:#6b7c80;font-style:italic}
        .oa-time{font-weight:700;color:#00191d;font-variant-numeric:tabular-nums}
        .oa-item{font-weight:700;color:#00191d}
        .oa-sub{font-size:.84rem;color:#4a5a5e;margin-top:3px;line-height:1.45}
        .oa-ref{display:inline-block;background:#caff74;border:1px solid #90c44f;border-radius:4px;padding:1px 6px;margin:3px 4px 0 0;font-size:.8rem;font-weight:700;color:#00191d}
        .oa-pil{display:inline-block;background:#e5f1ff;border:1px solid #a4c4e9;border-radius:4px;padding:1px 6px;margin-right:6px;font-size:.78rem;color:#255a64}
        .oa-who{font-weight:600;color:#00839B}
        .oa-lbl{font-weight:700;color:#255a64}
        .oa-lev{display:inline-block;background:#00839B;color:#fff;border-radius:4px;padding:1px 7px;margin-right:6px;font-size:.78rem;font-weight:700}
        </style>""", unsafe_allow_html=True)
        current = None
        html = []
        for _, row in timed.iterrows():
            sec = row["Section"] or ""
            if sec != "Break" and sec != current:
                bg, fg = AGENDA_SECTION_STYLE.get(sec, ("#00191d", "#fff"))
                sec_mins = int(timed.loc[timed["Section"] == sec, "Minutes"].sum())
                html.append(f'<div class="oa-sec" style="background:{bg};color:{fg}">{_esc(sec)} <span style="font-weight:400;opacity:.85">· {sec_mins} min</span></div>')
                current = sec
            if sec == "Break":
                html.append(f'<div class="oa-row break"><div class="oa-time">{row["Start"]}–{row["End"]}</div><div>{_esc(str(row["Item"]))}</div><div></div></div>')
                continue
            refs = split_refs(row["Level 3 refs"])
            ref_html = "" if not show_refs else "".join(f'<span class="oa-ref" title="{_esc(driver_names.get(r, ""))}">{_esc(r)} · {_esc(driver_names.get(r, "?"))}</span>' for r in refs)
            lev = str(row.get("Level 1 lever", "")).strip()
            pil = "" if not show_refs else (f'<span class="oa-lev">{_esc(lev)}</span>' if lev else "") + (
                f'<span class="oa-pil">{_esc(str(row["Level 2 pillar"]))}</span>' if str(row["Level 2 pillar"]).strip() else "")
            exhibits = f'<div class="oa-sub"><span class="oa-lbl">Suggested content:</span> {_esc(str(row["Key exhibits"]))}</div>' if str(row["Key exhibits"]).strip() else ""
            notes = f'<div class="oa-sub"><span class="oa-lbl">Note to presenter:</span> <em>{_esc(str(row["Notes"]))}</em></div>' if str(row["Notes"]).strip() else ""
            html.append(
                f'<div class="oa-row"><div class="oa-time">{row["Start"]}–{row["End"]}<div class="oa-sub">{int(row["Minutes"])} min</div></div>'
                f'<div><div class="oa-item">{pil}{_esc(str(row["Item"]))}</div><div>{ref_html}</div>{exhibits}{notes}</div>'
                f'<div class="oa-who">{_esc(str(row["Presenter"]))}</div></div>'
            )
        st.markdown("".join(html), unsafe_allow_html=True)

        if show_refs:
            st.markdown("**Top risks per agenda item** (across all registers, highest residual first)")
        for _, row in (timed.iterrows() if show_refs else iter(())):
            refs = split_refs(row["Level 3 refs"])
            if not refs:
                continue
            top = risks_for_refs(refs)
            with st.expander(f"{row['Start']} · {row['Item']} — {len(top)} risk(s)"):
                if top.empty:
                    st.caption("No risks tagged to these drivers yet. The presenter's register should add them.")
                else:
                    st.dataframe(top, hide_index=True, use_container_width=True)

    with t_pres:
        talk_rows = timed[timed["Section"] != "Break"]
        for fn, head in FUNCTIONS:
            mine = talk_rows[(talk_rows["Presenter function"].astype(str).str.strip() == fn)
                             | (talk_rows["Co-presenter function"].astype(str).str.strip() == fn)].copy()
            mine["Role"] = mine["Presenter function"].astype(str).str.strip().map(lambda f: "Lead" if f == fn else "Co-host")
            acc, _contrib = drivers_for_function(fn)
            st.markdown(f"#### {head} — {fn}" if head != fn else f"#### {fn}")
            if mine.empty:
                st.caption("No agenda items.")
            else:
                st.dataframe(mine[["Start", "End", "Section", "Item", "Role", "Minutes"]], hide_index=True, use_container_width=True)
            presented = {r for v in mine["Level 3 refs"] for r in split_refs(v)}
            missing = [r for r in acc["Level 3 ref"] if r not in presented]
            st.caption(f"{int(mine['Minutes'].sum())} min · accountable for {len(acc)} driver(s)"
                       + (f" · not presented: {', '.join(missing)}" if missing else " · all accountable drivers presented"))

    with t_check:
        checks, unknown = agenda_checks(agenda)
        ok = int((checks["Check"] == "OK").sum())
        st.metric("Level III drivers correctly on the agenda", f"{ok} / {len(checks)}")
        if unknown:
            st.error("Unknown Level III refs on the agenda: " + ", ".join(unknown))
        issues = checks[checks["Check"] != "OK"]
        if issues.empty:
            st.success("Every Level III driver is on the agenda exactly once, presented by its accountable executive.")
        else:
            st.warning(f"{len(issues)} driver(s) need attention.")
            st.dataframe(issues, hide_index=True, use_container_width=True)
        with st.expander("All drivers"):
            st.dataframe(checks, hide_index=True, use_container_width=True, height=700)

    with t_edit:
        with st.form("agenda_meta_form"):
            c1, c2, c3 = st.columns([3, 1, 1])
            title = c1.text_input("Meeting title", meta.get("title", ""))
            mdate = c2.text_input("Date", meta.get("date", ""), placeholder="e.g. 2026-12-03")
            start = c3.text_input("Start time", meta.get("start", "08:30"))
            if st.form_submit_button("Save meeting details"):
                save_agenda_meta({"title": title, "date": mdate, "start": start})
                st.success("Saved.")
                st.rerun()
        st.caption("Order sets the running order. Level III refs: separate with semicolons. Presenter should be the accountable function (see Checks).")
        input_zone_banner("Agenda — editable fields")
        edited = st.data_editor(
            agenda,
            num_rows="dynamic",
            hide_index=True,
            use_container_width=True,
            height=760,
            column_config={
                "Order": st.column_config.NumberColumn(step=1, width="small"),
                "Section": st.column_config.SelectboxColumn(options=AGENDA_SECTIONS),
                "Level 1 lever": st.column_config.SelectboxColumn(options=AGENDA_LEVERS),
                "Level 2 pillar": st.column_config.SelectboxColumn(options=AGENDA_PILLARS),
                "Presenter function": st.column_config.SelectboxColumn(options=[""] + FUNCTION_NAMES),
                "Co-presenter function": st.column_config.SelectboxColumn(options=[""] + FUNCTION_NAMES),
                "Minutes": st.column_config.NumberColumn(min_value=0, max_value=240, step=5),
                "Item": st.column_config.TextColumn(width="large"),
                "Key exhibits": st.column_config.TextColumn("Suggested content", width="large"),
                "Notes": st.column_config.TextColumn("Note to presenter", width="large"),
            },
            key="agenda_editor",
        )
        if st.button("Save agenda", type="primary", key="save_agenda"):
            edited.to_csv(agenda_path(), index=False)
            st.success("Agenda saved.")
            st.rerun()

    bio = BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        timed.drop(columns=["Presenter function", "Co-presenter function"], errors="ignore").rename(
            columns={"Key exhibits": "Suggested content", "Notes": "Note to presenter"}).to_excel(writer, sheet_name="Agenda", index=False)
        agenda_checks(agenda)[0].to_excel(writer, sheet_name="Driver checks", index=False)
    dl1, dl2 = st.columns([1, 1.4])
    with dl1:
        st.download_button("Download agenda (Excel)", bio.getvalue(),
                           file_name=f"Trident_Operating_Agenda_{date.today().isoformat()}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary")
    pdf_path = DATA_DIR / "exports" / "Trident_Operating_Agenda_2027_Presenter_edition.pdf"
    with dl2:
        if pdf_path.exists():
            st.download_button("Download presenter edition (PDF)", pdf_path.read_bytes(),
                               file_name=pdf_path.name, mime="application/pdf", type="primary", key="dl_agenda_pdf")
            if agenda_path().exists() and agenda_path().stat().st_mtime > pdf_path.stat().st_mtime + 60:
                st.caption("The agenda has been edited since this PDF was made – ask Claude to regenerate it.")
        else:
            st.caption("No PDF yet – ask Claude to generate the presenter edition.")


def drivers_in_manuals():
    """Per Level III driver: accountable C-level and where it appears in the ISO manuals (process register)."""
    table = driver_ownership_with_names()
    processes = collect_all_register_rows("processes")
    own, other = {}, {}
    if not processes.empty and "Linked Level 3 drivers" in processes.columns:
        sec_col = next((c for c in processes.columns if "Manual section" in c), None)
        for _, row in processes.iterrows():
            fn = REGISTER_FUNCTION.get(row["Source unit"], "")
            label = f'{row.get("Process ID", "")} {row.get("Process", "")}'.strip()
            if sec_col and str(row.get(sec_col, "")).strip():
                label += f" (§{row[sec_col]})"
            for ref in split_refs(row.get("Linked Level 3 drivers", "")):
                own.setdefault((ref, fn), []).append(label)
    rows = []
    for _, r in table.iterrows():
        ref, acc = r["Level 3 ref"], str(r["Accountable function"]).strip()
        in_own = own.get((ref, acc), [])
        in_other = [p for (rf, fn), ps in own.items() if rf == ref and fn != acc for p in ps]
        rows.append({
            "Level 3 ref": ref, "Value driver": r["Value driver"],
            "Accountable": CLEVEL_TITLE.get(acc, acc), "Accountable executive": r.get("Accountable executive", ""),
            "Processes in accountable manual": len(in_own),
            "Suggested main process": MAIN_PROCESS_SUGGESTION.get(ref, "To be named" if in_own else "Manual not yet built"),
            "Linked processes (own manual)": "; ".join(in_own),
            "Linked processes (other manuals)": "; ".join(in_other),
        })
    return pd.DataFrame(rows)


def render_drivers_in_manuals():
    st.subheader("How the value drivers appear in the ISO manuals")
    st.write(
        "Every process in an executive's ISO manual lists the Level III drivers it serves – that is the link. "
        "**Accountable:** the executive's own manual holds the *main process* that delivers the driver end-to-end, "
        "with its KPI, controls and linked risks. **Contributing:** the executive's process delivers an input to that "
        "main process (an interface), but does not own the outcome."
    )
    df = drivers_in_manuals()
    c = st.columns(3)
    c[0].metric("Drivers with a process in the accountable manual", str(int((df["Processes in accountable manual"] > 0).sum())) + f" / {len(df)}")
    c[1].metric("Main process suggested", int(df["Suggested main process"].map(lambda v: v not in ("To be named", "Manual not yet built")).sum()))
    c[2].metric("Accountable manual not yet built", int((df["Suggested main process"] == "Manual not yet built").sum()))
    fn_filter = st.selectbox("Show drivers for", ["All"] + sorted(df["Accountable"].unique().tolist()), key="manual_fn_filter")
    view = df if fn_filter == "All" else df[df["Accountable"] == fn_filter]
    st.dataframe(view, hide_index=True, use_container_width=True, height=760)
    st.caption("Next step: each executive names one main process per driver they are accountable for and writes it into their ISO manual. "
               "General processes that link to almost every driver (planning, risk integration, execution, value realisation) "
               "support all drivers but should not be the main process for any of them.")


def render_imers_equation():
    cols = [
        ("IMS", "HOW WE WORK", "Integrated Management System: our ISO manuals – processes, roles and controls in every department.", [
            ("ISO 9001 · 14001", "International standards for quality (9001) and environmental (14001) management."),
            ("Process · Level IV-A", "A repeatable way of working with an owner, steps, controls and KPIs."),
            ("Control = mitigation", "A step in an ISO process that also reduces a risk – done once."),
            ("KPI", "Key performance indicator: are we delivering what we promised?")]),
        ("ERM", "WHAT COULD STOP US", "Enterprise Risk Management: one company-wide way to find, assess, treat and follow up risks.", [
            ("Risk register · Level IV-B", "Each department's risks, tagged to the value driver they threaten."),
            ("Enterprise Risk Register", "The material risks from all registers, in one view for the CEO and board."),
            ("Appetite · residual risk", "Risk we accept · risk left after controls (likelihood × impact, 1–25)."),
            ("KRI", "Key risk indicator: an early warning that a risk is growing.")]),
        ("Value tree", "WHY WE DO IT", "A map of how Trident creates value: our goal broken down step by step to each department's work.", [
            ("Shareholder value · Level 0", "Our overall goal: equity value ≈ EBITDA × multiple − net debt."),
            ("Levers · pillars · Levels 1–2", "3 levers (EBITDA, multiple, cash) and 5 pillars where value is made."),
            ("Value driver · Level III", "35 concrete ways we create value, e.g. 3.1.1 Rate uplift on existing vessels."),
            ("Accountable executive", "The one executive who owns a value driver; others may contribute.")]),
    ]
    from html import escape as _e
    def col(name, eb, d, terms):
        t = "".join(f'<div style="background:#fff;border-radius:8px;padding:10px 12px;margin-top:8px">'
                    f'<div style="font-weight:700;color:#00222a">{_e(a)}</div>'
                    f'<div style="font-size:.85rem;color:#00222a;line-height:1.35">{_e(b)}</div></div>' for a, b in terms)
        return (f'<div style="background:#bcd9ff;border-radius:12px;padding:10px">'
                f'<div style="background:#00222a;border-radius:8px;padding:14px">'
                f'<div style="color:#caff74;font-size:.72rem;letter-spacing:.14em;font-weight:700">{eb}</div>'
                f'<div style="color:#fff;font-size:1.7rem;font-weight:700">{_e(name)}</div>'
                f'<div style="color:#f2ede6;font-size:.86rem;line-height:1.35">{_e(d)}</div></div>{t}</div>')
    op = lambda o: f'<div style="display:flex;align-items:flex-start;justify-content:center;padding-top:60px;font-size:2.6rem;font-weight:700;color:#00222a">{o}</div>'
    result = ('<div style="background:#caff74;border-radius:12px;padding:20px;color:#00222a">'
              '<div style="font-size:.72rem;letter-spacing:.14em;font-weight:700">THE RESULT</div>'
              '<div style="font-size:2.4rem;font-weight:800">IMERS</div>'
              '<div style="font-size:1.15rem;font-weight:600;margin-bottom:18px">Integrated Management &amp; Enterprise Risk System</div>'
              '<p>IMS, ERM and our value tree in one model.</p>'
              '<p>Every process and every risk traces to a value driver – and every driver to shareholder value.</p>'
              '<p><b>One owner. One process. One risk view.</b></p></div>')
    html = ('<div style="display:grid;grid-template-columns:1fr 40px 1fr 40px 1fr 40px 1fr;gap:0;align-items:stretch">'
            + col(*cols[0]) + op("+") + col(*cols[1]) + op("+") + col(*cols[2]) + op("=") + result + "</div>")
    st.markdown(html, unsafe_allow_html=True)


ERM_STEPS = ["1 · Identify", "2 · Assess", "3 · Decide", "4 · Act", "5 · Monitor", "6 · Escalate", "7 · Close & embed"]
ERM_LANES = [
    ("Risk owner (in the department)", ["Identifies risks against the department's value drivers", "Scores inherent and residual risk – residual only counts controls that are IV-A process steps", "Proposes treatment and target score", "Carries out treatment actions", "Follows KRIs; updates score and actions", "", "Completed action becomes a step in an IV-A process; reassesses the score"]),
    ("Executive (C-level, accountable for the driver)", ["Confirms the risks for own drivers", "", "Decides treatment, target and date – within appetite", "Provides resources", "Reviews the register quarterly in the department", "Raises risks that need CEO attention", "Approves the updated process"]),
    ("CS&BDO (procedure owner, SBD-P09)", ["Provides templates and the common scale", "Quality-assures scores across departments", "", "", "Consolidates the Enterprise Risk Register quarterly", "Brings material risks (12+ or outside appetite) to the CEO", "Updates the Enterprise Risk Register"]),
    ("CEO", ["", "", "Decides on material risks: treat, accept, transfer or avoid", "", "", "Prioritises across departments; reports to the board", ""]),
    ("Board", ["", "", "Approves risk appetite", "", "", "Receives the Enterprise Risk Register", ""]),
]


def render_erm_process_map():
    from html import escape as _e
    st.subheader("IV-B · The risk process – who does what")
    st.write("One common risk procedure for all of Trident (owned by CS&BDO, SBD-P09). Every department follows the same seven steps; "
             "IV-A holds each department's processes, IV-B shows how their risks are run. The cycle repeats quarterly.")
    head = "".join(f'<div style="background:#00222a;color:#caff74;font-weight:700;padding:8px;border-radius:6px;text-align:center;font-size:.85rem">{_e(x)}</div>' for x in ERM_STEPS)
    rows = ""
    for i, (lane, cells) in enumerate(ERM_LANES):
        bg = ["#eef4f6", "#e3eefc", "#f2ede6", "#fff3e6", "#f7e8e8"][i]
        rows += f'<div style="background:{bg};font-weight:700;padding:10px;border-radius:6px;font-size:.85rem;color:#00222a">{_e(lane)}</div>'
        for c in cells:
            if c:
                hl = "border:2px solid #00839B;" if "IV-A" in c else "border:1px solid #c9d6da;"
                rows += f'<div style="background:#fff;{hl}padding:8px;border-radius:6px;font-size:.8rem;line-height:1.3;color:#00222a">{_e(c)}</div>'
            else:
                rows += f'<div style="background:{bg};border-radius:6px;opacity:.55"></div>'
    st.markdown(f'<div style="display:grid;grid-template-columns:200px repeat(7,1fr);gap:6px;margin-top:8px"><div></div>{head}{rows}</div>',
                unsafe_allow_html=True)
    st.caption("Highlighted cells are where IV-B meets IV-A: residual scores rest on process controls, and completed actions become process steps.")


def render_about_imers():
    st.subheader("IMS + ERM + our value tree = IMERS")
    t_eq, t_map, t_abbr, t_deck = st.tabs(["What IMERS is", "IV-B · Risk process map", "Abbreviations", "Presentation"])
    with t_map:
        render_erm_process_map()
    with t_eq:
        render_imers_equation()
        st.caption("All abbreviations are listed under the Abbreviations tab.")
    with t_abbr:
        c_codes, c_abbr = st.columns([1, 2])
        with c_codes:
            st.markdown("**Department codes**")
            st.dataframe(pd.DataFrame(DEPARTMENT_CODES, columns=["Code", "Department"]), hide_index=True,
                         use_container_width=True, height=36 * (len(DEPARTMENT_CODES) + 1))
            st.caption("Used in risk and process IDs, e.g. SBD-R001. SBD is in use today; the other codes are proposed.")
        with c_abbr:
            st.markdown("**Codes and abbreviations**")
            st.dataframe(pd.DataFrame(ABBREVIATIONS, columns=["Abbreviation", "Meaning"]), hide_index=True,
                         use_container_width=True, height=36 * (len(ABBREVIATIONS) + 1))
    with t_deck:
        exp = DATA_DIR / EXPORTS_DIR_NAME
        pptx_path, pdf_path = exp / f"{IMERS_DECK_NAME}.pptx", exp / f"{IMERS_DECK_NAME}.pdf"
        st.write("The IMERS concept presentation for the management group – the same graphics as in this model.")
        c1, c2, _ = st.columns([1, 1, 2])
        if pptx_path.exists():
            c1.download_button("Download presentation (PowerPoint)", pptx_path.read_bytes(), file_name=pptx_path.name,
                               mime="application/vnd.openxmlformats-officedocument.presentationml.presentation", key="dl_imers_pptx")
        if pdf_path.exists():
            c2.download_button("Download presentation (PDF)", pdf_path.read_bytes(), file_name=pdf_path.name,
                               mime="application/pdf", key="dl_imers_pdf")
        slides = sorted((exp / "imers_slides").glob("slide-*.jpg"))
        if slides:
            n = st.slider("Slide", 1, len(slides), 1, key="imers_slide_no")
            st.image(str(slides[n - 1]), use_container_width=True)
        elif not pptx_path.exists():
            st.info(f"Place {IMERS_DECK_NAME}.pptx and .pdf in data/exports to show them here.")


CANDIDATE_COLUMNS = ["Candidate ID", "Proposed value driver", "Proposed pillar", "Proposed by", "Rationale",
                     "Related existing drivers", "Status", "Decision / comment"]
CANDIDATE_STATUS = ["Proposed", "Under review", "Accepted – add to Level III", "Merged into existing driver", "Rejected"]
PILLAR_OPTIONS = ["PIL-01 Organic EBITDA Growth", "PIL-02 Investment EBITDA Growth", "PIL-03 Multiple Expansion",
                  "PIL-04 Cash Conversion", "PIL-05 Capital Allocation & Balance-Sheet Optimization"]


def render_candidate_drivers():
    st.subheader("Candidate value drivers")
    st.write(
        "The 35 Level III drivers are our starting point, not the final list. While each department defines its processes, "
        "proposals for new, split or merged drivers are collected here – and decided together in one round "
        "(planned for the April calibration), so the value tree stays stable while the work is under way."
    )
    path = DATA_DIR / "candidate_drivers.csv"
    df = safe_read_csv(path, CANDIDATE_COLUMNS)
    for c in CANDIDATE_COLUMNS:
        if c not in df.columns:
            df[c] = ""
    df = df[CANDIDATE_COLUMNS].fillna("")
    cols = st.columns(3)
    cols[0].metric("Candidates", len(df))
    cols[1].metric("Open (proposed / under review)", int(df["Status"].isin(["Proposed", "Under review", ""]).sum()))
    cols[2].metric("Accepted", int(df["Status"].str.startswith("Accepted").sum()))
    input_zone_banner("Candidate drivers — editable fields")
    edited = st.data_editor(
        df, hide_index=True, use_container_width=True, num_rows="dynamic", height=420, key="candidate_editor",
        column_config={
            "Proposed pillar": st.column_config.SelectboxColumn(options=PILLAR_OPTIONS),
            "Proposed by": st.column_config.SelectboxColumn(options=FUNCTION_NAMES),
            "Status": st.column_config.SelectboxColumn(options=CANDIDATE_STATUS),
            "Rationale": st.column_config.TextColumn(width="large"),
            "Decision / comment": st.column_config.TextColumn(width="medium"),
        },
    )
    if st.button("Save candidate drivers", type="primary", key="save_candidates"):
        out = edited.fillna("")
        missing = out["Candidate ID"].astype(str).str.strip() == ""
        if missing.any():
            used = [int(x.split("-")[1]) for x in out["Candidate ID"] if str(x).startswith("CAND-") and str(x).split("-")[1].isdigit()]
            nxt = max(used, default=0)
            for i in out.index[missing]:
                nxt += 1
                out.at[i, "Candidate ID"] = f"CAND-{nxt:02d}"
        out[CANDIDATE_COLUMNS].to_csv(path, index=False)
        st.success("Candidate drivers saved.")
    st.caption("Accepted candidates are added to the Level III tree in one go after the April calibration, "
               "with an accountable executive and links to processes and risks.")


def render_enterprise_view():
    t_mat, t_own, t_cov, t_iso, t_cand = st.tabs(["Material risks", "Value driver ownership", "Value coverage", "Drivers in ISO manuals", "Candidate drivers"])
    with t_mat:
        render_material_risks()
    with t_own:
        render_driver_ownership_editor()
    with t_cov:
        render_value_coverage()
    with t_iso:
        render_drivers_in_manuals()
    with t_cand:
        render_candidate_drivers()


def render_driver_ownership_editor():
    st.subheader("Value driver ownership")
    st.write(
        "Every function traces to the value hierarchy through Level III. Each driver has **one accountable function** "
        "(owns delivery) and any number of **contributing functions** (their processes feed the driver). "
        "Mapping at Level III automatically places the function under its pillar (Level II) and value lever (Level I)."
    )
    ownership = load_driver_ownership()
    summary = function_summary(ownership)
    st.markdown("**Functions at a glance**")
    st.dataframe(summary, hide_index=True, use_container_width=True)
    if (summary["Accountable drivers"] == 0).any():
        st.warning("Some functions have no accountable driver. Either assign one, or the Level III tree is not refined enough for that function.")

    st.markdown("**Edit ownership**")
    st.caption("Contributing functions: separate with semicolons, using the function names above.")
    input_zone_banner("Driver ownership — editable fields")
    view = driver_ownership_with_names(ownership)
    edited = st.data_editor(
        view,
        hide_index=True,
        use_container_width=True,
        height=760,
        disabled=["Level 3 ref", "Pillar", "Value driver", "Accountable executive"],
        column_config={
            "Accountable function": st.column_config.SelectboxColumn(options=FUNCTION_NAMES, required=False),
            "Contributing functions": st.column_config.TextColumn(width="large"),
            "Notes": st.column_config.TextColumn(width="medium"),
        },
        key="driver_ownership_editor",
    )
    if st.button("Save driver ownership", type="primary", key="save_driver_ownership"):
        unknown = sorted({
            fn for v in edited["Contributing functions"] for fn in split_refs(v) if fn not in FUNCTION_NAMES
        })
        if unknown:
            st.error("Unknown function name(s) in Contributing functions: " + ", ".join(unknown))
        else:
            edited[DRIVER_OWNERSHIP_COLUMNS].fillna("").to_csv(driver_ownership_path(), index=False)
            st.success("Driver ownership saved.")

    with st.expander("Matrix view (A = accountable, C = contributing)"):
        st.dataframe(function_driver_matrix(ownership), hide_index=True, use_container_width=True, height=700)


def render_value_coverage():
    st.subheader("Value coverage across all registers")
    st.write(
        "For each Level III driver: who owns it, how many processes deliver it and how many risks protect it, "
        "counted across all unit registers. A driver is fully covered when it has an accountable function, "
        "at least one process and at least one risk."
    )
    coverage = value_coverage()
    covered = int((coverage["Gaps"] == "Covered").sum())
    no_owner = int(coverage["Gaps"].str.contains("No accountable|not recognised").sum())
    no_proc = int(coverage["Gaps"].str.contains("No processes").sum())
    no_risk = int(coverage["Gaps"].str.contains("No risks").sum())
    cols = st.columns(4)
    cols[0].metric("Drivers fully covered", f"{covered} / {len(coverage)}")
    cols[1].metric("Without accountable function", no_owner)
    cols[2].metric("Without processes", no_proc)
    cols[3].metric("Without risks", no_risk)

    st.markdown("**Coverage by pillar**")
    by_pillar = (
        coverage.assign(Covered=coverage["Gaps"].eq("Covered"))
        .groupby("Pillar")
        .agg(Drivers=("Level 3 ref", "count"), Covered=("Covered", "sum"), Risks=("Risks", "sum"), Processes=("Processes", "sum"))
        .reset_index()
    )
    st.dataframe(by_pillar, hide_index=True, use_container_width=True)
    explain = [
        ("Pillar", "The five value pillars, PIL-01 to PIL-05 (Level II)."),
        ("Drivers", "How many Level III value drivers sit under the pillar – 35 in total."),
        ("Covered", "Drivers with all three in place: an owner, a process and a risk."),
        ("Risks", "Risk links: a risk tagged to two drivers counts twice. What protects the value."),
        ("Processes", "ISO process links: one process can serve many drivers. What delivers the value."),
    ]
    st.markdown(
        '<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin:4px 0 18px">'
        + "".join(
            f'<div style="background:#00222a;color:#f2ede6;border-radius:8px;padding:10px 12px">'
            f'<div style="color:#caff74;font-weight:700;margin-bottom:4px">↑ {t}</div>'
            f'<div style="font-size:.85rem;line-height:1.35">{d}</div></div>'
            for t, d in explain
        )
        + "</div>",
        unsafe_allow_html=True,
    )

    only_gaps = st.toggle("Show only drivers with gaps", value=False, key="coverage_only_gaps")
    view = coverage[coverage["Gaps"] != "Covered"] if only_gaps else coverage
    st.dataframe(
        view,
        hide_index=True,
        use_container_width=True,
        height=760,
        column_config={"Highest residual": st.column_config.ProgressColumn(min_value=0, max_value=25, format="%d")},
    )
    st.caption("Most departments have not filled in their registers yet, so gaps are expected until each function has mapped its processes and risks.")


def render_function_value_map(selected_register):
    """On a unit's Context page: where this function sits in the value hierarchy."""
    function_name = REGISTER_FUNCTION.get(selected_register)
    if not function_name:
        st.info(
            f"**{selected_register}** is a geography rather than an executive function. Its processes and risks "
            "should link to the same Level III drivers as the functions it supports (see Enterprise Risk Register → Value driver ownership)."
        )
        return
    acc, contrib = drivers_for_function(function_name)
    with st.expander(f"Where {function_name} sits in the value hierarchy — {len(acc)} accountable, {len(contrib)} contributing drivers", expanded=False):
        left, right = st.columns(2)
        with left:
            st.markdown("**Accountable for**")
            if acc.empty:
                st.caption("No accountable drivers yet.")
            else:
                st.dataframe(acc[["Level 3 ref", "Pillar", "Value driver"]], hide_index=True, use_container_width=True)
        with right:
            st.markdown("**Contributes to**")
            if contrib.empty:
                st.caption("No contributing drivers yet.")
            else:
                st.dataframe(contrib[["Level 3 ref", "Pillar", "Value driver", "Accountable function"]], hide_index=True, use_container_width=True)
        st.caption("Link this register's processes and risks to these drivers. Ownership is maintained in Enterprise Risk Register → Value driver ownership.")


def render_material_risks():
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
    .vh-erm5-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:6px;align-items:start;margin-top:6px}
    .vh-erm5-col{border:1px solid #efd3c6;border-radius:8px;padding:5px;background:#fff;opacity:.7}
    .vh-erm5-col-on{opacity:1;border-color:#d94b18}
    .vh-erm5-head{background:#34464b;color:#fff;border-radius:6px;padding:5px 4px;text-align:center;font-size:.72rem;line-height:1.2;margin-bottom:5px}
    .vh-erm5-driver{border:1px solid #e3e3e3;border-radius:6px;padding:4px 5px;margin:6px 0 3px 0;font-size:.68rem;line-height:1.2;color:#9aa6a9;background:#fafafa;text-align:center}
    .vh-erm5-driver-on{background:#ffc9b0;border-color:#d94b18;color:#00191d}
    .vh-erm5-orphan{border-style:dashed;border-color:#d94b18;color:#8a3a18;background:#fff}
    .vh-erm-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(135px,1fr));gap:6px;align-items:start;margin-top:6px}
    .vh-erm-col{border:1px solid #efd3c6;border-radius:8px;padding:5px;background:#fff;opacity:.6}
    .vh-erm-col-on{opacity:1;border-color:#d94b18}
    .vh-erm-col-orphan{border-style:dashed}
    .vh-erm-head{background:#34464b;color:#fff;border-radius:6px;padding:5px 4px;text-align:center;font-size:.72rem;line-height:1.2;margin-bottom:5px}
    .vh-erm-count{color:#ffc9b0;font-size:.68rem;margin-top:2px}
    .vh-erm-card{background:#fff6f1;border:1px solid #f1b89c;border-radius:6px;padding:4px 5px;margin-bottom:4px;font-size:.68rem;line-height:1.2;color:#00191d;cursor:help}
    .vh-erm-card-top{display:flex;justify-content:space-between;align-items:center;margin-bottom:2px}
    .vh-erm-id{font-weight:700}
    .vh-erm-score{border-radius:4px;padding:0 5px;font-weight:700;font-size:.68rem}
    .vh-erm-iso{color:#8a3a18;font-size:.62rem;margin-top:2px}
    .vh-erm-legend{font-size:.72rem;color:#8a3a18;margin-top:6px}
    .vh-proc-bar{height:8px;background:#e3ece0;border-radius:4px;overflow:hidden;margin:-4px 0 4px 0}
    .vh-proc-bar div{height:100%;background:#00839B}
    .vh-proc-breadth{font-size:.75rem;color:#4b6166;margin-bottom:8px}
    .vh-proc-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:6px;align-items:start}
    .vh-proc-col{border:1px solid #d9e3e6;border-radius:8px;padding:5px;background:#fff;opacity:.65}
    .vh-proc-col-on{opacity:1;border-color:#90c44f}
    .vh-proc-head{background:#34464b;color:#fff;border-radius:6px;padding:5px 4px;text-align:center;font-size:.72rem;line-height:1.2;margin-bottom:5px}
    .vh-proc-count{color:#caff74;font-size:.68rem;margin-top:2px}
    .vh-proc-chip{border:1px solid #d9e3e6;border-radius:6px;padding:4px 5px;margin-bottom:4px;font-size:.68rem;line-height:1.2;color:#8a9a9e;background:#fff;text-align:center}
    .vh-proc-chip-on{background:#caff74;border-color:#90c44f;color:#00191d}
    
        
        div[class*="st-key-vh_help"] div[data-testid="stHorizontalBlock"] {
            gap: 0.35rem !important;
        }
        div[class*="st-key-vh_help"] div[data-testid="stColumn"] {
            flex: 0 0 auto !important;
            width: auto !important;
            min-width: 0 !important;
        }
        div[class*="st-key-vh_help"] button {
            width: auto !important;
            padding-left: 0.85rem !important;
            padding-right: 0.85rem !important;
            white-space: nowrap !important;
        }

/* Help buttons: Streamlit stamps class st-key-vh_help_* on keyed containers */
        div[class*="st-key-vh_help"] button,
        div[class*="st-key-vh_help"] [data-testid="stBaseButton-secondary"],
        div[class*="st-key-vh_help"] [data-testid="baseButton-secondary"] {
            background-color: #5a6570 !important;
            background-image: none !important;
            border: 1px solid #3d4650 !important;
            color: #ffffff !important;
            min-height: 2.1rem !important;
            font-weight: 700 !important;
            box-shadow: 0 1px 2px rgba(0,25,29,.14) !important;
        }
        div[class*="st-key-vh_help"] button:hover,
        div[class*="st-key-vh_help"] [data-testid="stBaseButton-secondary"]:hover {
            background-color: #3d4650 !important;
            border-color: #2a3138 !important;
            color: #ffffff !important;
        }
        div[class*="st-key-vh_help"] button p,
        div[class*="st-key-vh_help"] span {
            color: #ffffff !important;
        }

    
    /* Editable input zone — data_editor cells are canvas-drawn; grey the panel. */
    .vh-input-banner{
        background:#c5ccd6;border:1px solid #6b7580;border-radius:8px;
        padding:8px 12px;margin:0 0 10px 0;color:#00191d;font-size:.92rem;font-weight:600;
    }
    div[class*="st-key-vh_input"]{
        background:#d7dde5 !important;
        border:2px solid #6b7580 !important;
        border-radius:10px !important;
        padding:12px 12px 8px 12px !important;
        margin:0 0 10px 0 !important;
    }
    div[class*="st-key-vh_input"] [data-testid="stDataEditor"],
    div[class*="st-key-vh_input"] [data-testid="stDataFrame"]{
        background:#e4e8ee !important;
        border:1px solid #8b949e !important;
        border-radius:8px !important;
    }

</style>
    """, unsafe_allow_html=True)


def render_value_hierarchy(processes=None, risks=None, controls=None, actions=None, function_name=None):
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
    div[class*="st-key-l3acc_"] button[data-testid="stPopoverButton"]{background:#00839B !important;border:2px solid #006677 !important;color:#fff !important}
    div[class*="st-key-l3acc_"] button[data-testid="stPopoverButton"] p{color:#fff !important;font-weight:700 !important}
    div[class*="st-key-l3con_"] button[data-testid="stPopoverButton"]{background:#d6f0f4 !important;border:2px solid #00839B !important}
    div[class*="st-key-l3tag_"] button[data-testid="stPopoverButton"]{background:#fff !important;border:2px dashed #d94b18 !important}
    div[class*="st-key-l3non_"] button[data-testid="stPopoverButton"]{opacity:.38}
    div[class*="st-key-l3"] .stMarkdownBadge{background:#00222a !important;color:#ffffff !important;font-weight:700 !important;letter-spacing:.04em}
    div[class*="st-key-l3acc_"] .stMarkdownBadge{background:#caff74 !important;color:#00222a !important}
    .vh-mark-count{display:block;font-size:.8rem;font-weight:600;margin-top:4px;opacity:.95}
    .vh-legend{display:flex;flex-wrap:wrap;gap:16px;justify-content:center;font-size:.84rem;color:#255a64;margin:2px 0 10px}
    .vh-legend span{display:inline-flex;align-items:center;gap:6px}
    .vh-legend i{display:inline-block;width:22px;height:13px;border-radius:3px}
    </style>
    <div class="vh-level">Level 0 · Overall objective</div>
    <div class="vh-box vh-top">0 · Maximize shareholder value in Trident<br><span style="font-weight:400">Equity Value ≈ (EBITDA × EV/EBITDA multiple) − NIBD</span></div>
    <div class="vh-level">Level I · AIP value levers</div>
    """, unsafe_allow_html=True)
    driver_roles = {}
    own = load_driver_ownership()
    accountable_by_ref = {
        str(orow["Level 3 ref"]).strip(): str(orow["Accountable function"]).strip() for _, orow in own.iterrows()
    }
    if function_name:
        for _, orow in own.iterrows():
            ref = str(orow["Level 3 ref"]).strip()
            if str(orow["Accountable function"]).strip() == function_name:
                driver_roles[ref] = "acc"
            elif function_name in split_refs(orow["Contributing functions"]):
                driver_roles[ref] = "con"

    def role_counts(pillar_numbers):
        refs = [item["reference"] for item in level3_driver_catalog() if item["reference"].split(".")[1] in pillar_numbers]
        a = sum(1 for r in refs if driver_roles.get(r) == "acc")
        c = sum(1 for r in refs if driver_roles.get(r) == "con")
        return a, c

    def count_html(a, c):
        if not function_name:
            return ""
        if a == 0 and c == 0:
            return '<span class="vh-mark-count">not in scope</span>'
        return f'<span class="vh-mark-count">{a} accountable · {c} contributing</span>'

    aip_cols = st.columns([2, 1, 2])
    aip_labels = [
        '<span class="vh-aip-badge">1.1</span> EBITDA' + count_html(*role_counts(["1", "2"])),
        '<span class="vh-aip-badge">1.2</span> Multiple' + count_html(*role_counts(["3"])),
        '<span class="vh-aip-badge">1.3</span> Cash' + count_html(*role_counts(["4", "5"])),
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

    st.markdown('<div class="vh-level">Level II · Trident value pillars — where Trident creates and protects value</div>', unsafe_allow_html=True)
    pillar_cols = st.columns(5)
    for idx, (column, (pillar, drivers)) in enumerate(zip(pillar_cols, groups), start=1):
        with column:
            st.markdown(f'<div class="vh-box vh-pil"><div>{pillar}{count_html(*role_counts([str(idx)]))}</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="vh-level">Level III · Value drivers — how each pillar is delivered</div>', unsafe_allow_html=True)
    if function_name:
        st.markdown(
            '<div class="vh-legend">'
            f'<span><i style="background:#00839B;border:2px solid #006677"></i>{escape(function_name)} accountable</span>'
            '<span><i style="background:#d6f0f4;border:2px solid #00839B"></i>Contributing</span>'
            '<span><i style="background:#fff;border:2px dashed #d94b18"></i>Not in scope, but tagged by this register\'s risks</span>'
            '<span><i style="background:#fff;border:1px solid #a4c4e9;opacity:.38"></i>Not in scope</span>'
            '</div>',
            unsafe_allow_html=True,
        )
    driver_cols = st.columns(5)
    for column, (pillar, drivers) in zip(driver_cols, groups):
        with column:
            with st.container(border=True):
                for reference, driver in drivers:
                    if reference == "divider":
                        st.markdown(f'<div class="vh-cfo-divider">{driver}</div>', unsafe_allow_html=True)
                        continue
                    linked_processes = linked_processes_by_driver.get(reference, [])
                    linked_risks = linked_risks_by_driver.get(reference, [])
                    if function_name:
                        state = driver_roles.get(reference) or ("tag" if linked_risks else "non")
                    else:
                        state = "all"
                    _acc = accountable_by_ref.get(reference, "")
                    _tag = CLEVEL_TITLE.get(_acc, "")
                    _badge = f" :{'orange' if function_name and _acc == function_name else 'gray'}-badge[{_tag}]" if _tag else ""
                    with st.container(key=f"l3{state}_{reference.replace('.', '_')}_{ACTIVE_REGISTER_KEY}"), \
                            st.popover(f"{reference} · {driver}{_badge}", use_container_width=True):
                        if function_name:
                            role_text = {
                                "acc": f"**{function_name} is accountable** for this driver.",
                                "con": f"**{function_name} contributes** to this driver.",
                                "tag": f"Not in {function_name}'s scope, but risks in this register are tagged to it. Either move those risks to the accountable function's register or add {function_name} as contributor.",
                                "non": f"Not in {function_name}'s scope.",
                            }[state]
                            st.markdown(role_text)
                        acc_fn = accountable_by_ref.get(reference, "")
                        if acc_fn:
                            head = FUNCTION_HEAD.get(acc_fn, "")
                            st.caption(f"Accountable executive: {head} ({acc_fn})" if head and head != acc_fn else f"Accountable: {acc_fn}")
                        else:
                            st.caption("No accountable executive assigned yet.")
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
                            st.caption("No risks linked to this Level III driver yet.")

    st.markdown('<div class="vh-level">Level IV · Applied across every pillar and value driver</div>', unsafe_allow_html=True)
    iso_col, erm_col = st.columns(2)
    with iso_col:
        st.markdown('<div class="vh-support vh-iso"><strong>IV-A · ISO-aligned delivery and follow-up</strong>Processes, owners, interfaces, procedures, controls, KPIs, documentation, evidence and continual improvement strengthen delivery of all five pillars.</div>', unsafe_allow_html=True)
    with erm_col:
        st.markdown('<div class="vh-support vh-erm"><strong>IV-B · ERM monitoring and protection</strong>Threats, risk assessments, controls, KRIs, appetite, mitigation and escalation protect all five pillars from adverse movement.</div>', unsafe_allow_html=True)

    st.markdown(f'<div class="vh-level">Level IV in detail · ISO-aligned {escape(function_name or "Strategy & Business Development")} process architecture</div>', unsafe_allow_html=True)
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
        "Left: open a process for its Level III drivers (ISO). "
        "Right: all risks by pillar and Level III driver. "
        "Edit process links under More modules -> Processes & Process Owners."
    )
    iso_col, erm_col = st.columns(2, gap="medium")

    with iso_col:
        st.markdown(
            '<div class="vh-l5-iso-pane"><div class="vh-l5-pane-title">IV-A · ISO processes</div></div>',
            unsafe_allow_html=True,
        )
        for _, process in process_rows.iterrows():
            process_id = str(process.get("Process ID", ""))
            section = process.get("S&BD Manual section", "")
            process_name = process.get("Process", "")
            linked_refs = split_refs(process.get("Linked Level 3 drivers", ""))
            n_total = len(driver_lookup) or 35
            n_link = len({r for r in linked_refs if r in driver_lookup})
            pct = round(100 * n_link / n_total)
            process_label = f"{section} · {process_id} · {process_name}  —  {n_link}/{n_total} drivers ({pct} %)"
            with st.expander(process_label, expanded=False):
                breadth = ("Broad – supports most of the value tree; check whether it is a general management process or should be split"
                           if pct >= 60 else "Focused – supports a defined part of the value tree" if pct >= 15
                           else "Narrow – supports a few specific drivers")
                left_parts = [
                    '<div class="vh-l5-iso-pane">',
                    f'<div class="vh-l5-pane-title">Level III value drivers supported by this process · '
                    f'{n_link} of {n_total} ({pct} %)</div>',
                    f'<div class="vh-proc-bar"><div style="width:{pct}%"></div></div>'
                    f'<div class="vh-proc-breadth">{escape(breadth)}</div>',
                ]
                if not linked_refs:
                    left_parts.append('<div class="vh-l5-empty-slot">No Level III value drivers linked yet.</div>')
                else:
                    left_parts.append('<div class="vh-proc-grid">')
                    for pillar_number, pillar_name in pillar_lookup.items():
                        pillar_code, pillar_description = pillar_name.split(" · ", 1)
                        all_refs = sorted([r for r in driver_lookup if r.startswith(f"3.{pillar_number}.")],
                                          key=lambda r: [int(x) for x in r.split(".")])
                        n_linked = sum(1 for r in all_refs if r in linked_refs)
                        left_parts.append(
                            f'<div class="vh-proc-col{" vh-proc-col-on" if n_linked else ""}">'
                            f'<div class="vh-proc-head"><b>{escape(pillar_code)}</b><br>{escape(pillar_description)}'
                            f'<div class="vh-proc-count">{n_linked} of {len(all_refs)}</div></div>'
                        )
                        for reference in all_refs:
                            on = reference in linked_refs
                            left_parts.append(
                                f'<div class="vh-proc-chip{" vh-proc-chip-on" if on else ""}">'
                                f'<b>{escape(reference)}</b> {escape(driver_lookup.get(reference, ""))}</div>'
                            )
                        left_parts.append("</div>")
                    left_parts.append("</div>")
                left_parts.append("</div>")
                st.markdown("".join(left_parts), unsafe_allow_html=True)
                map_path = APP_DIR / "assets" / f"{process_id}_process_map.png"
                if map_path.exists():
                    st.markdown('<div class="vh-l5-pane-title" style="margin-top:14px">Process map – how the process runs</div>',
                                unsafe_allow_html=True)
                    st.image(str(map_path), use_container_width=True)

    with erm_col:
        st.markdown(
            '<div class="vh-l5-erm-pane"><div class="vh-l5-pane-title">'
            "IV-B · ERM risk categories (five pillars)</div></div>",
            unsafe_allow_html=True,
        )
        st.caption("All risks by pillar and Level III driver – the same layout as Level III above. "
                   "How risks are run step by step: About IMERS → IV-B · Risk process map.")

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

        process_label_by_id = {}
        if processes is not None and not processes.empty:
            for _, prow in processes.iterrows():
                pid = str(prow.get("Process ID", "")).strip()
                if pid:
                    sec = str(prow.get("S&BD Manual section", "")).strip()
                    process_label_by_id[pid] = f"{sec} · {pid} · {str(prow.get('Process', '')).strip()}" if sec else pid

        def heat(score):
            try:
                v = int(float(score))
            except (TypeError, ValueError):
                return "#e6ecee", "#00191d", ""
            if v >= 20: return "#7A1F2B", "#fff", str(v)
            if v >= 15: return "#C8433A", "#fff", str(v)
            if v >= 10: return "#E8894A", "#00191d", str(v)
            if v >= 5: return "#E9E58A", "#00191d", str(v)
            return "#BFD8C8", "#00191d", str(v)

        def risk_card(risk_row):
            rid = str(risk_row.get("Risk ID", ""))
            title = str(risk_row.get("Risk title", ""))
            bg, ink, sc = heat(risk_row.get("Residual score", ""))
            procs = split_refs(risk_row.get("Processes", ""))
            tip = "; ".join(process_label_by_id.get(pid, pid) for pid in procs) if procs else "Not yet linked to an ISO process"
            iso = ", ".join(procs) if procs else "no ISO process yet"
            return (f'<div class="vh-erm-card" title="ISO process coverage: {escape(tip)}">'
                    f'<div class="vh-erm-card-top"><span class="vh-erm-id">{escape(rid)}</span>'
                    f'<span class="vh-erm-score" style="background:{bg};color:{ink}">{escape(sc)}</span></div>'
                    f'<div class="vh-erm-title">{escape(title)}</div>'
                    f'<div class="vh-erm-iso">ISO: {escape(iso)}</div></div>')

        def sort_by_score(df):
            if "Residual score" in df.columns and not df.empty:
                return df.assign(_s=pd.to_numeric(df["Residual score"], errors="coerce")).sort_values("_s", ascending=False)
            return df

        total_risks = 0 if scored_risks_df.empty else len(scored_risks_df)
        own_pids = set(processes["Process ID"].astype(str)) if processes is not None and not processes.empty else set()
        _all_risks = collect_all_register_rows("risks")

        def all_pillar_risks(pillar_number, pillar_code):
            if _all_risks.empty:
                return _all_risks
            m = _all_risks.apply(lambda r: any(x.startswith(f"3.{pillar_number}.") for x in split_refs(r.get("Level 3 drivers", "")))
                                 or pillar_code in str(r.get("Value pillars", "")), axis=1)
            sub = _all_risks.loc[m]
            return sub.drop_duplicates(subset=["Risk ID"]) if "Risk ID" in sub.columns else sub
        if not _all_risks.empty and "Risk ID" in _all_risks.columns:
            _uniq = _all_risks.drop_duplicates(subset=["Risk ID"])
        else:
            _uniq = _all_risks
        n_ent = len(_uniq)
        n_ent_cov = int(_uniq.apply(lambda r: any(pid in own_pids for pid in split_refs(r.get("Processes", ""))), axis=1).sum()) if n_ent else 0
        pct_ent = round(100 * n_ent_cov / n_ent) if n_ent else 0
        parts = ['<div class="vh-l5-erm-pane"><div class="vh-l5-pane-title">'
                 f'Risks by pillar and Level III driver · {n_ent} risks in all registers · '
                 f'{n_ent_cov} covered by our processes ({pct_ent} %)</div>',
                 f'<div class="vh-erm-legend" style="margin:0 0 6px 0">Cards below show the {total_risks} risks in this register.</div>',
                 '<div class="vh-erm5-grid">']
        for pillar_number, pillar_name in pillar_lookup.items():
            pillar_code, pillar_description = pillar_name.split(" · ", 1)
            pillar_risks = risks_for_pillar(pillar_number, pillar_code)
            n_p = 0 if pillar_risks.empty else len(pillar_risks)
            ent_p = all_pillar_risks(pillar_number, pillar_code)
            n_all = len(ent_p)
            n_cov = int(ent_p.apply(lambda r: any(pid in own_pids for pid in split_refs(r.get("Processes", ""))), axis=1).sum()) if n_all else 0
            pct_c = round(100 * n_cov / n_all) if n_all else 0
            parts.append(f'<div class="vh-erm5-col{" vh-erm5-col-on" if n_p else ""}">'
                         f'<div class="vh-erm5-head"><b>{escape(pillar_code)}</b><br>{escape(pillar_description)}'
                         f'<div class="vh-erm-count">{n_cov} of {n_all} risks covered by our processes ({pct_c} %)</div></div>')
            shown = set()
            for reference, driver_name in [(r, d) for r, d in groups[int(pillar_number) - 1][1] if r != "divider"]:
                if not pillar_risks.empty and "Level 3 drivers" in pillar_risks.columns:
                    dr = pillar_risks.loc[pillar_risks["Level 3 drivers"].astype(str).apply(lambda v, r=reference: r in split_refs(v))]
                else:
                    dr = pd.DataFrame()
                on = not dr.empty
                parts.append(f'<div class="vh-erm5-driver{" vh-erm5-driver-on" if on else ""}">'
                             f'<b>{escape(reference)}</b> {escape(driver_name)}'
                             f'{f" · {len(dr)}" if on else ""}</div>')
                for _, rr in sort_by_score(dr).iterrows():
                    shown.add(str(rr.get("Risk ID", "")))
                    parts.append(risk_card(rr))
            if not pillar_risks.empty and "Risk ID" in pillar_risks.columns:
                orphans = pillar_risks.loc[~pillar_risks["Risk ID"].astype(str).isin(shown)]
                if not orphans.empty:
                    parts.append(f'<div class="vh-erm5-driver vh-erm5-orphan"><b>Pillar only</b> · Level III driver not set · {len(orphans)}</div>')
                    for _, rr in sort_by_score(orphans).iterrows():
                        parts.append(risk_card(rr))
            parts.append("</div>")
        parts.append("</div>")
        parts.append('<div class="vh-erm-legend">Number = residual score (likelihood × impact), coloured by heatmap zone. '
                     'Hover a risk to see its ISO process coverage. Grey drivers have no risks yet. Header: risks in the pillar across all department registers that our processes cover.</div></div>')
        st.markdown("".join(parts), unsafe_allow_html=True)



def extract_operational_questions(cause_text):
    """Pull Trident-side failure modes / numbered items from Cause for visual display."""
    import re as _re
    text_val = str(cause_text or "")
    upper = text_val.upper()
    if "TRIDENT-SIDE" in upper:
        idx = upper.find("TRIDENT-SIDE")
        chunk = text_val[idx:]
        found = _re.findall(r"\((\d+)\)\s*([^;]+)", chunk)
        if found:
            return [item.strip(" .;") for _n, item in found if item.strip()]
        after = chunk.split(":", 1)[-1] if ":" in chunk else chunk
        parts = [p.strip(" .;") for p in after.split(";") if p.strip()]
        return parts[:8]
    bits = [b.strip() for b in text_val.replace(".", ";").split(";") if b.strip()]
    return bits[:5]





TERM_PLAYBOOK_MD = """
**Trident term-playbook** — standard commercial menu for customer renewals and new fixtures
(so rate uplift is not left to ad-hoc negotiation).

**1. Rate and indexation**
- Base TC / day-rate corridor by vessel class and region (min / target / stretch).
- Indexation: annual CPI (or crewing + ops cost basket) with a floor (e.g. ≥2%) and a cap;
  mid-year reopen if crewing cost rises above an agreed threshold.
- Premium tier: +Y% for priority slots, guaranteed response window, or dedicated season cover.

**2. Duration and optionality**
- Preferred tenor: 24–36 months (short rolling terms only if paid for).
- Customer options at pre-agreed uplift; Trident redelivery / exit rights if utilization
  or payment falls outside corridor.
- Peak-season windows with higher rate or minimum committed days.

**3. Utilization and off-hire**
- Minimum committed days / season or take-or-pay band.
- Clear off-hire definition (what counts, notice, cure).
- Redeployment clause when regional demand shifts, with shared economics.

**4. Scope and service standard**
- What is in the rate (crew profile, biosecurity, reporting, welfare) vs chargeable extras.
- Incident / trust: open critical service incidents closed or disclosed before locking uplift.

**5. Negotiation rules**
- No signing below corridor without CCO / S&BD mandate.
- Pre-negotiation brief: comps, BATNA, which playbook clauses are in or out.
- Deal review gate if the customer pushes flat rates into a rising-cost year.
"""


def text_mentions_playbook(*parts):
    return any("playbook" in str(part or "").lower() for part in parts)


def highlight_library_terms_html(escaped_text):
    """After html.escape, mark the word playbook so it reads as clickable."""
    return re.sub(
        r"(?i)playbook",
        '<span class="vh-playbook-hit">playbook</span>',
        escaped_text,
    )


@st.dialog("Trident term-playbook")
def _term_playbook_dialog(risk_id=""):
    """Modal playbook — works inside expanders where st.popover is often clipped."""
    if risk_id:
        st.caption(f"Linked from {risk_id}")
    st.markdown(TERM_PLAYBOOK_MD)


def render_term_playbook_popover(risk_id):
    """Open term-playbook via button + dialog (unique key per risk)."""
    if st.button(
        "playbook",
        key=f"term_playbook_btn_{ACTIVE_REGISTER_KEY}_{risk_id}",
        help="Open Trident commercial term-playbook",
    ):
        _term_playbook_dialog(risk_id)



SBD_P05_AGENDA_MD = """
**SBD-P05 — Long-term operating agenda and rate uplift**

SBD-P05 is the Strategy & BD process that holds Trident’s **operating agenda**: where rate,
utilization, and commercial terms should go over the planning horizon (by vessel class,
region, and customer where defined).

**What “link SBD-P05 operating agenda to each material renewal” means**

It is **mostly** “compare to OA / agenda rates” — but wider than a one-line rate check.
Every material renewal should be an **execution of the agenda**, not a standalone deal.

**1. Pull agenda targets into the mandate**
- Target TC / corridor, indexation, duration, and any premium tier from the term-playbook,
  taken from the P05 agenda.
- Compare the ask to **agenda rates**, not only last year’s fixture or the customer’s opening.

**2. Show the gap before you sign**
- Proposed renewal vs agenda uplift path.
- Escalate if you are about to lock below corridor (deal review gate).

**3. Feed the outcome back into P05**
- Signed rate and terms update the renewal calendar and the P05 monitoring view
  so the agenda stays live.

**In one line**
Agenda → mandate → negotiation → signed terms → agenda tracking.

The **term-playbook** is the commercial menu of clauses. **SBD-P05** is the plan those
numbers should serve.
"""


def text_mentions_p05_agenda(*parts):
    blob = " ".join(str(part or "") for part in parts).lower()
    return ("sbd-p05" in blob) or ("operating agenda" in blob)


def highlight_library_terms_html(escaped_text):
    """After html.escape, mark playbook and SBD-P05 / operating agenda cues."""
    out = re.sub(
        r"(?i)playbook",
        '<span class="vh-playbook-hit">playbook</span>',
        escaped_text,
    )
    out = re.sub(
        r"(?i)SBD-P05",
        '<span class="vh-playbook-hit">SBD-P05</span>',
        out,
    )
    out = re.sub(
        r"(?i)operating agenda",
        '<span class="vh-playbook-hit">operating agenda</span>',
        out,
    )
    out = re.sub(
        r"(?i)redeployment",
        '<span class="vh-playbook-hit">redeployment</span>',
        out,
    )
    out = re.sub(
        r"(?i)cannibalisation",
        '<span class="vh-playbook-hit">cannibalisation</span>',
        out,
    )
    out = re.sub(
        r"(?i)cannibalization",
        '<span class="vh-playbook-hit">cannibalization</span>',
        out,
    )
    return out


@st.dialog("SBD-P05 operating agenda")
def _p05_agenda_dialog(risk_id=""):
    """Modal explaining how renewals link to the P05 operating agenda."""
    if risk_id:
        st.caption(f"Linked from {risk_id}")
    st.markdown(SBD_P05_AGENDA_MD)


def render_p05_agenda_button(risk_id):
    """Open SBD-P05 agenda explanation via button + dialog."""
    if st.button(
        "SBD-P05 agenda",
        key=f"p05_agenda_btn_{ACTIVE_REGISTER_KEY}_{risk_id}",
        help="What linking the operating agenda to a renewal means",
    ):
        _p05_agenda_dialog(risk_id)



REDEPLOYMENT_CASE_MD = """
**Regional redeployment case** — when demand is stronger in one region (e.g. Chile)
than where the vessel sits (e.g. Europe).

**Important:** tonnage is **not liquid**. A trigger does **not** mean “move the ship.”
It means **open a portfolio case** with full friction and destination impact.

**1. What the trigger opens**
- Pre-agreed gap vs plan (regional EBITDA, rate, or utilization spread).
- Named owner and decision deadline.
- Options on the table: **move / reconstruct-and-move / wait / serve demand another way**.

**2. Transaction costs and time (must be in the pack)**
- Reconstruction / conversion scope for the destination trade (yard slot, capex, off-hire).
- Transit, flag, class, and biosecurity path (Europe → Chile is a programme, not a voyage).
- Commercial exit or novation cost in the weak region.
- Delivery lag vs the Chile demand window (late arrival can destroy the case NPV).

**3. Collateral damage in the destination region**
- Stronger incoming vessel can **cannibalise** less competitive tonnage already in Chile:
  utilisation, achievable rate, and residual value on the existing fleet.
- Gross Chile uplift is not enough — use **net fleet EBITDA** after cannibalisation.

**4. Decision rule**
Approve only if **net** fleet economics (and risk) clear the hurdle after:
transaction costs + time risk + cannibalisation − avoided losses in the weak region.
Document rejected cases so the same alert does not loop forever.

**Linked processes**
- **SBD-P02** — see the regional spread (market intelligence).
- **SBD-P05** — “vs plan” baseline (operating agenda).
- **SBD-P06** — fleet portfolio choice including reconstruction and regional interaction.
"""


def text_mentions_redeployment(*parts):
    """True for real redeployment-case content — not a bare 'redeploy' in BATNA text (e.g. R101)."""
    blob = " ".join(str(part or "") for part in parts).lower()
    keys = (
        "redeployment",
        "not a liquid",
        "not liquid",
        "cannibalis",
        "reconstruct",
        "portfolio case",
        "regional ebitda gap",
        "regional spread vs plan",
    )
    return any(k in blob for k in keys)


@st.dialog("Regional redeployment case")
def _redeployment_case_dialog(risk_id=""):
    """Modal: trigger opens a costly portfolio case, not a liquid vessel move."""
    if risk_id:
        st.caption(f"Linked from {risk_id}")
    st.markdown(REDEPLOYMENT_CASE_MD)


def render_redeployment_case_button(risk_id):
    """Open regional redeployment case explanation via grey help button."""
    if st.button(
        "redeployment case",
        key=f"redeploy_case_btn_{ACTIVE_REGISTER_KEY}_{risk_id}",
        help="Redeployment is not liquid — reconstruction, costs, and Chile cannibalisation",
    ):
        _redeployment_case_dialog(risk_id)




PIL01_RISK_EXPLAINS = {
    "SBD-R001": """
**SBD-R001 — Investment in fleet capacity that does not match future demand**

**In plain words**
We commit money to **new vessels or capacity** based on forecasts of salmon production,
customer demand, and competitor tonnage. If those forecasts are wrong, we end up with
**ships that sit underused** — capital tied up, returns weak, and less room for better bets.

**What we can fail to do** (outcome drivers — not yet fully operationalized)
We treat uncertain demand as if it were certain. Capital commits go ahead without a clear
**demand evidence pack**, without stress-testing competitor orderbooks, and without a
kill/hold gate when forecasts soften. In short: **we buy capacity before demand is proven.**

**What we can do** *(draft S&BD suggestions — fill Current mitigation in Assess & decide)*
1. Require a **demand + competitor capacity brief** before each material investment gate (SBD-P02/P04).
2. Stress-test cases against **low / base / high** production and utilization scenarios.
3. Stage capital (options, slots, convertible designs) so we can **pause or reshape** if signals turn.
4. Link investment cadence to the **SBD-P05 / P06 / P07** portfolio and monitoring forums.
5. Document rejected or deferred cases so weak forecasts do not keep reopening the same bet.

**One sentence**
R001 is the risk that we **pay for tomorrow’s fleet today** while demand never shows up.
""",
    "SBD-R102": """
**SBD-R102 — Segment orderbook dilutes utilization of the existing fleet**

**In plain words**
When the industry (or we) deliver **too many similar vessels** into a segment, paid days on
**existing** ships fall — off-hire rises, utilization slips, and the organic EBITDA plan softens
even if our own ships are well run.

**What we can fail to do** (outcome drivers — not yet fully operationalized)
We watch deliveries as news, not as a **utilization threat to our current book**. Pricing and
renewal mandates stay optimistic while the segment is clearly overbuilding. Portfolio forums
do not force a response (idle, redeploy case, terms defence, or delay of our own growth).

**What we can do** *(draft S&BD suggestions — fill Current mitigation in Assess & decide)*
1. Track a **segment orderbook vs demand intensity** heat map into SBD-P02/P05/P06.
2. When deliveries spike, tighten **renewal corridors** and utilization assumptions early.
3. Open a ranked response: defend rates / accept idle / **redeployment case** / delay own growth.
4. Do not greenlight incremental capacity that **cannibalises** our own paid utilization.
5. Escalate when existing-fleet utilization drifts below the operating-agenda corridor.

**One sentence**
R102 is the risk that **everyone’s new ships steal days from our old ones** — including ours.
""",
    "SBD-R103": """
**SBD-R103 — Commercial terms erode (indexation, pass-through, duration)**

**In plain words**
Customers push to drop **CPI indexation**, **fuel pass-through**, or **multi-year tenure**.
We can still “win” the renewal on headline rate while the **economic protections** the plan
assumes quietly disappear — margin and earnings quality then slip.

**What we can fail to do** (outcome drivers — not yet fully operationalized)
Negotiators trade away indexation and tenure to close volume. There is no clear **terms floor**
or deal-review gate for material erosions. The operating agenda assumes protections that the
signed contracts no longer have.

**What we can do** *(draft S&BD suggestions — fill Current mitigation in Assess & decide)*
1. Put a **term playbook floor** (indexation, pass-through, duration) in every renewal mandate.
2. Require a signed **pre-negotiation brief** that lists which protections are non-negotiable.
3. Route below-floor term packages through a **deal review gate** before signature (SBD-P05/P02).
4. Track **terms quality**, not only headline TC, on the renewal calendar.
5. Escalate when a cluster of renewals shows systematic term giveaways vs plan.

**One sentence**
R103 is the risk that we keep the day rate and **give away the contract’s shock absorbers**.
""",
    "SBD-R105": """
**SBD-R105 — Underlying salmon supply growth undershoots consensus**

**In plain words**
Our growth story assumes farmers keep expanding sea-based production. If **regulation, biology,
or farmer efficiency** slow that growth, vessel-service demand softens — utilization and rate
momentum weaken even when we execute well commercially.

**What we can fail to do** (outcome drivers — not yet fully operationalized)
Investment and utilization plans stay locked to **consensus supply growth** after the
evidence has turned. S&BD does not refresh the demand bridge when caps, disease, or efficiency
data worsen. Capital and renewal optimism outrun the biology/regulation reality.

**What we can do** *(draft S&BD suggestions — fill Current mitigation in Assess & decide)*
1. Maintain a living **salmon supply outlook** (regs, biology, farmer efficiency) into SBD-P01/P02/P09.
2. Tie investment and utilization corridors to **updated supply scenarios**, not last year’s consensus.
3. Trigger a portfolio review when core-region supply growth undershoots the plan band.
4. Prefer flexible capacity and **redeployment options** over hard growth bets in soft-supply windows.
5. Align the narrative to boards/investors with the same supply evidence pack Commercial uses.

**One sentence**
R105 is the risk that we plan a busy fleet on **fish that never get into the water**.
""",
    "SBD-R106": """
**SBD-R106 — Crewing and operating-cost inflation outpaces rate growth**

**In plain words**
Trident's **cost to run the vessels** (crew wages, operating costs) can rise faster than
what customers pay on renewals. Even if the **day rate (TC)** looks fine on paper, the
**margin** can shrink — busy ships that earn less than the plan assumed.

**What we can fail to do**
Cost news arrives (crewing, opex), but renewal instructions to Commercial stay on the old
numbers. People negotiate **as if costs were still yesterday's**. That lag between cost
signals and renewal instructions is the core failure mode.

**What we can do (treat)**
1. Every quarter, pull a **cost-inflation outlook** from Crewing / Ops / Finance into the
   pricing corridor.
2. When costs are rising hard, renewals must include **indexation or pass-through** —
   do not lock a flat rate into a rising-cost year.
3. Before talks: a short **rate-vs-cost bridge** (what we need on rate given where costs
   are going).
4. **Reject or escalate** deals that freeze rates while costs are climbing.
5. Manage to **margin after crewing/opex**, not only the headline TC
   (**SBD-P05** operating agenda / rate path; **SBD-P12** execution monitoring).

**One sentence**
R106 is the risk that we **sell tomorrow's vessel days at yesterday's prices** while the
crew and opex bill keeps climbing.
""",
    "SBD-R111": """
**SBD-R111 — Norway share build fails despite claimed right-to-play**

**In plain words**
Norway is the large strategic market in the plan. We claim we can win **wellboat / harvest /
premium service** share — but incumbents, tender rules, thin local presence, or a “too expensive”
perception can block awards. Growth and diversification then stall.

**What we can fail to do** (outcome drivers — not yet fully operationalized)
The Norway story stays high-level while **tender criteria, relationships, and local presence**
are not worked as a campaign. Pricing and offer design ignore how Norwegian buyers actually
award. Wins are assumed; pipeline quality is not stress-tested against real barriers.

**What we can do** *(draft S&BD suggestions — fill Current mitigation in Assess & decide)*
1. Build a Norway **account / tender map** with barriers (incumbent, criteria, presence, price).
2. Sequence presence and partnership moves before expecting material awards (SBD-P03/P08).
3. Align premium pricing with a clear **right-to-play proof pack** for each tender.
4. Track Norway pipeline vs plan monthly in SBD-P02/P05 with early escalation on miss.
5. Prefer a few winnable beachheads over a thin scatter of bids that never convert.

**One sentence**
R111 is the risk that we **talk Norway share** while the awards keep going to someone already there.
""",
    "SBD-R113": """
**SBD-R113 — Segment mix bets misread demand intensity by vessel type**

**In plain words**
We overweight growth in **wellboat, premium service, harvest, or feed-carrier** relative to
what each region’s biology and adoption will actually support. Capital lands in the wrong
segment; investment EBITDA disappoints and existing ships in the overbuilt type soften.

**What we can fail to do** (outcome drivers — not yet fully operationalized)
Segment enthusiasm outruns **region-specific demand evidence**. Portfolio choices copy a global
narrative instead of local adoption and biology drivers. Competitor capacity in the fashionable
segment is underweighted until utilization proves the miss.

**What we can do** *(draft S&BD suggestions — fill Current mitigation in Assess & decide)*
1. Require a **segment × region demand brief** (biology, adoption, competitor orderbook) at P02/P03/P04 gates.
2. Cap capital to any one fashionable segment until utilization evidence clears a hurdle.
3. Rebalance the mix when leading indicators (tenders, farmer tech, biology) diverge from the bet.
4. Stress-test investment cases against **wrong-segment** scenarios before commit.
5. Review segment mix quarterly against realized awards and paid utilization.

**One sentence**
R113 is the risk that we **buy the popular vessel type** for a market that wanted something else.
""",
    "SBD-R120": """
**SBD-R120 — Farming-technology or regulatory shifts change vessel-demand mix**

**In plain words**
Faster moves to **closed / semi-closed / land-based / offshore** systems — or abrupt policy
(e.g. open-cage limits) — can change **which vessels and services** farmers need. Our current
fleet and pipeline can suddenly look mis-specified for the demand that remains.

**What we can fail to do** (outcome drivers — not yet fully operationalized)
Technology and policy signals stay in strategy papers, not in **fleet and pipeline decisions**.
We keep ordering and positioning for yesterday’s farming model. Scenario triggers for
spec/geographic shift are missing, so the growth narrative keeps promising the old mix.

**What we can do** *(draft S&BD suggestions — fill Current mitigation in Assess & decide)*
1. Run a standing **farming-tech & policy watch** into SBD-P02/P09/P10 with clear triggers.
2. Map each material shift to **vessel-spec / service / geography** implications before capital commits.
3. Prefer adaptable designs and options that survive more than one farming model.
4. Refresh the multiple-expansion narrative when the demand mix evidence changes.
5. Escalate when a region’s policy path would obsolete a planned segment bet.

**One sentence**
R120 is the risk that the **farming system changes under our fleet** while we keep building for open cages.
""",
    "SBD-R121": """
**SBD-R121 — Premium positioning or farmer trust is damaged**

**In plain words**
Trident wants to be paid as a **premium** partner (better rate / terms) because farmers trust
the service. That trust breaks when service fails, biosecurity worries rise, or we look
inflexible — and then **rate uplift talks get harder**, even when the market could support them.

**What we can fail to do**
Renewal talks go ahead as if nothing happened, while Ops/HSEQ know about recent incidents.
Commercial pushes uplift without seeing open critical issues. The growth story runs ahead of
what the fleet can reliably deliver. Farmer feedback never makes it back into how we design
the offer. In short: **we negotiate price while ignoring trust.**

**What we can do (treat)**
1. Tie a clear **premium service standard** to the rate tier (what "premium" means in the contract).
2. **Incident-to-account alert** before renewal — Ops/HSEQ warn Commercial early.
3. Put a **trust dashboard** (NPS, complaints, incidents) in the pre-negotiation brief.
4. **Do not push rate uplift** where open critical incidents still sit on the account.
5. Keep a **partnership review cadence** with top farmers
   (**SBD-P05** agenda/rate path; **P09** strategic risk; **P10** sustainability / trust topics).

**One sentence**
R121 is the risk that we ask for premium rates after we have spent the farmer's trust —
or while an open service wound is still bleeding.
""",
    "SBD-R135": """
**SBD-R135 — Existing-fleet operating performance undershoots plan**

**In plain words**
Even with decent rates, **reliability, maintenance quality, or operating discipline** can miss
the organic performance agenda. Contribution margins and off-hire-adjusted results then fall —
organic EBITDA and cash conversion weaken while the commercial story still looks fine.

**What we can fail to do** (outcome drivers — not yet fully operationalized)
S&BD tracks rates and renewals but does not force **Ops performance vs plan** into the same
operating agenda. Soft reliability or maintenance slips stay local until the quarter is lost.
There is no early bridge from vessel performance signals into portfolio and pricing forums.

**What we can do** *(draft S&BD suggestions — fill Current mitigation in Assess & decide)*
1. Put **off-hire / reliability / contribution margin** next to rates on the SBD-P05 agenda.
2. Joint S&BD–Ops–Technical review when performance drifts below the organic corridor (P06/P12).
3. Do not assume rate wins repair a **performance miss** — treat both legs of EBITDA.
4. Feed chronic underperformers into redeployment / intervention cases early.
5. Align incentives so volume wins are not celebrated while operating discipline slips.

**One sentence**
R135 is the risk that we **price like a premium fleet while we run like an average one**.
""",
    "SBD-R137": """
**SBD-R137 — Vessel EBITDA volatility remains above the multiple-expansion tolerance**

**In plain words**
Investors (and our own plan) need **steadier vessel EBITDA** to support a higher multiple.
Spot exposure, off-hire spikes, or wild segment-mix swings keep earnings **noisy** — and the
multiple-expansion story loses credibility even if average earnings look okay.

**What we can fail to do** (outcome drivers — not yet fully operationalized)
We chase upside without a **volatility budget**. Contract mix, spot share, and off-hire risk
are not managed to an explicit tolerance. Period noise is explained away until the exit /
valuation narrative cracks.

**What we can do** *(draft S&BD suggestions — fill Current mitigation in Assess & decide)*
1. Define a clear **EBITDA volatility tolerance** tied to the multiple-expansion case (P05/P09).
2. Manage contract mix (tenure, indexation, spot share) against that tolerance, not only upside.
3. Attack off-hire and segment-swing drivers jointly with Ops in SBD-P02/P12 forums.
4. Flag when rolling volatility breaches the band — force a mix or coverage response.
5. Keep the investor narrative honest: average EBITDA without a volatility path does not sell the multiple.

**One sentence**
R137 is the risk that earnings **jump around too much** for anyone to pay a premium multiple.
""",
}

PIL02_RISK_EXPLAINS = {
    "SBD-R003": """
**SBD-R003 — SFaaS expansion creates exposures outside established capabilities**

**In plain words**
We expand from vessel services into **aquaculture infrastructure / SFaaS**. That can put
capital, technology, and commercial structure into a model we have not yet proven we can
operate. If it underperforms, we take **capital loss, operational liabilities, and reputation hits**.

**What we can fail to do** (outcome drivers — not yet fully operationalized)
We treat SFaaS as a growth slogan rather than a **capability gap**. Operating model, tech,
and commercial structure are assumed to work without stage gates. Core fleet attention and
capital are diverted before the new platform has evidence it can deliver.

**What we can do** *(draft S&BD suggestions — fill Current mitigation in Assess & decide)*
1. Require a **capability & operating-model pack** (tech, commercial, Ops/HSEQ) before material SFaaS commits (SBD-P03/P04/P07/P08).
2. Stage capital behind **commercial / technical / return milestones** — no full build-out on slides alone.
3. Cap management attention and capital share until the platform clears a defined evidence hurdle.
4. Run kill/hold gates when milestones miss; do not “double down” without a refreshed case.
5. Keep core Investment EBITDA delivery ring-fenced so SFaaS misses cannot quietly consume the plan.

**One sentence**
R003 is the risk that we **buy into a new business model** before we can actually run it.
""",
    "SBD-R005": """
**SBD-R005 — Acquisitions fail to deliver expected synergies**

**In plain words**
We buy a business expecting **synergies, scale, and cleaner group governance**. If diligence,
integration planning, or **ownership of synergies** is weak, the asset sits half-integrated —
costs rise, synergies slip, and the group stays fragmented.

**What we can fail to do** (outcome drivers — not yet fully operationalized)
The deal closes on a synergy story nobody owns after day one. Integration plans are thin;
commercial and Ops workstreams are not staffed. Post-close forums track “integration progress”
without forcing **identifiable synergy capture** against the investment case.

**What we can do** *(draft S&BD suggestions — fill Current mitigation in Assess & decide)*
1. Make **synergy ownership** (name, metric, date) a close condition — not a post-close hope (SBD-P08/P12).
2. Require an integration plan with cost, culture, systems, and commercial workstreams before signing.
3. Track synergy EBITDA vs case monthly; escalate when the bridge goes red.
4. Hold back contingent consideration / follow-on capital when integration gates miss.
5. Prefer fewer, better-integrated platforms over a string of under-owned bolt-ons.

**One sentence**
R005 is the risk that we **pay for synergies on closing day** and never collect them in cash.
""",
    "SBD-R107": """
**SBD-R107 — Newbuild economics miss approved yield and IRR thresholds**

**In plain words**
Board-approved newbuilds assume a **yield / IRR**. Yard CAPEX inflation, specification creep,
delayed delivery, or weaker charter terms than underwritten can make delivered ships earn
**below the hurdle** — growth that destroys equity value and ties up scarce capital.

**What we can fail to do** (outcome drivers — not yet fully operationalized)
Underwriting stays frozen while yard prices, specs, and charter markets move. Change orders
and delays are absorbed without refreshing the **IRR bridge**. Ships are accepted into the
fleet narrative even when economics no longer clear the Board bar.

**What we can do** *(draft S&BD suggestions — fill Current mitigation in Assess & decide)*
1. Re-underwrite yield/IRR at each **spec / yard / charter** gate (SBD-P03/P04/P07) — not only at FID.
2. Cap specification creep with a change-order budget and Board re-approval above threshold.
3. Stress-test cases for CAPEX inflation and delivery slip before committing slots.
4. Kill or reshape when refreshed IRR falls below approved criteria — do not “hope into delivery”.
5. Report Investment EBITDA quality as **hurdle compliance**, not just tonnage delivered.

**One sentence**
R107 is the risk that we **launch ships that clear the yard but miss the Board’s return bar**.
""",
    "SBD-R108": """
**SBD-R108 — Yard capacity and delivery risk delays growth CAPEX realization**

**In plain words**
Growth CAPEX only creates Investment EBITDA when ships **actually deliver and start**. Limited
global yard slots, long equipment lead times, or supplier bottlenecks can slip newbuild /
reconstruction vs the commercial start-up plan — EBITDA deferred, windows missed, carrying costs up.

**What we can fail to do** (outcome drivers — not yet fully operationalized)
The plan assumes yard dates are firm. Slot scarcity and supplier lead times stay in Technical
reports, not in **portfolio timing and cash planning**. Commercial start-up and investor
narratives keep promising dates the yard cannot hit.

**What we can do** *(draft S&BD suggestions — fill Current mitigation in Assess & decide)*
1. Maintain a live **yard slot / critical-path equipment** watch into SBD-P07/P04.
2. Build schedule contingency and alternative yards/suppliers into every growth case.
3. Align commercial start-up and financing assumptions to **realistic delivery bands**, not optimistic yard quotes.
4. Escalate early when critical-path slips threaten the Investment EBITDA bridge.
5. Prefer optionality (convertible slots, staged commits) over single-yard single-path bets.

**One sentence**
R108 is the risk that **growth CAPEX sits in the yard calendar** while the EBITDA plan assumes it is already sailing.
""",
    "SBD-R109": """
**SBD-R109 — Second-hand vessel or reconstruction investments are mispriced**

**In plain words**
Buying second-hand or reconstructing can look cheaper than newbuild — until **technical diligence,
residual value, or upgrade costs** prove optimistic, or an auction forces overpay. The asset then
misses risk-adjusted hurdles and locks capital in a suboptimal ship.

**What we can fail to do** (outcome drivers — not yet fully operationalized)
Deal heat and auction clocks compress diligence. Residual-value and upgrade assumptions stay
optimistic. Portfolio forums celebrate “cheap steel” without a hard **post-integration ROIC** test.

**What we can do** *(draft S&BD suggestions — fill Current mitigation in Assess & decide)*
1. Mandatory **technical + residual + upgrade-cost** diligence pack before bid (SBD-P03/P04/P06/P07).
2. Set a walk-away price from risk-adjusted hurdles — do not chase auction heat past the cap.
3. Stress-test reconstruction cost overruns and off-hire during yard time.
4. Re-score the case after survey findings; kill if the refreshed ROIC fails the hurdle.
5. Compare every second-hand case against newbuild and organic alternatives on the same capital stack.

**One sentence**
R109 is the risk that we **buy cheap steel that turns out expensive** once diligence and upgrades land.
""",
    "SBD-R110": """
**SBD-R110 — Platform M&A overpays or fails to capture identifiable synergies**

**In plain words**
Platform deals are meant to buy **scale, Investment EBITDA, and a higher multiple**. Aggressive
bidding, weak commercial diligence, or unclear synergy ownership post-close means acquired
EBITDA arrives late, diluted, or below case — after integration costs.

**What we can fail to do** (outcome drivers — not yet fully operationalized)
Winning the auction becomes the goal. Diligence on commercial quality is thin; synergy owners
are unnamed. Post-close, the investment case is not forced against **actual EBITDA bridges**
in SBD-P08/P04/P12 forums.

**What we can do** *(draft S&BD suggestions — fill Current mitigation in Assess & decide)*
1. Separate **price discipline** from deal momentum — Board walk-away tied to identifiable synergies.
2. Diligence commercial quality and synergy sources with named owners before signing (SBD-P08).
3. Track acquired EBITDA vs case net of integration costs on a fixed cadence (P04/P12).
4. Hold governance / earn-out levers when synergies miss; do not refinance hope.
5. Prefer platforms that clear hurdles on conservative cases, not on peak-cycle synergy dreams.

**One sentence**
R110 is the risk that we **win the deal and lose the returns** — overpay in, under-deliver out.
""",
    "SBD-R112": """
**SBD-R112 — New growth platforms (e.g., SFaaS) underperform or divert focus**

**In plain words**
Adjacent growth platforms (SFaaS and similar) can miss **commercial, technical, or capital-return**
milestones while still consuming management attention and cash. Core Investment EBITDA delivery
slows; capital and reputation are at risk.

**What we can fail to do** (outcome drivers — not yet fully operationalized)
New platforms stay on the agenda without **milestone gates**. Attention and capital keep flowing
after evidence turns. The core fleet plan absorbs the distraction cost invisibly until both
stories are late.

**What we can do** *(draft S&BD suggestions — fill Current mitigation in Assess & decide)*
1. Put every new platform on a **milestone dashboard** (commercial, tech, return) with kill/hold rules (SBD-P03/P04/P07/P08).
2. Cap management hours and capital share until milestones clear — protect core Investment EBITDA.
3. Require an explicit “continue / reshape / exit” decision when a milestone misses.
4. Do not open a second adjacent platform while the first is still unproven.
5. Report distraction cost (leadership time, deferred core decisions) alongside platform P&L.

**One sentence**
R112 is the risk that a **shiny adjacent platform** burns the calendar and the capital the core fleet needed.
""",
    "SBD-R129": """
**SBD-R129 — ROIC on growth investments stays below cost of capital**

**In plain words**
Growth CAPEX only creates equity value when **portfolio ROIC clears the cost of capital** after
stabilization. Optimistic underwriting, cost overrun, or weaker utilization and rates can leave
balance-sheet capacity consumed without commensurate value creation.

**What we can fail to do** (outcome drivers — not yet fully operationalized)
Projects are approved on underwriting ROIC and never **re-measured** against realized results.
Overruns and soft utilization are explained away. Capital keeps flowing to the same pattern
while hurdle compliance is not forced in SBD-P04/P07/P13.

**What we can do** *(draft S&BD suggestions — fill Current mitigation in Assess & decide)*
1. Track **post-stabilization ROIC vs WACC/hurdle** for every material growth commitment (SBD-P04/P07/P13).
2. Re-underwrite when CAPEX, utilization, or rates diverge from case — before more capital follows.
3. Rank growth uses against debt reduction and distributions under the same capital constraint.
4. Stop or reshape serial below-hurdle patterns; do not average them away in the portfolio story.
5. Report Investment EBITDA growth **only alongside** ROIC-vs-hurdle compliance.

**One sentence**
R129 is the risk that we **grow the balance sheet faster than we grow economic returns**.
""",
}

PIL03_RISK_EXPLAINS = {
    "SBD-R002": """
**SBD-R002 — Strategic initiatives fail to translate into accountable execution**

**In plain words**
Multiple expansion needs **governance and delivery** — contract quality, fleet modernization,
integration, and exit readiness only move the multiple if initiatives are **owned, staffed, and
milestoned**. When ownership, capacity, or cross-functional alignment is thin, material programs
slip or stall half-done and the value-creation story loses credibility.

**What we can fail to do** (outcome drivers — not yet fully operationalized)
We announce strategic programs without **named owners, capacity, and milestones**. Forums track
activity, not accountable outcomes. Cross-unit initiatives (coverage, modernization, integration)
sit between functions with no single throat to choke — so growth, integration, and multiple
support targets quietly miss.

**What we can do** *(draft S&BD suggestions — fill Current mitigation in Assess & decide)*
1. Require **owner / capacity / milestone / metric** before any material initiative is marked Active (SBD-P01/P12).
2. Put a living **initiative dashboard** (RAG vs milestone) into the operating and strategic-risk forums.
3. Kill or reshape when capacity is missing — do not keep “priority” labels on unstaffed work.
4. Force cross-functional RACI for initiatives that span Commercial, Ops, Technical, and Finance.
5. Tie executive reviews to **outcome gates** (coverage, volatility, fleet quality, exit readiness), not slide progress.

**One sentence**
R002 is the risk that we **write a multiple-expansion plan** and then fail to execute the work that would earn it.
""",
    "SBD-R004": """
**SBD-R004 — Strategic decisions rely on incomplete or unreliable information**

**In plain words**
Contract coverage, earnings visibility, and fleet-quality bets only support a higher multiple if
the **data behind them is trustworthy**. When group data and external intelligence are fragmented
or inconsistent, management decides on untested assumptions — capital misallocates and corrective
moves come late.

**What we can fail to do** (outcome drivers — not yet fully operationalized)
Coverage, volatility, and residual-value views live in **disconnected spreadsheets**. External
farmer / policy / orderbook signals are not reconciled with internal books. Investment and
renewal gates proceed without a single tested evidence pack — so wrong bets survive too long.

**What we can do** *(draft S&BD suggestions — fill Current mitigation in Assess & decide)*
1. Define a **single source of truth** for contracted EBITDA, tenure, volatility, and fleet quality (SBD-P01/P02/P04).
2. Require an **assumption / evidence brief** at every material strategy and capital gate.
3. Reconcile external intelligence (supply, policy, competitor capacity) with internal utilization and coverage data monthly.
4. Flag decisions taken on incomplete packs — force a re-open when data quality is red.
5. Keep the multiple narrative aligned to the same KPI pack Finance and Commercial use in diligence.

**One sentence**
R004 is the risk that we **steer earnings quality on foggy numbers** and discover the miss too late to fix the multiple.
""",
    "SBD-R114": """
**SBD-R114 — Earnings visibility weakened by lower long-term TC coverage**

**In plain words**
The multiple-expansion case assumes a healthy share of **contracted EBITDA** and decent
**remaining tenure**. When expiries cluster, renewals shorten, or more vessels slide to spot /
short tenors, visibility falls — and buyers discount the exit multiple for unpredictability.

**What we can fail to do** (outcome drivers — not yet fully operationalized)
We celebrate headline rates while **coverage and duration** quietly erode. The renewal calendar
has no hard tenure / contracted-EBITDA corridor. Spot share creeps up without a forced response
in SBD-P05/P02 forums tied to the multiple plan.

**What we can do** *(draft S&BD suggestions — fill Current mitigation in Assess & decide)*
1. Set explicit targets for **contracted EBITDA share** and **average remaining tenure** vs the multiple case.
2. Pre-plan clustered expiries with a ranked response (extend / re-tender / accept short / idle).
3. Put coverage and tenor next to rate on every renewal mandate (SBD-P05/P02).
4. Escalate when rolling coverage drifts below the earnings-quality band — force mix action.
5. Do not sell a visibility story to boards/investors that the backlog no longer supports.

**One sentence**
R114 is the risk that **short tenors and spot creep** hollow out the earnings visibility the multiple needs.
""",
    "SBD-R115": """
**SBD-R115 — Counterparty or top-customer concentration crystallizes**

**In plain words**
Heavy exposure to a **small set of large farmers or regional counterparties** can look efficient —
until loss, renegotiation, or distress at one name removes a disproportionate share of
contracted EBITDA. Visibility, cash collection, and exit-multiple quality then deteriorate fast.

**What we can fail to do** (outcome drivers — not yet fully operationalized)
Concentration is tolerated as “relationship strength” without **limits or offsets**. Diversification
targets stay soft. Diligence and renewal forums do not force a concentration bridge when one
account dominates contracted earnings.

**What we can do** *(draft S&BD suggestions — fill Current mitigation in Assess & decide)*
1. Track **top-N counterparty share of contracted EBITDA** against a Board-visible concentration band.
2. Prefer tenure and terms that improve quality **without** deepening single-name dependency beyond limits.
3. Build diversification offsets (new accounts, regions, segments) into the commercial pipeline (SBD-P02/P05).
4. Stress-test the multiple case for loss / distress of the largest 1–2 customers.
5. Escalate early when one account’s renewal or credit signal threatens the visibility narrative.

**One sentence**
R115 is the risk that **one farmer’s problem becomes Trident’s multiple problem**.
""",
    "SBD-R116": """
**SBD-R116 — Fleet obsolescence erodes residual value and commercial relevance**

**In plain words**
Multiple support from **fleet quality** assumes vessels stay commercially relevant and residual
values hold. When technology, size, and fish-handling standards advance faster than modernization
and divestment, older ships become unattractive — residuals fall and the quality premium fades.

**What we can fail to do** (outcome drivers — not yet fully operationalized)
Obsolescence signals (spec, gentle-handling, size) stay in Technical reports, not in a
**forced modernization / divest cadence**. Hold cases stay optimistic while farmer standards
move. Disposal and replacement plans lag until residuals and commercial relevance are already gone.

**What we can do** *(draft S&BD suggestions — fill Current mitigation in Assess & decide)*
1. Maintain a living **fleet quality / residual-value scorecard** into SBD-P06/P09 and the portfolio forum.
2. Link modernization and divest triggers to farmer-spec and residual thresholds — not sentiment.
3. Prefer disciplined replacement over holding obsolete tonnage for optionality that never pays.
4. Stress residual assumptions in the multiple case when tech standards jump.
5. Align CapEx and disposal timing so quality support for the multiple does not silently decay.

**One sentence**
R116 is the risk that the **fleet ages out of the market** while the valuation still prices a modern peer set.
""",
    "SBD-R117": """
**SBD-R117 — Fleet modernization and disciplined divestments slip**

**In plain words**
Even with a modernization plan, **sale processes slip**, attachment to underperforming assets
lingers, or replacement capital is insufficient. Aging vessels stay longer than the quality and
residual-value plan allows — avoidable opex, downtime, and valuation discounts pile up vs peers.

**What we can fail to do** (outcome drivers — not yet fully operationalized)
Divest lists exist but **processes stall**. Capital for replacements is deferred. Forums debate
hold cases without a hard exit gate. The multiple narrative keeps promising a modernized fleet
the portfolio no longer matches.

**What we can do** *(draft S&BD suggestions — fill Current mitigation in Assess & decide)*
1. Put named **divest / replace milestones** with owners on every non-core or aging vessel (SBD-P06/P12).
2. Cap hold-case optimism with a time-boxed re-decision — sell, replace, or reshape.
3. Ring-fence replacement capital so modernization is not crowded out by growth bets alone.
4. Track avoidable opex and downtime on aging ships as a cost of delay, not background noise.
5. Keep the exit-multiple story honest: no quality premium without a delivered modernization path.

**One sentence**
R117 is the risk that we **talk modernization** while the old ships quietly stay and discount the multiple.
""",
    "SBD-R118": """
**SBD-R118 — Governance, reporting, or scalability gaps impair exit readiness**

**In plain words**
Buyers and lenders pay for **auditability, KPI reliability, and management bandwidth**. If
systems, processes, and controls across the combined platform stay incompletely integrated,
diligence questions the numbers and the team — achievable EV/EBITDA and process certainty fall.

**What we can fail to do** (outcome drivers — not yet fully operationalized)
Integration of reporting and controls is treated as IT backlog, not as **exit readiness**. KPI
definitions differ by legacy unit. Management bandwidth is over-committed. The multiple story
assumes institutional quality that diligence would not yet accept.

**What we can do** *(draft S&BD suggestions — fill Current mitigation in Assess & decide)*
1. Run an **exit-readiness / diligence pack** (systems, controls, KPI dictionary, ownership) on a fixed cadence (SBD-P08/P12).
2. Close material reporting and control gaps before marketing a higher-multiple narrative.
3. Standardize contracted-EBITDA, coverage, and volatility KPIs across the combined platform.
4. Protect management bandwidth for diligence-critical workstreams — do not overload key people.
5. Escalate when auditability or KPI reliability would fail a buyer/lender walk-through today.

**One sentence**
R118 is the risk that **exit diligence fails the governance test** and the multiple we planned never clears.
""",
    "SBD-R119": """
**SBD-R119 — Key-person dependency limits scalable execution**

**In plain words**
Critical **commercial, technical, or yard relationships** concentrated in a few individuals make
growth and integration fragile. Loss or overload of those people slows tenders, newbuilds,
integration, or farmer relationships — and perceived institutional quality that supports the
multiple weakens.

**What we can fail to do** (outcome drivers — not yet fully operationalized)
We celebrate rainmakers without **backup coverage, documentation, or succession**. Relationship
maps live in heads, not in the operating system. Scalability and exit readiness assume a bench
that does not exist.

**What we can do** *(draft S&BD suggestions — fill Current mitigation in Assess & decide)*
1. Map **key-person / key-relationship concentration** and force dual coverage on material accounts and yard paths (SBD-P12).
2. Document commercial and technical playbooks so execution survives absence or departure.
3. Cap overload — redistribute tenders and integration load before single points of failure burn out.
4. Include key-person risk in exit-readiness and governance reviews (with R118).
5. Hire or develop bench strength where concentration exceeds the scalability tolerance.

**One sentence**
R119 is the risk that the **multiple depends on a few people** the institution has not yet replaced.
""",
    "SBD-R123": """
**SBD-R123 — Maintenance-capex overruns or deferred backlog catch-up**

**In plain words**
Protecting **uptime and residual value** (and therefore fleet-quality support for the multiple)
needs realistic dry-dock, upgrade, and compliance spend. Underestimated maintenance CapEx — or
a deferred backlog that forces lumpy catch-up — hits cash conversion and near-term liquidity
while the quality story still assumes a well-kept fleet.

**What we can fail to do** (outcome drivers — not yet fully operationalized)
Maintenance plans stay optimistic; backlog is deferred to “protect” short-term cash. Residual
and uptime assumptions in the multiple case ignore the **catch-up bill**. Forums do not force a
honest CapEx corridor when Technical signals turn red.

**What we can do** *(draft S&BD suggestions — fill Current mitigation in Assess & decide)*
1. Rebase maintenance CapEx and backlog visibility jointly with Ops/Technical/Finance (SBD-P06/P13).
2. Do not defer dry-dock / compliance spend that protects residual value and contracted uptime.
3. Stress the cash and liquidity bridge for lumpy catch-up scenarios before they crystallize.
4. Link fleet-quality / residual KPIs to funded maintenance — not to unfunded aspirations.
5. Escalate when backlog catch-up would breach the cash-conversion corridor assumed in the plan.

**One sentence**
R123 is the risk that we **underfund the fleet that is supposed to earn the quality multiple**.
""",
    "SBD-R132": """
**SBD-R132 — Disposal of underperforming assets is delayed or value-destructive**

**In plain words**
Identified **non-core or underperforming vessels** should leave the portfolio in a disciplined way.
Thin second-hand markets, optimistic hold cases, or process delays keep capital trapped — ROIC
dilutes and the modernization narrative that supports the multiple weakens (or forced sales
destroy value).

**What we can fail to do** (outcome drivers — not yet fully operationalized)
Disposal lists stall. Hold cases re-open without new evidence. Process ownership is unclear.
We either wait too long (capital trapped) or dump into a thin market without a prepared path —
both hurt portfolio quality optics.

**What we can do** *(draft S&BD suggestions — fill Current mitigation in Assess & decide)*
1. Assign **named disposal owners and deadlines** for every vessel on the non-core list (SBD-P06/P12).
2. Time-box hold cases; require fresh evidence to extend — default is execute the disposal path.
3. Prepare sale processes early (surveys, marketing, buyer map) so thin markets do not force fire-sale timing alone.
4. Track trapped capital and ROIC dilution as an explicit cost of delay in portfolio forums.
5. Align disposal outcomes with the modernization story used in the multiple-expansion case.

**One sentence**
R132 is the risk that **underperforming steel stays on the books** and quietly taxes both ROIC and the multiple.
""",
    "SBD-R136": """
**SBD-R136 — Long-term contract coverage falls below the earnings-quality target**

**In plain words**
Multiple expansion needs a target share of EBITDA on **long-term contracts**. When renewals
shorten tenure or the contracted backlog is not rebuilt at target duration, long-term coverage
slips — earnings visibility and valuation support weaken even if near-term utilization looks fine.

**What we can fail to do** (outcome drivers — not yet fully operationalized)
We track awards and rates but not **long-term coverage vs the earnings-quality target**. Short
renewals are accepted as temporary. The backlog rebuild plan has no forced cadence when coverage
drifts below the band assumed in the exit multiple.

**What we can do** *(draft S&BD suggestions — fill Current mitigation in Assess & decide)*
1. Define a clear **long-term coverage target** (share of EBITDA / tenure band) tied to the multiple case.
2. Put coverage vs target on the SBD-P05/P02 renewal and portfolio agenda every cycle.
3. Prefer tenure rebuild actions (extensions, multi-year awards) when coverage is below band — not only rate defense.
4. Trigger a commercial response plan when rolling coverage breaches the floor.
5. Keep investor and Board narratives matched to actual long-term backlog, not to the aspirational target alone.

**One sentence**
R136 is the risk that **long-term coverage slips under the quality bar** the multiple-expansion plan requires.
""",
}


PIL04_RISK_EXPLAINS = {
    "SBD-R122": """
**SBD-R122 — Working-capital and DSO discipline slips as the group scales**

**In plain words**
Cash conversion needs **EBITDA to become operating cash** — not just sit in receivables and
inventory-like working capital. As the group grows and integrates entities, fragmented billing,
multi-entity processes, or customer payment-term pressure can push **DSO and net working capital**
above the cash-conversion plan even when reported earnings look fine.

**What we can fail to do** (outcome drivers — not yet fully operationalized)
We scale Commercial and Ops without equally rigorous **billing, collections, and WC ownership**.
Payment-term giveaways win awards but silently lengthen cash conversion. Multi-entity processes
stay fragmented after integration — so free cash flow lags EBITDA and leverage optics worsen.

**What we can do** *(draft S&BD suggestions — fill Current mitigation in Assess & decide)*
1. Set explicit **DSO / NWC vs cash-conversion plan** corridors with named Finance+Commercial owners (SBD-P05/P13).
2. Standardize billing and collections across entities before celebrating integration complete.
3. Cap payment-term concessions in tenders — force a cash-conversion trade-off, not a free giveaway.
4. Put WC and DSO variance next to EBITDA in operating and Board cash bridges.
5. Escalate when rolling DSO/NWC drifts above the band assumed in the FCF / NIBD plan.

**One sentence**
R122 is the risk that we **grow the P&L while working capital quietly eats the cash**.
""",
    "SBD-R124": """
**SBD-R124 — Cash interest burden rises with rates or leverage**

**In plain words**
EBITDA-to-cash conversion after financing depends on **cash interest** staying inside the plan.
Higher market rates, refinancing margins, or more NIBD from the growth program can make cash
interest consume a larger share of operating cash — compressing free cash flow and covenant
headroom even if operating EBITDA holds.

**What we can fail to do** (outcome drivers — not yet fully operationalized)
Growth and CapEx cases price EBITDA but underweight **cash interest sensitivity**. Refinancing
and rate paths are not stress-tested into the cash-conversion corridor. Forums celebrate
investment EBITDA while cash interest silently crowds out distributions and optionality.

**What we can do** *(draft S&BD suggestions — fill Current mitigation in Assess & decide)*
1. Embed **cash-interest / FCF bridges** (rate and leverage scenarios) in every material growth and refinancing gate (SBD-P07/P13).
2. Set a Board-visible cash-interest share-of-OCF band tied to the cash-conversion plan.
3. Prefer funding mixes and hedge / tenor choices that protect the conversion corridor, not only headline IRR.
4. Re-cut the cash plan when rates or NIBD path breach the interest burden assumption.
5. Escalate early when cash interest would breach covenant or distribution headroom under base+stress cases.

**One sentence**
R124 is the risk that **cash interest eats the conversion** the growth story still assumes is free.
""",
    "SBD-R125": """
**SBD-R125 — Cash-tax leakage exceeds plan across jurisdictions**

**In plain words**
Cash conversion embeds an assumption about **cash taxes paid**, not just book tax. Cross-border
structure, limited loss utilization, or changing rules in core farming regions can push cash
taxes above the conversion plan — so free cash flow and equity value per NOK of EBITDA decline
even when operating results look on track.

**What we can fail to do** (outcome drivers — not yet fully operationalized)
Plans use optimistic **effective cash-tax** rates without jurisdiction bridges. Structure and
loss-utilization opportunities sit outside the operating cash forum. Rule changes land late into
the FCF bridge — corrective structuring lags the leakage.

**What we can do** *(draft S&BD suggestions — fill Current mitigation in Assess & decide)*
1. Maintain a living **cash-tax by jurisdiction** bridge vs the cash-conversion plan (Finance ownership with S&BD visibility).
2. Stress conversion for limited loss utilization and known rule-change scenarios in core regions.
3. Align entity and financing structure choices with cash-tax outcomes before locking growth footprints.
4. Put cash-tax variance next to WC and interest in the monthly FCF pack — not only in annual tax notes.
5. Escalate when cash taxes would breach the conversion band assumed for NIBD and distributions.

**One sentence**
R125 is the risk that **cash taxes leak** what the EBITDA-to-cash plan thought was convertible.
""",
    "SBD-R126": """
**SBD-R126 — Growth CAPEX timing mismatches cash generation**

**In plain words**
Cash conversion during the investment cycle needs **growth CapEx timing** to match when
associated TC cash flows start. Front-loaded newbuild progress payments before contracted cash
arrives can leave operating cash after maintenance short — forcing incremental debt, leverage
spikes, and poor cash-conversion optics even if long-run IRR still looks fine.

**What we can fail to do** (outcome drivers — not yet fully operationalized)
Newbuild and growth cases show returns but not a **month-by-month cash bridge** from progress
payments to first hire. Maintenance and growth CapEx compete without a forced sequencing rule.
The cash-conversion narrative ignores the investment-cycle trough until liquidity is already tight.

**What we can do** *(draft S&BD suggestions — fill Current mitigation in Assess & decide)*
1. Require a **progress-payment vs TC-cash timing bridge** at every material growth CapEx gate (SBD-P04/P07).
2. Sequence commitments so operating cash after maintenance can fund the curve — or pre-arrange funding explicitly.
3. Stress leverage and conversion optics for delay / early-payment / late-hire scenarios before signing.
4. Separate maintenance-capex protection (R123) from growth CapEx so short-term cash pressure does not defer upkeep.
5. Escalate when the investment curve would breach the cash-conversion / NIBD corridor in the plan.

**One sentence**
R126 is the risk that we **pay for growth steel before the cash shows up** and conversion optics break mid-cycle.
""",
    "SBD-R127": """
**SBD-R127 — Cash-conversion forecasting and KPI ownership remain weak**

**In plain words**
You cannot manage **EBITDA-to-cash** if reporting stays EBITDA-centric without equally rigorous
free-cash bridges, owners, and variance routines. When forecasting and KPI ownership for
conversion (WC, DSO, maintenance CapEx, interest, tax) stay weak, management detects cash
shortfalls late — corrective action lags and exit diligence questions cash quality vs earnings.

**What we can fail to do** (outcome drivers — not yet fully operationalized)
Dashboards stop at EBITDA. FCF bridges are ad hoc. No single owner for **conversion KPI pack**
(DSO, NWC, maint. CapEx, cash interest, cash tax). Variances are explained after the miss, not
governed as leading indicators — so the cash-conversion plan is aspiration, not an operating system.

**What we can do** *(draft S&BD suggestions — fill Current mitigation in Assess & decide)*
1. Institutionalize a monthly **EBITDA → FCF bridge** with named owners per conversion line (SBD-P01/P13).
2. Put DSO, NWC, maint. CapEx, cash interest, and cash tax on the same operating agenda as EBITDA.
3. Define variance thresholds that force action before the quarter-end cash miss crystallizes.
4. Align Board and exit diligence packs to the same cash-quality KPIs Finance uses internally.
5. Kill “earnings quality” narratives that cannot be reconciled to the live conversion bridge.

**One sentence**
R127 is the risk that we **manage the P&L in high definition and the cash bridge in fog**.
""",
    "SBD-R138": """
**SBD-R138 — DSO and collection performance slip versus cash-conversion targets**

**In plain words**
Cash conversion depends on **getting paid on time** — billing quality, dispute handling, and
customer payment behaviour. As the group scales, DSO and collection outcomes can miss the
cash-conversion plan even when utilization and rates look healthy — working capital absorbs cash
and NIBD headroom tightens.

**What we can fail to do** (outcome drivers — not yet fully operationalized)
Collections stay a back-office chase, not a **commercial+finance KPI**. Disputes linger without
aging discipline. Billing errors multiply with multi-entity growth. The cash-conversion target
assumes DSO that operations no longer deliver.

**What we can do** *(draft S&BD suggestions — fill Current mitigation in Assess & decide)*
1. Set hard **DSO and collection-rate targets** vs the cash-conversion plan with joint Commercial/Finance ownership (SBD-P05).
2. Fix billing quality at source — reduce dispute root causes, not only chase overdue balances.
3. Run aging and dispute cadences with escalation at defined days-past-due thresholds.
4. Tie renewal and credit decisions to payment behaviour, not only rate and tenure.
5. Escalate when rolling DSO breaches the conversion band — force a collections response plan.

**One sentence**
R138 is the risk that **slow collections turn contracted EBITDA into trapped cash**.
""",
}

PIL05_RISK_EXPLAINS = {
    "SBD-R128": """
**SBD-R128 — Capital deployed to lower risk-adjusted uses than available alternatives**

**In plain words**
Capital allocation is a **ranking problem under scarce cash and debt capacity**. Organic growth,
M&A, debt reduction, and distributions compete. When ranking is incomplete or soft, cash goes to
projects or hold decisions with **inferior risk-adjusted equity-value creation** — ROIC and value
per NOK deployed miss the mandate even if individual cases still look “fine” in isolation.

**What we can fail to do** (outcome drivers — not yet fully operationalized)
We approve uses one-by-one without a binding **cross-alternative stack** (growth vs delever vs
distributions). Hold cases for weak assets are not forced against disposal or redeployment.
Capital constraints stay narrative — so inferior uses win by inertia, not by Board rule.

**What we can do** *(draft S&BD suggestions — fill Current mitigation in Assess & decide)*
1. Run a living **capital stack** ranking organic, M&A, debt reduction, and distributions under the same constraint (SBD-P03/P04/P07/P13).
2. Require risk-adjusted equity-value per NOK for every material use — reject orphan approvals outside the stack.
3. Force hold-vs-dispose / hold-vs-delever trade-offs into the same forum as growth gates.
4. Re-cut the stack when cash conversion, rates, or leverage bands shift — do not freeze last quarter’s ranking.
5. Escalate when capital is committed to a use that ranks below a clearly available alternative on the Board stack.

**One sentence**
R128 is the risk that we **spend scarce capital on the second-best use** because we never forced a real ranking.
""",
    "SBD-R130": """
**SBD-R130 — NIBD and leverage exceed target band during growth**

**In plain words**
Growth only preserves optionality if **NIBD and leverage stay inside the Board band**. Simultaneous
newbuild commitments, softer cash conversion, or delayed EBITDA from deliveries can push
NIBD/EBITDA and related metrics through internal targets toward covenants — constraining
financing flexibility, distributions, and exit readiness.

**What we can fail to do** (outcome drivers — not yet fully operationalized)
Investment cases clear IRR gates without a **rolling NIBD / leverage bridge** through the delivery
trough. Soft conversion and late EBITDA ramp are treated as surprises. Forums celebrate capacity
growth while leverage optics breach the band assumed in the capital plan.

**What we can do** *(draft S&BD suggestions — fill Current mitigation in Assess & decide)*
1. Embed a **NIBD and leverage corridor** (base + stress) in every material growth commitment gate (SBD-P07/P13).
2. Sequence newbuilds and funding so peak leverage stays inside the Board band — or pre-arrange equity/debt explicitly.
3. Re-forecast leverage monthly when cash conversion or delivery EBITDA diverges from plan.
4. Tie distribution and further CapEx capacity to remaining headroom inside the band — not to headline EBITDA alone.
5. Escalate early when the path would breach internal targets or approach covenants under base+stress cases.

**One sentence**
R130 is the risk that **growth steel and soft cash push leverage through the band** the Board thought it owned.
""",
    "SBD-R131": """
**SBD-R131 — Liquidity or covenant headroom becomes insufficient**

**In plain words**
Liquidity and **covenant headroom** are the last lines before forced action. Undrawn facility
limits, progress-payment peaks, or EBITDA shortfalls versus covenant definitions can drop
available liquidity or headroom below Board tolerance — inviting emergency refinancing, forced
sales, or a hard stop on investment capacity.

**What we can fail to do** (outcome drivers — not yet fully operationalized)
Plans track facilities at close but not **peak draw vs undrawn** through the CapEx calendar.
Covenant definitions (add-backs, EBITDA timing) sit outside operating forums. Headroom is assumed
until a payment peak or EBITDA miss crystallizes the squeeze.

**What we can do** *(draft S&BD suggestions — fill Current mitigation in Assess & decide)*
1. Maintain a forward **liquidity and covenant-headroom bridge** through progress-payment and EBITDA troughs (SBD-P07/P09/P13).
2. Stress undrawn limits and covenant EBITDA definitions — not only book leverage at year-end.
3. Pre-arrange amendments, RCF headroom, or funding before peaks that would pierce Board tolerance.
4. Link CapEx commitment gates to remaining liquidity/covenant buffer, not only to IRR.
5. Escalate immediately when forecast headroom falls below the Board floor under base or defined stress.

**One sentence**
R131 is the risk that we **discover we are out of liquidity or covenant room** only when the next payment is due.
""",
    "SBD-R133": """
**SBD-R133 — Refinancing or financing flexibility is constrained at need**

**In plain words**
Strategy assumes **financing flexibility when we need it** — new facilities, amendments, or
bond/bank capacity on acceptable terms. Credit-market tightness, vessel-collateral perceptions, or
ownership/exit-timing uncertainty can make that capacity unavailable or punitive exactly when
growth or refinancing windows open — pausing investments and hurting exit readiness.

**What we can fail to do** (outcome drivers — not yet fully operationalized)
We underwrite growth on today’s markets and treat refinancing as a future admin task. Collateral
and ownership narratives are not stress-tested into **access and pricing** scenarios. Optionality
is assumed until the market (or lenders) say no.

**What we can do** *(draft S&BD suggestions — fill Current mitigation in Assess & decide)*
1. Keep a living **financing-flexibility scorecard** (tenor, undrawn, amendment room, collateral headroom) on the Board agenda (SBD-P01/P07/P13).
2. Pre-negotiate capacity and amendment paths before large CapEx or refinance cliffs — not after.
3. Stress access and pricing for credit-tight and exit-timing scenarios in every material funding plan.
4. Align vessel quality, documentation, and ownership clarity with what lenders and buyers will underwrite.
5. Escalate when forecast need would rely on markets or terms we cannot currently evidence.

**One sentence**
R133 is the risk that **the balance sheet is inflexible exactly when strategy needs it to flex**.
""",
    "SBD-R134": """
**SBD-R134 — Debt reduction versus growth trade-offs lack a binding decision rule**

**In plain words**
Under stress, the Board must choose **delever versus fund accretive projects** with clear
thresholds — not vibes. Without a binding decision rule, capital choices oscillate between
over-investment and excessive conservatism: leverage risk rises in good moods, and value-accretive
opportunities are systematically forgone when fear dominates.

**What we can fail to do** (outcome drivers — not yet fully operationalized)
Thresholds for when to **stop growth CapEx and delever** (or the reverse) stay undefined.
Stress scenarios are discussed qualitatively. Ad hoc calls replace a published rule — so
execution teams cannot plan, and equity value is left on the table or put at risk by inconsistency.

**What we can do** *(draft S&BD suggestions — fill Current mitigation in Assess & decide)*
1. Codify Board **delever-vs-invest thresholds** (leverage band, covenant buffer, ROIC hurdle) under base and stress (SBD-P01/P07/P13).
2. Publish the rule into capital gates so S&BD and Finance apply the same switch — not quarterly mood.
3. Pre-authorize which growth uses survive a stress trigger and which pause automatically.
4. Review the rule when WACC, credit markets, or cash conversion regimes shift — amend explicitly, do not freestyle.
5. Escalate when proposed capital actions would violate the published trade-off rule without a Board exception.

**One sentence**
R134 is the risk that **without a binding delever-vs-grow rule, we lurch between over-betting and under-investing**.
""",
}

RISK_LIBRARY_EXPLAINS = {**PIL01_RISK_EXPLAINS, **PIL02_RISK_EXPLAINS, **PIL03_RISK_EXPLAINS, **PIL04_RISK_EXPLAINS, **PIL05_RISK_EXPLAINS}

_PIL01_EXPLAIN_DIALOG_TITLES = {
    "SBD-R001": "SBD-R001 — fleet capacity vs future demand",
    "SBD-R102": "SBD-R102 — segment orderbook vs utilization",
    "SBD-R103": "SBD-R103 — commercial terms erosion",
    "SBD-R105": "SBD-R105 — salmon supply growth undershoot",
    "SBD-R106": "SBD-R106 — cost inflation vs rate growth",
    "SBD-R111": "SBD-R111 — Norway share build",
    "SBD-R113": "SBD-R113 — segment mix vs demand",
    "SBD-R120": "SBD-R120 — farming tech / policy demand shift",
    "SBD-R121": "SBD-R121 — premium trust and farmer relationships",
    "SBD-R135": "SBD-R135 — existing-fleet operating performance",
    "SBD-R137": "SBD-R137 — vessel EBITDA volatility",
}

_PIL02_EXPLAIN_DIALOG_TITLES = {
    "SBD-R003": "SBD-R003 — SFaaS expansion capability gap",
    "SBD-R005": "SBD-R005 — acquisition synergies miss",
    "SBD-R107": "SBD-R107 — newbuild yield / IRR miss",
    "SBD-R108": "SBD-R108 — yard delivery delays growth CAPEX",
    "SBD-R109": "SBD-R109 — second-hand / reconstruction misprice",
    "SBD-R110": "SBD-R110 — platform M&A overpay / synergies",
    "SBD-R112": "SBD-R112 — new growth platforms divert focus",
    "SBD-R129": "SBD-R129 — growth ROIC below cost of capital",
}

_PIL03_EXPLAIN_DIALOG_TITLES = {
    "SBD-R002": "SBD-R002 — strategic initiatives lack accountable execution",
    "SBD-R004": "SBD-R004 — decisions on incomplete / unreliable information",
    "SBD-R114": "SBD-R114 — long-term TC coverage / earnings visibility",
    "SBD-R115": "SBD-R115 — counterparty / top-customer concentration",
    "SBD-R116": "SBD-R116 — fleet obsolescence / residual value",
    "SBD-R117": "SBD-R117 — modernization and divestment slip",
    "SBD-R118": "SBD-R118 — governance / exit readiness gaps",
    "SBD-R119": "SBD-R119 — key-person dependency",
    "SBD-R123": "SBD-R123 — maintenance-capex / backlog catch-up",
    "SBD-R132": "SBD-R132 — disposal of underperforming assets",
    "SBD-R136": "SBD-R136 — long-term contract coverage vs quality target",
}

_PIL04_EXPLAIN_DIALOG_TITLES = {
    "SBD-R122": "SBD-R122 — working-capital / DSO discipline at scale",
    "SBD-R124": "SBD-R124 — cash interest burden vs conversion",
    "SBD-R125": "SBD-R125 — cash-tax leakage across jurisdictions",
    "SBD-R126": "SBD-R126 — growth CapEx timing vs cash generation",
    "SBD-R127": "SBD-R127 — cash-conversion forecasting / KPI ownership",
    "SBD-R138": "SBD-R138 — DSO and collection vs conversion targets",
}

_PIL05_EXPLAIN_DIALOG_TITLES = {
    "SBD-R128": "SBD-R128 — capital stack / inferior risk-adjusted uses",
    "SBD-R130": "SBD-R130 — NIBD and leverage vs target band",
    "SBD-R131": "SBD-R131 — liquidity / covenant headroom",
    "SBD-R133": "SBD-R133 — refinancing / financing flexibility at need",
    "SBD-R134": "SBD-R134 — debt reduction vs growth decision rule",
}

_RISK_EXPLAIN_DIALOG_TITLES = {**_PIL01_EXPLAIN_DIALOG_TITLES, **_PIL02_EXPLAIN_DIALOG_TITLES, **_PIL03_EXPLAIN_DIALOG_TITLES, **_PIL04_EXPLAIN_DIALOG_TITLES, **_PIL05_EXPLAIN_DIALOG_TITLES}


@st.dialog("Risk library explanation")
def _pil01_risk_explain_dialog(risk_id: str):
    """Show tailored plain-language explain markdown for a PIL-01/PIL-02/PIL-03/PIL-04/PIL-05 library risk."""
    title = _RISK_EXPLAIN_DIALOG_TITLES.get(risk_id, risk_id)
    st.caption(title)
    body = RISK_LIBRARY_EXPLAINS.get(risk_id, "")
    if body:
        st.markdown(body)
    else:
        st.info("No explanation text is defined for this risk yet.")


# Keep legacy names pointing at dict entries so any leftover references still resolve.
SBD_R106_EXPLAIN_MD = PIL01_RISK_EXPLAINS["SBD-R106"]
SBD_R121_EXPLAIN_MD = PIL01_RISK_EXPLAINS["SBD-R121"]


def render_risk_explain_button(risk_id, driver_ref=""):
    """Explicit per-risk help buttons only — never auto-copied from keyword matching.

    Keys always include driver_ref so a risk linked to several Level III drivers
    does not hit StreamlitDuplicateElementKey (which previously hid PIL-02–05).
    Buttons sit in a keyed container so CSS can target .st-key-vh_help-* (Streamlit
    default white styles otherwise win).

    R101 / R104 keep shared concept buttons only (no extra explain).
    Any risk_id in RISK_LIBRARY_EXPLAINS gets an ``explain Rxxx`` button.
    """
    suffix = f"{ACTIVE_REGISTER_KEY}_{risk_id}_{driver_ref or 'na'}"
    _help_ids = (
        "SBD-R001",
        "SBD-R002",
        "SBD-R003",
        "SBD-R004",
        "SBD-R005",
        "SBD-R101",
        "SBD-R102",
        "SBD-R103",
        "SBD-R104",
        "SBD-R105",
        "SBD-R106",
        "SBD-R107",
        "SBD-R108",
        "SBD-R109",
        "SBD-R110",
        "SBD-R111",
        "SBD-R112",
        "SBD-R113",
        "SBD-R114",
        "SBD-R115",
        "SBD-R116",
        "SBD-R117",
        "SBD-R118",
        "SBD-R119",
        "SBD-R120",
        "SBD-R121",
        "SBD-R122",
        "SBD-R123",
        "SBD-R124",
        "SBD-R125",
        "SBD-R126",
        "SBD-R127",
        "SBD-R128",
        "SBD-R129",
        "SBD-R130",
        "SBD-R131",
        "SBD-R132",
        "SBD-R133",
        "SBD-R134",
        "SBD-R135",
        "SBD-R136",
        "SBD-R137",
        "SBD-R138",
    )
    if risk_id not in _help_ids:
        return

    with st.container(key=f"vh_help_{suffix}"):
        c1, c2, c3, _sp = st.columns([1.05, 1.25, 1.45, 6.2], gap="small")
        if risk_id == "SBD-R101":
            with c1:
                if st.button(
                    "playbook",
                    key=f"term_playbook_btn_{suffix}",
                    help="Open Trident commercial term-playbook",
                ):
                    _term_playbook_dialog(risk_id)
            with c2:
                if st.button(
                    "SBD-P05 agenda",
                    key=f"p05_agenda_btn_{suffix}",
                    help="What linking the operating agenda to a renewal means",
                ):
                    _p05_agenda_dialog(risk_id)
        elif risk_id == "SBD-R104":
            with c1:
                if st.button(
                    "redeployment case",
                    key=f"redeploy_case_btn_{suffix}",
                    help="Redeployment is not liquid — reconstruction, costs, and Chile cannibalisation",
                ):
                    _redeployment_case_dialog(risk_id)
        elif risk_id in RISK_LIBRARY_EXPLAINS:
            short = risk_id.split("-")[-1]  # e.g. R001
            with c1:
                if st.button(
                    f"explain {short}",
                    key=f"risk_explain_btn_{suffix}",
                    help=f"Plain-language explanation of {risk_id}",
                ):
                    _pil01_risk_explain_dialog(risk_id)



def extract_mitigation_bullets(mitigation_text):
    """Split Current mitigation into successive action bullets (numbered or semicolon lists)."""
    import re as _re
    text_val = str(mitigation_text or "").strip()
    if not text_val:
        return []
    found = _re.findall(r"\((\d+)\)\s*([^;]+)", text_val)
    if found:
        return [item.strip(" .;") for _n, item in found if item.strip()]
    # Drop a short owner prefix like "S&BD+Commercial:" then split on semicolons
    if ":" in text_val and text_val.index(":") < 40:
        after = text_val.split(":", 1)[1].strip()
        if after:
            text_val = after
    parts = [p.strip(" .;") for p in text_val.split(";") if p.strip()]
    return parts if len(parts) > 1 else ([text_val] if text_val else [])


def render_risk_library(risks_df, processes_df=None, function_name=None):
    """Risk library in the same visual language as Context ERM (peach pane, chips), with ops questions."""
    st.markdown(
        """
        <style>
        .vh-ref-badge{display:inline-block;color:#00191d;background:#caff74;border:1px solid #90c44f;border-radius:4px;padding:2px 7px;margin-right:8px;font-size:.9rem;font-weight:700;white-space:nowrap}
        .vh-pil-badge{display:inline-block;color:#00191d;background:#90c4ce;border:1px solid #255a64;border-radius:4px;padding:3px 8px;margin-right:8px;font-size:.9rem;font-weight:700;white-space:nowrap}
        .vh-driver-link{margin:0 0 9px 0;font-size:.96rem;line-height:1.6}
        .vh-process-pillar{margin:11px 0 8px;font-size:.98rem;font-weight:700}
        .vh-l5-erm-pane{background:rgba(255,107,53,.12);border:1px solid #d94b18;border-radius:8px;padding:12px 12px 8px;min-height:40px;margin-bottom:10px}
        .vh-l5-pane-title{font-weight:700;color:#00191d;font-size:.96rem;margin:0 0 10px 0}
        .vh-l5-risk-badge{display:inline-block;color:#00191d;background:#ffc9b0;border:1px solid #d94b18;border-radius:4px;padding:2px 7px;margin-right:8px;font-size:.9rem;font-weight:700;white-space:nowrap}
        .vh-l5-erm-coverage{font-size:.82rem;color:#8a3a18;margin:2px 0 10px 28px;line-height:1.35}
        .vh-l5-erm-coverage strong{color:#00191d}
        .vh-l5-empty-slot{color:#6b7c80;font-size:.85rem;font-style:italic;margin:0 0 9px 0;padding:4px 0}
        .vh-l5-driver-slot{margin:0 0 9px 0;min-height:1.55em}
        .vh-playbook-hit{color:#00839B;font-weight:700;text-decoration:underline;text-underline-offset:2px}

        /* Help buttons: Streamlit stamps class st-key-vh_help_* on keyed containers */
        div[class*="st-key-vh_help"] button,
        div[class*="st-key-vh_help"] [data-testid="stBaseButton-secondary"],
        div[class*="st-key-vh_help"] [data-testid="baseButton-secondary"] {
            background-color: #5a6570 !important;
            background-image: none !important;
            border: 1px solid #3d4650 !important;
            color: #ffffff !important;
            min-height: 2.1rem !important;
            font-weight: 700 !important;
            box-shadow: 0 1px 2px rgba(0,25,29,.14) !important;
        }
        div[class*="st-key-vh_help"] button:hover,
        div[class*="st-key-vh_help"] [data-testid="stBaseButton-secondary"]:hover {
            background-color: #3d4650 !important;
            border-color: #2a3138 !important;
            color: #ffffff !important;
        }
        div[class*="st-key-vh_help"] button p,
        div[class*="st-key-vh_help"] span {
            color: #ffffff !important;
        }
</style>
        """,
        unsafe_allow_html=True,
    )
    st.write(
        "Same layout as **Context** Level IV-B ERM: pillars → Level III drivers → risk chips. "
        "Under each risk: **what we can fail to do** and **what we can do** (ISO process links come later). "
        "Risk chips show failure modes and mitigations. Tailored **explain** buttons cover PIL-01–05 Strategy library risks linked here (PIL-01: R001, R102, R103, R105, R106, R111, R113, R120, R121, R135, R137; PIL-02 adds R003, R005, R107–R110, R112, R129 — plus shared R001/R105/R111/R113; PIL-03 adds R002, R004, R114–R119, R123, R132, R136 — plus shared R003/R005/R102/R103/R110/R120/R121/R137; PIL-04 adds R122, R124–R127, R138 — plus shared R123; PIL-05 adds R128, R130, R131, R133, R134 — plus shared R001/R005/R107/R109/R110/R116/R117/R124/R126/R129/R132); R101 also has playbook + P05, and R104 has the shared redeployment-case tag — not auto-copied outside this explicit list."
    )
    catalog = level3_driver_catalog()
    scope = function_scope(function_name)
    only_scope = False
    if scope:
        only_scope = st.toggle(
            f"Show only {function_name}'s Level III drivers ({len(scope)})",
            value=True,
            key=f"lib_scope_{ACTIVE_REGISTER_KEY}",
        )
    if only_scope:
        catalog = [row for row in catalog if row["reference"] in scope]
    scored_risks = scored(risks_df) if not risks_df.empty and "Risk ID" in risks_df.columns else risks_df.copy()
    if not scored_risks.empty and "Level 3 drivers" not in scored_risks.columns:
        scored_risks["Level 3 drivers"] = ""

    for pillar_label, _drivers in VALUE_HIERARCHY_GROUPS:
        plain = pillar_label.replace("<br>", " · ")
        pillar_id = plain.split("PIL-0")[1][:1] if "PIL-0" in plain else ""
        pillar_code = f"PIL-0{pillar_id}" if pillar_id else ""
        drivers_for_pillar = [row for row in catalog if row["pillar_id"] == pillar_code]
        if only_scope and not drivers_for_pillar:
            continue
        pillar_description = plain.rsplit(" · ", 1)[-1].strip() if " · " in plain else plain

        pillar_risk_ids = set()
        for row in drivers_for_pillar:
            ref = row["reference"]
            if scored_risks.empty:
                continue
            mask = scored_risks["Level 3 drivers"].astype(str).apply(lambda value, r=ref: r in split_refs(value))
            pillar_risk_ids.update(scored_risks.loc[mask, "Risk ID"].astype(str).tolist())
        count = len(pillar_risk_ids)

        with st.expander(f"{pillar_code} · {pillar_description} ({count})", expanded=False):
            st.markdown(
                (
                    '<div class="vh-l5-erm-pane">'
                    '<div class="vh-l5-pane-title">Risks under this pillar - by Level III driver</div>'
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

                if linked.empty:
                    st.markdown(
                        (
                            '<div class="vh-l5-erm-pane">'
                            f'<div class="vh-process-pillar"><span class="vh-ref-badge">{escape(ref)}</span>'
                            f'{escape(driver_name)}</div>'
                            '<div class="vh-l5-empty-slot">No risks linked to this Level III driver yet.</div>'
                            "</div>"
                        ),
                        unsafe_allow_html=True,
                    )
                    continue

                st.markdown(
                    (
                        '<div class="vh-l5-erm-pane" style="min-height:0;padding-bottom:4px;">'
                        f'<div class="vh-process-pillar"><span class="vh-ref-badge">{escape(ref)}</span>'
                        f'{escape(driver_name)}</div></div>'
                    ),
                    unsafe_allow_html=True,
                )

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

                    questions = extract_operational_questions(risk_row.get("Cause", ""))
                    mitigation = str(risk_row.get("Current mitigation", "") or "").strip()
                    treatment = str(risk_row.get("Treatment decision", "") or "").strip()
                    bullets = extract_mitigation_bullets(mitigation)

                    parts = [
                        '<div class="vh-l5-erm-pane">',
                        (
                            f'<div class="vh-driver-link vh-l5-driver-slot">'
                            f'<span class="vh-l5-risk-badge">{escape(rid)}</span>'
                            f'{escape(title)}{escape(score_txt)}</div>'
                        ),
                    ]

                    if questions:
                        q_html = "".join(
                            f"<li>{highlight_library_terms_html(escape(q.rstrip(' ?')))}?</li>"
                            for q in questions
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

                    if bullets:
                        m_html = "".join(
                            f"<li>{highlight_library_terms_html(escape(b))}</li>" for b in bullets
                        )
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
                    # Explicit helps only for risks we have tailored (not keyword auto-copy)
                    if rid in ("SBD-R001", "SBD-R002", "SBD-R003", "SBD-R004", "SBD-R005", "SBD-R101", "SBD-R102", "SBD-R103", "SBD-R104", "SBD-R105", "SBD-R106", "SBD-R107", "SBD-R108", "SBD-R109", "SBD-R110", "SBD-R111", "SBD-R112", "SBD-R113", "SBD-R114", "SBD-R115", "SBD-R116", "SBD-R117", "SBD-R118", "SBD-R119", "SBD-R120", "SBD-R121", "SBD-R122", "SBD-R123", "SBD-R124", "SBD-R125", "SBD-R126", "SBD-R127", "SBD-R128", "SBD-R129", "SBD-R130", "SBD-R131", "SBD-R132", "SBD-R133", "SBD-R134", "SBD-R135", "SBD-R136", "SBD-R137", "SBD-R138"):
                        render_risk_explain_button(rid, driver_ref=ref)

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



def render_assess_and_decide(risks_df):
    """Pedagogical Assess & decide: read failure modes / mitigations, score residual, choose treatment."""
    st.markdown(
        """
        <style>
        .vh-assess-score-green{display:inline-block;background:#caff74;border:1px solid #90c44f;color:#00191d;border-radius:6px;padding:6px 12px;font-weight:800;font-size:1.05rem}
        .vh-assess-score-amber{display:inline-block;background:#ffe08a;border:1px solid #c9a227;color:#00191d;border-radius:6px;padding:6px 12px;font-weight:800;font-size:1.05rem}
        .vh-assess-score-red{display:inline-block;background:#ffc9b0;border:1px solid #d94b18;color:#00191d;border-radius:6px;padding:6px 12px;font-weight:800;font-size:1.05rem}
        .vh-assess-hint{color:#6b7c80;font-size:.88rem;font-style:italic;margin:4px 0 8px 0}
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
**Assess & decide — five steps**

1. **Pick a risk** — one at a time (filter by pillar if helpful).
2. **Read failure modes** — *What we can fail to do* (from Cause).
3. **Read current mitigations** — *What we can do* (from Current mitigation).
4. **Score residual** — likelihood × impact **after** current mitigation (feeds the heatmap). Material line: residual ≥ **{MATERIAL_RESIDUAL_THRESHOLD}**.
5. **Choose treatment & appetite** — Treat / Accept / Monitor / Transfer / Avoid, then save.
        """.strip()
    )

    if risks_df is None or risks_df.empty or "Risk ID" not in risks_df.columns:
        st.warning("No risks in this register yet. Add them in **Risk library** or **Risk register**.")
        return

    work = ensure_risk_treatment_columns(risks_df)
    scored_df = scored(work)

    # --- metrics ---
    outside_n = int((scored_df.get("Appetite status", pd.Series(dtype=str)).astype(str).str.strip() == "Outside appetite").sum())
    resid = pd.to_numeric(scored_df.get("Residual score", pd.Series(dtype=float)), errors="coerce")
    material_n = int((resid.fillna(0) >= MATERIAL_RESIDUAL_THRESHOLD).sum())
    rl = pd.to_numeric(scored_df.get("Residual likelihood", pd.Series(dtype=float)), errors="coerce")
    ri = pd.to_numeric(scored_df.get("Residual impact", pd.Series(dtype=float)), errors="coerce")
    missing_n = int(((rl.isna()) | (ri.isna()) | (rl.fillna(0) <= 0) | (ri.fillna(0) <= 0)).sum())
    m1, m2, m3 = st.columns(3)
    m1.metric("Outside appetite", outside_n)
    m2.metric(f"Residual ≥ {MATERIAL_RESIDUAL_THRESHOLD}", material_n)
    m3.metric("Missing residual scores", missing_n)

    # --- picker (optional pillar filter) ---
    pillar_options = ["All pillars"]
    for pillar_label, _drivers in VALUE_HIERARCHY_GROUPS:
        plain = pillar_label.replace("<br>", " · ")
        pillar_id = plain.split("PIL-0")[1][:1] if "PIL-0" in plain else ""
        pillar_code = f"PIL-0{pillar_id}" if pillar_id else ""
        if pillar_code:
            pillar_options.append(pillar_code)

    fcol, scol = st.columns([1, 2])
    with fcol:
        pillar_filter = st.selectbox(
            "Pillar filter",
            pillar_options,
            key=f"assess_pillar_filter_{ACTIVE_REGISTER_KEY}",
        )
    filtered = scored_df
    if pillar_filter != "All pillars" and "Value pillars" in filtered.columns:
        filtered = filtered[
            filtered["Value pillars"].astype(str).str.contains(pillar_filter, na=False)
        ]
    if filtered.empty:
        st.info("No risks match this pillar filter.")
        return

    def _picker_label(row):
        rid = str(row.get("Risk ID", "")).strip()
        title = str(row.get("Risk title", "") or "").strip()
        try:
            score = int(float(row.get("Residual score", 0) or 0))
        except (TypeError, ValueError):
            score = 0
        try:
            lik = int(float(row.get("Residual likelihood", 0) or 0))
            imp = int(float(row.get("Residual impact", 0) or 0))
            lxI = f"{lik}×{imp}={score}"
        except (TypeError, ValueError):
            lxI = str(score)
        return f"{rid} — {title} (residual {lxI})"

    labels = []
    id_by_label = {}
    for _, row in filtered.sort_values("Risk ID").iterrows():
        lab = _picker_label(row)
        labels.append(lab)
        id_by_label[lab] = str(row.get("Risk ID", "")).strip()

    with scol:
        chosen_label = st.selectbox(
            "Select risk",
            labels,
            key=f"assess_risk_picker_{ACTIVE_REGISTER_KEY}",
        )
    rid = id_by_label.get(chosen_label, "")
    if not rid:
        st.warning("Select a risk to assess.")
        return

    risk_rows = scored_df[scored_df["Risk ID"].astype(str) == rid]
    if risk_rows.empty:
        st.error(f"Risk {rid} not found.")
        return
    risk_row = risk_rows.iloc[0]
    title = str(risk_row.get("Risk title", "") or "")
    try:
        residual_score = int(float(risk_row.get("Residual score", 0) or 0))
    except (TypeError, ValueError):
        residual_score = 0
    try:
        cur_lik = int(float(risk_row.get("Residual likelihood", 0) or 0))
        cur_imp = int(float(risk_row.get("Residual impact", 0) or 0))
        score_badge = f"{cur_lik}×{cur_imp} = {residual_score}"
    except (TypeError, ValueError):
        score_badge = str(residual_score)

    questions = extract_operational_questions(risk_row.get("Cause", ""))
    bullets = extract_mitigation_bullets(risk_row.get("Current mitigation", ""))

    # --- selected risk card (library visual language) ---
    st.markdown(
        (
            '<div class="vh-l5-erm-pane">'
            f'<div class="vh-l5-pane-title">'
            f'<span class="vh-l5-risk-badge">{escape(rid)}</span>'
            f'{escape(title)}'
            f' &nbsp; <span class="vh-l5-risk-badge">residual {escape(score_badge)}</span>'
            f"</div></div>"
        ),
        unsafe_allow_html=True,
    )

    left, right = st.columns(2)
    with left:
        if questions:
            q_html = "".join(
                f"<li>{highlight_library_terms_html(escape(q.rstrip(' ?')))}?</li>"
                for q in questions
            )
            st.markdown(
                (
                    '<div class="vh-l5-erm-pane">'
                    '<div class="vh-l5-pane-title">What we can fail to do</div>'
                    '<div class="vh-l5-erm-coverage">'
                    '<ul style="margin:4px 0 0 18px;padding:0;">'
                    f"{q_html}</ul></div></div>"
                ),
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                (
                    '<div class="vh-l5-erm-pane">'
                    '<div class="vh-l5-pane-title">What we can fail to do</div>'
                    '<div class="vh-l5-empty-slot">No failure modes yet — add Trident-side items in '
                    "<strong>Cause</strong> via Risk register / library.</div></div>"
                ),
                unsafe_allow_html=True,
            )
    with right:
        if bullets:
            m_html = "".join(
                f"<li>{highlight_library_terms_html(escape(b))}</li>" for b in bullets
            )
            st.markdown(
                (
                    '<div class="vh-l5-erm-pane">'
                    '<div class="vh-l5-pane-title">What we can do</div>'
                    '<div class="vh-l5-erm-coverage">'
                    '<ul style="margin:4px 0 0 18px;padding:0;">'
                    f"{m_html}</ul></div></div>"
                ),
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                (
                    '<div class="vh-l5-erm-pane">'
                    '<div class="vh-l5-pane-title">What we can do</div>'
                    '<div class="vh-l5-empty-slot">No mitigations yet — fill '
                    "<strong>Current mitigation</strong> in Risk register / library.</div></div>"
                ),
                unsafe_allow_html=True,
            )

    def _clamp_1_5(val, default=3):
        try:
            n = int(float(val))
            if n < 1 or n > 5:
                return default
            return n
        except (TypeError, ValueError):
            return default

    def _opt_index(options, value, default=0):
        v = str(value or "").strip()
        if v in options:
            return options.index(v)
        return default

    # --- score & decide strip ---
    input_zone_banner("Score & decide — residual after current mitigation")
    with st.container(key=f"vh_input_assess_score_{ACTIVE_REGISTER_KEY}_{rid}"):
        c1, c2, c3 = st.columns([1, 1, 1.2])
        with c1:
            new_lik = st.selectbox(
                "Residual likelihood (1–5)",
                [1, 2, 3, 4, 5],
                index=_clamp_1_5(risk_row.get("Residual likelihood", 3), 3) - 1,
                key=f"assess_rl_{ACTIVE_REGISTER_KEY}_{rid}",
            )
        with c2:
            new_imp = st.selectbox(
                "Residual impact (1–5)",
                [1, 2, 3, 4, 5],
                index=_clamp_1_5(risk_row.get("Residual impact", 3), 3) - 1,
                key=f"assess_ri_{ACTIVE_REGISTER_KEY}_{rid}",
            )
        live_score = int(new_lik) * int(new_imp)
        if live_score >= MATERIAL_RESIDUAL_THRESHOLD:
            score_class = "vh-assess-score-red"
            score_note = "material / escalate attention"
        elif live_score >= 9:
            score_class = "vh-assess-score-amber"
            score_note = "approaching material line"
        else:
            score_class = "vh-assess-score-green"
            score_note = "below material line"
        with c3:
            st.markdown("**Residual score** (likelihood × impact)")
            st.markdown(
                f'<span class="{score_class}">{new_lik} × {new_imp} = {live_score}</span>'
                f' <span class="vh-assess-hint">{escape(score_note)}</span>',
                unsafe_allow_html=True,
            )

        d1, d2 = st.columns(2)
        with d1:
            treatment = st.selectbox(
                "Treatment decision",
                TREATMENT_DECISIONS,
                index=_opt_index(TREATMENT_DECISIONS, risk_row.get("Treatment decision", ""), 0),
                key=f"assess_treat_{ACTIVE_REGISTER_KEY}_{rid}",
            )
        with d2:
            appetite = st.selectbox(
                "Appetite status",
                APPETITE,
                index=_opt_index(APPETITE, risk_row.get("Appetite status", ""), 0),
                key=f"assess_app_{ACTIVE_REGISTER_KEY}_{rid}",
            )

        with st.expander("Accept / escalate", expanded=False):
            status = st.selectbox(
                "Status",
                STATUSES,
                index=_opt_index(STATUSES, risk_row.get("Status", ""), 0),
                key=f"assess_status_{ACTIVE_REGISTER_KEY}_{rid}",
            )
            esc_opts = ["No", "Yes"]
            esc_cur = str(risk_row.get("Enterprise escalation", "No") or "No").strip()
            if esc_cur not in esc_opts:
                esc_cur = "No"
            escalation = st.selectbox(
                "Enterprise escalation",
                esc_opts,
                index=esc_opts.index(esc_cur),
                key=f"assess_esc_{ACTIVE_REGISTER_KEY}_{rid}",
            )
            evidence = st.text_area(
                "Evidence / rationale",
                value=str(risk_row.get("Evidence / rationale", "") or ""),
                height=100,
                key=f"assess_evidence_{ACTIVE_REGISTER_KEY}_{rid}",
            )

        if st.button(
            "Save assessment for this risk",
            type="primary",
            key=f"assess_save_{ACTIVE_REGISTER_KEY}_{rid}",
        ):
            # Ensure Accept/escalate fields exist even if expander never opened (Streamlit still runs widgets)
            row = pd.DataFrame(
                [
                    {
                        "Risk ID": rid,
                        "Residual likelihood": new_lik,
                        "Residual impact": new_imp,
                        "Treatment decision": treatment,
                        "Appetite status": appetite,
                        "Status": status,
                        "Enterprise escalation": escalation,
                        "Evidence / rationale": evidence,
                    }
                ]
            )
            update_risks(
                row,
                [
                    "Residual likelihood",
                    "Residual impact",
                    "Treatment decision",
                    "Appetite status",
                    "Status",
                    "Enterprise escalation",
                    "Evidence / rationale",
                ],
            )

    st.caption(
        "To edit the five mitigations or failure modes, use **Risk register** "
        "(or refine in library source fields)."
    )

    # --- optional bulk grid ---
    with st.expander("Bulk residual score grid", expanded=False):
        st.caption("Power-user grid: inherent and residual L/I only — no mitigation prose.")
        bulk_cols = [
            "Risk ID",
            "Risk title",
            "Inherent likelihood",
            "Inherent impact",
            "Residual likelihood",
            "Residual impact",
        ]
        present = [c for c in bulk_cols if c in work.columns]
        input_zone_banner("Bulk residual scores — editable inputs")
        with st.container(key=f"vh_input_assess_bulk_{ACTIVE_REGISTER_KEY}"):
            bulk_edited = st.data_editor(
                work[present],
                hide_index=True,
                use_container_width=True,
                height=360,
                key=f"assess_bulk_editor_{ACTIVE_REGISTER_KEY}",
            )
        if st.button(
            "Save bulk residual scores",
            type="primary",
            key=f"assess_bulk_save_{ACTIVE_REGISTER_KEY}",
        ):
            update_cols = [
                c
                for c in [
                    "Inherent likelihood",
                    "Inherent impact",
                    "Residual likelihood",
                    "Residual impact",
                ]
                if c in present
            ]
            update_risks(bulk_edited, update_cols)

    st.info(
        "Detailed multi-step action plans remain under **More modules → Actions & target risk** "
        "if you need them later."
    )



# Strategy retains seed + migration on strategy_*.csv (backward compatible).
set_active_register("strategy")
seed_data()
migrate_existing_data()

_ASSETS = Path(__file__).resolve().parent / "assets"
_LOGO = _ASSETS / "trident_logo.png"
_ICON = _ASSETS / "trident_icon.png"
_page_icon = str(_ICON) if _ICON.exists() else "△"
st.set_page_config(
    page_title="Trident IMERS",
    page_icon=_page_icon,
    layout="wide",
)
apply_brand_theme()

if _LOGO.exists():
    try:
        st.logo(str(_LOGO), size="large")
    except TypeError:
        st.logo(str(_LOGO))
elif _ICON.exists():
    st.logo(str(_ICON))

# Enlarge Streamlit sidebar logo beyond the built-in "large" size
st.markdown(
    """
    <style>
    [data-testid="stSidebar"] img,
    [data-testid="stSidebarHeader"] img,
    [data-testid="stLogo"] img,
    div[data-testid="stSidebarCollapsedControl"] img {
        max-height: 120px !important;
        height: 120px !important;
        width: auto !important;
        object-fit: contain !important;
    }
    [data-testid="stSidebar"] [data-testid="stLogo"] {
        margin: 0.35rem 0 0.75rem 0 !important;
        width: 100% !important;
        max-width: 100% !important;
    }
    [data-testid="stSidebar"] [data-testid="stLogo"] img {
        max-width: 100% !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

folder_labels = [label for label, _fn, _regs in FOLDERS]
with st.sidebar.expander("Configured ERM registers"):
    for unit, owner, title in UNITS:
        st.write(f"**{unit}**  \n{owner}, {title}")
    st.write("**Enterprise Risk Register**  \nConsolidated material risks, value driver ownership and value coverage")

st.markdown(
    """
    <div style="margin:4px 0 10px 0;">
      <div style="font-size:1.75rem;font-weight:800;color:#00191d;line-height:1.15;letter-spacing:.01em;">
        Trident <span style="color:#00839B;">IMERS</span>
      </div>
      <div style="font-size:.95rem;color:#255a64;margin-top:2px;">
        Integrated Management &amp; Enterprise Risk System
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <style>
    .st-key-folder_tabs [role="radiogroup"]{gap:0 !important;flex-wrap:wrap;border-bottom:3px solid #00839B;margin-bottom:2px}
    .st-key-folder_tabs [role="radiogroup"] label{
        margin:0 2px 0 0 !important;padding:6px 11px 5px !important;border:1px solid #a4c4e9;border-bottom:none;
        border-radius:9px 9px 0 0;background:#eef4f6;cursor:pointer}
    .st-key-folder_tabs [role="radiogroup"] label > div:first-child:not(:has([data-testid="stMarkdownContainer"])){display:none}
    .st-key-folder_tabs [role="radiogroup"] label div:has(> div:empty):not(:has([data-testid="stMarkdownContainer"])){display:none}
    .st-key-folder_tabs [role="radiogroup"] label p{font-size:.86rem;white-space:nowrap;font-weight:600;color:#255a64}
    .st-key-folder_tabs [role="radiogroup"] label:has(input:checked){background:#00839B;border-color:#00839B}
    .st-key-folder_tabs [role="radiogroup"] label:has(input:checked) p{color:#fff}
    .st-key-folder_tabs [role="radiogroup"] label:hover{background:#d9ecef}
    .st-key-folder_tabs [role="radiogroup"] label:has(input:checked):hover{background:#006677}
    </style>
    """,
    unsafe_allow_html=True,
)
with st.container(key="folder_tabs"):
    selected_folder = st.radio(
        "Department folder",
        folder_labels,
        index=folder_labels.index(DEFAULT_FOLDER),
        horizontal=True,
        label_visibility="collapsed",
        key="department_folder",
    )
_folder_label, selected_function, folder_registers = next(f for f in FOLDERS if f[0] == selected_folder)
if len(folder_registers) > 1:
    selected_register = st.selectbox(
        f"Register in the {selected_folder} folder",
        folder_registers,
        key=f"folder_register_{selected_folder}",
    )
else:
    selected_register = folder_registers[0]

if selected_register == ABOUT_IMERS:
    st.caption("About IMERS | The concept, the words we use and the management-group presentation")
    render_about_imers()
    st.stop()

if selected_register == OPERATING_AGENDA:
    st.caption("Operating Agenda | Meeting running order, presenters and Level I–III topics")
    render_operating_agenda()
    st.stop()

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
    render_function_value_map(selected_register)
    render_value_hierarchy(data["processes"], data["risks"], data["controls"], data["actions"], function_name=selected_function)
    st.caption(
        "Context for Strategy & BD. Risks should link to Level III drivers and pillars. "
        "Score risks in **01 Risks & Opportunities**, then open **02 Heatmap**."
    )
elif page == "01 Risks & Opportunities" or str(page).startswith("02 Risks"):
    risks_work = ensure_risk_treatment_columns(data["risks"])
    data["risks"] = risks_work
    t_lib, t_reg, t_assess, t_opp = st.tabs(["Risk library", "Risk register", "Assess & decide", "Opportunities"])
    with t_lib:
        render_risk_library(risks_work, data.get("processes"), function_name=selected_function)
    with t_reg:
        st.write("Shared Strategy & BD risk inventory. Use **Assess & decide** for mitigation, residual score, and appetite.")
        outside = out_of_scope_tags(risks_work, selected_function)
        if outside:
            st.warning(
                f"{len(outside)} risk(s) are tagged to Level III drivers outside {selected_function}'s scope: "
                + "; ".join(f"{rid} → {', '.join(refs)}" for rid, refs in outside.items())
                + ". Retag them to an in-scope driver, record the other driver under **Handed-over drivers**, "
                "or move the risk to the accountable function's register."
            )
        input_zone_banner("Risk register — editable fields")
        risk_config = {
            "Category": st.column_config.SelectboxColumn(options=RISK_CATEGORIES),
            "Appetite status": st.column_config.SelectboxColumn(options=APPETITE),
            "Trend": st.column_config.SelectboxColumn(options=TRENDS),
            "Status": st.column_config.SelectboxColumn(options=STATUSES),
            "Enterprise escalation": st.column_config.SelectboxColumn(options=["Yes", "No"]),
            "Treatment decision": st.column_config.SelectboxColumn(options=TREATMENT_DECISIONS),
        }
        editor("risks", risks_work, risk_config, height=780)
    with t_assess:
        render_assess_and_decide(risks_work)
    with t_opp:
        editor("opportunities", data["opportunities"])
elif page == "03 Ownership" or page == "04 Ownership" or str(page).startswith("03 Ownership"):
    render_ownership_page(data["risks"])
elif page in ("04 Actions", "05 Actions", "Actions & target risk") or str(page).startswith("09 Responses"):
    st.subheader("Responses, actions and target risk")
    t1, t2 = st.tabs(["Treatment actions", "Target risk"])
    with t1:
        actions_edit = data["actions"].copy()
        if "Due date" in actions_edit.columns:
            actions_edit["Due date"] = pd.to_datetime(actions_edit["Due date"], errors="coerce", dayfirst=False).dt.date
        if "Progress %" in actions_edit.columns:
            actions_edit["Progress %"] = pd.to_numeric(actions_edit["Progress %"], errors="coerce")
        editor(
            "actions",
            actions_edit,
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
