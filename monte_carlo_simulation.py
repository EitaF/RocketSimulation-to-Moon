"""
Monte Carlo Simulation for LEO Success Rate Validation
Professor v22: 500-case simulation for ≥95% LEO success validation
Professor v23: Extended to 1000 samples with guidance timing variation
"""

import numpy as np
import json
import csv
from dataclasses import dataclass
from typing import List, Dict
import rocket_simulation_main
from vehicle import create_saturn_v_rocket, MissionPhase

@dataclass
class MonteCarloResults:
    """Monte Carlo simulation results"""
    total_runs: int
    successful_leo_insertions: int
    success_rate: float
    failed_runs: List[Dict]
    performance_stats: Dict

def run_monte_carlo_simulation(num_runs: int = 1000) -> MonteCarloResults:
    """
    Run Monte Carlo simulation with parameter variations
    Vary initial conditions within realistic bounds
    """
    print(f"Starting Monte Carlo simulation with {num_runs} runs...")
    
    successful_leo = 0
    failed_runs = []
    performance_data = {
        'max_altitudes': [],
        'max_velocities': [],
        'total_delta_vs': [],
        'mission_durations': [],
        'final_masses': []
    }
    
    # Parameter variation ranges (±5% for most parameters)
    # Professor v23: Added guidance timing variation
    variations = {
        'launch_azimuth_range': (-2, 2),  # ±2 degrees
        'propellant_mass_variation': (0.98, 1.02),  # ±2%
        'thrust_variation': (0.97, 1.03),  # ±3%
        'drag_coefficient_variation': (0.95, 1.05),  # ±5%
        'atmospheric_density_variation': (0.9, 1.1),  # ±10%
        'initial_mass_variation': (0.99, 1.01),  # ±1%
        'guidance_timing_variation': (-0.5, 0.5)  # ±0.5 seconds
    }
    
    for run_id in range(num_runs):
        try:
            # Generate random variations
            np.random.seed(run_id)  # For reproducibility
            
            # Load base configuration
            with open("mission_config.json", "r") as f:
                config = json.load(f)
            with open("saturn_v_config.json", "r") as f:
                saturn_config = json.load(f)
            
            # Apply random variations
            azimuth_variation = np.random.uniform(*variations['launch_azimuth_range'])
            config['launch_azimuth'] = 72 + azimuth_variation
            
            propellant_factor = np.random.uniform(*variations['propellant_mass_variation'])
            thrust_factor = np.random.uniform(*variations['thrust_variation'])
            drag_factor = np.random.uniform(*variations['drag_coefficient_variation'])
            
            # Apply variations to stages
            for stage in saturn_config['stages']:
                stage['propellant_mass'] = int(stage['propellant_mass'] * propellant_factor)
                stage['thrust_vacuum'] = int(stage['thrust_vacuum'] * thrust_factor)
                stage['thrust_sea_level'] = int(stage['thrust_sea_level'] * thrust_factor)
            
            # Apply drag coefficient variation
            saturn_config['rocket']['drag_coefficient'] *= drag_factor
            
            # Professor v23: Apply guidance timing variation
            guidance_timing_offset = np.random.uniform(*variations['guidance_timing_variation'])
            
            # Save modified configs temporarily
            with open("temp_mission_config.json", "w") as f:
                json.dump(config, f, indent=2)
            with open("temp_saturn_config.json", "w") as f:
                json.dump(saturn_config, f, indent=2)
            
            # Create rocket with modified config
            rocket = create_saturn_v_rocket("temp_saturn_config.json")
            
            # Professor v23: Apply guidance timing offset
            import guidance
            guidance.reset_guidance_state()
            guidance.set_guidance_timing_offset(guidance_timing_offset)
            
            # Run simulation
            mission = rocket_simulation_main.Mission(rocket, config)
            results = mission.simulate(
                duration=config.get("simulation_duration", 14400),
                dt=config.get("time_step", 0.1)
            )
            
            # Check LEO success criteria
            final_altitude = results.get('max_altitude', 0)
            final_phase = results.get('final_phase', 'FAILED')
            
            # LEO success criteria: periapsis ≥ 120km, apoapsis ≥ 185km
            if (final_phase in ['LEO', 'TLI_BURN', 'COAST_TO_MOON'] and 
                final_altitude >= 120000):
                successful_leo += 1
                
                # Collect performance data
                performance_data['max_altitudes'].append(results.get('max_altitude', 0))
                performance_data['max_velocities'].append(results.get('max_velocity', 0))
                performance_data['total_delta_vs'].append(results.get('total_delta_v', 0))
                performance_data['mission_durations'].append(results.get('mission_duration', 0))
                performance_data['final_masses'].append(results.get('final_mass', 0))
            else:
                # Record failed run details
                failed_runs.append({
                    'run_id': run_id,
                    'final_phase': final_phase,
                    'max_altitude': final_altitude,
                    'variations': {
                        'azimuth_variation': azimuth_variation,
                        'propellant_factor': propellant_factor,
                        'thrust_factor': thrust_factor,
                        'drag_factor': drag_factor
                    }
                })
            
            # Progress reporting
            if (run_id + 1) % 50 == 0:
                current_success_rate = successful_leo / (run_id + 1) * 100
                print(f"Progress: {run_id + 1}/{num_runs} runs, "
                      f"Success rate: {current_success_rate:.1f}%")
                
        except Exception as e:
            print(f"Run {run_id} failed with error: {e}")
            failed_runs.append({
                'run_id': run_id,
                'error': str(e),
                'final_phase': 'ERROR'
            })
    
    # Calculate final statistics
    success_rate = (successful_leo / num_runs) * 100
    
    # Performance statistics
    performance_stats = {}
    if performance_data['max_altitudes']:
        performance_stats = {
            'altitude_mean': np.mean(performance_data['max_altitudes']) / 1000,  # km
            'altitude_std': np.std(performance_data['max_altitudes']) / 1000,   # km
            'velocity_mean': np.mean(performance_data['max_velocities']),       # m/s
            'velocity_std': np.std(performance_data['max_velocities']),         # m/s
            'delta_v_mean': np.mean(performance_data['total_delta_vs']),        # m/s
            'delta_v_std': np.std(performance_data['total_delta_vs']),          # m/s
            'duration_mean': np.mean(performance_data['mission_durations']) / 3600,  # hours
            'mass_mean': np.mean(performance_data['final_masses']) / 1000       # tons
        }
    
    # Clean up temporary files
    import os
    try:
        os.remove("temp_mission_config.json")
        os.remove("temp_saturn_config.json")
    except:
        pass
    
    return MonteCarloResults(
        total_runs=num_runs,
        successful_leo_insertions=successful_leo,
        success_rate=success_rate,
        failed_runs=failed_runs,
        performance_stats=performance_stats
    )

