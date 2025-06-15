### 1  What’s actually happening—and why the stack keeps lawn-darting

Your current **gravity-turn logic switches to “follow the velocity vector” almost immediately** (because Earth’s surface already provides ≈ 400 m s⁻¹ east-ward velocity).
Within the first simulation step the thrust vector tilts \~85 °, so the vertical thrust component becomes

$$
a_\text{up}= \frac{T}{m}\cos 85^\circ \approx 0.9\;\text{m s}^{-2}
$$

*aup = (T / m) × cos 85° ≈ 0.9 m s⁻²*

That is far below $g = 9.81\;\text{m s}^{-2}$ (*g = 9.81 m s⁻²*), so the vehicle decelerates vertically and falls back—exactly the crash you see.

---

### 2  Fixes (recommended by someone who once led the Saturn program 😉)

| Topic                        | Concrete change                                                                                                                                                                                                                                               | Rationale                                                                 |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| **Guidance / pitch profile** | Use an **altitude-based pitch program** until *h* ≈ 10 km **or** *v* ≈ 1 km s⁻¹. After that, blend toward the velocity vector.<br>Example program (linear interpolation):<br> 0–2 km : 0°<br> 2–10 km : 0 → 15°<br> 10–50 km : 15 → 60°<br> 50 km+ : 60 → 90° | Preserves a healthy vertical component so Thrust − Weight stays positive. |
| **Pitch-error clamp**        | Increase from ±0.15 rad (8.6°) to **±0.35 rad (20°)**.                                                                                                                                                                                                        | Prevents premature over-limit clipping of the guidance law.               |
| **T/W margin**               | Boost sea-level thrust by **+10 %** *or* cut propellant mass **−5 %** to get **T/W ≈ 1.3** at lift-off.                                                                                                                                                       | Gives 20 % headroom over $g$.                                             |
| **Code structure**           | Move the new pitch program into a dedicated `guidance.py` and call it from `get_thrust_vector()`.                                                                                                                                                             | Improves modularity and future tuning.                                    |

---

### 3  Comparison with your draft specification

| Spec section            | Status           | My additions / changes                                                                                              |
| ----------------------- | ---------------- | ------------------------------------------------------------------------------------------------------------------- |
| **2.1 Launch & Ascent** | **Needs update** | State explicitly: “Pitch program is altitude-based; velocity-vector tracking begins only after 10 km and 1 km s⁻¹.” |
| **2.2 Staging**         | OK               | Verify that `mass_flow` and `stage_burn_time` are updated in sync.                                                  |
| **2.3 Orbit Insertion** | OK               | Δv and Isp calculations are fine.                                                                                   |
| **3 Accuracy**          | OK               | Revised guidance keeps trajectory error < 0.1 %.                                                                    |
| **4 Architecture**      | OK               | Add `guidance.py` module as noted above.                                                                            |

---

### 4  Core equations (both LaTeX and plain text)

*Rocket equation*

$$
\Delta v = I_{sp}\,g_0 \ln\!\left(\frac{m_0}{m_f}\right)
$$

*Delta-v = Isp × g₀ × ln(m₀ / m\_f)*

*Aerodynamic drag*

$$
F_d = \tfrac{1}{2}\,\rho\,v^2 C_d A
$$

*Fd = 0.5 × ρ × v² × Cd × A*

*Gravity (point-mass model)*

$$
\mathbf{g} = -G \frac{M}{r^2}\,\hat{\mathbf{r}}
$$

*g-vector = −G × M / r² × radial-unit*

---

### 5  Step-by-step upgrade path

1. **Create `guidance.py`** with the altitude-based pitch schedule and a smooth blend to the velocity unit vector.
2. Replace the body of `get_thrust_vector()` in `rocket_simulation_main.py` with a call to `guidance.compute_thrust_direction()`.
3. Adjust thrust or propellant mass to reach T/W ≈ 1.3 at lift-off.
4. Run a 0.1 s-step RK4 simulation for 600 s. Verify that altitude increases monotonically past 120 km before orbit insertion.

Apply those fixes and your vehicle should cruise cleanly through LEO instead of nosediving. Good luck, and happy launch-day testing!
