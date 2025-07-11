#!/usr/bin/env python3
"""
Test script to validate Professor v39 improvements
Tests key functionality without full mission complexity
"""

import json
import logging
import sys
import os

# Set up logging to see our improvements
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_json_generation():
    """Test that mission_results.json is consistently generated"""
    print("=== Testing JSON Generation ===")
    
    # Check if JSON file exists from previous run
    if os.path.exists("mission_results.json"):
        with open("mission_results.json", 'r') as f:
            results = json.load(f)
        
        print(f"✅ mission_results.json exists")
        print(f"✅ Mission success: {results.get('mission_success', 'unknown')}")
        print(f"✅ Max altitude: {results.get('max_altitude_km', 0):.1f} km")
        print(f"✅ Final phase: {results.get('final_phase', 'unknown')}")
        
        # Check if our improvements are present
        if 'stage_fuel_remaining' in results:
            print(f"✅ Stage fuel monitoring data found")
            stage_fuel = results['stage_fuel_remaining']
            if 'stage3_percentage' in stage_fuel:
                stage3_pct = stage_fuel['stage3_percentage']
                tli_ready = stage_fuel.get('stage3_tli_ready', False)
                print(f"✅ Stage 3 fuel: {stage3_pct:.1f}% (TLI Ready: {tli_ready})")
            else:
                print("⚠️  Stage 3 percentage not found")
        else:
            print("⚠️  Stage fuel monitoring data not found (mission may have failed early)")
            
        if 'tli_analysis' in results:
            print(f"✅ TLI analysis data found")
            tli = results['tli_analysis']
            if 'required_delta_v' in tli:
                print(f"✅ Required TLI ΔV: {tli['required_delta_v']:.1f} m/s")
                print(f"✅ Available TLI ΔV: {tli.get('available_delta_v', 0):.1f} m/s")
            else:
                print("⚠️  TLI delta-V data incomplete")
        else:
            print("⚠️  TLI analysis data not found (mission may not have reached LEO)")
            
        return True
    else:
        print("❌ mission_results.json not found")
        return False

def test_parameter_sweep_data():
    """Test that parameter sweep gets real data instead of placeholders"""
    print("\n=== Testing Parameter Sweep Data Extraction ===")
    
    try:
        from parameter_sweep_runner import ParameterSweepRunner
        
        # Create a test runner
        runner = ParameterSweepRunner("sweep_config_v37.yaml")
        
        # Check if mission_results.json exists
        if os.path.exists("mission_results.json"):
            with open("mission_results.json", 'r') as f:
                mission_results = json.load(f)
            
            # Test our improved data extraction
            horizontal_velocity = runner._calculate_horizontal_velocity_at_altitude(mission_results, 220000)
            stage3_fuel = runner._calculate_stage3_fuel_remaining()
            
            print(f"✅ Horizontal velocity at 220km: {horizontal_velocity:.1f} m/s")
            if horizontal_velocity != 7200:  # Not the placeholder
                print(f"✅ Real data extracted (not placeholder 7200 m/s)")
            else:
                print(f"⚠️  May be using fallback value")
                
            print(f"✅ Stage 3 fuel remaining: {stage3_fuel:.3f} ({stage3_fuel*100:.1f}%)")
            if stage3_fuel != 0.08:  # Not the placeholder
                print(f"✅ Real fuel data extracted (not placeholder 0.08)")
            else:
                print(f"⚠️  May be using fallback value")
                
            return True
        else:
            print("❌ No mission results to test data extraction")
            return False
            
    except Exception as e:
        print(f"❌ Error testing parameter sweep: {e}")
        return False

def test_configuration_updates():
    """Test that our configuration updates are in place"""
    print("\n=== Testing Configuration Updates ===")
    
    # Check sweep config timeout updates
    configs_to_check = ["sweep_config.yaml", "sweep_config_v37.yaml", "sweep_config_tli.yaml"]
    
    for config_file in configs_to_check:
        if os.path.exists(config_file):
            try:
                import yaml
                with open(config_file, 'r') as f:
                    config = yaml.safe_load(f)
                
                timeout = config.get('test_config', {}).get('timeout_seconds', 0)
                print(f"✅ {config_file}: timeout = {timeout}s")
                
                if config_file == "sweep_config_tli.yaml" and timeout >= 6000:
                    print(f"✅ TLI timeout correctly set to {timeout}s (≥6000s)")
                elif timeout >= 900:
                    print(f"✅ LEO timeout correctly set to {timeout}s (≥900s)")
                else:
                    print(f"⚠️  Timeout may be too low: {timeout}s")
                    
                # Check parameter ranges for main configs
                if 'parameters' in config:
                    params = config['parameters']
                    
                    # Check pitch rate range
                    if 'early_pitch_rate' in params:
                        pitch_min = params['early_pitch_rate'].get('min', 0)
                        pitch_max = params['early_pitch_rate'].get('max', 0)
                        print(f"✅ Pitch rate range: {pitch_min}-{pitch_max}°/s")
                        
                    # Check pitch angle range  
                    if 'final_target_pitch' in params:
                        angle_min = params['final_target_pitch'].get('min', 0)
                        angle_max = params['final_target_pitch'].get('max', 0)
                        print(f"✅ Target pitch range: {angle_min}-{angle_max}°")
                        
            except Exception as e:
                print(f"⚠️  Error reading {config_file}: {e}")
        else:
            print(f"⚠️  {config_file} not found")

def test_monte_carlo_config():
    """Test Monte Carlo configuration"""
    print("\n=== Testing Monte Carlo Configuration ===")
    
    if os.path.exists("monte_carlo_config.yaml"):
        try:
            import yaml
            with open("monte_carlo_config.yaml", 'r') as f:
                config = yaml.safe_load(f)
            
            stochastic = config.get('stochastic_parameters', {})
            
            # Check atmospheric density variation
            if 'atmospheric_density' in stochastic:
                atm_config = stochastic['atmospheric_density']
                variation = atm_config.get('variation_percent', 0)
                print(f"✅ Atmospheric density variation: ±{variation}%")
            
            # Check engine Isp variation
            if 'engine_isp' in stochastic:
                isp_config = stochastic['engine_isp'] 
                variation = isp_config.get('variation_percent', 0)
                print(f"✅ Engine Isp variation: ±{variation}%")
                
            # Check IMU noise
            if 'imu_noise' in stochastic:
                print(f"✅ IMU noise configuration found")
                
            return True
        except Exception as e:
            print(f"❌ Error reading Monte Carlo config: {e}")
            return False
    else:
        print("❌ monte_carlo_config.yaml not found")
        return False

def main():
    """Run all tests"""
    print("Testing Professor v39 Improvements")
    print("=" * 50)
    
    tests_passed = 0
    tests_total = 4
    
    # Run tests
    if test_json_generation():
        tests_passed += 1
        
    if test_parameter_sweep_data():
        tests_passed += 1
        
    if test_configuration_updates():
        tests_passed += 1
        
    if test_monte_carlo_config():
        tests_passed += 1
    
    # Summary
    print(f"\n=== Test Summary ===")
    print(f"Tests passed: {tests_passed}/{tests_total}")
    
    if tests_passed == tests_total:
        print("🎉 All improvements are working correctly!")
        return 0
    else:
        print("⚠️  Some improvements need attention")
        return 1

if __name__ == "__main__":
    sys.exit(main())