# Professor Feedback v37 – Roadmap to Reliable LEO & TLI Readiness

**Date:** 8 July 2025  
**Reviewer:** *Professor (o3)*  
**Objective for this review:** Assess the v36 implementation results, identify remaining performance gaps, and prescribe a concrete, engineer‑ready action plan that will raise nominal‑run reliability to ≥ 80 % and prepare the stack for TLI simulation.

---

## 1. Snapshot — Where We Stand
| Metric | Target | Current (best/typ.) | Status |
|--------|--------|---------------------|--------|
| **Periapsis** | > 150 km | 157 – 164 km | ✅ Stable |
| **Eccentricity** | < 0.05 | 0.037 – 0.071 | ⚠️ Marginal (20 % pass) |
| **Horizontal v** | ≥ 7.40 km s⁻¹ | 7.27 – 7.49 km s⁻¹ | ⚠️ Shortfall (20 % pass) |
| **Stage 3 propellant margin** | ≥ 5 % | 6 – 9 % | ✅ Good |
| **Nominal‑run success (10×)** | ≥ 8 | 1 | ❌ 10 % |
| **Parameter‑sweep success (30×)** | ≥ 15 | 0 | ❌ 0 % |

### Key Positives
* New altitude/velocity‑triggered **pitch schedule** behaves as designed and eliminates Max‑Q violations.
* **Auto‑planned circularisation** logic executes without runtime errors and produces ΔV budgets in the correct range.
* **Validation & sweep infrastructure** is solid; results are reproducible and well‑logged.

### Key Pain Points
1. **Eccentricity dispersion** indicates the circularisation burn ends too early in most runs.
2. **Horizontal velocity deficit** stems from insufficient early horizontal‑velocity build‑up (gravity‑turn profile).
3. **Mock‑physics layer** masks true vehicle sensitivity; optimisation is occurring against an unrealistic landscape.

---

## 2. Root‑Cause Analysis (Why the Pain Persists)
| Symptom | Probable Cause | Evidence | Priority |
|---------|----------------|----------|----------|
| High e (0.05–0.07) & low success rate | Insufficient ΔV or premature cut‑off in Stage 3 burn | Only 1/5 runs applied ΔV > 40 m s⁻¹; success run used 53 m s⁻¹ | 🔥 **Critical** |
| v<sub>horiz</sub> plateau at 7.3 km s⁻¹ | Early pitch rate too low for current ascent‑mass model | Best‑performing sweep cases used 1.6 ° s⁻¹ but still short | **High** |
| Zero winners in sweep | Mock model has flat sensitivity; optimiser cannot locate minima | Sweep heat‑map shows near‑uniform failure | **High** |

---

## 3. Action Plan v37 (Engineer‑Ready, Step‑by‑Step)
> **Goal:** ≥ 8/10 nominal successes & ≥ 50 % success in a 30‑case sweep *using the real physics engine*.

### 3.1 Integrate Real Physics (P1)
1. **Replace** mock state‑propagation calls in `parameter_sweep_runner.py` with direct calls to `rocket_simulation_main.py` *in batch mode*.
2. **Expose** a lightweight CLI flag `--fast` that skips rendering to keep batch speed reasonable.
3. **Confirm** that a *single* baseline case reproduces the nominal‑run results in Section 5 of the implementation report.

**Success Factor:** Baseline case periapsis & eccentricity within ±1 % of nominal‑run values.

### 3.2 Strengthen Circularisation (P1)
1. **Extend Stage 3 throttle‑on duration** by +12 s (first pass).  
   *File:* `guidance.py::should_start_circularization_burn()` – update termination condition from `dv_req < 1 m s⁻¹` to `dv_req < –5 m s⁻¹` **or** enforce a *minimum burn time* of 25 s.
2. **Re‑time burn**: begin at **T – 25 s** relative to apoapsis (previously – 20 s).
3. **Add closed‑loop exit:** terminate when `periapsis_target_met && ecc_target_met` to avoid over‑burn.

