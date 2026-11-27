# Trident Integrated Management & Enterprise Risk System

Version 2 is a working Streamlit prototype for Trident IMS & ERM. It combines a process-led ISO-aligned management-system structure with unit risk registers and an Enterprise roll-up of material risks.

## Start on Windows

```bash
py -m pip install -r requirements.txt
py -m streamlit run app.py
```

You can also double-click `start_trident_erm.bat` after Python is installed.

## Multi-register data model

- **Twelve unit registers** (Strategy & Business Development, Finance, Commercial, Vessel Operations, Technical & HSEQ, Crewing, Onshore Employees & Organization, Administration, ICT, Legal & Compliance, Chile Operations, Shetland Operations).
- CSV files live in `data/` as `{register_key}_{dataset}.csv` (for example `strategy_risks.csv`, `finance_risks.csv`).
- **Strategy** keeps the existing `strategy_*.csv` naming, seed content, and `migrate_existing_data` behavior for backward compatibility.
- Other units start with **empty CSVs** (correct columns) when first selected.
- Use the sidebar **Risk register** selector to switch units. Workflow pages 00–14 operate on the selected unit’s data.

## Enterprise Risk Register

Selecting **Enterprise Risk Register** shows a consolidated roll-up (not a thirteenth seed dump).

**Materiality criteria** (documented in the UI):

- Enterprise escalation = Yes, **or**
- Appetite status = Outside appetite, **or**
- Residual score ≥ 12 (residual likelihood × residual impact)

The Enterprise view includes metrics, a residual heatmap, a provenance table (source unit + risk fields), linked treatment actions, and an Excel export with an **Enterprise** sheet plus **ERM Structure**.

## Value hierarchy Level 5 (ISO + ERM)

On **00 Value Hierarchy & Context**, each Level 5 process expander includes:

- **Green — 4.1 ISO-aligned delivery**: process owner, interfaces, activities, outputs, review cadence, linked Level 3 drivers, and matching ISO alignment-matrix elements.
- **Orange — 4.2 ERM monitoring**: risks that list that Process ID, plus controls and treatment actions for those risks.

### Owned vs not-owned assets (Nov 2026)

The test between pillar 2.1 and 2.2 is "does Trident own the asset today?". Reconstruction of owned vessels moved from 2.2
to **3.1.6 Value-accretive reconstruction of owned vessels** (accountable: CS&BDO for the investment case; Technical & HSEQ
delivers). 2.2 now covers only assets Trident does not own: 3.2.1 Newbuilds, 3.2.2 Second-hand acquisitions and
sale-leasebacks, 3.2.3 M&A and synergies, 3.2.4 New platforms (SFaaS). All tags were remapped
(old 3.2.2→3.1.6, 3.2.3→3.2.2, 3.2.4→3.2.3, 3.2.5→3.2.4). Backup: `data/strategy_risks_backup_before_316_renumber.csv`.
Every Level 3 box has exactly one accountable executive, shown on the box.

## Operating Agenda folder

The **Operating Agenda** tab defines the management meeting: running order with start/end times in nine chapters that run
from concrete to abstract for new participants (Welcome, How we create value, Life at sea, Customers and the business plan,
Our fleet, Growth, One Trident, Finance, Decisions), each item tagged with its Level 1 lever, Level 2 pillar, the Level 3 drivers each item covers, presenter,
minutes and key exhibits. Rule: every Level 3 driver is presented exactly once, by its accountable executive.
- **Running order:** the agenda by section, plus the top risks (all registers) for each item.
- **Stakeholder alignment:** every Level 3 driver mapped to the stakeholder groups and material topics of the Sustainability
  Statement 2025 (VSME DMA: E1, E3, E4, S1, G1 double material; E2 impact material; fish welfare cross-cutting; SDG 8/12/13/14).
  Illustration (Level 0 → 1 → 2 → stakeholders), stakeholder cards with 2025 statement data, matrix, and editable mapping
  (`data/stakeholder_alignment.csv`).
- **By presenter:** each executive's items, minutes, and any accountable driver they do not present.
- **Checks:** flags drivers missing from the agenda, duplicated, or presented by someone other than the accountable executive.
- **Edit agenda:** meeting title, date and start time (`data/operating_agenda_meta.json`) and the agenda rows (`data/operating_agenda.csv`).
- Excel download of the agenda and checks.

