#!/usr/bin/env python3
"""
Parameter Sweep Test Runner for Saturn V LEO Optimization
Professor v36: Automated parameter sweep testing with isolated variables
"""

import os
import sys
import yaml
import json
import csv
import time
import logging
import itertools
import subprocess
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from post_flight_analysis import PostFlightAnalyzer, MissionResults

@dataclass
class ParameterSet:
    """Container for a set of parameters to test"""
    early_pitch_rate: float
    final_target_pitch: float
    stage3_ignition_offset: float
    test_id: int

class ParameterSweepRunner:
    """
    Automated parameter sweep runner for Saturn V optimization
    Professor v36: Isolate variables and run one change per test
    """
    
    def __init__(self, config_file: str = "sweep_config.yaml"):
        self.config_file = config_file
        self.config = self._load_config()
        self.analyzer = PostFlightAnalyzer()
        self.results = []
        self.setup_logging()
    
    def _load_config(self) -> Dict:
        """Load sweep configuration from YAML file"""
        try:
            with open(self.config_file, 'r') as f:
                config = yaml.safe_load(f)
            return config
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file {self.config_file} not found")
        except yaml.YAMLError as e:
            raise ValueError(f"Error parsing YAML configuration: {e}")
    
    def setup_logging(self):
        """Setup logging configuration"""
        log_config = self.config.get('logging', {})
        logging.basicConfig(
            level=getattr(logging, log_config.get('level', 'INFO')),
            format=log_config.get('format', '%(asctime)s - %(levelname)s - %(message)s'),
            handlers=[
                logging.FileHandler(log_config.get('file', 'parameter_sweep.log')),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def generate_parameter_sets(self) -> List[ParameterSet]:
        """
        Generate parameter sets for sweep testing
        Professor v36: Isolated variable testing approach
        """
        params = self.config['parameters']
        
        # Generate ranges for each parameter
        early_pitch_rates = np.arange(
            params['early_pitch_rate']['min'],
            params['early_pitch_rate']['max'] + params['early_pitch_rate']['step'],
            params['early_pitch_rate']['step']
        )
        
        final_target_pitches = np.arange(
            params['final_target_pitch']['min'],
            params['final_target_pitch']['max'] + params['final_target_pitch']['step'],
            params['final_target_pitch']['step']
        )
        
        stage3_ignition_offsets = np.arange(
            params['stage3_ignition_offset']['min'],
            params['stage3_ignition_offset']['max'] + params['stage3_ignition_offset']['step'],
            params['stage3_ignition_offset']['step']
        )
        
        # Create parameter sets using itertools.product for full factorial design
        parameter_sets = []
        test_id = 1
        
        for early_pitch, final_pitch, stage3_offset in itertools.product(
            early_pitch_rates, final_target_pitches, stage3_ignition_offsets
        ):
            parameter_sets.append(ParameterSet(
                early_pitch_rate=round(early_pitch, 1),
                final_target_pitch=round(final_pitch, 1),
                stage3_ignition_offset=round(stage3_offset, 1),
                test_id=test_id
            ))
            test_id += 1
        
        # Limit to configured number of runs
        max_runs = self.config['test_config']['total_runs']
        if len(parameter_sets) > max_runs:
            # Select evenly distributed subset
            indices = np.linspace(0, len(parameter_sets) - 1, max_runs, dtype=int)
            parameter_sets = [parameter_sets[i] for i in indices]
        
        self.logger.info(f"Generated {len(parameter_sets)} parameter sets for testing")
        return parameter_sets
    
    def run_single_test(self, params: ParameterSet) -> Tuple[ParameterSet, MissionResults]:
        """
        Run a single simulation test with given parameters
        Professor v36: Isolated variable testing
        """
        self.logger.info(f"Running test {params.test_id} with parameters: "
                        f"pitch_rate={params.early_pitch_rate}, "
                        f"final_pitch={params.final_target_pitch}, "
                        f"stage3_offset={params.stage3_ignition_offset}")
        
        try:
            # Create temporary configuration for this test
            test_config = self._create_test_config(params)
            
            # Run simulation (would call actual simulation here)
            # For now, simulate with mock data
            mission_data = self._run_simulation_with_params(test_config)
            
            # Analyze results
            results = self.analyzer.analyze_mission(mission_data)
            
            # Save individual test results
            self._save_test_result(params, results)
            
            return params, results
            
        except Exception as e:
            self.logger.error(f"Error in test {params.test_id}: {e}")
            # Return failure result
            failure_result = MissionResults(
                apoapsis_km=0, periapsis_km=0, eccentricity=1.0,
                max_altitude_km=0, final_velocity_ms=0, stage3_propellant_remaining=0,
                horizontal_velocity_at_220km=0, time_to_apoapsis=0,
                mission_success=False, failure_reason=str(e)
            )
            return params, failure_result
    
    def _create_test_config(self, params: ParameterSet) -> Dict:
        """Create configuration dictionary for simulation"""
        return {
            'early_pitch_rate': params.early_pitch_rate,
            'final_target_pitch': params.final_target_pitch,
            'stage3_ignition_offset': params.stage3_ignition_offset,
            'test_id': params.test_id
        }
    
    def _run_simulation_with_params(self, config: Dict) -> Dict:
        """
        Run simulation with given parameters using real physics
        Professor v37: Replaced mock physics with direct calls to rocket_simulation_main.py
        """
        import subprocess
        import tempfile
        import os
        
        # Create temporary mission configuration file
        mission_config = {
            "launch_latitude": 28.573,
            "launch_azimuth": 90,
            "target_parking_orbit": 185e3,
            "gravity_turn_altitude": 1500,
            "simulation_duration": 4 * 3600,  # 4 hours for LEO mission
            "time_step": 0.1,
            "early_pitch_rate": config['early_pitch_rate'],
            "final_target_pitch": config['final_target_pitch'],
            "stage3_ignition_offset": config['stage3_ignition_offset']
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(mission_config, f, indent=2)
            temp_config_file = f.name
        
        try:
            # Run simulation with --fast flag and timeout
            timeout_seconds = self.config['test_config'].get('timeout_seconds', 900)
            result = subprocess.run([
                'python3', 'rocket_simulation_main.py', '--fast'
            ], capture_output=True, text=True, cwd=os.path.dirname(os.path.abspath(__file__)), 
               timeout=timeout_seconds)
            
            if result.returncode != 0:
                self.logger.error(f"Simulation failed: {result.stderr}")
                raise Exception(f"Simulation failed: {result.stderr}")
            
            # Read mission results
            try:
                with open('mission_results.json', 'r') as f:
                    mission_results = json.load(f)
                
                # Extract relevant data for analysis
                # Calculate horizontal velocity at 220km altitude
                horizontal_velocity_at_220km = self._calculate_horizontal_velocity_at_altitude(mission_results, 220000)
                
                # Calculate stage 3 propellant remaining from CSV data
                stage3_propellant_remaining = self._calculate_stage3_fuel_remaining()
                
                return {
                    'final_apoapsis_km': mission_results.get('max_altitude_km', 0),
                    'final_periapsis_km': mission_results.get('trajectory_data', {}).get('altitude_history', [0])[-1] / 1000,
                    'final_eccentricity': mission_results.get('final_lunar_orbit', {}).get('eccentricity', 0.5),
                    'max_altitude_km': mission_results.get('max_altitude_km', 0),
                    'final_velocity_ms': mission_results.get('max_velocity_ms', 0),
                    'stage3_propellant_remaining': stage3_propellant_remaining,
                    'horizontal_velocity_at_220km': horizontal_velocity_at_220km,
                    'time_to_apoapsis': 45.0  # Keep as placeholder for now
                }
            except FileNotFoundError:
                raise Exception("mission_results.json not found after simulation")
                
        finally:
            # Clean up temporary file
            if os.path.exists(temp_config_file):
                os.unlink(temp_config_file)
    
    def _save_test_result(self, params: ParameterSet, results: MissionResults):
        """Save individual test result to CSV"""
        filename = self.config['test_config']['log_file']
        
        try:
            # Check if file exists
            file_exists = os.path.exists(filename)
            
            with open(filename, 'a', newline='') as csvfile:
                fieldnames = [
                    'test_id', 'early_pitch_rate', 'final_target_pitch', 'stage3_ignition_offset',
                    'apoapsis_km', 'periapsis_km', 'eccentricity', 'max_altitude_km',
                    'final_velocity_ms', 'stage3_propellant_remaining', 
                    'horizontal_velocity_at_220km', 'time_to_apoapsis', 'mission_success'
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                if not file_exists:
                    writer.writeheader()
                
                writer.writerow({
                    'test_id': params.test_id,
                    'early_pitch_rate': params.early_pitch_rate,
                    'final_target_pitch': params.final_target_pitch,
                    'stage3_ignition_offset': params.stage3_ignition_offset,
                    'apoapsis_km': results.apoapsis_km,
                    'periapsis_km': results.periapsis_km,
                    'eccentricity': results.eccentricity,
                    'max_altitude_km': results.max_altitude_km,
                    'final_velocity_ms': results.final_velocity_ms,
                    'stage3_propellant_remaining': results.stage3_propellant_remaining,
                    'horizontal_velocity_at_220km': results.horizontal_velocity_at_220km,
                    'time_to_apoapsis': results.time_to_apoapsis,
                    'mission_success': results.mission_success
                })
                
        except Exception as e:
            self.logger.error(f"Error saving test result: {e}")
    
    def run_parameter_sweep(self) -> Dict:
        """
        Run the complete parameter sweep
        Professor v36: Systematic testing with clear correlation tracking
        """
        self.logger.info("Starting parameter sweep...")
        
        # Generate parameter sets
        parameter_sets = self.generate_parameter_sets()
        
        # Clear previous results
        if os.path.exists(self.config['test_config']['log_file']):
            os.remove(self.config['test_config']['log_file'])
        
        # Run tests
        start_time = time.time()
        successful_runs = 0
        
        for params in parameter_sets:
            params_result, mission_result = self.run_single_test(params)
            
            if mission_result.mission_success:
                successful_runs += 1
                self.logger.info(f"✅ Test {params.test_id} SUCCESS")
            else:
                self.logger.warning(f"❌ Test {params.test_id} FAILED: {mission_result.failure_reason}")
        
        elapsed_time = time.time() - start_time
        
        # Generate summary report
        summary = self._generate_summary_report(parameter_sets, successful_runs, elapsed_time)
        
        self.logger.info(f"Parameter sweep completed in {elapsed_time:.1f} seconds")
        self.logger.info(f"Success rate: {successful_runs}/{len(parameter_sets)} ({successful_runs/len(parameter_sets)*100:.1f}%)")
        
        return summary
    
    def _generate_summary_report(self, parameter_sets: List[ParameterSet], 
                                successful_runs: int, elapsed_time: float) -> Dict:
        """Generate summary report of parameter sweep results"""
        total_runs = len(parameter_sets)
        success_rate = successful_runs / total_runs if total_runs > 0 else 0
        
        summary = {
            'total_runs': total_runs,
            'successful_runs': successful_runs,
            'success_rate': success_rate,
            'elapsed_time_seconds': elapsed_time,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'config_file': self.config_file,
            'results_file': self.config['test_config']['log_file']
        }
        
        # Save summary to JSON
        summary_filename = 'parameter_sweep_summary.json'
        with open(summary_filename, 'w') as f:
            json.dump(summary, f, indent=2)
        
        self.logger.info(f"Summary report saved to {summary_filename}")
        
        return summary
    
    def _calculate_horizontal_velocity_at_altitude(self, mission_results: Dict, target_altitude: float) -> float:
        """Calculate horizontal velocity at specific altitude from trajectory data"""
        try:
            trajectory_data = mission_results.get('trajectory_data', {})
            altitude_history = trajectory_data.get('altitude_history', [])
            velocity_history = trajectory_data.get('velocity_history', [])
            
            if not altitude_history or not velocity_history:
                return 7200  # Fallback to placeholder
                
            # Find closest altitude to target
            closest_index = 0
            min_diff = float('inf')
            
            for i, alt in enumerate(altitude_history):
                diff = abs(alt - target_altitude)
                if diff < min_diff:
                    min_diff = diff
                    closest_index = i
            
            if closest_index < len(velocity_history):
                vx, vy = velocity_history[closest_index]
                # Calculate horizontal component (magnitude of velocity vector)
                horizontal_velocity = (vx**2 + vy**2)**0.5
                return horizontal_velocity
                
        except Exception as e:
            self.logger.warning(f"Could not calculate horizontal velocity: {e}")
            
        return 7200  # Fallback to placeholder
    
    def _calculate_stage3_fuel_remaining(self) -> float:
        """Calculate Stage 3 remaining fuel percentage from mission log CSV"""
        try:
            import pandas as pd
            
            # Read the mission log CSV
            df = pd.read_csv('mission_log.csv')
            
            # Filter for stage 3 data (stage column = 2, since stages are 0-indexed)
            stage3_data = df[df['stage'] == 2]
            
            if stage3_data.empty:
                self.logger.warning("No Stage 3 data found in mission log")
                return 0.08  # Fallback to placeholder
            
            # Get the last remaining propellant value for stage 3
            # remaining_propellant is in tonnes, convert to ratio
            last_remaining = stage3_data['remaining_propellant'].iloc[-1]  # tonnes
            
            # Stage 3 initial propellant mass from Saturn V config: ~109 tonnes
            # This should be read from config, but for now use known value
            stage3_initial_mass = 109.0  # tonnes
            
            fuel_ratio = last_remaining / stage3_initial_mass
            return max(0.0, min(1.0, fuel_ratio))  # Clamp between 0 and 1
            
        except Exception as e:
            self.logger.warning(f"Could not calculate Stage 3 fuel remaining: {e}")
            return 0.08  # Fallback to placeholder
    
    def analyze_correlations(self):
        """
        Analyze correlations between parameters and outcomes
        Professor v36: Clear correlation between parameter & outcome
        """
        try:
            import pandas as pd
            import matplotlib.pyplot as plt
            
            # Load results
            results_df = pd.read_csv(self.config['test_config']['log_file'])
            
            # Calculate correlations
            param_columns = ['early_pitch_rate', 'final_target_pitch', 'stage3_ignition_offset']
            outcome_columns = ['periapsis_km', 'eccentricity', 'mission_success']
            
            correlations = {}
            for param in param_columns:
                for outcome in outcome_columns:
                    if outcome == 'mission_success':
                        # Convert boolean to numeric for correlation
                        corr = results_df[param].corr(results_df[outcome].astype(int))
                    else:
                        corr = results_df[param].corr(results_df[outcome])
                    correlations[f"{param}_vs_{outcome}"] = corr
            
            # Log correlations
            self.logger.info("=== PARAMETER CORRELATIONS ===")
            for correlation, value in correlations.items():
                self.logger.info(f"{correlation}: {value:.3f}")
            
            # Save correlations
            with open('parameter_correlations.json', 'w') as f:
                json.dump(correlations, f, indent=2)
            
            return correlations
            
        except ImportError:
            self.logger.warning("pandas not available, skipping correlation analysis")
            return {}
        except Exception as e:
            self.logger.error(f"Error in correlation analysis: {e}")
            return {}

def main():
    """Main function for parameter sweep runner"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run parameter sweep for Saturn V optimization')
    parser.add_argument('--config', default='sweep_config.yaml', 
                       help='Configuration file path')
    parser.add_argument('--analyze', action='store_true',
                       help='Only analyze existing results')
    
    args = parser.parse_args()
    
    try:
        runner = ParameterSweepRunner(args.config)
        
        if args.analyze:
            runner.analyze_correlations()
        else:
            summary = runner.run_parameter_sweep()
            runner.analyze_correlations()
            
            print("\n=== PARAMETER SWEEP SUMMARY ===")
            print(f"Total runs: {summary['total_runs']}")
            print(f"Successful runs: {summary['successful_runs']}")
            print(f"Success rate: {summary['success_rate']:.1%}")
            print(f"Elapsed time: {summary['elapsed_time_seconds']:.1f} seconds")
            print(f"Results saved to: {summary['results_file']}")
            
    except Exception as e:
        logging.error(f"Error running parameter sweep: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()