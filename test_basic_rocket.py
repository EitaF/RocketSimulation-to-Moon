#!/usr/bin/env python3
"""
Test Basic Rocket - Test with minimal modifications to isolate issues
"""

import sys
import os
import logging

# Add project root to path  
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from vehicle import create_saturn_v_rocket
import json

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_rocket_creation():
    """Test if rocket creation works correctly"""
    logger.info("=== Testing Rocket Creation ===")
    
    rocket = create_saturn_v_rocket()
    
    logger.info(f"Rocket created successfully")
    logger.info(f"Total mass: {rocket.total_mass/1000:.1f} tons")
    logger.info(f"Number of stages: {len(rocket.stages)}")
    
    for i, stage in enumerate(rocket.stages):
        thrust_sl = stage.thrust_sea_level if hasattr(stage, 'thrust_sea_level') else 0
        logger.info(f"Stage {i+1}: {thrust_sl/1000:.0f} kN thrust")
    
    # Test basic properties
    assert rocket.total_mass > 0, "Rocket should have mass"
    assert len(rocket.stages) > 0, "Rocket should have stages"
    assert rocket.stages[0].thrust_sea_level > 0, "First stage should have thrust"
    
    logger.info("✅ Rocket creation test passed")
    return True

def test_thrust_calculation():
    """Test thrust calculation at different altitudes"""
    logger.info("=== Testing Thrust Calculation ===")
    
    rocket = create_saturn_v_rocket()
    stage1 = rocket.stages[0]
    
    # Test thrust at different altitudes
    altitudes = [0, 10000, 20000, 50000]
    
    for alt in altitudes:
        thrust = stage1.get_thrust(alt)
        is_thrusting = rocket.is_thrusting(0.0, alt)  # t=0, so should be thrusting
        logger.info(f"Altitude {alt/1000:.0f}km: Thrust={thrust/1000:.0f}kN, Thrusting={is_thrusting}")
    
    # Should have maximum thrust at sea level
    assert stage1.get_thrust(0) > 0, "Should have thrust at sea level"
    
    logger.info("✅ Thrust calculation test passed")
    return True

def main():
    logger.info("🔧 Testing Basic Rocket Components")
    
    try:
        # Test 1: Rocket creation
        rocket_ok = test_rocket_creation()
        
        # Test 2: Thrust calculation  
        thrust_ok = test_thrust_calculation()
        
        if rocket_ok and thrust_ok:
            logger.info("✅ All basic rocket tests passed")
            logger.info("The issue is likely in the simulation loop or guidance integration")
        else:
            logger.error("❌ Basic rocket components have issues")
            
    except Exception as e:
        logger.error(f"Test failed with exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()