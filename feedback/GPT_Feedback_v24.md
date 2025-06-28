# Moon Mission Simulation – Detailed Action Plan (Rev. 2025‑06‑28)

## Purpose  
This document expands the previously agreed **5‑Step Roadmap** into concrete engineering actions, ready for direct assignment in Jira.  
All tasks include output artifacts and measurable *Success Factors* (SF).

---

## 1. Integrated Monte Carlo Campaign (E2E)

### Objectives
* Quantify end‑to‑end (LEO→Landing) success probability **≥ 90 %**  
* Achieve 95 % confidence‑interval width (CI) **≤ 3 %**

### Detailed Actions
| ID | Action | Artifact | SF |
|----|--------|----------|----|
| 1‑1 | Draft `mc_config.json` with distributions for: launch azimuth ±0.25°, pitch timing ±0.5 s, stage ΔV ±2 %, sensor noise per spec | JSON schema & sample | Validates via CI lint job |
| 1‑2 | Refactor `sim_orchestrator.py` to ingest config and spawn container jobs (`--batch 0‑999`) | Updated Python module | 1000 sim run < 2 h on CI |
| 1‑3 | Create Jenkins pipeline **MC_E2E** (K8s batch namespace) | `Jenkinsfile` | Pipeline passes first try |
| 1‑4 | Implement `metrics_logger.py` → CSV (`run_ID_metrics.csv`) incl. landing lat/lon, v_final, prop_margin | Python module + sample CSV | Missing data ≤ 0.1 % |
| 1‑5 | Build `analyze_mc.py` to aggregate results, compute success rate & CI, output `montecarlo_summary.md` | Markdown report | SF hit when ≥90 % & ≤3 % |

---

## 2. Altitude‑Dependent Thrust Model

### Objectives
* Replace constant‑thrust simplification with altitude‑aware engine curves  
* Match reference static‑fire data **±2 %**

### Detailed Actions
| ID | Action | Artifact | SF |
|----|--------|----------|----|
| 2‑1 | Extract sea‑level & vacuum *Isp* from datasheet; derive thrust vs. altitude points every 1 km | `engine_curve_raw.csv` | Data reviewed by Propulsion |
| 2‑2 | Encode curve as `engine_curve.json` (altitude[m]→thrust[N]) | JSON file | JSON schema validated |
| 2‑3 | Extend `engine.py::get_thrust(alt,throttle)` to interpolate via Cubic‑Spline | Updated module + unit tests | Unit tests all pass |
| 2‑4 | Add regression test comparing model output to reference curve | `test_engine_curve.py` | MAE ≤ 2 % |
| 2‑5 | Run static‑climb sim (0‑150 km) & plot thrust, ΔV | `static_climb_report.md` + PNG | Curve smooth, no spikes |

---

## 3. Layered Abort Framework (AM‑I – AM‑IV)

### Objectives
* Provide deterministic fault‑tolerant paths for major failure modes  
* Verify all abort modes trigger & recover in SIL tests

### Detailed Actions
| ID | Action | Artifact | SF |
|----|--------|----------|----|
| 3‑1 | Define abort logic table (trigger, response, safe‑state) | `abort_matrix.xlsx` | Signed‑off by Systems |
| 3‑2 | Implement `fault_detector.py` (thrust deficit, attitude dev > 5°, sensor dropout > 1 s) | Python module | 95 % fault detection in tests |
| 3‑3 | Code state‑machine `abort_manager.py` switching GNC profiles | Module + UML diagram | UML ↔ code parity check |
| 3‑4 | Add safe‑hold attitude controller (`safe_hold.py`) | Controller module | Rate damped in < 60 s |
| 3‑5 | Create `test_abort_modes.py` injecting synthetic faults | PyTest suite | All four modes pass |

---

## 4. Flight‑Data Validation vs. Apollo 11 (AS‑506)

### Objectives
* Align sim telemetry with historical flight **±5 % RMSE**

### Detailed Actions
| ID | Action | Artifact | SF |
|----|--------|----------|----|
| 4‑1 | Acquire digitized AS‑506 telemetry CSV | `AS506_telemetry.csv` | File checksum logged |
| 4‑2 | Build alignment script `align_telemetry.py` (time‑shift, resample 10 Hz) | Python script | Alignment error < 0.2 s |
| 4‑3 | Define KPI list: dynamic pressure, pitch, roll, yaw, ΔV, altitude | `kpi_definition.md` | Reviewed by GNC |
| 4‑4 | Compute RMSE & %error, output `validation_report.md` | Report + plots | RMSE ≤ 5 % each KPI |
| 4‑5 | Calibrate model coefficients (aero drag, Isp) to meet target | Patch diff + note | Validation report re‑pass |

---

## 5. Mission Readiness Review (MRR) Package

### Objectives
* Deliver a self‑contained evidence bundle for professor sign‑off

### Detailed Actions
| ID | Action | Artifact | SF |
|----|--------|----------|----|
| 5‑1 | Tag codebase `v1.0‑MRR` & export git diff vs `v0.9` | `code_diff.html` | Diff builds w/o errors |
| 5‑2 | Collate MC campaign & validation reports into `MRR_Report.pdf` | Compiled PDF | All figures legible |
| 5‑3 | Update risk register (`risk_log.xlsx`) & RPN trends | Excel file | No critical risk unowned |
| 5‑4 | Prepare 15‑slide deck (`MRR_Slides.pptx`) | PowerPoint | Dry‑run ≤ 20 min |
| 5‑5 | Upload all artifacts to Confluence page *Mission > MRR*; mention @Professor | Confluence link | Page passes QA checklist |

---

## Timeline & Ownership (Target Dates)

| Step | Lead | Start | Finish |
|------|------|-------|--------|
| 1 | Simulation | 2025‑07‑01 | 2025‑07‑10 |
| 2 | Propulsion | 2025‑07‑05 | 2025‑07‑12 |
| 3 | GNC | 2025‑07‑08 | 2025‑07‑18 |
| 4 | Data Sci | 2025‑07‑11 | 2025‑07‑20 |
| 5 | PMO | 2025‑07‑15 | 2025‑07‑22 |

*Critical Path*: Steps **1 → 4 → 5**

---

## Acceptance Criteria Summary

* **End‑to‑End Success Rate** ≥ 90 %  
* **95 % CI Width** ≤ 3 %  
* **Engine Curve MAE** ≤ 2 %  
* **RMSE vs. AS‑506** ≤ 5 % each KPI  
* **All Abort Modes** pass fault‑injection tests  
* **MRR Bundle** uploaded & approved

---

*Prepared by:* _Mission Analysis Lead_  
*Date:* 2025‑06‑28