## Department folders

The top of the app has one folder tab per executive function (CEO, Strategy & BD, Finance, Commercial, Vessel Operations,
Technical & HSEQ, HR, Admin & ICT, Legal & Compliance) plus **Enterprise**. Folders with more than one register show a
register selector (Vessel Operations: Vessel Operations / Chile / Shetland; HR: Crewing / Onshore Employees; Admin & ICT:
Administration / ICT). Levels 0–3 are identical in every folder; on **00 Context** the Level 3 drivers are marked for the
selected function: solid teal = accountable, light teal = contributing, dashed orange = not in scope but tagged by this
register's risks, faded = not in scope. Levels 1 and 2 show the accountable/contributing counts.

## Value driver ownership (every function traces to value)

Every executive function (CEO + eight departments) traces to the value hierarchy through Level 3:
Level 3 driver → Level 2 pillar → Level 1 lever (EBITDA, Multiple, Cash) → Level 0 equity value.

- **2.3 Multiple Expansion** is split into *earnings quality* (3.3.1–3.3.6) and a **strong operating platform** (3.3.7–3.3.12):
  3.3.7 Governance and reliable reporting · 3.3.8 Scalable operating model and integration capability ·
  3.3.9 People, competence, leadership and succession · 3.3.10 HSEQ performance (safety, environment, quality, ESG) ·
  3.3.11 Regulatory compliance and legal robustness · 3.3.12 Digital, data and cyber resilience.
- `data/driver_ownership.csv` holds one **accountable function** per driver plus **contributing functions**. Edit it under
  **Enterprise Risk Register → Value driver ownership**. Seed values are proposals and need validation by each function head.
- **Enterprise Risk Register → Value coverage** shows, per driver, linked processes and risks across all registers and flags gaps
  (no accountable function, no processes, no risks).
- Each unit's **00 Context** page shows the drivers that function is accountable for and contributes to.
  Crewing and Onshore Employees map to HR; Administration and ICT map to Administration & ICT; Chile and Shetland are
  geographies that contribute to the functions' drivers.
- Key-person risk (SBD-R119) moved from 3.3.8 to 3.3.9.

### Scope rule for risk tags

A register's risks may only be tagged to Level 3 drivers in that function's scope (accountable or contributing).
Drivers that belong to another function are recorded in the risk's **Handed-over drivers** column, and risks with no
in-scope driver are moved to the accountable function's register. The Risk register tab warns about out-of-scope tags,
and the Risk library shows only the function's drivers by default.

Strategy & BD retag (Nov 2026): 35 risks kept and trimmed to the 16 S&BD drivers; SBD-R122, R124, R125, R127, R137, R138
moved to Finance and SBD-R102, R135 to Vessel Operations (marked "Transferred from"). Backup:
`data/strategy_risks_backup_before_scope_retag.csv`.

## Risk library (pillar → Level 3 → risks)

On **03 Risks & Opportunities**, the **Risk library** tab mirrors all five pillars and every Level 3 driver from **3.1.1 through 3.5.7**. Risks link via the optional **Level 3 drivers** field. Empty slots highlight coverage gaps; draft risks can be created into a chosen slot.

## Included

- Inherent, residual and target 5×5 heatmaps
- Shareholder-value hierarchy based on EBITDA, EV/EBITDA multiple and NIBD
- Five value pillars with the full Level 3 driver tree
- Fleet quality and residual value protection under Multiple Expansion
- CEO sponsorship separated from accountable functional executives
- Sequenced unit ERM and ISO workflow (pages 00–14)
- Controls, actions, appetite and Enterprise escalation
- Cross-functional dependencies and opportunity register
- Preliminary ISO alignment matrix and Excel export (unit sheets + Enterprise + ERM Structure)
- Twelve unit registers and one Enterprise roll-up

Starter entries are illustrative and require management validation. This is a single-user prototype; authentication, permissions, database storage, formal audit trails and controlled documents belong in later versions.

Neutral risk IDs (27 Nov 2026): all 53 risks renumbered from department prefixes (SBD-R…, LEG-R…) to Trident-wide
IDs TRI-R001–TRI-R053, ordered by pillar and Level III driver. Risks belong to Trident; departments own processes.
Old → new mapping: `data/risk_id_map.csv`. Process, control and action IDs keep their department prefixes.
