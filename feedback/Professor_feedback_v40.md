# Next-Phase Engineering Tasks – LEO ▶ TLI Capability (Professor v39 Follow-up)

## Objective
Demonstrate a full **LEO → TLI** mission with validated ΔV margins and >90 % reliability under Monte‑Carlo uncertainty.

---

## Task List

| ID | Description | Owner | Acceptance Criteria |
|----|-------------|-------|---------------------|
| **A1** | **Execute a 6 000 s simulation including the real S‑IVB TLI burn** using the new `_calculate_and_report_tli_requirements()` output to trigger `MissionPhase.TLI_BURN`. | Simulation Team | *C3 energy* > 0 km²/s² and spacecraft apogee ≈ 400 000 km with ≥ 5 % Stage‑3 propellant left. |
| **A2** | **Run a 100‑case Monte Carlo campaign** with `monte_carlo_config.yaml` (±5 % ρ, ±1 % Isp, IMU noise). Parallelize jobs via the `--fast` flag. | Simulation Team | ≥ 90 % of runs reach stable LEO and enter TLI with positive ΔV margin. |
| **A3** | **Unit‑test `launch_window_calculator`** to cover edge cases (phase angle 0‑180°). Provide pytest cases in `tests/test_launch_window.py`. | GNC Team | All tests pass; mean phase‑angle error < 1°. |
| **A4** | **Introduce logging level switch** (`--debug / --quiet`) and replace high‑frequency debug prints with `logger.debug`. | DevOps | Default run log size ≤ 5 MB; `--debug` restores full verbosity. |
| **A5** | **Re‑run the expanded parameter sweep** (`sweep_config.yaml`) after A1‑A4, identify top‑5 configurations with Stage‑3 fuel ≥ 35 %. | Analysis Team | Report delivered in CSV + summary dashboard. |

---

## Milestones & Timeline

| Milestone | Deadline |
|-----------|----------|
| A1 Completed & Mission Log Review | **2025‑07‑15** |
| A2 Monte‑Carlo Statistics Report | **2025‑07‑18** |
| A3 Unit Tests Merged to `main` | **2025‑07‑18** |
| A4 Logging Refactor in Release v40 | **2025‑07‑20** |
| A5 Parameter Sweep & Final TLI Config | **2025‑07‑22** |

---

## Success Metrics

1. **ΔV Margin:** ≥ 100 m/s average across Monte Carlo runs  
2. **Reliability:** ≥ 90 % LEO + TLI success rate  
3. **Fuel Economy:** Median Stage‑3 remaining propellant ≥ 35 %  
4. **Launch Window Error:** ‹ 1° phase‑angle deviation in unit tests  

*Let’s push to v40 and get that spacecraft on a lunar trajectory!* 🚀
