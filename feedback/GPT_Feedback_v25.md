# Moon Mission Simulation – Detailed Action Plan **(Rev. 2025‑06‑28 b)**

> **Purpose**  
> Incorporate the second‑opinion review (high‑fidelity atmosphere, constants consolidation, guidance modularisation) without bloating the roadmap.  
> New tasks are **highlighted in blue** and appended to the relevant step so the ownership structure remains unchanged.

---

## Changelog vs. Rev. a  

| Area | Change | Impact |
|------|--------|--------|
| Atmospheric Model | **Added Task 2‑6** – integrate NRLMSISE‑00 density model | Higher fidelity drag / Max‑Q |
| Guidance Architecture | **Added Task 3‑6** – Strategy‑pattern refactor of guidance logic | Cleaner fault handling & extendibility |
| Physical Constants | **Added Task 5‑6** – centralise constants in `constants.py` & enforce via CI | Eliminate drift / magic numbers |

All other tasks are **unchanged**.

---

## 1 Integrated Monte Carlo Campaign (E2E)

*No changes – see Rev. a tasks 1‑1 … 1‑5.*

---

## 2 Altitude‑Dependent Thrust & Atmosphere Model

> **Objective (updated)**  
> *Model engine thrust and atmospheric density consistently from 0 – 150 km.*

### Existing Tasks 2‑1 … 2‑5 (unchanged)

### **New Task** <span style="color:#1E90FF">2‑6 Integrate NRLMSISE‑00 Density</span>

| ID | Action | Artifact | Success Factor |
|----|--------|----------|----------------|
| 2‑6‑1 | Vendor & containerise `pymsis` fork (license OK) | Dockerfile + SBOM | Image vulnerability scan 0 critical |
| 2‑6‑2 | Wrap API `atmos.get_density(alt,lat,lon,utc)` | `atmosphere.py` | Unit test delta ρ ≤ 0.5 % vs. NASA ref |
| 2‑6‑3 | Replace legacy ISA call‑site in `aero.py` | Patch diff | All tests pass; runtime +≤ 5 % |
| 2‑6‑4 | Re‑run static‑climb sim; plot ρ & q_dyn | `atm_validation.md` + PNG | Max‑Q shift ≤ 2 km vs. Apollo 11 |

---

## 3 Layered Abort Framework & Guidance Modularisation

### Existing Tasks 3‑1 … 3‑5 (unchanged)

### **New Task** <span style="color:#1E90FF">3‑6 Strategy‑Pattern Guidance Refactor</span>

| ID | Action | Artifact | Success Factor |
|----|--------|----------|----------------|
| 3‑6‑1 | Draft UML: `GuidanceContext` + `IGuidanceStrategy` | `guidance_arch.md` | Reviewed by GNC & SW Leads |
| 3‑6‑2 | Implement concrete strategies: `GravityTurn`, `Coast`, `TLI`, `LOI`, `PDI` | `guidance/*.py` | Smoke sim completes w/o exceptions |
| 3‑6‑3 | Inject via `GuidanceFactory` (Cfg‑driven) | Factory module | Strategy switch latency ≤ 50 ms |
| 3‑6‑4 | Add PyTest for strategy coverage ≥ 90 % | Coverage report | CI gate enforces coverage |

---

## 4 Flight‑Data Validation vs. Apollo 11

*Unchanged.*

---

## 5 Mission Readiness Review (MRR) Package

### Existing Tasks 5‑1 … 5‑5 (unchanged)

### **New Task** <span style="color:#1E90FF">5‑6 Centralise Physical Constants</span>

| ID | Action | Artifact | Success Factor |
|----|--------|----------|----------------|
| 5‑6‑1 | Create `constants.py` (G, R_earth, μ_earth, etc.) | Module + docstring | Peer‑review sign‑off |
| 5‑6‑2 | Replace hard‑coded literals project‑wide via script | Patch diff | `git grep` shows 0 magic numbers |
| 5‑6‑3 | Add flake8 rule `NO_CONST_LITERALS` | `.flake8` config | CI fails if new literal found |
| 5‑6‑4 | Document constants in `SRS.md` | Updated spec | Traceability matrix complete |

---

## Updated Timeline & Ownership

| Step | Lead | Start | Finish | Notes |
|------|------|-------|--------|-------|
| 1 | Simulation | 2025‑07‑01 | 2025‑07‑10 | unchanged |
| 2 | Propulsion | 2025‑07‑05 | **2025‑07‑14** | +2 days for NRLMSISE |
| 3 | GNC | 2025‑07‑08 | **2025‑07‑20** | +2 days for refactor |
| 4 | Data Sci | 2025‑07‑11 | 2025‑07‑20 | unchanged |
| 5 | PMO | 2025‑07‑15 | **2025‑07‑24** | +2 days constant work |

> **Critical Path remains**: 1 → 4 → 5 (Step 2/3 slack absorbed)

---

## Procedure Clarification

1. **Branching Model**:  
   * Create feature branches `feat/step2_atmos`, `feat/step3_guidance_refactor`, `feat/step5_constants`.  
   * Merge via PR once *all* SF metrics in task tables turn **green**.

2. **CI Gates**:  
   * Lint → Unit Tests → Coverage → Integration Tests → Static Analysis → Artifact Publish.

3. **Weekly Sync** (every Tue 10:00 JST):  
   * Owner demo task progress *live* against SF checklist.

4. **Definition of Done**:  
   * Task artifacts committed, CI green, section in relevant Markdown report updated.

---

## Acceptance Criteria (unchanged)

* End‑to‑End Success Rate ≥ 90 %  
* 95 % CI Width ≤ 3 %  
* Engine Curve MAE ≤ 2 %  
* RMSE vs. AS‑506 ≤ 5 % each KPI  
* All Abort Modes pass fault‑injection tests  
* MRR Bundle uploaded & approved  

---

*Prepared by:* *Mission Analysis Lead* *Date:* 2025‑06‑28  
