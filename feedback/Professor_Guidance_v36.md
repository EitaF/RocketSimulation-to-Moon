# Professor's Guidance v36 – Path to First Stable LEO

**Date:** 8 July 2025  
**Objective:** Achieve one complete nominal mission with a stable 160 × 160 km LEO (e < 0.05) using the current vehicle.

---

## 1. Verified Achievements  
| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| Max altitude | ≥ 250 km | 280 km | ✅ |
| Stage transitions | Smooth | Smooth | ✅ |
| Periapsis | > 150 km | **< 0 km** | ❌ |
| Eccentricity | < 0.05 | > 0.05 | ❌ |

*See `Professor_v35_Implementation_Report.md` for full logs.*

---

## 2. Root-Cause Recap  
1. **Velocity shortfall** of ~1.9 km/s at end-of-Stage 2 burn.  
2. Stage 3 propellant is available but not exploited for proper circularisation.  
3. Time-based pitch program produces sub-optimal gravity-turn profile when thrust levels change.

---

## 3. Action Plan (Step-by-Step)

| Step | Action | File / Function | Success Factor |
|------|--------|-----------------|----------------|
| 1 | **Refactor pitch schedule to altitude/velocity triggers** | `guidance.py::get_target_pitch_angle()` | Horizontal velocity ≥ 7.4 km/s by 220 km alt. |
| 2 | **Implement auto-planned circularisation burn** | New `guidance.py::plan_circularization_burn()` called upon `apoapsis_raise` → `circularize` transition | Periapsis > 150 km |
| 3 | **Parameter sweep tests**: <br>• Early pitch rate 1.3–1.7 °/s <br>• Final target pitch 8–12 ° <br>• Stage 3 ignition offset ±5 s | `sweep_config.yaml` + CLI loop | Identify config hitting both success factors |
| 4 | **Isolate variables** – run one change per test; log KPI (`apoapsis`, `periapsis`, `ecc`) to `sweep_results.csv` | `run_single_test.sh` | Clear correlation between parameter & outcome |
| 5 | **Freeze winning config** and perform **10× nominal runs** to confirm repeatability before Monte-Carlo | `rocket_simulation_main.py` | ≥ 8/10 runs stable LEO |

---

## 4. Code Snippet – Circularisation Helper

```python
def plan_circularization_burn(state):
    """Plan delta-V to raise periapsis at next apoapsis."""
    mu = state.mu_earth
    r_apo = state.r_apo
    v_apo_circ = (mu / r_apo) ** 0.5
    dv_req = v_apo_circ - state.v_apo
    return max(dv_req, 0.0)
```

Invoke this ~20 s before apoapsis; throttle Stage 3 until ΔV requirement ≈ 0.

---

## 5. Validation

1. **Automated check** in `post_flight_analysis.py`:

```python
assert periapsis_km > 150 and eccentricity < 0.05
```

2. Plot `velocity_vs_time.png` and `flight_path_angle.png` for manual sanity.  
3. Ensure Stage 3 has ≥ 5 % propellant at circularisation completion.

---

## 6. Contingency (if still sub-orbital)

| Symptom | Mitigation |
|---------|------------|
| Periapsis just below zero | Increase Stage 3 burn by +50 m/s |
| Eccentricity > 0.1 | Reduce early pitch rate by 0.1 °/s |
| Max-Q violation after pitch change | Delay initial pitch by +2 s |

---

## 7. Deliverables

- Updated `guidance.py`, `sweep_config.yaml`, `post_flight_analysis.py`  
- `sweep_results.csv` summarising 30 test runs  
- Short report confirming first stable LEO and propellant margin

---

*Once Step 5 confirms stability, we can proceed to the planned 500-run Monte Carlo to prove ≥ 95 % mission success with 99 % confidence.*

Good luck & keep the iterations tight!

— **Professor**
