#!/usr/bin/env python3
"""
Debug Guidance System - Test guidance commands in isolation
"""

import sys
import os
import logging

# Add project root to path  
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from rocket_simulation_main import Mission
from vehicle import create_saturn_v_rocket, Vector3
from guidance_strategy import VehicleState, GuidanceFactory

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_guidance_commands():
    """Test what guidance commands are being generated"""
    logger.info("=== Testing Guidance Commands ===")
    
    config = {
        "launch_latitude": 28.5,
        "launch_azimuth": 90,
        "target_parking_orbit": 200000,
        "gravity_turn_altitude": 1500
    }
    
    rocket = create_saturn_v_rocket()
    mission = Mission(rocket, config)
    
    # Test at launch conditions
    position = Vector3(5.60e+06, 3.04e+06, 0.00e+00)  # Earth surface
    velocity = Vector3(-185, 342, 0)  # Initial velocity from Earth rotation
    altitude = 0.0
    
    # Create vehicle state
    vehicle_state = VehicleState(
        position=position,
        velocity=velocity,
        altitude=altitude,
        mass=rocket.total_mass,
        mission_phase=rocket.phase,
        time=0.0
    )
    
    target_state = {
        'target_apoapsis': 200000 + 6371000,
        'target_altitude': 200000
    }
    
    # Test guidance command
    guidance_command = mission.guidance_context.compute_guidance(vehicle_state, target_state)
    
    logger.info(f"Launch conditions:")
    logger.info(f"  Position: {position}")
    logger.info(f"  Velocity: {velocity}")
    logger.info(f"  Altitude: {altitude:.1f} m")
    
    logger.info(f"Guidance command:")
    logger.info(f"  Thrust direction: {guidance_command.thrust_direction}")
    logger.info(f"  Thrust magnitude: {guidance_command.thrust_magnitude:.3f}")
    logger.info(f"  Target pitch: {guidance_command.target_pitch:.1f}°")
    logger.info(f"  Phase: {guidance_command.guidance_phase.value}")
    
    # Calculate expected thrust vector
    stage1_thrust = rocket.stages[0].get_thrust(altitude)
    expected_thrust_vector = guidance_command.thrust_direction * (stage1_thrust * guidance_command.thrust_magnitude)
    
    logger.info(f"Expected thrust vector:")
    logger.info(f"  Magnitude: {expected_thrust_vector.magnitude()/1000:.0f} kN")
    logger.info(f"  Direction: ({expected_thrust_vector.x:.0f}, {expected_thrust_vector.y:.0f}, {expected_thrust_vector.z:.0f}) N")
    
    # Compare with radial direction (should be pointing away from Earth)
    radial_unit = position.normalized()
    logger.info(f"Radial unit vector (away from Earth): {radial_unit}")
    
    # Check if thrust is pointing in the right direction
    thrust_unit = guidance_command.thrust_direction
    dot_product = radial_unit.data @ thrust_unit.data
    logger.info(f"Dot product with radial (should be ~1.0 for vertical): {dot_product:.3f}")
    
    if abs(dot_product - 1.0) < 0.1:
        logger.info("✅ Thrust direction appears correct (vertical)")
    else:
        logger.warning("❌ Thrust direction may be incorrect")
    
    return guidance_command

def test_thrust_vs_gravity():
    """Test if thrust can overcome gravity"""
    logger.info("=== Testing Thrust vs Gravity ===")
    
    rocket = create_saturn_v_rocket()
    
    # Thrust force
    stage1_thrust = rocket.stages[0].get_thrust(0)  # Sea level
    rocket_mass = rocket.total_mass
    
    # Thrust acceleration
    thrust_accel = stage1_thrust / rocket_mass
    
    # Gravity acceleration at surface
    G = 6.67430e-11
    M_EARTH = 5.972e24
    R_EARTH = 6371e3
    gravity_accel = G * M_EARTH / (R_EARTH * R_EARTH)
    
    logger.info(f"Rocket mass: {rocket_mass/1000:.1f} tons")
    logger.info(f"Stage 1 thrust: {stage1_thrust/1000:.0f} kN")
    logger.info(f"Thrust acceleration: {thrust_accel:.1f} m/s²")
    logger.info(f"Gravity acceleration: {gravity_accel:.1f} m/s²")
    logger.info(f"Net acceleration: {thrust_accel - gravity_accel:.1f} m/s²")
    logger.info(f"Thrust-to-weight ratio: {thrust_accel/gravity_accel:.2f}")
    
    if thrust_accel > gravity_accel:
        logger.info("✅ Thrust can overcome gravity")
        return True
    else:
        logger.error("❌ Thrust cannot overcome gravity")
        return False

def main():
    logger.info("🔍 Debugging Guidance System")
    
    # Test 1: Thrust vs gravity
    thrust_ok = test_thrust_vs_gravity()
    
    # Test 2: Guidance commands
    guidance_cmd = test_guidance_commands()
    
    if thrust_ok:
        logger.info("Basic thrust physics looks correct")
    else:
        logger.error("Basic thrust physics has issues")

if __name__ == "__main__":
    main()