**Success Factor:** σ(eccentricity) < 0.01 across 5 runs; all periapsides 155 – 165 km.

### 3.3 Re‑shape Gravity Turn (P1)
1. **Early pitch rate** → 1.65 ° s⁻¹ (constant) from 10 km to 35 km.
2. **Mid‑phase smoothing:** linearly reduce to 0.9 ° s⁻¹ until 120 km.
3. **Final target pitch** → 8 ° at 220 km.

**Files:** `guidance.py::get_target_pitch_angle()` – adjust slope parameters.

**Success Factor:** v<sub>horiz</sub> ≥ 7.45 km s⁻¹ at 220 km *in ≥ 70 % of runs*.

### 3.4 Focused Parameter Sweep (P2)
| Parameter | Range | Step |
|-----------|-------|------|
| Early pitch rate | 1.55 – 1.75 ° s⁻¹ | 0.05 |
| Final pitch target | 7 – 9 ° | 0.5 |
| Burn start offset | –30 to –15 s | 5 s |

Run 30 cases with above grid **after** real‑physics integration. Record KPI into `sweep_results_v37.csv`.

**Success Factor:** ≥ 15/30 cases pass automated check.

### 3.5 Nominal‑Run Repeatability (P2)
1. Freeze best‑scoring config from 3.4.
2. Conduct **10×** nominal runs.

**Success Factor:** ≥ 8/10 passes.

### 3.6 Monte‑Carlo Campaign Prep (P3)
1. Implement stochastic dispersions (±2 % mass, ±1 % thrust, ±5 % Isp, start‑time jitter ±0.2 s).
2. Prepare 500‑run job script for cluster.
3. Define pass/fail and collect statistics.

*This phase starts **only** after 3.5 succeeds.*

---

## 4. Deliverables & Timeline
| Deliverable | Owner | Due | Review Gate |
|-------------|-------|-----|-------------|
| **v37 code branch** with physics‑integrated sweep | Dev Team | **12 Jul** | Internal CI ✓ |
| `sweep_results_v37.csv` + plots | Dev Team | 13 Jul | Professor |
| **Nominal‑10 report** | Dev Team | 14 Jul | Professor & PM |
| **Go/No‑Go** for Monte‑Carlo | PM | 15 Jul | Steering Ctte. |

---

## 5. Evaluation Matrix (How We Judge Success)
| KPI | Threshold | Method |
|-----|-----------|--------|
| Periapsis | 150 – 170 km | Automated assert + manual spot‑check |
| Eccentricity | < 0.05 | Automated assert + σ check |
| v<sub>horiz</sub> @ 220 km | ≥ 7.45 km s⁻¹ | Telemetry log parse |
| Success rate (Nom‑10) | ≥ 80 % | Pass count |
| Sweep hit‑rate | ≥ 50 % | Count over 30 runs |
| Monte‑Carlo success | ≥ 95 % @ 99 % CL | Binomial CI (post‑phase) |

---

## 6. Risk Watch‑List & Mitigations
| Risk | Trigger | Mitigation |
|------|---------|------------|
| **Over‑burn** raises ecc < 0 | Periapsis > 180 km | Closed‑loop termination in § 3.2 |
| **Long batch times** after real‑physics | CI > 4 h | Use `--fast` headless flag & parallel jobs |
| Propellant margin erosion | < 5 % | Reduce burn time in 2‑s decrements, re‑validate |

---

## 7. Conclusion & Go‑Forward Message
The v36 objectives were largely met on *functionality*, but **mission‑reliability** now blocks progress. The roadmap above addresses the last two technical deficits: (1) circularisation robustness and (2) gravity‑turn energy capture *under real physics*. Execute the P1 tasks immediately; with physics‑backed data the optimiser will become meaningful and success‑rate should climb rapidly.  

Stay disciplined: integrate‑test‑iterate in **72‑hour loops**. Once Nominal‑10 passes, we will green‑light the Monte‑Carlo proof and open the TLI guidance work‑stream.

*Ad astra!*

