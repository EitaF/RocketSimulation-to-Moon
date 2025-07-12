
# Lunar Landing Simulation – **MVP** Feedback  
“Done is better than perfect.” – **Mark Zuckerberg**

---

## 1. Mission Focus
- **Objective**: Deliver a **complete end‑to‑end simulation** (LEO → TLI → LOI → Descent → Lunar touchdown).  
- **Priority**: Finish a working baseline first; defer fine‑tuning and advanced features until *after* touchdown is reliably reproduced.

---

## 2. Scope & Success Criteria (MVP)
| Metric | Target (Nominal) |
|--------|------------------|
| Touchdown velocity | ≤ 2 m/s |
| Touchdown tilt | ≤ 5° |
| Baseline run completion | No runtime errors; generates full state logs |
| Monte Carlo validation | **100 Latin Hypercube runs** → Success ≥ 90 % |

*100 runs gives ±3 % (95 %CI) around 97 % success—but we accept ≥ 90 % for MVP.*

---

## 3. Deliverables
1. **`lunar_sim_main.py`** that reaches touchdown with the targets above.  
2. **Quick‑look plots** (`orbit_track.png`, `altitude_vs_time.png` – Matplotlib default OK).  
3. **`MVP_summary.md`** auto‑generated report (metrics table + log links).  

---

## 4. Task List – *Finish First*  
| # | Deadline (Δ from now) | Task | Owner | Done Criteria |
|---|---|---|---|---|
| 1 | **+3 days** | Integrate v42 guidance pipeline end‑to‑end; run nominal script (`run_nominal.sh`). | **GNC** | Script exits 0; touchdown meets velocity/tilt limits. |
| 2 | +5 days | Implement simple throttle schedule to shave excess ΔV in final 500 m. | Propulsion | ΔV margin ≥ 3 % after landing. |
| 3 | +5 days | **100‑run Latin Hypercube Monte Carlo** (CPU, 8‑thread). Capture failures & cluster causes. | GNC | Success ≥ 90 %; failure modes documented. |
| 4 | +6 days | Prepare quick‑look plots & auto‑report script. | DevOps | Artifacts generated in `/reports/MVP/`. |
| 5 | +7 days | **Submit `MVP_summary.md` + logs** to professor review. | All | Professor sign‑off. |

---

## 5. Out‑of‑Scope (Post‑MVP Backlog)
- GPU acceleration / sub‑5‑minute Monte Carlo  
- J2/J3・SRP高忠実度摂動  
- Closed‑loop EKF + LQR guidance  
- Deep‑space extensions (Mars, asteroid)  
- SaaS API & external user interface  

---

## 6. Guiding Principles
> 1. **Finish, then polish.**  
> 2. **Document known issues**—don’t block delivery.  
> 3. Prefer **simple, deterministic fixes** over complex optimal solutions at this stage.  

Let’s hit the touchdown marker first—refinement comes next.
