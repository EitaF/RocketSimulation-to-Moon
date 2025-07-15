#!/usr/bin/env python3
"""
Quick test to validate burn termination and fuel conservation improvements
Uses a known good parameter set to test the improvements
"""

import subprocess
import json
import tempfile
import os

def create_test_config():
    """Create a test mission config with parameters that should work"""
    config = {
        "launch_latitude": 28.5,
        "early_pitch_rate": 1.65,  # Good middle value
        "final_target_pitch": 8.0,  # Good middle value
        "stage3_ignition_offset": -25.0,  # Good middle value
        "simulation_duration": 3600,  # 1 hour
        "time_step": 0.1,
        "verbose_abort": True,
        "abort_thresholds": {
            "earth_impact_altitude": -100.0,
            "propellant_critical_percent": 99.5,
            "min_safe_time": 5.0,
            "max_flight_path_angle": 85.0,
            "min_thrust_threshold": 5000.0
        }
    }
    return config

def run_test_mission():
    """Run a single test mission with good parameters"""
    print("=== Running Test Mission with Optimized Parameters ===")
    
    # Create test config
    config = create_test_config()
    
    # Write to temporary config file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config, f, indent=2)
        temp_config = f.name
    
    try:
        # Save original config if it exists
        original_config = None
        if os.path.exists("mission_config.json"):
            with open("mission_config.json", 'r') as f:
                original_config = json.load(f)
        
        # Copy our test config to mission_config.json
        with open("mission_config.json", 'w') as f:
            json.dump(config, f, indent=2)
        
        # Run simulation
        result = subprocess.run([
            'python3', 'rocket_simulation_main.py', '--fast'
        ], capture_output=True, text=True, timeout=300)
        
        print(f"Return code: {result.returncode}")
        if result.returncode != 0:
            print("STDERR:", result.stderr)
            return False
        
        # Check results
        if os.path.exists("mission_results.json"):
            with open("mission_results.json", 'r') as f:
                results = json.load(f)
            
            success = results.get('mission_success', False)
            max_alt = results.get('max_altitude_km', 0)
            final_phase = results.get('final_phase', 'unknown')
            
            print(f"Mission Success: {success}")
            print(f"Max Altitude: {max_alt:.1f} km") 
            print(f"Final Phase: {final_phase}")
            
            # Check our improvements
            if 'stage_fuel_remaining' in results:
                stage_fuel = results['stage_fuel_remaining']
                print(f"✅ Stage fuel data found")
                
                if 'stage3_percentage' in stage_fuel:
                    stage3_pct = stage_fuel['stage3_percentage']
                    tli_ready = stage_fuel.get('stage3_tli_ready', False)
                    print(f"Stage 3 fuel: {stage3_pct:.1f}% (TLI Ready: {tli_ready})")
                    
                    if stage3_pct >= 30.0:
                        print("✅ FUEL CONSERVATION SUCCESS: >30% Stage 3 fuel remaining!")
                    else:
                        print(f"⚠️  Fuel conservation needs improvement: {stage3_pct:.1f}% < 30%")
            
            if 'tli_analysis' in results:
                tli = results['tli_analysis']
                print(f"✅ TLI analysis found")
                print(f"Required ΔV: {tli.get('required_delta_v', 0):.1f} m/s")
                print(f"Available ΔV: {tli.get('available_delta_v', 0):.1f} m/s")
                print(f"TLI Ready: {tli.get('tli_ready', False)}")
            
            return success
        else:
            print("❌ No mission_results.json found")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Mission timed out")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        # Restore original config
        if original_config:
            with open("mission_config.json", 'w') as f:
                json.dump(original_config, f, indent=2)
        
        # Clean up temp file
        if os.path.exists(temp_config):
            os.unlink(temp_config)

def check_burn_termination_logs():
    """Check logs for evidence of improved burn termination"""
    print("\n=== Checking Burn Termination Logic ===")
    
    try:
        with open("mission_log.csv", 'r') as f:
            lines = f.readlines()
        
        # Look for circularization phase
        circ_lines = [line for line in lines if 'circularization' in line.lower()]
        
        if circ_lines:
            print(f"Found {len(circ_lines)} circularization log entries")
            
            # Check last few entries for fuel levels
            for line in circ_lines[-5:]:
                parts = line.strip().split(',')
                if len(parts) > 12:  # remaining_propellant is column 12
                    time = parts[0]
                    fuel = parts[12]
                    phase = parts[5]
                    print(f"t={time}s, fuel={fuel}t, phase={phase}")
            
            return True
        else:
            print("⚠️  No circularization phase found in logs")
            return False
            
    except Exception as e:
        print(f"❌ Error reading logs: {e}")
        return False

if __name__ == "__main__":
    success = run_test_mission()
    check_burn_termination_logs()
    
    if success:
        print("\n🎉 Test mission completed successfully!")
    else:
        print("\n⚠️  Test mission needs debugging")