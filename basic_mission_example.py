#!/usr/bin/env python3
"""
Basic Mission Simulation Example
Demonstrates the correct imports and basic usage of the rocket simulation system
"""

import json
import sys
import os

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Core imports from the rocket simulation system
from rocket_simulation_main import Mission
from vehicle import create_saturn_v_rocket, Vector3, MissionPhase
from guidance_strategy import GuidanceFactory
from orbital_monitor import create_orbital_monitor

def create_basic_mission_config():
    """Create a basic mission configuration"""
    return {
        "launch_latitude": 28.573,  # Kennedy Space Center
        "launch_azimuth": 90,  # East-facing launch
        "target_parking_orbit": 185e3,  # 185 km parking orbit
        "gravity_turn_altitude": 1500,  # Start gravity turn at 1500m
        "simulation_duration": 2 * 3600,  # 2 hours simulation
        "time_step": 0.1,  # 0.1 second time step
        "verbose_abort": False
    }

def create_basic_saturn_v_config():
    """Create basic Saturn V configuration"""
    return {
        "stages": [
            {
                "name": "S-IC (1st Stage)",
                "dry_mass": 130000,
                "propellant_mass": 2150000,
                "thrust_sea_level": 34020000,
                "thrust_vacuum": 35100000,
                "specific_impulse_sea_level": 263,
                "specific_impulse_vacuum": 289,
                "burn_time": 168
            },
            {
                "name": "S-II (2nd Stage)",
                "dry_mass": 40000,
                "propellant_mass": 540000,
                "thrust_sea_level": 4400000,
                "thrust_vacuum": 5000000,
                "specific_impulse_sea_level": 395,
                "specific_impulse_vacuum": 421,
                "burn_time": 500
            },
            {
                "name": "S-IVB (3rd Stage)",
                "dry_mass": 13494,
                "propellant_mass": 193536,
                "thrust_sea_level": 825000,
                "thrust_vacuum": 1000000,
                "specific_impulse_sea_level": 441,
                "specific_impulse_vacuum": 461,
                "burn_time": 1090
            }
        ],
        "rocket": {
            "name": "Saturn V",
            "payload_mass": 45000,
            "drag_coefficient": 0.3,
            "cross_sectional_area": 80.0
        }
    }

def run_basic_mission():
    """Run a basic mission simulation"""
    print("=== Basic Mission Simulation ===")
    print("Setting up mission configuration...")
    
    # Create mission configuration
    mission_config = create_basic_mission_config()
    
    # Create and save Saturn V configuration
    saturn_config = create_basic_saturn_v_config()
    with open("saturn_v_config.json", "w") as f:
        json.dump(saturn_config, f, indent=2)
    
    # Create rocket instance
    print("Creating Saturn V rocket...")
    rocket = create_saturn_v_rocket("saturn_v_config.json")
    
    # Create mission instance
    print("Initializing mission...")
    mission = Mission(rocket, mission_config)
    
    # Run simulation
    print("Starting simulation...")
    results = mission.simulate(
        duration=mission_config["simulation_duration"],
        dt=mission_config["time_step"]
    )
    
    # Display results
    print("\n" + "="*50)
    print("MISSION RESULTS")
    print("="*50)
    print(f"Mission Success: {results.get('mission_success', 'Unknown')}")
    print(f"Final Phase: {results.get('final_phase', 'Unknown')}")
    print(f"Mission Duration: {results.get('mission_duration', 0)/3600:.1f} hours")
    print(f"Max Altitude: {results.get('max_altitude', 0)/1000:.1f} km")
    print(f"Max Velocity: {results.get('max_velocity', 0):.1f} m/s")
    print(f"Total Delta-V: {results.get('total_delta_v', 0):.1f} m/s")
    print(f"Propellant Used: {results.get('propellant_used', 0)/1000:.1f} tons")
    print(f"Final Mass: {results.get('final_mass', 0)/1000:.1f} tons")
    
    return results

def demonstrate_component_usage():
    """Demonstrate usage of individual components"""
    print("\n=== Component Usage Examples ===")
    
    # Vector3 usage
    print("\n1. Vector3 Usage:")
    position = Vector3(1000, 2000, 3000)
    velocity = Vector3(100, 200, 300)
    print(f"Position: {position}")
    print(f"Velocity: {velocity}")
    print(f"Position magnitude: {position.magnitude():.1f} m")
    print(f"Velocity magnitude: {velocity.magnitude():.1f} m/s")
    
    # Rocket creation
    print("\n2. Rocket Creation:")
    rocket = create_saturn_v_rocket()
    print(f"Rocket name: {rocket.name}")
    print(f"Number of stages: {len(rocket.stages)}")
    print(f"Total mass: {rocket.get_total_mass()/1000:.1f} tons")
    
    # Orbital monitor
    print("\n3. Orbital Monitor:")
    orbital_monitor = create_orbital_monitor(update_interval=1.0)
    print(f"Orbital monitor created with update interval: {orbital_monitor.update_interval} seconds")
    
    # Guidance system
    print("\n4. Guidance System:")
    guidance_config = {"guidance_type": "standard"}
    guidance_context = GuidanceFactory.create_context(guidance_config)
    print(f"Guidance context created")

if __name__ == "__main__":
    try:
        # Demonstrate component usage
        demonstrate_component_usage()
        
        # Run basic mission
        results = run_basic_mission()
        
        print("\n=== Simulation Complete ===")
        print("Check mission_log.csv for detailed flight data")
        
    except Exception as e:
        print(f"Error during simulation: {e}")
        import traceback
        traceback.print_exc()