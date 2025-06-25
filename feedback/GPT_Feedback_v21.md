# Engineering Feedback & Action Plan: Achieving Stable LEO

To the Engineering Team,

First and foremost, excellent work on the simulation. Successfully implementing the multi-stage sequence for the Saturn V and significantly improving the total ΔV are major accomplishments. You have built a solid foundation.

I have reviewed the test report, simulation code, and external feedback. The final milestone—a stable Low Earth Orbit (LEO)—is now within reach. This document outlines the remaining gap, its root cause, and a concrete action plan to achieve mission success.

---

### 1. Current Gap to Milestone

The primary goal is a **stable circular orbit at ~185 km altitude (LEO)**. Here is a summary of the current gap between our target and the latest simulation results.

| Metric                  | Target Value          | Current Result          | Gap Analysis                                     |
| :---------------------- | :-------------------- | :---------------------- | :----------------------------------------------- |
| **Orbital Shape (Periapsis)** | **≥ 120 km** (Above atmosphere) | **-6,000 km** (Sub-orbital) | **Critical:** Trajectory impacts Earth.         |
| **Orbital Velocity (Horizontal)** | **~7,800 m/s**        | **~2,700 m/s**          | **~5,100 m/s short:** Insufficient speed for orbit. |
| **Final Mission Phase** | `LEO` or `LANDED`     | `failed`                | Fails during the circularization attempt.        |

**In short: The rocket reaches a sufficient altitude, but it lacks the critical horizontal velocity to stay in orbit. Instead, it follows a ballistic trajectory and re-enters the atmosphere.**

---

### 2. Root Cause Analysis

The fundamental problem is that **Stage-3's ΔV potential is not being used efficiently to gain orbital velocity.** This can be traced to three technical factors:

1.  **Improper Circularization Burn Termination Logic:**
    *   **Current State:** The `circularization` phase lacks a clear "success" condition. The code in `rocket_simulation_main.py` shows that this phase continues until the engine runs out of fuel (`not self.rocket.is_thrusting`), which immediately triggers a `failed` state.
    *   **The Problem:** There is no logic to check if the target orbit (i.e., a sufficiently high periapsis) has been achieved. The burn either continues wastefully past the target or, more likely, fails before the target is met.

2.  **Inefficient Circularization Burn Initiation Timing:**
    *   **Current State:** The transition from `COAST_TO_APOAPSIS` to `CIRCULARIZATION` is controlled by a complex set of conditions.
    *   **The Problem:** The most fuel-efficient moment to perform the circularization burn is **precisely at apoapsis**, where the flight path angle is zero. Burning at any other time directs thrust inefficiently toward changing altitude instead of maximizing horizontal speed to raise the periapsis.

3.  **Inefficient Thrust Vectoring During Circularization:**
    *   **Current State:** The pitch control logic in `guidance.py` is primarily designed for the initial gravity turn. There is no specialized guidance mode for the circularization burn.
    *   **The Problem:** A circularization burn is most efficient when conducted as a **"prograde" burn**, where the thrust vector is perfectly aligned with the velocity vector. The current guidance logic does not guarantee this, leading to energy loss.

---

### 3. Action Plan to Bridge the Gap

To resolve these issues, I propose the following three-step action plan.

| Action ID | Action Name                          | Objective                                                          |
| :-------- | :----------------------------------- | :----------------------------------------------------------------- |
| **A1**    | **Overhaul Circularization Control Logic** | Monitor periapsis altitude and terminate the burn upon success.      |
| **A2**    | **Refine Burn Initiation Timing**    | Initiate the circularization burn precisely at apoapsis (Flight Path Angle ≈ 0°). |
| **A3**    | **Implement Optimal Thrust Vectoring** | Ensure the thrust vector is always prograde during the circularization burn. |

---

### 4. Engineering Breakdown of Actions

Here are the specific, code-level instructions for implementing each action.

#### **Action A1: Overhaul Circularization Control Logic**
*   **File to Modify:** `rocket_simulation_main.py`
*   **Function to Modify:** `_update_mission_phase`
*   **Code Block to Target:** `elif current_phase == MissionPhase.CIRCULARIZATION:`

**Step-by-Step Instructions:**
1.  At the beginning of the block, get the current orbital elements, especially `periapsis`.
2.  Define a success condition: check if the periapsis is at a safe altitude (e.g., 120 km).
3.  Implement the new logic:
    *   **IF** the success condition is met, change the phase to `MissionPhase.LEO` and log a success message.
    *   **ELSE IF** the rocket runs out of fuel before success, change the phase to `MissionPhase.FAILED` and log a failure message.
    *   **ELSE**, continue the burn (i.e., do nothing and let the loop continue).

**Example Code Snippet:**
```python
# in rocket_simulation_main.py, _update_mission_phase function

elif current_phase == MissionPhase.CIRCULARIZATION:
    # 1. Get current orbital elements
    apoapsis, periapsis, eccentricity = self.rocket.get_orbital_elements()
    
    # 2. Define success condition: periapsis is above the atmosphere
    # Let's target 120km altitude for safety
    is_orbit_stable = periapsis >= (R_EARTH + 120e3) 

    # 3. Implement the new logic
    if is_orbit_stable:
        self.rocket.phase = MissionPhase.LEO
        self.logger.info(f"SUCCESS: LEO insertion complete. Achieved stable orbit.")
        self.logger.info(f" -> Apoapsis: {(apoapsis-R_EARTH)/1000:.1f} km, Periapsis: {(periapsis-R_EARTH)/1000:.1f} km")
    
    elif not self.rocket.is_thrusting:
        self.rocket.phase = MissionPhase.FAILED
        self.logger.error(f"FAILURE: Out of fuel during circularization burn.")
        self.logger.error(f" -> Final Periapsis: {(periapsis-R_EARTH)/1000:.1f} km (Target > 120 km)")

    # else: continue burning...
```

