# LEO to TLI Transition Problem Analysis and Solutions

## Executive Summary

This report analyzes the current issues preventing progression from Low Earth Orbit (LEO) to Trans-Lunar Injection (TLI) phase in the rocket simulation system. Through systematic examination of the codebase and simulation outputs, we have identified six critical problems that must be addressed before successful TLI implementation. The solutions provided offer clear engineering steps to resolve these issues and enable lunar trajectory insertion.

## Identified Problems (Root Causes for TLI Phase Blockage) ✅

### 1. Simulation Output Placeholder Values

The parameter sweep execution code returns hardcoded placeholder values for critical results including **horizontal velocity** and **remaining fuel**. For example, `horizontal_velocity_at_220km` consistently returns `7200 m/s`, and Stage-3 remaining fuel is fixed at `0.08` (8%). This prevents **accurate orbital performance reflection**, making analysis and optimization impossible.

**Impact**: Unable to perform real trajectory analysis or optimization based on actual simulation data.

### 2. Missing `mission_results.json` File Generation

The main rocket simulation (`rocket_simulation_main.py`) does not consistently generate the **results JSON file**. When this file is missing, the parameter sweep **forcibly terminates** with an exception, preventing subsequent test cases from running.

**Impact**: Simulation chain breaks, preventing systematic parameter exploration.

### 3. Improper Orbit Insertion (Circularization) Termination Logic

The **circular orbit burn termination condition** is inadequate, causing **incorrect burn shutdown timing**. Currently using **"remaining ΔV requirement < -5 m/s"** (over-burn tendency), which means the engine continues burning until significant over-expenditure occurs. This leads to **fuel waste** and potential orbit overshoot.

**Impact**: Excessive fuel consumption during orbit insertion, leaving insufficient propellant for TLI.

### 4. Insufficient Simulation Timeout Duration

Current automatic execution terminates simulations after **300 seconds** (5 minutes). While sufficient for LEO achievement, **TLI phase requires significantly longer** computation time. Orbital coast phases and lunar transfer calculations are **terminated prematurely**, resulting in false failures.

**Impact**: TLI phase calculations cannot complete, preventing successful lunar trajectory insertion.

### 5. Limited Optimization Parameter Ranges

**Gravity turn initial pitch rate** exploration ranges are too narrow, currently covering approximately *1.55~1.75°/s* (effectively useful range is limited despite 1.3~1.7° settings). **Final pitch angle** is also coarsely stepped at 8~12°, preventing **precision tuning and margin verification** required for TLI.

**Impact**: Risk of missing optimal solutions and proceeding with insufficient design margins.

### 6. Insufficient Third Stage (S-IVB) Fuel Remaining

LEO achievement leaves approximately **5~8% third stage fuel remaining**, making it unclear whether the required **ΔV ≈ 3100 m/s for lunar transfer** can be achieved. Current success criteria set **5% remaining** as minimum, but actual simulation results show **6~9% at best**, indicating excessive fuel consumption during orbit insertion.

**Impact**: Insufficient propellant for TLI engine ignition, preventing lunar transfer phase initiation.

## Improvement Strategies for Next Phase (TLI Implementation) 🔧

The following solutions address the engineering challenges systematically, enabling progression to Trans-Lunar Injection (TLI) phase. Each step specifies software modifications and their expected effects.

### 1. Accurate Simulation Results JSON Output

Replace placeholder values with actual calculated telemetry data including **horizontal velocity at 220km altitude** and **remaining fuel percentages**. Specifically, compute and save rocket **maximum altitude**, **orbital eccentricity**, and **third stage fuel ratio** to the JSON file.

**Implementation**: Modify result output functions to calculate real values from simulation state.
**Expected Effect**: Enable accurate downstream analysis and optimization based on real data.

### 2. Orbit Insertion Completion Logic Correction