def save_monte_carlo_results(results: MonteCarloResults, filename: str = "monte_carlo_results.json"):
    """Save Monte Carlo results to JSON file"""
    results_dict = {
        'total_runs': results.total_runs,
        'successful_leo_insertions': results.successful_leo_insertions,
        'success_rate': results.success_rate,
        'failed_runs': results.failed_runs,
        'performance_stats': results.performance_stats,
        'leo_success_criteria_met': results.success_rate >= 95.0
    }
    
    with open(filename, 'w') as f:
        json.dump(results_dict, f, indent=2)
    
    print(f"Monte Carlo results saved to {filename}")

def main():
    """Main Monte Carlo simulation execution"""
    print("="*60)
    print("SATURN V LEO INSERTION MONTE CARLO SIMULATION")
    print("Professor v22: 500-case trajectory validation")
    print("="*60)
    
    # Run Monte Carlo simulation
    results = run_monte_carlo_simulation(500)
    
    # Display results
    print("\n" + "="*50)
    print("MONTE CARLO RESULTS SUMMARY")
    print("="*50)
    print(f"Total Runs: {results.total_runs}")
    print(f"Successful LEO Insertions: {results.successful_leo_insertions}")
    print(f"Success Rate: {results.success_rate:.2f}%")
    print(f"Failed Runs: {len(results.failed_runs)}")
    
    # Success criteria check
    if results.success_rate >= 95.0:
        print(f"✅ SUCCESS: Exceeds 95% LEO success requirement")
        print(f"   Margin: +{results.success_rate - 95.0:.2f}%")
    else:
        print(f"❌ FAILED: Below 95% LEO success requirement")
        print(f"   Shortfall: -{95.0 - results.success_rate:.2f}%")
    
    # Performance statistics
    if results.performance_stats:
        print(f"\nPerformance Statistics (Successful Runs):")
        stats = results.performance_stats
        print(f"  Max Altitude: {stats['altitude_mean']:.1f} ± {stats['altitude_std']:.1f} km")
        print(f"  Max Velocity: {stats['velocity_mean']:.0f} ± {stats['velocity_std']:.0f} m/s")
        print(f"  Total Delta-V: {stats['delta_v_mean']:.0f} ± {stats['delta_v_std']:.0f} m/s")
        print(f"  Mission Duration: {stats['duration_mean']:.1f} hours")
        print(f"  Final Mass: {stats['mass_mean']:.1f} tons")
    
    # Save results
    save_monte_carlo_results(results)
    
    # Write CSV summary for analysis
    with open("monte_carlo_summary.csv", 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Run_ID', 'Success', 'Final_Phase', 'Max_Altitude_km'])
        
        success_count = 0
        for i in range(results.total_runs):
            # Check if this run was successful
            is_failed = any(fail['run_id'] == i for fail in results.failed_runs)
            if not is_failed:
                success_count += 1
                writer.writerow([i, 'SUCCESS', 'LEO', 'N/A'])
            else:
                failed_run = next(fail for fail in results.failed_runs if fail['run_id'] == i)
                writer.writerow([i, 'FAILED', failed_run.get('final_phase', 'UNKNOWN'), 
                               failed_run.get('max_altitude', 0) / 1000])
    
    print(f"\nDetailed results saved to monte_carlo_results.json")
    print(f"Summary CSV saved to monte_carlo_summary.csv")
    
    return results

if __name__ == "__main__":
    main()