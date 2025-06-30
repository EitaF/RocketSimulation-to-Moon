### **Action Plan: Rocket Simulation System v2.1**

This document breaks down the feedback from `PROFESSOR_Feedback_v26.md` into specific, actionable items for the engineering team.

#### **1. Monte Carlo Campaign Resumption**

*   **Issue:** The Monte Carlo simulation framework cannot be resumed if interrupted. Long-running campaigns are vulnerable to being lost due to system restarts or accidental termination.
*   **Action Items:**
    1.  Modify the `MonteCarloOrchestrator` to periodically save its state to a file (e.g., `campaign_state.json`) within the output directory. This should happen every `N` runs (e.g., `N=10`).
    2.  The state file should contain the number of completed runs and the state of the NumPy random number generator (`np.random.get_state()`)
    3.  Add a `--resume` command-line argument to `monte_carlo_simulation.py`.
    4.  When `--resume` is used, the orchestrator should load the state file, restore the random number generator (`np.random.set_state()`), and continue the campaign from the last completed run.
*   **Success Factor:** A simulation campaign can be stopped and resumed without losing progress or compromising the statistical integrity of the results.
*   **Evaluation:**
    1.  Start a 1000-run campaign.
    2.  Terminate the process after approximately 100-150 runs have completed.
    3.  Execute the script again with the `--resume` flag.
    4.  **Verification:** The logs must show the campaign resuming from the correct run number. The final `run_metrics.csv` must contain exactly 1000 unique run IDs, and the summary report should reflect 1000 total runs.

#### **2. Engine Throttling Performance Model**

*   **Issue:** The engine model assumes Specific Impulse (Isp) is only a function of altitude. In reality, Isp also changes with the engine's throttle level. This inaccuracy affects the fidelity of landing simulations and other throttle-dependent maneuvers.
*   **Action Items:**
    1.  Update the `engine_curve.json` schema to support 2D data. For each engine stage, `isp_curve` should become a dictionary where keys are throttle levels (e.g., "1.0", "0.75") and values are the existing altitude-to-Isp mappings.
    2.  Modify `EnginePerformanceModel._build_interpolators` to create a 2D interpolator for Isp (e.g., using `scipy.interpolate.RectBivariateSpline`). This will take both altitude and throttle as inputs.
    3.  Update the `get_specific_impulse` method to accept a `throttle` argument and use the new 2D interpolator.
    4.  Add a new unit test to `test_engine_curve.py` to verify this functionality.
*   **Success Factor:** The simulation more accurately models real-world engine behavior by adjusting Isp based on the current throttle setting, leading to more precise propellant consumption calculations.
*   **Evaluation:**
    1.  The new unit test must call `get_specific_impulse()` at a fixed altitude with varying throttle levels (e.g., 1.0, 0.8, 0.6).
    2.  **Verification:** The test must assert that the returned Isp values are different for each throttle level and follow the expected trend (Isp generally decreases as throttle is reduced).

#### **3. Dependency Management**

*   **Issue:** The dependency on the `pymsis` library for the advanced atmospheric model is not explicitly defined, complicating the environment setup for new developers.
*   **Action Items:**
    1.  Create a `requirements.txt` file in the project's root directory.
    2.  Add `numpy`, `scipy`, and `pymsis` to this file. Also include optional dependencies like `matplotlib` and `pytest`.
    3.  Update the `README.md` file with a "Setup" section, instructing users to install all dependencies by running `pip install -r requirements.txt`.
    4.  Modify `atmosphere.py` to provide a more user-friendly error message upon an `ImportError`, guiding the user to run the installation command.
*   **Success Factor:** A new engineer can set up the complete project environment and run the simulation with a single, documented command.
*   **Evaluation:**
    1.  On a clean environment, clone the repository.
    2.  Run `pip install -r requirements.txt`.
    3.  Run `python monte_carlo_simulation.py --single-run 1`.
    4.  **Verification:** The simulation must run successfully, and the log must show that the "NRLMSISE-00 atmospheric model loaded successfully."

#### **4. "Stuck-At" Sensor Fault Detection**

*   **Issue:** The fault detection system can identify sensor dropouts but not a "stuck-at" failure, where a sensor continuously reports the exact same value.
*   **Action Items:**
    1.  In `fault_detector.py`, enhance the history-tracking mechanism to store the last `N` (e.g., `N=10`) raw values for critical sensors like altitude and velocity.
    2.  Implement a new private method, `_check_stuck_sensors()`, that is called from `update_telemetry()`.
    3.  This method will check if the last `N` values in a sensor's history are all identical.
    4.  If a stuck sensor is detected, it should generate a `FaultEvent` with a new `FaultType` (e.g., `STUCK_SENSOR`) and `FaultSeverity.MEDIUM`.
    5.  Add a unit test that simulates a stuck sensor and asserts that the fault is correctly detected after `N` identical updates.
*   **Success Factor:** The system's reliability is enhanced by detecting a critical and common sensor failure mode, preventing the guidance system from acting on stale data.
*   **Evaluation:**
    1.  The new unit test will call `update_telemetry()` `N` times. In each call, the telemetry data for one sensor (e.g., altitude) will be identical, while other data changes.
    2.  **Verification:** The test must assert that on the Nth call, a `FaultEvent` for a stuck sensor is returned.

#### **5. Advanced Guidance Implementation (Powered Explicit Guidance)**

*   **Issue:** The current `GravityTurnStrategy` is based on a pre-programmed pitch profile, which is not optimal for correcting deviations caused by real-world perturbations like engine underperformance.
*   **Action Items:**
    1.  Research the mathematical principles of Powered Explicit Guidance (PEG).
    2.  Implement a new guidance strategy class, `PEGStrategy(IGuidanceStrategy)`. This class will contain the core PEG algorithm, which calculates the ideal steering vector and engine cutoff time to achieve a target orbital state.
    3.  Integrate `PEGStrategy` into the `GuidanceContext`, to be used for the ascent phase, replacing the `GravityTurnStrategy`.
    4.  Create a new end-to-end simulation test that compares the final orbit achieved by PEG vs. the old strategy when an engine anomaly is injected.
*   **Success Factor:** The rocket achieves its target orbit with higher precision and uses propellant more efficiently, especially when compensating for off-nominal conditions.
*   **Evaluation:**
    1.  Run two simulations: (A) with the old strategy and (B) with the new `PEGStrategy`.
    2.  Both simulations will have a simulated 5% engine thrust deficit for 10 seconds during ascent.
    3.  **Verification:** Compare the final orbital parameters (apoapsis, periapsis) against the target. The orbit from the `PEGStrategy` run must be significantly closer to the target, and its final propellant margin should be higher than the run with the old strategy.