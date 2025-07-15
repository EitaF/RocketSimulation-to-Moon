# v32 Implementation Plan

**Objective:** Achieve an accurate, predictable, and correctable trajectory to the Moon.

This plan breaks down the four main action items from the Professor's v32 feedback into concrete engineering tasks.

---

### **Action Item 1: Implement Patched Conic Approximation Solver**

- **Objective:** Model the gravitational transition from an Earth-centric to a Moon-centric frame of reference.
- **Files to Create:**
    - `patched_conic_solver.py`: Will contain the core logic for Sphere of Influence (SOI) transition calculations.
    - `test_patched_conic_solver.py`: Unit tests for the solver.
- **Implementation Details:**
    1.  **`patched_conic_solver.py`:**
        - Define the Moon's Sphere of Influence (SOI) radius as a constant. `R_SOI_moon = 66,100 km`.
        - Implement a primary function `check_soi_transition(spacecraft_state, moon_state)` that returns `True` if the spacecraft is within the Moon's SOI.
        - Implement a function `convert_to_lunar_frame(spacecraft_state, moon_state)` that converts the spacecraft's state vector (position, velocity) from Earth-centric to a Moon-centric frame.
    2.  **`test_patched_conic_solver.py`:**
        - Write unit tests for both functions with known inputs to validate their correctness.
- **Integration:**
    - The main simulation loop in `rocket_simulation_main.py` must be modified to call `check_soi_transition` at each time step post-TLI. Upon transition, the physics model must switch to a Moon-centric gravitational model.

---

### **Action Item 2: Develop Optimal TLI Launch Window Calculator**

- **Objective:** Determine the correct time to start the TLI burn to ensure a lunar intercept.
- **Files to Create:**
    - `launch_window_calculator.py`: Contains the logic for calculating the TLI timing.
    - `test_launch_window_calculator.py`: Unit tests for the calculator.
- **Implementation Details:**
    1.  **`launch_window_calculator.py`:**
        - Implement a function to calculate the required phase angle between the spacecraft in its parking orbit and the Moon.
        - This will require calculating the estimated time-of-flight for the trans-lunar trajectory (a simplified Hohmann transfer calculation is a good starting point).
        - The final output should be the optimal time (or orbital position) to initiate the TLI burn.
    2.  **`test_launch_window_calculator.py`:**
        - Create a test with a known set of orbital parameters and verify the calculated burn time against a pre-calculated, correct value.

---

### **Action Item 3: Enhance Trajectory Visualizer**

- **Objective:** Visually confirm the lunar intercept trajectory.
- **Files to Modify:**
    - `trajectory_visualizer.py`
- **Implementation Details:**
    1.  Upgrade the visualizer to accept and plot multiple trajectories: the spacecraft and the Moon.
    2.  The plot must be in a shared, Earth-centric reference frame.
    3.  Clearly render the Earth, the Moon's orbit, the spacecraft's transfer orbit, and a circle representing the Moon's SOI at the intercept point.
- **Validation:**
    - The primary deliverable is a saved image file (`lunar_intercept_trajectory.png`) that is visually clear and accurate.

---

### **Action Item 4: Design Mid-Course Correction (MCC) Module**

- **Objective:** Create the capability to perform small, impulsive trajectory correction burns.
- **Files to Create:**
    - `mid_course_correction.py`: The module to define and execute burns.
    - `test_mid_course_correction.py`: Unit tests for the MCC module.
- **Implementation Details:**
    1.  **`mid_course_correction.py`:**
        - Create a function `execute_mcc_burn(spacecraft_state, delta_v_vector)` that applies an instantaneous change in velocity to the spacecraft.
    2.  **`test_mid_course_correction.py`:**
        - Write a test to confirm that the function correctly modifies the velocity vector of a given spacecraft state.
- **Integration:**
    - The main simulation loop must be adapted to allow for scheduling these burns at specific times during the trajectory.
