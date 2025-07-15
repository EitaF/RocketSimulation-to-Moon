#!/usr/bin/env python3
"""
Execute 6000s TLI simulation - Professor v40 Task A1
Modified version of main simulation to run for exactly 6000s and report TLI metrics
"""

import json
import sys
import logging
from rocket_simulation_main import Mission
from vehicle import create_saturn_v_rocket

def run_tli_simulation():
    """Run a 6000s simulation focusing on TLI performance"""
    
    # Configure quiet logging
    logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')
    
    print("=== 6000s TLI SIMULATION - PROFESSOR V40 TASK A1 ===")
    
    # Load default configuration
    config = {
        "gravity_turn_altitude": 1000,
        "target_parking_orbit": 185000,
        "max_q_operational": 40000,
        "abort_thresholds": {
            "max_q_limit": 60000,
            "excessive_heating_threshold": 2000,
            "structural_failure_acceleration": 150,
            "earth_impact_altitude": -1000,
            "attitude_error_limit": 45,
            "propellant_depletion_threshold": 95.0
        },
        "guidance": {
            "type": "enhanced",
            "cross_sectional_area": 80.0
        }
    }
    
    try:
        # Load Saturn V configuration
        with open('saturn_v_config.json', 'r') as f:
            saturn_config = json.load(f)
        if "abort_thresholds" in saturn_config:
            config["abort_thresholds"] = saturn_config["abort_thresholds"]
    except FileNotFoundError:
        print("Warning: saturn_v_config.json not found, using defaults")
    
    # Create rocket and mission
    rocket = create_saturn_v_rocket("saturn_v_config.json")
    mission = Mission(rocket, config)
    
    print(f"Starting 6000s simulation...")
    print(f"Target: C3 energy > 0, apogee ~400,000 km, Stage-3 fuel ≥5%")
    print(f"Sequence: Launch → LEO → LEO_STABLE → TLI_BURN → Coast to Moon")
    
    # Run the simulation - use shorter dt for better accuracy
    results = mission.simulate(duration=6000.0, dt=0.1)
    
    # Extract key metrics
    print(f"\n=== SIMULATION COMPLETE ===")
    print(f"Mission status: {results.get('mission_status', 'Unknown')}")
    print(f"Final phase: {results.get('final_phase', 'Unknown')}")
    print(f"Duration: {results.get('duration', 0):.1f} s")
    
    # Physical constants for calculations
    G = 6.67430e-11
    M_EARTH = 5.972e24
    R_EARTH = 6371e3
    
    # Calculate derived metrics
    final_velocity = results.get('final_velocity', 0)
    final_altitude = results.get('final_altitude', 0)
    final_apoapsis = results.get('final_apoapsis', 0)
    stage3_fuel_remaining = results.get('stage3_fuel_remaining_percent', 0)
    
    print(f"\n=== TLI PERFORMANCE METRICS ===")
    print(f"Final velocity: {final_velocity:.1f} m/s")
    print(f"Final altitude: {final_altitude/1000:.1f} km")
    print(f"Final apoapsis: {final_apoapsis/1000:.1f} km")
    print(f"Stage-3 fuel remaining: {stage3_fuel_remaining:.1f}%")
    
    # Calculate C3 energy
    r = max(R_EARTH + final_altitude, R_EARTH + 1000)  # Avoid division by zero
    escape_velocity = (2 * G * M_EARTH / r) ** 0.5
    c3_energy = final_velocity**2 - escape_velocity**2
    
    print(f"Escape velocity at position: {escape_velocity:.1f} m/s")
    print(f"C3 energy: {c3_energy/1e6:.3f} km²/s²")
    
    # Success criteria evaluation
    print(f"\n=== SUCCESS CRITERIA ===")
    c3_positive = c3_energy > 0
    apoapsis_target = final_apoapsis >= 400000e3  # 400,000 km
    fuel_sufficient = stage3_fuel_remaining >= 5.0  # 5%
    
    print(f"C3 energy > 0: {'✓ PASS' if c3_positive else '✗ FAIL'} ({c3_energy/1e6:.3f} km²/s²)")
    print(f"Apogee ≥ 400,000 km: {'✓ PASS' if apoapsis_target else '✗ FAIL'} ({final_apoapsis/1000:.0f} km)")
    print(f"Stage-3 fuel ≥ 5%: {'✓ PASS' if fuel_sufficient else '✗ FAIL'} ({stage3_fuel_remaining:.1f}%)")
    
    overall_success = c3_positive and apoapsis_target and fuel_sufficient
    print(f"\nOverall TLI Mission: {'✓ SUCCESS' if overall_success else '✗ FAILED'}")
    
    # Save detailed results
    detailed_results = {
        'task': 'Professor_v40_Task_A1',
        'simulation_duration': 6000.0,
        'results': results,
        'tli_metrics': {
            'c3_energy_km2_s2': c3_energy / 1e6,
            'apoapsis_km': final_apoapsis / 1000,
            'stage3_fuel_remaining_percent': stage3_fuel_remaining,
            'final_velocity_ms': final_velocity,
            'final_altitude_km': final_altitude / 1000
        },
        'success_criteria': {
            'c3_positive': c3_positive,
            'apoapsis_400k_km': apoapsis_target,
            'fuel_5_percent': fuel_sufficient,
            'overall_success': overall_success
        }
    }
    
    with open('tli_6000s_results.json', 'w') as f:
        json.dump(detailed_results, f, indent=2)
    
    print(f"\nDetailed results saved to: tli_6000s_results.json")
    
    return overall_success

if __name__ == "__main__":
    try:
        success = run_tli_simulation()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Simulation failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)