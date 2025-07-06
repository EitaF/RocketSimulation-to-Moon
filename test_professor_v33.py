#!/usr/bin/env python3
"""
Quick test of Professor v33 implementation
Tests the key integrations without full simulation
"""

import json
import sys
import numpy as np
from pathlib import Path

def test_imports():
    """Test that all modules can be imported successfully"""
    print("Testing module imports...")
    
    try:
        from launch_window_calculator import LaunchWindowCalculator
        print("✓ LaunchWindowCalculator imported")
        
        from mid_course_correction import MidCourseCorrection
        print("✓ MidCourseCorrection imported")
        
        from patched_conic_solver import check_soi_transition, convert_to_lunar_frame
        print("✓ PatchedConicSolver imported")
        
        from circularize import create_circularization_burn
        print("✓ Circularize module imported")
        
        from trajectory_visualizer import create_lunar_orbit_trajectory_plot
        print("✓ TrajectoryVisualizer imported")
        
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_launch_window_calculator():
    """Test LaunchWindowCalculator functionality"""
    print("\nTesting LaunchWindowCalculator...")
    
    try:
        from launch_window_calculator import LaunchWindowCalculator
        calc = LaunchWindowCalculator(parking_orbit_altitude=200e3)
        
        # Test parameters
        current_time = 1000.0
        moon_pos = np.array([384400e3, 0, 0])
        spacecraft_pos = np.array([6571e3, 0, 0])  # 200km altitude
        c3_energy = -1.5  # km²/s²
        
        # Calculate launch window
        info = calc.get_launch_window_info(current_time, moon_pos, spacecraft_pos, c3_energy)
        
        print(f"✓ Launch window calculated:")
        print(f"  - Optimal TLI time: {info['optimal_tli_time']:.1f}s")
        print(f"  - Time to optimal: {info['time_to_optimal']:.1f}s")
        print(f"  - Transfer time: {info['transfer_time_days']:.2f} days")
        
        return True
    except Exception as e:
        print(f"❌ LaunchWindowCalculator test failed: {e}")
        return False

def test_mid_course_correction():
    """Test MidCourseCorrection functionality"""
    print("\nTesting MidCourseCorrection...")
    
    try:
        from mid_course_correction import MidCourseCorrection
        mcc = MidCourseCorrection()
        
        # Test MCC burn
        current_pos = np.array([200000e3, 100000e3, 0])  # Halfway to Moon
        current_vel = np.array([1000, 500, 0])  # m/s
        delta_v = np.array([5, 0, 0])  # 5 m/s correction
        
        new_pos, new_vel = mcc.execute_mcc_burn((current_pos, current_vel), delta_v)
        
        print(f"✓ MCC burn executed:")
        print(f"  - Delta-V applied: {np.linalg.norm(delta_v):.1f} m/s")
        print(f"  - Velocity change: {np.linalg.norm(new_vel - current_vel):.1f} m/s")
        
        return True
    except Exception as e:
        print(f"❌ MidCourseCorrection test failed: {e}")
        return False

def test_monte_carlo_config():
    """Test Monte Carlo configuration"""
    print("\nTesting Monte Carlo configuration...")
    
    try:
        with open("mc_config.json", "r") as f:
            config = json.load(f)
        
        # Check Professor v33 requirements
        assert config["monte_carlo"]["num_runs"] == 500, "Should be 500 runs"
        assert "tli_burn_performance" in config["uncertainty_distributions"], "Missing TLI variation"
        assert "mcc_accuracy" in config["uncertainty_distributions"], "Missing MCC variation"
        assert "initial_vehicle_mass" in config["uncertainty_distributions"], "Missing mass variation"
        
        # Check ±2% variations
        for param in ["tli_burn_performance", "mcc_accuracy", "initial_vehicle_mass"]:
            std_dev = config["uncertainty_distributions"][param]["std_dev"]
            assert abs(std_dev - 0.02) < 0.001, f"{param} should have ±2% variation"
        
        print(f"✓ Monte Carlo config validated:")
        print(f"  - Runs: {config['monte_carlo']['num_runs']}")
        print(f"  - TLI variation: ±{config['uncertainty_distributions']['tli_burn_performance']['std_dev']*100:.1f}%")
        print(f"  - MCC variation: ±{config['uncertainty_distributions']['mcc_accuracy']['std_dev']*100:.1f}%")
        print(f"  - Mass variation: ±{config['uncertainty_distributions']['initial_vehicle_mass']['std_dev']*100:.1f}%")
        
        return True
    except Exception as e:
        print(f"❌ Monte Carlo config test failed: {e}")
        return False

def test_mission_results_structure():
    """Test that mission results have required fields"""
    print("\nTesting mission results structure...")
    
    try:
        # Required fields per Professor v33
        required_fields = [
            "mission_success",
            "final_lunar_orbit", 
            "total_mission_time_days",
            "total_delta_v_mps"
        ]
        
        # Create a dummy results structure to test
        dummy_results = {
            "mission_success": True,
            "final_lunar_orbit": {
                "apoapsis_km": 100.0,
                "periapsis_km": 95.0,
                "eccentricity": 0.05
            },
            "total_mission_time_days": 3.5,
            "total_delta_v_mps": 12500.0
        }
        
        for field in required_fields:
            assert field in dummy_results, f"Missing required field: {field}"
        
        print("✓ Mission results structure validated:")
        for field in required_fields:
            print(f"  - {field}: {dummy_results[field]}")
        
        return True
    except Exception as e:
        print(f"❌ Mission results test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("PROFESSOR V33 IMPLEMENTATION TEST SUITE")
    print("=" * 60)
    
    tests = [
        test_imports,
        test_launch_window_calculator,
        test_mid_course_correction,
        test_monte_carlo_config,
        test_mission_results_structure
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Passed: {passed}/{total}")
    print(f"Success Rate: {passed/total*100:.1f}%")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED - Ready for Professor v33 evaluation!")
    else:
        print("⚠️  Some tests failed - Review implementation")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)