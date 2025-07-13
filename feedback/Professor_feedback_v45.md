# 🌍🚀🌙 End-to-End Earth-to-Moon Simulation  
## System-Level Action Plan (Professor v45)

*Audience*: Software engineers with limited rocket-engineering background  
*Objective*: Repair the launch phase so the existing **LEO → Moon** chain runs **without demo fall-backs**, while preserving global ΔV and mass budgets.

---

### 0. Mission Architecture Recap
```
Launch → Gravity-turn ascent → Stage separations → LEO insertion → TLI → Coast/MCC → LOI → Powered descent → Lunar touchdown
```
State vectors (position `r`, velocity `v`, mass `m`, time `t`) travel unchanged between phase controllers.

---

### 1. Guiding Principles for *Global* Optimality
1. **Budget Consistency** – Phase ΔV + margins must sum to ≤ total capability (see §7).  
2. **State Continuity** – Each phase receives *physically coherent* `r,v,m,t`.  
3. **Energy Line-of-Sight** – Track progress with specific mechanical energy ε, not altitude alone.  
4. **Automation** – CI must nightly run ≥20 Monte-Carlo shots; success ≥95 %.

---

### 2. Root-Cause Map
| Symptom | Evidence | Root Cause |
|---|---|---|
| Pad-crash ≤15 s | γ swings to −1.6° immediately | Thrust-vector sign + wrong v₀ |
| `Mission.time` missing | Abort log | Guidance clock never added |
| Guidance fallback each frame | Catch-block in `get_thrust_vector` | Strategy ctx invalid at *t* = 0 |
| Atmospheric warning | ISA fallback | `pymsis` absent |

---

### 3. Action Plan (with calculations)

> **Notation**: \(g_0 = 9.80665\;\mathrm{m\,s^{-2}}\), \(R_E = 6.371 × 10^{6}\;\mathrm{m}\).

| ID | Action | Engineering Calculations | Success Metric |
|---|---|---|---|
| **A1** | **Coherent launch initial conditions**<br><br>```python<br>v_earth = ω × r_pad  # ≈ 407 m/s east<br>v0 = (0, 0, 0)       # inertial frame<br>``` | Convert LC-39A (lat 28.573° lon −80.649°) to ECI. | Log shows `v=0 m/s` at *t* = 0 (earth-rot removed later). |
| **A2** | **Add mission clock**<br>```python<br>class Mission:<br>    self.time = 0.0<br>    def step(self,dt):<br>        self.time += dt<br>``` | — | No more `AttributeError: time` and monotonic `t` in telemetry. |
| **A3** | **Rocket-API alignment**<br>\(\dot m = F/(I_{sp} g_0)\), \(t_{burn}=m_{\text{prop}}/ \dot m\).<br>Expose:<br>```python<br>stage_burn_time(i)<br>get_thrust_vector(t)<br>``` | Unit test: `|t_burn – cfg| < 0.5 s`. |
| **A4** | **Pitch & gravity-turn guidance**<br>\(\gamma(h)=90^\circ\!-\!(90^\circ\!-\!0^\circ)\frac{h-2}{65-2}\) for 2–65 km. | γ never < 0° before 20 s; apoapsis > 100 km before γ = 0°. |
| **A5** | **Thrust vector sign check**<br>\(a_z=(F\cos\gamma-D-mg)/m>4 \mathrm{m\,s^{-2}}\) for *t* < 10 s. | Integrator assertion passes; vertical accel positive. |
| **A6** | **Install pymsis** → density error < 2 % @ 50 km. | Warning disappears; density test passes. |
| **A7** | **Global ΔV & mass budget guard**<br>| Phase limits (m/s): Launch 9300, TLI 3150, LOI 850, Descent 1700. | Post-run assert `total_delta_v ≤ 15000 m/s`. |
| **A8** | **CI & Monte-Carlo**<br>GitHub Actions nightly cron:<br>```yaml<br>- run: python3 full_mission_driver.py --montecarlo 20<br>``` | Success ≥ 95 %; badge green. |

---

### 4. Verification Flow
1. **Unit tests** (A1–A3).  
2. **Nominal run** – check γ vs *h* plot.  
3. **Monte-Carlo 100** – dispersion of ε & landing metrics.  

---

### 5. Deliverables
- Updated code + unit-tests  
- `README_LAUNCH_GUIDANCE.md` with derivations  
- CI badge (launch + nightly campaign)  
- `ΔV_budget.xlsx` auto-filled from run outputs  

---

### 6. Timeline
| Date | Milestone |
|---|---|
| **Jul 15** | A1–A3 merged; unit tests green |
| **Jul 16** | First full-mission success (no fallback) |
| **Jul 17** | A4–A6 validated; ΔV within budget |
| **Jul 18** | Monte-Carlo 100 success ≥ 95 % |
| **Jul 20** | Docs & CI finalized |

---

*Executing the eight steps above restores a physically correct ascent while **leaving the validated LEO → Moon chain untouched**, achieving true system-level optimum rather than local patches.*
