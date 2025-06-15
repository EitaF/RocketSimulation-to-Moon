Below is a concise, engineer-friendly requirements specification in English. It highlights the design changes and code fixes needed to turn the simulation from “immediate crash” into a successful Earth-to-Moon flight and landing.

---

## 1. Overview

* **Goal**: Refactor the Python rocket simulation so that it reliably reaches low Earth orbit (LEO), performs a Trans-Lunar Injection (TLI), and executes a controlled lunar landing instead of crashing immediately.
* **Context**: The current code mismanages mission phases, never ignites the third stage, under-models atmospheric drag, and uses an overly aggressive gravity-turn profile.

## 2. Key Problems to Fix

1. **Stage-separation logic**

   * Third stage (S-IVB) drops straight into `COAST` phase, so it never reignites and the vehicle re-enters immediately.
2. **Mission-phase update timing**

   * Phases are updated only after integration steps, causing the first thrust to be skipped.
3. **Δv (delta-V) budgeting**

   * Fuel masses and burn times are inconsistent; theoretical Δv is mis-allocated.
4. **Gravity-turn (pitch-over) schedule**

   * Pitch angles ramp too quickly at low altitude, limiting apoapsis height.
5. **Atmosphere & drag model**

   * Uses a fixed cross-sectional area and treats >150 km as perfect vacuum, ignoring thin upper atmosphere.
6. **TLI trigger**

   * Fires after a fixed coast time rather than confirming parking orbit and available Δv for TLI.

## 3. Functional Requirements

### 3.1 Mission Phase Management

* **Always** call `update_phase(t)` at the very start of each simulation loop, **before** any position/velocity integration.
* Initialize `rocket.phase = MissionPhase.LAUNCH` at t = 0.

### 3.2 Stage-Separation & Ignition Logic

* After each `STAGE_SEPARATION`:

  * If entering third stage (index 2), transition to `APOAPSIS_RAISE` rather than `COAST`.
  * Only enter `COAST` if (a) circular parking orbit achieved (e.g., apoapsis & periapsis ≥185 × 185 km) **and** (b) remaining Δv is reserved for TLI.

### 3.3 Δv Calculation & Validation

* Compute Δv per stage using:

  $$
    \Delta v = I_{sp}\,g_0\,\ln\bigl(m_0/m_f\bigr)
  $$
* At stage-ignition and stage-cutoff, log actual Δv achieved and compare against theoretical budget.
* Validate that cumulative Δv ≥ 9.4 km/s before coasting for parking orbit, and ≥ 11 km/s before TLI.

### 3.4 Gravity-Turn Profile

* Define a pitch-over schedule as a function of **both** altitude and velocity:

  * 0–10 km → near-vertical (> 85°)
  * 10–40 km → gradually pitch from 85° to 45°
  * 40–80 km → hold \~45° until orbital velocity (\~7.8 km/s) reached
  * > 7.8 km/s → transition to horizontal (90°)
* Allow easy adjustment of breakpoints via configuration.

### 3.5 Atmosphere & Drag Model

* **Altitude bands**:

  1. 0–100 km: International Standard Atmosphere.
  2. 100–150 km: Exponential or linear decay to near-vacuum.
  3. > 150 km: Residual density \~1 × 10⁻⁶ kg/m³ for stability.
* Use per-stage `cross_sectional_area` (e.g. 80 m² → 30 m² → 18 m²) read from config.
* Compute drag $D = \tfrac12 \rho v^2 C_d A$ with altitude-dependent density ρ.

### 3.6 Trans-Lunar Injection (TLI) Logic

* Only trigger TLI burn when:

  1. Parking orbit is circularized (periapsis ≈ apoapsis ≥185 km).
  2. Remaining Δv ≥ required TLI Δv (calculate via patched-conic approximation).
* Compute TLI Δv from:

  $$
    v_{\text{TLI}} \approx \sqrt{GM\!\Bigl(\tfrac{2}{r_p}-\tfrac{1}{a}\Bigr)}
  $$

  where $a=(r_p+r_{\rm moon})/2$.

### 3.7 Configuration File

* Load all numeric parameters from an external JSON or TOML file:

  ```jsonc
  {
    "stages": [
      {"m0": 3.0185e6, "mf": 8.685e5, "Isp_vac": 263, "Isp_sl": 220, "thrust_vac": 3.44e7, "thrust_sl": 2.5e7, "burn_time": 162, "area": 80},
      { /* stage 2 */ },
      { /* stage 3 */ }
    ],
    "gravity_turn": [{"alt":0,"pitch":90}, … ],
    "simulation": {"dt":0.1,"max_time":20000}
  }
  ```
* Perform schema validation on load; reject negative or missing values.

### 3.8 Logging & Visualization

* Write a CSV log with columns: `time, altitude, velocity, mass, phase, Δv_stage, cumulative_Δv`.
* Provide utility functions (e.g. `plot_trajectory()`) that read the log and plot altitude/velocity/Δv vs. time.

## 4. Non-Functional Requirements

* **Performance**: 100 s of simulated flight must complete in <1 s real time.
* **Maintainability**: Modularize into clear submodules (e.g. `physics.py`, `mission.py`, `config.py`).
* **Testability**: Achieve ≥ 80% unit-test coverage. Include tests for:

  * Phase transitions
  * Δv calculations
  * Gravity-turn interpolation
  * Atmosphere density function
* **Documentation**: Each module and public function must have a docstring. Provide a top-level README with setup, config examples, and run instructions.

## 5. Deliverables

1. Refactored Python code with the above changes.
2. Sample configuration file (JSON/TOML).
3. Unit-test suite.
4. Generated sample CSV and corresponding plots (PNG).
5. Updated README and API reference.

---

Please use this specification to guide your code redesign and ensure the simulation meets all functional and performance goals. Let me know if you need any clarifications!
