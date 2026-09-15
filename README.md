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