#### **Action A2: Refine Burn Initiation Timing**
*   **File to Modify:** `rocket_simulation_main.py`
*   **Function to Modify:** `_update_mission_phase`
*   **Code Block to Target:** `elif current_phase == MissionPhase.COAST_TO_APOAPSIS:`

**Step-by-Step Instructions:**
1.  Get the current Flight Path Angle.
2.  Make the primary trigger for the burn the moment the Flight Path Angle is nearly zero, which guarantees the burn starts at apoapsis.

**Example Code Snippet:**
```python
# in rocket_simulation_main.py, _update_mission_phase function

elif current_phase == MissionPhase.COAST_TO_APOAPSIS:
    flight_path_angle_deg = np.degrees(self.rocket.get_flight_path_angle())
    apoapsis, periapsis, _ = self.rocket.get_orbital_elements()

    # The most efficient time to burn is exactly at apoapsis,
    # where the flight path angle is zero.
    is_at_apoapsis = abs(flight_path_angle_deg) < 0.1  # Trigger within a tight 0.1-degree window

    # Ensure we have fuel for Stage-3 and the orbit is not already circular
    stage3_has_fuel = len(self.rocket.stages) > 2 and self.rocket.stages[2].propellant_mass > 0
    can_circularize = stage3_has_fuel and periapsis < (R_EARTH + 120e3)

    if is_at_apoapsis and can_circularize:
        self.rocket.phase = MissionPhase.CIRCULARIZATION
        self.logger.info(f"APOAPSIS PASS. Initiating circularization burn.")
        self.logger.info(f" -> Flight Path Angle: {flight_path_angle_deg:.3f} deg, Altitude: {self.rocket.get_altitude()/1000:.1f} km")
```

#### **Action A3: Implement Optimal Thrust Vectoring**
*   **File to Modify:** `guidance.py`
*   **Function to Modify:** `compute_thrust_direction`

**Step-by-Step Instructions:**
1.  At the start of the function, check the current mission phase.
2.  If the phase is `MissionPhase.CIRCULARIZATION`, set the thrust direction to be perfectly aligned with the current velocity vector (prograde).
3.  For all other phases, use the existing gravity turn logic.

**Example Code Snippet:**
```python
# in guidance.py

def compute_thrust_direction(rocket: 'Rocket', thrust_magnitude: float) -> 'Vector3':
    # ... import necessary modules ...

    # Action A3: Add dedicated logic for circularization phase
    if rocket.phase == MissionPhase.CIRCULARIZATION:
        # Thrust should be perfectly prograde (aligned with the velocity vector).
        # This maximizes the energy added to the orbit to raise the periapsis.
        if rocket.velocity.magnitude() > 0:
            thrust_direction = rocket.velocity.normalized()
            return thrust_direction * thrust_magnitude
        else:
            # Fallback for zero velocity case
            return Vector3(0, 0, 0)

    # --- Existing Guidance Logic for other phases ---
    altitude = rocket.get_altitude()
    velocity_mag = rocket.velocity.magnitude()

    # Get target pitch angle from the schedule
    pitch_angle_deg = get_target_pitch_angle(altitude, velocity_mag)
    # ... (rest of the existing code)
```

---

### 5. Success Factors for Each Action

| Action ID | Success Factor (Definition of Success)                                                                                                    |
| :-------- | :---------------------------------------------------------------------------------------------------------------------------------------- |
| **A1**    | - The `final_phase` becomes `leo`.<br>- The final **periapsis altitude is ≥ 120 km**.                                                         |
| **A2**    | - The `flight_path_angle` at the start of `CIRCULARIZATION` is **within ±0.5 degrees**.<br>- Fuel efficiency improves, leaving **>5% propellant margin** post-insertion. |
| **A3**    | - With the same mission profile, the vehicle **reaches the same orbit with less fuel** or **achieves a higher periapsis with the same fuel**. |

---

### 6. Evaluation Protocol

1.  **Single-Run Validation (Qualitative & Quantitative):**
    *   After implementing each action, run the simulation.
    *   **Check Console Logs:** Verify that the logs for `CIRCULARIZATION` start/end show the correct periapsis, flight path angle, and phase transitions.
    *   **Validate Result Files:** Open `mission_results.json` and check that `"final_phase": "leo"`. Open `mission_log.csv` and verify that the final row shows `periapsis` > 120km and `eccentricity` < 0.05.

2.  **Automated Regression Testing:**
    *   Create a simple Python evaluation script (e.g., `evaluate_mission.py`) to parse `mission_results.json` and `mission_log.csv` and automatically check the success factors.
    *   Integrate this script into a CI/CD pipeline to ensure future code changes do not degrade orbital insertion performance.

You have done fantastic work to get to this point. This is the most challenging and rewarding phase of ascent. I am confident that by implementing these targeted changes, you will successfully achieve LEO and be ready to proceed to Trans-Lunar Injection (TLI).

Good luck!