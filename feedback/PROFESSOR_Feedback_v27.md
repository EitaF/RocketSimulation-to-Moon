
# Professor's Feedback & Next Steps: v27

**Project:** Earth-to-Moon Rocket Simulation System  
**Reviewer:** Professor E. Fukumoto  
**Date:** July 1, 2025  
**Focus:** Achieving First Major Milestone - Stable Low Earth Orbit (LEO)

---

## 1. Overall Assessment & Vision

The progress demonstrated in the v26 implementation is **outstanding**. The team has successfully built a robust simulation framework with professional-grade features like Monte Carlo analysis, high-fidelity engine modeling, and advanced fault detection. You have constructed a world-class launchpad.

Our **ultimate goal** remains a successful, high-fidelity simulation of a crewed or robotic landing on the Moon.

To achieve this, we must proceed in logical steps. The **first critical milestone** is to reliably achieve a stable, near-circular Low Earth Orbit (LEO). This is the foundational capability upon which all translunar operations are built.

This document outlines the key challenges and actionable steps required to meet this milestone.

---

## 2. Critical Challenges to Achieving LEO

While the current system is excellent, it is not yet equipped for the precision required for orbital insertion. Three critical challenges must be solved:

1.  **Guidance Precision:** The current `GravityTurnStrategy` is an "open-loop" system. It cannot react to real-world perturbations (e.g., engine underperformance, atmospheric variations) and will therefore consistently miss the narrow "keyhole" in space required for a stable orbit.
2.  **Orbital Insertion Mechanics:** A stable LEO is not achieved with a single, continuous burn. It requires a precise main engine cutoff (MECO) to establish an elliptical transfer orbit, followed by a coast phase and a final, timed "circularization burn" at the orbit's highest point (apoapsis). This logic is currently absent.
3.  **On-Board State Determination:** The simulated flight computer has no way of knowing its own orbital parameters in real-time. Without this, it cannot know when or how to perform the circularization burn, nor can it confirm if the mission milestone has been achieved.

---

## 3. Action Items for v27

The engineering team is directed to focus exclusively on the following three action items.

### **Action Item 1: Implement Powered Explicit Guidance (PEG)**

*   **Description:** Replace the open-loop `GravityTurnStrategy` with a closed-loop PEG system that actively steers the rocket to a precise target, correcting for real-time deviations.
*   **Engineer Actions:**
    1.  **Develop Core Algorithm:** In `peg.py`, implement the mathematical core of the PEG algorithm. This module must calculate the required velocity-to-be-gained (`V_go`) vector based on the vehicle's current state and a target orbital state. This should be unit-tested extensively for mathematical correctness.
    2.  **Integrate as a Strategy:** Create a new `PEGStrategy` class in `guidance_strategy.py` that uses the `peg.py` module to calculate steering commands.
    3.  **Set as Default:** Modify the `GuidanceContext` to use `PEGStrategy` during the ascent-to-orbit phase of the mission.
*   **Success Measure:** The guidance system can deliver the vehicle to a target apoapsis of 200 km (±5 km tolerance) even when a persistent 5% engine thrust deficit is simulated.
*   **Evaluation:** Run two simulations with the 5% thrust deficit: one with the old `GravityTurnStrategy` and one with the new `PEGStrategy`. The PEG run must succeed in reaching the target apoapsis, while the gravity turn run should fail significantly.

### **Action Item 2: Develop a Two-Stage Orbital Insertion Capability**

*   **Description:** Implement the multi-burn sequence required to achieve a near-circular orbit.
*   **Engineer Actions:**
    1.  **Define MECO Logic:** The `PEGStrategy` must determine the precise moment for Main Engine Cutoff (MECO) to achieve the target transfer orbit.
    2.  **Implement Coast Phase:** Add a "Coast to Apoapsis" phase to the main mission state machine. During this phase, the vehicle is unpowered, and its trajectory is purely ballistic.
    3.  **Implement Circularization Burn:** In `circularize.py`, implement the logic to execute a timed, directed burn when the vehicle reaches apoapsis. This will raise the periapsis to the target LEO altitude.
*   **Success Measure:** The simulation successfully executes a two-burn ascent sequence. The final orbit's apoapsis and periapsis are within 5 km of each other (e.g., 200 km x 195 km).
*   **Evaluation:** Analyze the mission log (`mission_log.csv`). The log must clearly show: (1) MECO, (2) a coast phase of several minutes, and (3) a second, short engine burn. The final orbital parameters must meet the success criteria.

### **Action Item 3: Implement an On-Board Orbit Determination Module**

*   **Description:** Create a module that allows the simulated flight computer to be aware of its own orbit in real-time.
*   **Engineer Actions:**
    1.  **Create `OrbitalMonitor`:** Develop a new class or module (`orbital_monitor.py`) that takes the vehicle's state vector (position, velocity) and calculates the six key orbital elements (apoapsis, periapsis, inclination, etc.).
    2.  **Integrate into Main Loop:** The main simulation loop must call the `OrbitalMonitor` at each time step to update the vehicle's perceived orbital state.
    3.  **Drive Mission Events:** Use the real-time data from the `OrbitalMonitor` to trigger mission events. For example, the decision to start the circularization burn should be triggered when `current_altitude` is approximately equal to the `apoapsis` calculated by the monitor.
*   **Success Measure:** The `OrbitalMonitor`'s real-time calculated apoapsis and periapsis must match the results from a post-flight analysis of the trajectory data with less than 0.5% error.
*   **Evaluation:** At the end of a simulated flight, create a script to analyze the final state vector from `mission_log.csv` using a trusted, independent orbital mechanics library (e.g., `astropy`). Compare this "ground truth" result to the final values calculated by the `OrbitalMonitor` during the flight.

---

## 4. Final Remarks

Completing these three action items will represent the successful achievement of our first major project milestone. This will provide us with the high-confidence foundation needed to begin designing and simulating the complex translunar injection and lunar landing phases. I have full confidence in the team's ability to execute this plan.
