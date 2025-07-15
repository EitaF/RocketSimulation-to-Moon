#!/usr/bin/env python3
"""
Test LEO progression to verify TLI sequence - Professor v40 Task A1 prep
"""

import json
import logging
from rocket_simulation_main import Mission
from vehicle import create_saturn_v_rocket

def test_leo_progression():
    """Test that the mission progresses through LEO phases correctly"""
    
    # Configure minimal logging
    logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')
    
    print("=== LEO PROGRESSION TEST ===")
    
    # Default configuration
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
    
    # Create mission
    rocket = create_saturn_v_rocket("saturn_v_config.json")
    mission = Mission(rocket, config)
    
    print("Running simulation for 1500s to reach LEO_STABLE...")
    
    # Run simulation for 1500s (should be enough to reach LEO_STABLE)
    results = mission.simulate(duration=1500.0, dt=0.1)
    
    print(f"\n=== LEO PROGRESSION RESULTS ===")
    print(f"Final phase: {results.get('final_phase', 'Unknown')}")
    print(f"Duration: {results.get('duration', 0):.1f} s")
    
    # Check phase progression
    phase_history = getattr(mission, 'phase_history', [])
    unique_phases = []
    for phase in phase_history:
        if not unique_phases or unique_phases[-1] != phase:
            unique_phases.append(phase)
    
    print(f"Phase progression: {' → '.join([p.value if hasattr(p, 'value') else str(p) for p in unique_phases[-10:]])}")
    
    # Check final state
    final_velocity = results.get('final_velocity', 0)
    final_altitude = results.get('final_altitude', 0)
    stage3_fuel = results.get('stage3_fuel_remaining_percent', 0)
    
    print(f"Final velocity: {final_velocity:.1f} m/s")
    print(f"Final altitude: {final_altitude/1000:.1f} km")
    print(f"Stage-3 fuel: {stage3_fuel:.1f}%")
    
    # Success assessment
    reached_leo_stable = 'leo_stable' in [str(p).lower() for p in unique_phases]
    sufficient_fuel = stage3_fuel >= 30.0
    reasonable_orbit = 150 <= final_altitude/1000 <= 250
    
    print(f"\n=== LEO READINESS CHECK ===")
    print(f"Reached LEO_STABLE: {'✓' if reached_leo_stable else '✗'}")
    print(f"Stage-3 fuel ≥30%: {'✓' if sufficient_fuel else '✗'} ({stage3_fuel:.1f}%)")
    print(f"Reasonable orbit altitude: {'✓' if reasonable_orbit else '✗'} ({final_altitude/1000:.1f} km)")
    
    overall_ready = reached_leo_stable and sufficient_fuel and reasonable_orbit
    print(f"\nTLI Ready: {'✓ YES' if overall_ready else '✗ NO'}")
    
    return overall_ready, results

if __name__ == "__main__":
    try:
        ready, results = test_leo_progression()
        if ready:
            print("\n✓ Mission ready for 6000s TLI test!")
        else:
            print("\n✗ Mission not ready - check configuration")
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()