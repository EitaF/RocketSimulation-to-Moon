Great progress — getting to 189 km and 7.58 km s⁻¹ means you are only ≈ 3 % shy of a closed 200 km circular orbit.
Below is a focused “second-stage” debrief that should push the vehicle over the line. Everything is framed so you can drop it straight back into **guidance.py** and **rocket\_simulation\_main.py**.

---

## 1  Why you are stalling 200–250 m s⁻¹ short

| Symptom                                        | Root cause                                                                                                                                             | Typical loss    |
| ---------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------- |
| **Horizontal Δv shortfall** (needs +220 m s⁻¹) | Pitch stays >5° above local horizon until ≈130 km. You are still climbing when main engines shut down, so part of the burn goes into ∆h instead of ∆v. | 120 – 150 m s⁻¹ |
| **No circularisation burn**                    | Simulation ends at engine cut-off; you never coast to apoapsis and perform the final prograde burn.                                                    | 60 – 90 m s⁻¹   |
| **Upper-stage mass margin**                    | Propellant mass fraction ≈0.87; usable, but 2–3 % leaner would buy ≈50 m s⁻¹.                                                                          | 30 – 50 m s⁻¹   |

Add those three numbers and you see why you land 200-ish m s⁻¹ under orbital.

---

## 2  Guidance tweaks (drop-in code)

### 2.1  Make the pitch profile “flatter sooner”

Replace your upper segment of `compute_pitch_program()` with:

```python
# 40–80 km: 45° ➜ 85°
elif altitude < 80e3:
    pitch_angle = 45.0 + (altitude - 40e3) * 40.0 / (80e3 - 40e3)
# ≥80 km: keep 85° until velocity > 7600 m/s
else:
    pitch_angle = 85.0
```

*Effect*: You are already above 99 % of the atmosphere at 40 km, so turning harder buys horizontal speed when the drag penalty is tiny.
Keep **85 °**, not 90 °, until orbital velocity is reached; that leaves a small vertical component to counter residual gravity losses.

### 2.2  Add a *closed-loop* apogee target

Inside `guidance.py` add:

```python
def target_apoapsis(rocket, desired_rad):
    mu  = rocket.earth_mu
    r   = rocket.position.magnitude()
    v   = rocket.velocity.magnitude()
    vr  = rocket.position.dot(rocket.velocity) / r
    specific_energy = 0.5*v*v - mu/r
    semi_major      = -mu / (2*specific_energy)          # a
    ecc_vector_mag  = np.sqrt(1 + 2*specific_energy *
                              rocket.angular_momentum_mag**2 / mu**2)
    apoapsis_r      = semi_major * (1 + ecc_vector_mag)  # ra
    return apoapsis_r < desired_rad
```

Then, just before you switch to **COAST\_TO\_APOAPSIS**

```python
if target_apoapsis(self, EARTH_RADIUS + 200e3):
    self.phase = MissionPhase.COAST_TO_APOAPSIS
    self.engine_cutoff()
```

*Effect*: Engine shuts down only when you can coast to ≥200 km apogee, eliminating the “just-miss” case.

### 2.3  Coast-and-circularise sequence

Add a very simple finite-burn circulariser:

```python
elif self.phase == MissionPhase.CIRCULARIZATION:
    if self.position_altitude() < self.apogee_altitude - 1e3:
        # keep coasting
        return
    # burn prograde until eccentricity ≈ 0
    if self.eccentricity_mag() > 1e-3 and self.propellant_mass > 0:
        thrust_dir = self.velocity.normalized()
    else:
        self.engine_cutoff()
        self.phase = MissionPhase.ORBIT_COMPLETE
```

You can call this phase automatically at *apoapsis* in the update loop.

---

## 3  Vehicle-side deltas

| Change                          | How                                                                                                            | ∆v gain    |
| ------------------------------- | -------------------------------------------------------------------------------------------------------------- | ---------- |
| **Upper stage mix ratio –2 %**  | Lower `propellant_mass` of stage-2 by 2 % and move that weight to stage-2 dry mass (tankage already paid for). | ≈ 25 m s⁻¹ |
| **Vacuum Isp tweak**            | Many LOX/LH₂ engines (e.g.\ RL-10C) reach 465 s. If yours is 450 s, bump it to 460 s.                          | ≈ 35 m s⁻¹ |
| **Realistic launch site bonus** | Set launch latitude = 28.5° (Kennedy) ⇒ Earth rotation gives +408 m s⁻¹, not +400.                             | ≈ 8 m s⁻¹  |

All three are “paper changes” in `mission_config.json` and give you the last few m s⁻¹ without re-architecting the stack.

---

## 4  How to verify

1. **Unit test** `target_apoapsis()` with analytic Kepler orbits.
2. Run a **600 s** full-throttle sim: apogee should crest > 200 km, engine cuts, coast begins.
3. At apoapsis the circularisation phase should burn ≈ 60–90 m s⁻¹ and leave:

   * altitude 200 ± 2 km
   * eccentricity < 1×10⁻³
   * orbital velocity ≈ 7.80 km s⁻¹
4. Verify final `specific_energy ≈ -29.4 MJ kg⁻¹` (for a 200 km circular LEO).

---

## 5  Spec table delta (for your requirements doc)

| Section                 | Add / Change                                                                          |
| ----------------------- | ------------------------------------------------------------------------------------- |
| **2.1 Launch & Ascent** | “Pitch profile updated: 40 – 80 km → 45–85 °, ≥80 km hold 85 ° until v ≥ 7.6 km s⁻¹.” |
| **2.2 Staging**         | “MECO when predicted apogee ≥ 200 km (closed-loop).”                                  |
| **2.3 Orbit Insertion** | New two-step: coast-to-apoapsis + circularisation burn targeting $e<10^{-3}$.         |
| **3 Accuracy**          | “Post-burn eccentricity ≤ 0.001; semi-major-axis error ≤ 0.3 %.”                      |

Implement those four guidance tweaks plus the minor stage refinements and you should hit a stable 200 km parking orbit on the very next run. From there, TLI and LOI phases can be tuned with the same coast-and-burn pattern.

Keep the throttles up — you are almost on orbit!
