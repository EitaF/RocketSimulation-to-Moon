
# Implementation Review – v40

## 1. Summary  
- **A3 Launch Window Calculator** and **A4 Logging System** fully meet Prof v40 requirements.  
  - Wide test coverage, angular error < **1 °**  
  - Logging design supports future batch operations  
- **A1 TLI Simulation** stalls due to Stage‑3 fuel depletion; this bottleneck cascades into **A2** and **A5**.  
  - Current overall progress: **≈ 40 %**

---

## 2. Strengths
| Item | Reason | Notes |
|------|--------|-------|
| **Test design (A3)** | Edge‑case coverage, error < 1 ° | `pytest`‑based, maintainable |
| **Logging (A4)** | `--debug / --quiet` output control | Default run < 5 MB logs |
| **Module separation** | Clear responsibilities (`LaunchWindowCalculator`, `Mission`, …) | Easy CI/CD integration |

---

## 3. Major Blocker – A1

| Symptom | Observed | Hypotheses |
|---------|----------|------------|
| Stage‑3 fuel 100 % consumed → altitude ‑245 m, crash | *t* = 500–840 s during circularization | 1. Orbit‑error tolerance too tight → burn continues<br>2. Revised `mass_flow_rate` increases consumption<br>3. Guidance stop condition disabled (`Δv_remaining < ε`) |

---

## 4. Recommended Debug Steps

1. **Visualize fuel flow**  
   - Log `Stage3.mass_flow_rate` & remaining fuel every **0.1 s**  
   - Target: **≥ 5 %** fuel at circularization finish  

2. **Verify burn‐stop conditions**  
   - Inspect `guidance.py` lines 212‑235  
   - Ensure loop breaks when `Δv_error` & `periapsis_error` below thresholds  

3. **Diff vs v39**  
   - `git diff v39..v40 guidance.py mission_config.json`  
   - Identify unintended changes to propellant mass & target orbit  

4. **Local simulation slice**  
   - Reproduce **t = 480–900 s** only  
   - Compare time‑steps 0.05 / 0.1 / 0.5 s for numerical stability  

5. **Fail‑safe fuel limiter (temporary)**  
   ```python
   if stage3.fuel_fraction() <= 0.05:
       logger.warning("Fuel guard‑rail hit; forcing burn shutdown.")
       break
   ```  
   - Record residual orbit error; if < 1 km continue, else retune guidance  

**Success metrics**

```
fuel_remaining ≥ 5 %
apoapsis ≈ 185–195 km
periapsis ≥ 180 km
Δv_remaining error < 5 m/s
```

---

## 5. Next Milestones

| Phase | Completion Criteria | Target Date |
|-------|--------------------|-------------|
| **A1 fix** | Success metrics achieved, TLI burn ready | **2025‑07‑19** |
| **A2 Monte Carlo** | ≥ 90 % LEO→TLI success, stats report | **2025‑07‑26** |
| **A5 Param Sweep** | Top‑5 configs with Stage‑3 **≥ 35 %** fuel margin | **2025‑07‑31** |

---

## Engineer‑Facing Action Plan (English)

> **Goal:** Restore nominal Stage‑3 fuel margin during circularization and unblock TLI simulations.

1. **Instrument Stage‑3 burn**
   ```python
   logger.debug(
       f"{t:.1f}s | m_dot={stage3.mass_flow_rate:.3f} kg/s "
       f"fuel_left={stage3.fuel:.1f} kg "
       f"periapsis_err={periapsis_error:.1f} m"
   )
   ```

2. **Unit‑test burn termination**  
   - Simulate a 180 × 180 km target orbit with negligible attitude error.  
   - Assert burn stops when `|periapsis_error| < 500 m` **or** `fuel_remaining < 5 %`.

3. **Config diff audit**  
   - Compare **v39** ↔ **v40**: `SIVB_PROPELLANT_MASS`, `TARGET_PERIAPSIS`, `PEG_GAMMA_DAMPING`.  
   - Re‑apply any lost fuel‑saving heuristics.

4. **Minimal repro script** (`circularization_only.py`)  
   - Init orbit 180 × ‑5000 km; run Stage‑3 only.  
   - Sweep `dt`: 0.05 / 0.1 / 0.5 s, validate stability.

5. **Guard‑rail limiter (hot‑fix)**  
   ```python
   if stage3.fuel_fraction() <= 0.05:
       logger.warning("Fuel guard‑rail hit; forcing burn shutdown.")
       break
   ```
   - If residual periapsis error < 1 km, proceed to full mission run.

> **Success criteria:**  
> `fuel_remaining ≥ 5 %`, periapsis > 180 km, and mission proceeds to TLI without crash.

Once **A1** passes, launch the Monte Carlo batch with  
`python mission.py --fast --quiet`, then feed the resulting CSV into the parameter‑sweep dashboard.
