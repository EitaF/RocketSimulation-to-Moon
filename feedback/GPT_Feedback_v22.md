# Design Change Rationale & Action Plan – Stable LEO Insertion

## 1. Executive Summary
Our software and avionics stack is feature‑complete, but flight tests show the vehicle delivers only **~3.1 km/s** of ΔV versus the **9.3 km/s** required for Low‑Earth Orbit. The remaining gap is purely physical—mass, propellant volume, and thrust—not software. The following document explains why design changes are unavoidable and details the engineering tasks needed to close the performance gap.

## 2. Functional Successes to Date
- Guidance, Navigation & Control (GNC) phases LAUNCH → CIRCULARIZATION execute without fault.
- Telemetry, fault‑handling, and staging logic have passed Monte‑Carlo robustness tests (500 runs, 100 % phase‑transition success).
- All known software bugs from Professor Feedback v21 (A1–A3) are fixed.

## 3. Why Vehicle Design Must Change
| Metric | Target for LEO | Current Best | Shortfall | Root Cause |
|--------|---------------|--------------|-----------|-----------|
| Total ΔV (incl. losses) | ≥ 9.3 km/s | 3.1 km/s | −6.2 km/s | Propellant mass & stage architecture |
| Max horizontal speed | 7.8 km/s | 3.05 km/s | −4.75 km/s | Gravity turn too vertical + ΔV deficit |
| Apoapsis altitude | ≥ 185 km | 50 km | −135 km | Same as above |
| Periapsis altitude | ≥ 120 km | −6,020 km | N/A | Ballistic re‑entry |

*Even a perfectly tuned controller cannot compensate for a 2×–3× energy deficit.* See ΔV analysis below.

### Rocket Equation Insight
\[
\Delta v = I_{sp}\,g_0\,\ln\!\left(\dfrac{m_0}{m_f}\right)
\]

Given the current stage masses, even with ideal engines (I<sub>sp</sub> = 450 s) the mass ratio limits ΔV to ~7.3 km/s. Additional propellant and/or staging is mandatory.

## 4. Required Physical Modifications
1. **Increase Stage‑2 propellant** from 540 t to 900 t (structural mass ≤ 10 %).
2. **Add Stage‑3 (S‑IVB class)** delivering ≥ 2.8 km/s ΔV.
3. **Re‑tune gravity‑turn pitch schedule** to reach 6 km/s horizontal velocity @ 100 km.
4. **Re‑calibrate aero & mass models** to keep combined losses ≤ 8 %.

## 5. Engineering Task List

| ID | Task | Owner | Deliverable | Success Metric |
|----|------|-------|-------------|----------------|
| V‑1 | Boost Stage‑2 propellant mass | Propulsion | Updated mass/ΔV budget | Total ΔV ≥ 9.3 km/s |
| V‑2 | Optimize gravity‑turn profile | GNC | Pitch schedule curve & sim run | V<sub>horiz</sub> ≥ 6 km/s @ 100 km |
| V‑3 | Integrate Stage‑3 | Vehicle | Stage‑3 CAD, thrust table | Post‑burn apoapsis ≥ 185 km |
| V‑4 | Update aero & mass models | Aero | Rev‑C performance deck | Losses ≤ 8 % |
| V‑5 | Full‑stack Monte‑Carlo sim | GNC | 500‑case trajectory log | ≥ 95 % LEO success |

## 6. Acceptance Criteria
- **Periapsis ≥ 120 km** after circularization burn.
- **≥ 5 % residual propellant** for deorbit & contingency.
- ΔV margin documented ≥ 150 m/s.

## 7. Timeline
| Week | Milestone |
|------|-----------|
| +1 | V‑1 mass budget frozen |
| +2 | V‑2 pitch schedule validated |
| +3 | Stage‑3 PDR complete |
| +5 | Integrated aero/mass model release |
| +6 | Monte‑Carlo campaign finished |
| +7 | Mission Readiness Review |

---

*Prepared by: Professor X, Ph.D.*  
*Date: 25 Jun 2025*
