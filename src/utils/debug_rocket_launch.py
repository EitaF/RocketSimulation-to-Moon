#!/usr/bin/env python3
"""
Debug Rocket Launch
Simple test to debug basic rocket launch issues
"""

import sys
import os
import logging

# Add project root to path  
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from rocket_simulation_main import Mission
from vehicle import create_saturn_v_rocket

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_basic_launch():
    """Test basic rocket launch without modifications"""
    logger.info("=== Testing Basic Rocket Launch ===")
    
    config = {
        "launch_latitude": 28.5,
        "launch_azimuth": 90,
        "target_parking_orbit": 200000,
        "gravity_turn_altitude": 1500
    }
    
    rocket = create_saturn_v_rocket()
    mission = Mission(rocket, config)
    
    logger.info(f"Initial rocket mass: {rocket.total_mass/1000:.1f} tons")
    logger.info(f"Stage 1 thrust: {rocket.stages[0].thrust_sea_level/1000:.0f} kN")
    logger.info(f"Stage 1 specific impulse: {rocket.stages[0].get_specific_impulse(0)} s")
    
    # Run for just 30 seconds to see if basic thrust works
    results = mission.simulate(duration=30, dt=0.1)
    
    final_altitude = results.get('max_altitude', 0)
    final_velocity = results.get('final_velocity', 0)
    
    logger.info(f"After 30s:")
    logger.info(f"  Max altitude reached: {final_altitude:.1f} m")
    logger.info(f"  Final velocity: {final_velocity:.1f} m/s")
    logger.info(f"  Mission phases: {[p.value for p in mission.phase_history[-5:]]}")
    
    if final_altitude > 1000:  # Should reach at least 1km in 30s
        logger.info("✅ Basic launch appears to be working")
        return True
    else:
        logger.error("❌ Basic launch is not working - rocket not gaining altitude")
        return False

def test_thrust_vector_calculation():
    """Test if thrust vector calculation is working"""
    logger.info("=== Testing Thrust Vector Calculation ===")
    
    config = {
        "launch_latitude": 28.5,
        "launch_azimuth": 90,
        "target_parking_orbit": 200000,
        "gravity_turn_altitude": 1500
    }
    
    rocket = create_saturn_v_rocket()
    mission = Mission(rocket, config)
    
    # Check thrust at launch
    thrust_vector = mission.get_thrust_vector(0.0)
    altitude = mission.get_altitude()
    
    logger.info(f"At launch (t=0s):")
    logger.info(f"  Altitude: {altitude:.1f} m")
    logger.info(f"  Thrust vector: ({thrust_vector.x:.0f}, {thrust_vector.y:.0f}, {thrust_vector.z:.0f}) N")
    logger.info(f"  Thrust magnitude: {thrust_vector.magnitude():.0f} N")
    logger.info(f"  Expected thrust: {rocket.stages[0].thrust_sea_level:.0f} N")
    
    # Check if rocket is thrusting
    is_thrusting = rocket.is_thrusting(0.0, altitude)
    logger.info(f"  Is thrusting: {is_thrusting}")
    
    # Check guidance output
    try:
        import guidance
        pitch_angle = guidance.get_target_pitch_angle(altitude, 400)  # Initial velocity ~400 m/s
        logger.info(f"  Target pitch angle: {pitch_angle:.1f}°")
    except Exception as e:
        logger.error(f"  Guidance error: {e}")
    
    return thrust_vector.magnitude() > 0

def main():
    logger.info("🚀 Starting Rocket Debug Tests")
    
    # Test 1: Basic launch
    basic_works = test_basic_launch()
    
    # Test 2: Thrust vector
    thrust_works = test_thrust_vector_calculation()
    
    if basic_works and thrust_works:
        logger.info("✅ Basic systems appear to be working")
        logger.info("Issue might be with PEG guidance or orbital monitor integration")
    else:
        logger.error("❌ Fundamental rocket systems have issues")
        logger.error("Need to fix basic thrust/guidance before testing PEG")

if __name__ == "__main__":
    main()