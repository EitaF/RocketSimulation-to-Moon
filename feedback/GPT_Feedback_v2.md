Here’s the requirements definition for Claude in English—friendly and clear:

---

## 1. Purpose & Background

* **Purpose**: Adapt the existing Python simulation so that it accurately models a rocket launch from Earth and landing on the Moon when refactored in Claude.
* **Background**: The current implementation crashes immediately due to mission-phase timing issues, Δv (delta-V) shortfall, and an overly simplified atmosphere model.

## 2. Terminology

| Term         | Definition                                            |
| ------------ | ----------------------------------------------------- |
| Δv (delta-V) | Velocity change computed via the rocket equation      |
| $I_{sp}$     | Specific impulse (in seconds)                         |
| $g_0$        | Standard gravity acceleration (9.81 m/s²)             |
| RK4          | Fourth-order Runge–Kutta numerical integration method |

## 3. High-Level Requirements

1. **Mission Phase Management**

   * Always update the phase at the start of each loop iteration.
   * Initialize the simulation with phase set to `LAUNCH`.

2. **Numerical Integration Accuracy**

   * Support time step Δt ≤ 0.1 s.
   * Implement RK4 by copying the full state, computing intermediate steps, then applying a single state update.

3. **Externalized Rocket Parameters**

   * Load each stage’s $\{m_0, m_f, I_{sp}, F_{thrust}, t_{burn}\}$ from a JSON or TOML file.
   * Validate the config on load.

4. **Thrust & Specific Impulse Model**

   * Switch between sea-level and vacuum thrust values based on altitude.
   * Adjust $I_{sp}$ similarly with altitude.

5. **Atmosphere Model**

   * **0–100 km**: Approximate International Standard Atmosphere.
   * **100–150 km**: Thin atmosphere—use linear interpolation or exponential decay.
   * **>150 km**: Vacuum.

6. **Δv Calculation & Logging**

   * Compute $\Delta v$ at each stage ignition/extinguish event.
   * Log time, altitude, velocity, mass, and cumulative Δv to a CSV.

7. **Visualization API**

   * Provide functions to plot altitude, velocity, and Δv curves (e.g., via Matplotlib or Plotly).

## 4. Detailed Functional Requirements

### 4.1 Mission Phase Update

* **Requirement**: Call `update_mission_phase(t)` at the very start of the simulation loop.
* **Example**:

  ```python
  while t < total_duration and mission_ok:
      rocket.update_mission_phase(t)
      state = rocket.rk4_step(state, dt)
      t += dt
  ```

### 4.2 Rocket Equation (Δv Calculation)

* **Formula** (LaTeX):

  $$
    \Delta v = I_{\mathrm{sp}} \times g_0 \times \ln\frac{m_0}{m_f}
  $$
* **Formula** (text):
  Δv = I\_sp × g₀ × ln(m₀/m\_f)
* **Requirement**: Automatically compute and log Δv when each stage ignites or shuts down.

### 4.3 Atmosphere Model

* **Altitude Bands**:

  1. 0–100 km: ISA
  2. 100–150 km: thin atmosphere (linear or exponential decay)
  3. > 150 km: vacuum
* **Requirement**: Return air density and drag coefficient as functions of altitude.

### 4.4 Configuration File Schema

* **Format**: JSON example

  ```json
  {
    "stages": [
      {"m0": 3.0185e6, "mf": 8.685e5, "Isp": 263, "thrust": 3.44e7, "burn_time": 162},
      {"m0": 8.685e5, "mf": 3.885e5, "Isp": 421, "thrust": 4.11e6, "burn_time": 360},
      {"m0": 3.885e5, "mf": 2.285e5, "Isp": 421, "thrust": 1.03e6, "burn_time": 660}
    ],
    "simulation": {"dt": 0.1, "duration": 20000}
  }
  ```
* **Requirement**: Validate on load (e.g., check positive values, stage order).

## 5. Non-Functional Requirements

* **Extensibility**: Support an arbitrary number of stages.
* **Performance**: Complete a 100 s simulation in under 1 s.
* **Testing**: ≥ 80% unit-test coverage for core modules.
* **Documentation**: Docstrings for every function and a README with setup & run instructions.

## 6. Deliverables

1. Refactored Python code for Claude
2. Configuration file templates (JSON and TOML)
3. Unit-test suite
4. Markdown API reference & execution guide
5. Sample logs (CSV) and plots (PNG)

---

Let me know if you need any tweaks!
