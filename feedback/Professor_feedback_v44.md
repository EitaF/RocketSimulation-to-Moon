
# Full Mission Simulation Integration – Engineer Action List

**Mission Scope:** Integrate the existing *launch-to-LEO* simulator (`rocket_simulation_main.py`) with the MVP *LEO‑to‑lunar‑landing* stack (`lunar_sim_main.py`, `unified_trajectory_system.py`, `engine.py`, etc.) to deliver a *single‑command* end‑to‑end simulation from lift‑off to soft landing on the Moon.

---

## 1. Deliverables

| ID | Artifact | Description |
|----|----------|-------------|
| D1 | **`full_mission_driver.py`** | Orchestrates launch → LEO hand‑shake → TLI → LOI → PDI → touchdown |
| D2 | **`leo_state.json` spec** | Standardised state vector hand‑over (UTC, r, v, mass, RAAN, ecc) |
| D3 | **Updated `engine.py` tables** | Thrust–Isp lookup tuned to preserve ≥ 3 % total ΔV margin |
| D4 | **`docs/full_mission_flow.md`** | Updated flow diagram + ΔV budget & success matrix |
| D5 | **CI Monte‑Carlo suite** | 100‑run Latin Hypercube with success ≥ 95 % |

---

## 2. Step‑by‑Step Action Plan

| # | Action | Owner | Acceptance Criteria |
|---|--------|-------|---------------------|
| **0** | **Branch Setup** – create `feature/full_mission` from current `main`. | DevOps | Branch pushed & CI green |
| **1** | **Refactor** `lunar_sim_main.py` → expose `run_from_leo_state(state_json)` (pure function). | Prop Team | Unit test passes: given demo `leo_state.json`, returns `Landing SUCCESS` |
| **2** | **Define Interface** – draft `leo_state.schema.json` (units: km, km/s, kg, rad). Validate with `pydantic`. | Guidance | Schema merged, CI validator green |
| **3** | **Emit LEO State** – modify `check_leo_success()` inside `rocket_simulation_main.py` to dump compliant `leo_state.json` on success. | Launch Team | File created with ecc < 0.01, h≈185 ± 5 km |
| **4** | **Build Orchestrator** `full_mission_driver.py`: ① call launch, ② load JSON, ③ call lunar run, ④ aggregate logs & exit code. | GNC Team | Single command `python full_mission_driver.py --montecarlo 1` runs complete mission |
| **5** | **ΔV / Mass Budget Audit** – cross‑check Stage‑3 residual fuel ≥ (ΔV_TLI+LOI+PDI) × 1.03. Adjust engine tables or tank size if violated. | Prop Team | Budget spreadsheet shows margin ≥ 3 % |
| **6** | **RAAN Alignment Test** – vary launch time ±5 min; ensure `launch_window_preprocessor.py` keeps ΔV_TLI penalty ≤ 50 m/s. | Guidance | Monte‑Carlo log average penalty ≤ 30 m/s |
| **7** | **Monte‑Carlo Suite** – LHS 100 runs (mass ±2 %, Isp ±1.5 %, nav error ±50 m). Expect ≥ 95 % landing success. | QA | CI job artifacts: success ≥ 95 % |
| **8** | **Performance Benchmark** – mission wall‑clock time < 10 min on `dev-station‑01` (AMD 7600). | Perf | Benchmark report in docs |
| **9** | **Documentation Update** – extend `MVP_summary.md` with new mission flow + diagrams. | Docs | PR approved |
| **10** | **Code Review & Merge** – run full test matrix; squash‑merge into `main`; tag `v1.0.0`. | All | Tag pushed; CHANGELOG updated |

---

## 3. Success Factors

| Metric | Target |
|--------|--------|
| End‑to‑end success rate | **≥ 95 %** across 100 Monte‑Carlo runs |
| Total ΔV margin | **≥ 3 %** after landing |
| RAAN alignment penalty | **≤ 50 m/s** (mean ≤ 30 m/s) |
| Execution time | **≤ 10 min** on dev hardware |
| Code Coverage | **≥ 85 %** lines, **≥ 80 %** branches |

---

## 4. Validation Methods

1. **Unit Tests** – pytest for each module with fixtures.
2. **Integration Test** – `full_mission_driver.py` returns exit code 0 & generates cumulative log.
3. **Continuous Integration** – GitHub Actions matrix (Python 3.10 / 3.11, Ubuntu & macOS).
4. **Monte‑Carlo CI Job** – nightly run; stores CSV of key metrics.
5. **Peer Review** – minimum 2 approving reviews before merge.

---

## 5. Timeline (Indicative)

| Day | Milestone |
|-----|-----------|
| D+0 | Branch setup, interface schema draft |
| D+2 | Refactor lunar module & JSON emission done |
| D+4 | Orchestrator operational (single run) |
| D+6 | ΔV budget tuning & RAAN test pass |
| D+8 | Monte‑Carlo 100 run ≥ 95 % |
| D+9 | Documentation & peer reviews done |
| D+10 | Merge & project close-out |

---

## 6. References

- `unified_trajectory_system.py` – Lambert + patch‑conic solver
- `rocket_simulation_main.py` – Launch & ascent
- `engine.py` – Thrust/Isp tables
- `launch_window_preprocessor.py` – RAAN alignment
- `MVP_summary.md` – Prior mission overview
