#!/usr/bin/env python3
"""
TLI Burn Test Script - Professor v30 Action 1
Test the TLI burn functionality starting from a stable LEO orbit

This script tests the TLI guidance system independently of the full launch sequence
to validate the C3 energy requirements as specified by the Professor.
"""

import numpy as np
import json
import logging
from vehicle import Vector3, Rocket, RocketStage, MissionPhase, create_saturn_v_rocket
from tli_guidance import create_tli_guidance
from guidance_strategy import GuidanceContext, GuidanceFactory, VehicleState

# Physical constants
G = 6.67430e-11  # Gravitational constant [m^3/kg/s^2]
M_EARTH = 5.972e24  # Earth mass [kg]
R_EARTH = 6371e3  # Earth radius [m]

def setup_logging():
    """Setup logging for the test"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

def create_leo_state():
    """Create a rocket state in stable LEO for TLI burn testing"""
    # LEO parameters (185 km circular orbit)
    orbit_altitude = 185e3  # 185 km
    orbit_radius = R_EARTH + orbit_altitude
    orbital_velocity = np.sqrt(G * M_EARTH / orbit_radius)
    
    print(f"Creating LEO state:")
    print(f"  Orbit altitude: {orbit_altitude/1000:.1f} km")
    print(f"  Orbit radius: {orbit_radius/1000:.1f} km") 
    print(f"  Orbital velocity: {orbital_velocity:.1f} m/s")
    
    # Create rocket in LEO (S-IVB stage only for TLI)
    rocket = create_saturn_v_rocket("saturn_v_config.json")
    
    # Simulate that we've already used Stage 1 and Stage 2
    rocket.current_stage = 2  # S-IVB stage (index 2)
    rocket.phase = MissionPhase.LEO_STABLE
    
    # Position the rocket in LEO (starting at apogee for simplicity)
    rocket.position = Vector3(orbit_radius, 0, 0)
    rocket.velocity = Vector3(0, orbital_velocity, 0)
    
    # For LEO test, we'll use the rocket's existing mass calculation
    # The S-IVB stage should have full propellant for TLI burn
    print(f"  Initial total mass: {rocket.total_mass/1000:.1f} tons")
    print(f"  S-IVB propellant: {rocket.stages[2].propellant_mass/1000:.1f} tons")
    
    return rocket

def test_tli_burn():
    """Test the TLI burn and validate C3 energy requirements"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("=== TLI BURN TEST - Professor v30 Action 1 ===")
    
    # Create rocket in LEO
    rocket = create_leo_state()
    
    # Create TLI guidance system
    tli_guidance = create_tli_guidance(185000)  # 185 km parking orbit
    
    logger.info("TLI Guidance Parameters:")
    logger.info(f"  Target C3 energy: {tli_guidance.tli_params.target_c3_energy/1e6:.3f} km²/s²")
    logger.info(f"  Required delta-V: {tli_guidance.tli_params.delta_v_required:.1f} m/s")
    logger.info(f"  Estimated burn duration: {tli_guidance.tli_params.burn_duration:.1f} s")
    
    # Simulation parameters
    dt = 0.1  # Time step [s]
    max_time = 600.0  # Maximum simulation time [s]
    time = 0.0
    
    # Storage for results
    time_history = []
    velocity_history = []
    c3_history = []
    
    # Transition to TLI burn phase
    rocket.phase = MissionPhase.TLI_BURN
    logger.info("Starting TLI burn simulation...")
    
    # Simulation loop
    while time < max_time:
        # Get current state
        position = rocket.position
        velocity = rocket.velocity
        speed = velocity.magnitude()
        
        # Calculate current C3 energy
        escape_velocity = np.sqrt(2 * G * M_EARTH / position.magnitude())
        current_c3 = speed**2 - escape_velocity**2
        
        # Store data
        time_history.append(time)
        velocity_history.append(speed)
        c3_history.append(current_c3)
        
        # Log progress every 10 seconds
        if time % 10.0 < dt:
            logger.info(f"t={time:.1f}s: v={speed:.1f}m/s, C3={current_c3/1e6:.3f}km²/s²")
        
        # Check if TLI burn should terminate
        if tli_guidance.should_terminate_burn(velocity):
            logger.info("TLI burn termination criteria met!")
            break
        
        # Check if rocket is still thrusting
        if not rocket.is_thrusting(time, position.magnitude() - R_EARTH):
            logger.warning("Rocket stopped thrusting (fuel depleted)")
            break
        
        # Get TLI guidance command
        thrust_direction, thrust_magnitude = tli_guidance.get_guidance_command(
            position, velocity, time
        )
        
        # Apply thrust
        if rocket.is_thrusting(time, position.magnitude() - R_EARTH):
            # Get current mass using the rocket's method
            mass = rocket.get_current_mass(time, position.magnitude() - R_EARTH)
            
            # Get thrust force
            thrust_force = rocket.get_thrust(position.magnitude() - R_EARTH) * thrust_magnitude
            
            # Apply thrust acceleration
            thrust_acceleration = thrust_direction * (thrust_force / mass)
            
            # Gravitational acceleration
            r_vec = position
            r_mag = r_vec.magnitude()
            gravity_acceleration = r_vec.normalized() * (-G * M_EARTH / r_mag**2)
            
            # Total acceleration
            total_acceleration = thrust_acceleration + gravity_acceleration
            
            # Update velocity and position (simple Euler integration)
            rocket.velocity = rocket.velocity + total_acceleration * dt
            rocket.position = rocket.position + rocket.velocity * dt
            
            # Update fuel consumption
            if len(rocket.stages) > rocket.current_stage:
                current_stage = rocket.stages[rocket.current_stage]
                mass_flow_rate = thrust_force / (current_stage.specific_impulse_vacuum * 9.80665)
                fuel_consumed = mass_flow_rate * dt
                current_stage.propellant_mass = max(0, current_stage.propellant_mass - fuel_consumed)
        
        # Update TLI burn state
        tli_guidance.update_burn_state(dt, rocket.velocity)
        
        time += dt
    
    # Final results
    final_velocity = rocket.velocity.magnitude()
    final_position = rocket.position
    final_escape_velocity = np.sqrt(2 * G * M_EARTH / final_position.magnitude())
    final_c3 = final_velocity**2 - final_escape_velocity**2
    
    # Calculate apogee for hyperbolic trajectory
    mu = G * M_EARTH
    r = final_position.magnitude()
    v = final_velocity
    
    if v**2 > 2 * mu / r:  # Hyperbolic trajectory
        # For hyperbolic trajectory, calculate the hyperbolic excess velocity
        v_infinity = np.sqrt(v**2 - 2 * mu / r)
        c3_check = v_infinity**2
        apogee = float('inf')  # Hyperbolic - no apogee
    else:
        # Elliptical trajectory
        semi_major_axis = 1 / (2/r - v**2/mu)
        if semi_major_axis > 0:
            apogee = 2 * semi_major_axis - r - R_EARTH
        else:
            apogee = r - R_EARTH
        c3_check = final_c3
    
    # Results summary
    logger.info("=== TLI BURN TEST RESULTS ===")
    logger.info(f"Burn duration: {time:.1f} s")
    logger.info(f"Final velocity: {final_velocity:.1f} m/s")
    logger.info(f"Final C3 energy: {final_c3/1e6:.3f} km²/s²")
    
    # Professor v30 validation criteria
    c3_min = -2.0  # km²/s²
    c3_max = -1.5  # km²/s²
    c3_km2_s2 = final_c3 / 1e6
    
    validation_passed = (c3_km2_s2 >= c3_min) and (c3_km2_s2 <= c3_max)
    
    logger.info(f"Target C3 range: {c3_min:.1f} to {c3_max:.1f} km²/s²")
    logger.info(f"Achieved C3: {c3_km2_s2:.3f} km²/s²")
    logger.info(f"Validation: {'PASSED' if validation_passed else 'FAILED'}")
    
    if apogee != float('inf'):
        logger.info(f"Final apogee: {apogee/1000:.1f} km")
    else:
        logger.info("Trajectory: Hyperbolic (escape trajectory)")
    
    # Save results to JSON
    results = {
        "test_name": "TLI_Burn_Test_v30",
        "burn_duration": time,
        "final_velocity": final_velocity,
        "final_c3_energy_m2_s2": final_c3,
        "final_c3_energy_km2_s2": c3_km2_s2,
        "target_c3_min_km2_s2": c3_min,
        "target_c3_max_km2_s2": c3_max,
        "validation_passed": bool(validation_passed),
        "final_apogee_km": apogee/1000 if apogee != float('inf') else None,
        "trajectory_type": "hyperbolic" if apogee == float('inf') else "elliptical",
        "time_history": time_history,
        "velocity_history": velocity_history,
        "c3_history": [c3/1e6 for c3 in c3_history]
    }
    
    with open("tli_test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    logger.info("Results saved to tli_test_results.json")
    
    return validation_passed

if __name__ == "__main__":
    success = test_tli_burn()
    exit(0 if success else 1)