#!/usr/bin/env python3
"""
Quick mission test with accelerated parameters for trajectory visualization
"""

import json
import numpy as np
from rocket_simulation_main import Mission, create_saturn_v_rocket
from trajectory_visualizer import create_trajectory_plots

def run_accelerated_mission():
    """Run mission with accelerated time parameters for quick visualization"""
    
    # Accelerated configuration for faster simulation
    config = {
        "launch_latitude": 28.573,
        "launch_azimuth": 90,
        "target_parking_orbit": 200e3,
        "gravity_turn_altitude": 1500,
        "simulation_duration": 2 * 24 * 3600,  # 2 days instead of 10
        "time_step": 1.0  # 1 second timestep instead of 0.1 for speed
    }
    
    print("Creating Saturn V rocket...")
    rocket = create_saturn_v_rocket("saturn_v_config.json")
    
    print("Starting accelerated mission simulation...")
    mission = Mission(rocket, config)
    
    # Run simulation
    results = mission.simulate(
        duration=config["simulation_duration"],
        dt=config["time_step"]
    )
    
    print(f"\nMission completed!")
    print(f"Final phase: {results['final_phase']}")
    print(f"Mission success: {results.get('mission_success', False)}")
    print(f"Duration: {results['mission_duration']/3600:.1f} hours")
    print(f"Max altitude: {results['max_altitude']/1000:.1f} km")
    print(f"Lunar orbits completed: {results.get('lunar_orbits_completed', 0)}")
    
    # Create trajectory visualization
    print("\nGenerating trajectory visualization...")
    fig = create_trajectory_plots(results, [], [], save_filename='quick_mission_trajectory.png')
    print("Trajectory plot saved as 'quick_mission_trajectory.png'")
    
    # Save results
    with open("quick_mission_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("Results saved to 'quick_mission_results.json'")
    
    return results

if __name__ == "__main__":
    results = run_accelerated_mission()