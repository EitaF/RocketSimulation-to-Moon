#!/usr/bin/env python3
"""
Quick test script to validate LEO insertion capability
"""
import json
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from rocket_simulation_main import Mission
from guidance import reset_guidance_state

def quick_leo_test():
    """Run a quick test to see if we can achieve LEO"""
    print("Starting quick LEO insertion test...")
    
    # Reset guidance state
    reset_guidance_state()
    
    # Create rocket from config file
    from vehicle import create_saturn_v_rocket
    rocket = create_saturn_v_rocket("saturn_v_config.json")
    
    # Basic mission config
    config = {
        "launch_latitude": 28.573,
        "launch_azimuth": 90,
        "target_parking_orbit": 185e3,
        "gravity_turn_altitude": 1500,
        "simulation_duration": 600,  # 10 minutes
        "time_step": 0.1
    }
    
    # Create mission
    mission = Mission(rocket, config)
    
    # Run simulation for a limited time (600 seconds = 10 minutes)
    max_time = 600
    dt = 0.1
    t = 0
    
    while t < max_time:
        try:
            # Update mission
            mission.update(dt)
            
            # Check if mission failed
            if mission.is_mission_failed():
                print(f"Mission failed at t={t:.1f}s")
                break
                
            # Check if we achieved LEO
            altitude = mission.get_altitude()
            if altitude > 160000:  # 160km
                velocity = mission.rocket.velocity.magnitude()
                print(f"Reached {altitude/1000:.1f}km altitude at t={t:.1f}s")
                print(f"Velocity: {velocity:.1f} m/s")
                
                # Check orbital parameters
                apoapsis = mission.get_apoapsis()
                periapsis = mission.get_periapsis()
                eccentricity = mission.get_eccentricity()
                
                print(f"Apoapsis: {apoapsis/1000:.1f}km")
                print(f"Periapsis: {periapsis/1000:.1f}km") 
                print(f"Eccentricity: {eccentricity:.3f}")
                
                if periapsis > 150000 and eccentricity < 0.05:
                    print("SUCCESS: Achieved stable LEO!")
                    return True
                    
            t += dt
            
        except Exception as e:
            print(f"Error at t={t:.1f}s: {e}")
            break
    
    print("Test completed - LEO not achieved")
    return False

if __name__ == "__main__":
    success = quick_leo_test()
    sys.exit(0 if success else 1)