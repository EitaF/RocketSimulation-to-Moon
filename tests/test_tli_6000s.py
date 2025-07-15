#!/usr/bin/env python3
"""
Test script for 6000s TLI simulation - Professor v40 Task A1
"""

import json
import sys
from rocket_simulation_main import Mission
from vehicle import create_saturn_v_rocket

def run_6000s_tli_test():
    """Run a 6000s simulation with TLI burn and analyze results"""
    print("Starting 6000s TLI simulation test...")
    
    # Load mission configuration
    try:
        with open('mission_config.json', 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        print("Using default configuration")
        config = {}
    
    # Create rocket instance
    rocket = create_saturn_v_rocket("saturn_v_config.json")
    
    # Create mission instance
    mission = Mission(rocket, config)
    
    # Run simulation for 6000s
    results = mission.simulate(duration=6000.0, dt=0.1)
    
    # Analyze results
    print(f"\n=== 6000s TLI SIMULATION RESULTS ===")
    print(f"Mission status: {results.get('mission_status', 'Unknown')}")
    print(f"Final phase: {results.get('final_phase', 'Unknown')}")
    print(f"Simulation duration: {results.get('duration', 0):.1f} s")
    
    # Check TLI specific metrics
    final_velocity = results.get('final_velocity', 0)
    final_altitude = results.get('final_altitude', 0)
    final_apoapsis = results.get('final_apoapsis', 0)
    stage3_fuel_remaining = results.get('stage3_fuel_remaining_percent', 0)
    
    print(f"Final velocity: {final_velocity:.1f} m/s")
    print(f"Final altitude: {final_altitude/1000:.1f} km")
    print(f"Final apoapsis: {final_apoapsis/1000:.1f} km")
    print(f"Stage-3 fuel remaining: {stage3_fuel_remaining:.1f}%")
    
    # Calculate C3 energy
    G = 6.67430e-11
    M_EARTH = 5.972e24
    R_EARTH = 6371e3
    
    # Position magnitude (assuming roughly circular at final altitude)
    r = R_EARTH + final_altitude
    escape_velocity = (2 * G * M_EARTH / r) ** 0.5
    c3_energy = final_velocity**2 - escape_velocity**2
    
    print(f"Escape velocity at final position: {escape_velocity:.1f} m/s")
    print(f"C3 energy: {c3_energy/1e6:.3f} km²/s²")
    
    # Success criteria check
    success_criteria = {
        'c3_positive': c3_energy > 0,
        'apoapsis_400km': final_apoapsis >= 400000e3,  # 400,000 km
        'stage3_fuel_5percent': stage3_fuel_remaining >= 5.0
    }
    
    print(f"\n=== SUCCESS CRITERIA CHECK ===")
    for criterion, passed in success_criteria.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{criterion}: {status}")
    
    overall_success = all(success_criteria.values())
    print(f"\nOverall TLI mission success: {'✓ PASS' if overall_success else '✗ FAIL'}")
    
    return results, success_criteria

if __name__ == "__main__":
    try:
        results, criteria = run_6000s_tli_test()
        
        # Save results for analysis
        with open('tli_6000s_test_results.json', 'w') as f:
            json.dump({
                'results': results,
                'success_criteria': criteria,
                'test_timestamp': str(sys.modules['datetime'].datetime.now()) if 'datetime' in sys.modules else 'unknown'
            }, f, indent=2)
        
        print(f"\nResults saved to tli_6000s_test_results.json")
        
    except Exception as e:
        print(f"Error during simulation: {e}")
        sys.exit(1)