Change circular orbit engine cutoff condition from current `dv_req < -5 m/s` to **`|dv_req| < 5 m/s`** (remaining ΔV within ±5 m/s). Additionally verify **perigee altitude > 150km** and **eccentricity < 0.05** (nearly circular orbit).

**Implementation**: Update burn termination logic in orbit insertion module.
**Expected Effect**: Stop burning immediately upon reaching required velocity, preventing over-burn and conserving third stage fuel.

### 3. Parameter Search Range Expansion

Expand exploration ranges for launch **initial pitch rate**, **final target pitch angle**, and **third stage ignition timing**. Example ranges: initial pitch rate **1.50~1.80°/s (step 0.05)**, final pitch angle **7~9° (step 0.25°)**, third stage re-ignition offset **-35~-10 seconds (step 5 seconds)**.

**Implementation**: Modify parameter sweep configuration files.
**Expected Effect**: Find better parameter combinations that reduce fuel consumption while achieving stable orbit, ensuring third stage fuel reserves.

### 4. Phase-Specific Simulation Time Limits

Set **maximum 900 seconds** for LEO achievement calculations, **maximum 6000 seconds** (~100 minutes) when including TLI phase. This allows proper execution of **orbital coast time and lunar transfer orbit calculations**.

**Implementation**: Modify timeout settings in simulation controller.
**Expected Effect**: Prevent premature termination during TLI phase, enabling complete lunar transfer calculations.

### 5. Third Stage Fuel Monitoring and Conservation

Output **third stage remaining fuel percentage** to simulation logs and results JSON, targeting **30% or more remaining** at LEO achievement. Record propellant mass ratio at each test case completion, adjusting launch profile to maintain 30%+ average.

**Implementation**: Add fuel monitoring to telemetry output system.
**Expected Effect**: Ensure sufficient propellant margin for TLI, enable team verification of orbit insertion vs. TLI fuel allocation.

### 6. Monte Carlo Simulation Preparation

Prepare for future reliability verification by enabling **random element introduction** in simulations. Parameterize atmospheric density ±5% variation, engine specific impulse (Isp) ±1% fluctuation, and IMU noise through YAML configuration.

**Implementation**: Add stochastic parameter support to simulation framework.
**Expected Effect**: Create robust control systems resistant to uncertainties, identify unexpected behaviors before TLI phase transition.

### 7. Trans-Lunar Injection (TLI) Pre-Planning and Rehearsal

Immediately after LEO achievement, automatically calculate **additional ΔV required** for lunar transfer and execute mock runs using third stage engine. Target approximately **3130 m/s additional ΔV** as reference for **burning to Earth escape velocity**.

**Implementation**: Integrate TLI calculation module with LEO achievement system.
**Expected Effect**: Achieve **C3 > 0** (Earth gravity escape orbit) with apogee reaching ~400,000 km (approximately lunar orbit distance).

## Implementation Timeline and Verification

1. **Phase 1** (Immediate): Fix JSON output and burn termination logic
2. **Phase 2** (Short-term): Expand parameter ranges and extend timeouts  
3. **Phase 3** (Medium-term): Implement fuel monitoring and TLI preparation
4. **Phase 4** (Long-term): Monte Carlo capability and full TLI integration

Each phase should be verified incrementally, with particular focus on third stage fuel margins and TLI achievement conditions. Through these systematic improvements, the simulation will transition from a **stable LEO platform** to **reliable TLI phase progression**.

## Success Criteria

- **LEO Achievement**: Consistent orbit insertion with >30% third stage fuel remaining
- **TLI Readiness**: Successful lunar transfer calculation and mock execution
- **System Reliability**: 90%+ success rate across parameter variations
- **Data Integrity**: All telemetry values reflect actual simulation results

These solutions enable engineers to **identify and resolve issues through data-driven approaches** without requiring extensive rocket engineering background, while achieving lunar orbit insertion scenarios. 🚀

---

**Sources:**
* Rocket Simulation Codebase (v37)
* Professor's Feedback Document (v38)
* Simulation Configuration & Logs