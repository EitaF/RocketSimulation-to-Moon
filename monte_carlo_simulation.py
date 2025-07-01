"""
Monte Carlo Simulation Orchestrator
Implements end-to-end Monte Carlo campaign for mission reliability assessment
Task 1-1 to 1-5: Complete MC framework with config-driven parameters
"""

import json
import numpy as np
import logging
import multiprocessing as mp
from pathlib import Path
from typing import Dict, List, Tuple, Any
import argparse
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
import time
import csv
from dataclasses import dataclass

from metrics_logger import MetricsLogger, extract_metrics_from_mission_results
import rocket_simulation_main
from vehicle import create_saturn_v_rocket

class MonteCarloOrchestrator:
    """Orchestrates Monte Carlo simulation campaign"""
    
    def __init__(self, config_path: str = "mc_config.json"):
        self.config_path = config_path
        self.config = self._load_config()
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('monte_carlo.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Initialize metrics logger
        self.metrics_logger = MetricsLogger(self.config['monte_carlo']['output_dir'])
        
        # Campaign state management
        self.output_dir = Path(self.config['monte_carlo']['output_dir'])
        self.state_file = self.output_dir / 'campaign_state.json'
        self.save_interval = self.config['monte_carlo'].get('state_save_interval', 10)
        
        # Set random seed for reproducibility
        np.random.seed(self.config['monte_carlo']['seed'])
    
    def _load_config(self) -> Dict:
        """Load Monte Carlo configuration"""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            self.logger.error(f"Configuration file {self.config_path} not found")
            raise
    
    def _save_campaign_state(self, completed_runs: int) -> None:
        """Save campaign state for resumption"""
        state = {
            'completed_runs': completed_runs,
            'random_state': np.random.get_state(),
            'timestamp': time.time(),
            'config_path': self.config_path
        }
        
        # Convert numpy arrays to lists for JSON serialization
        random_state = list(state['random_state'])
        random_state[1] = random_state[1].tolist()  # Convert numpy array to list
        state['random_state'] = random_state
        
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
            self.logger.debug(f"Campaign state saved: {completed_runs} runs completed")
        except Exception as e:
            self.logger.warning(f"Failed to save campaign state: {e}")
    
    def _load_campaign_state(self) -> Dict:
        """Load campaign state for resumption"""
        try:
            with open(self.state_file, 'r') as f:
                state = json.load(f)
            
            # Convert lists back to numpy format
            random_state = state['random_state']
            random_state[1] = np.array(random_state[1], dtype=np.uint32)
            state['random_state'] = tuple(random_state)
            
            return state
        except FileNotFoundError:
            return None
        except Exception as e:
            self.logger.error(f"Failed to load campaign state: {e}")
            return None
    
    def _clear_campaign_state(self) -> None:
        """Clear campaign state file"""
        try:
            if self.state_file.exists():
                self.state_file.unlink()
                self.logger.debug("Campaign state file cleared")
        except Exception as e:
            self.logger.warning(f"Failed to clear campaign state: {e}")
    
    def _generate_parameter_variations(self, run_id: int) -> Dict:
        """Generate parameter variations for a single run"""
        variations = {'run_id': run_id}
        
        # Set per-run random seed for reproducibility
        run_seed = self.config['monte_carlo']['seed'] + run_id
        np.random.seed(run_seed)
        
        distributions = self.config['uncertainty_distributions']
        
        # Launch azimuth variation
        if 'launch_azimuth' in distributions:
            dist = distributions['launch_azimuth']
            if dist['type'] == 'normal':
                variations['launch_azimuth'] = np.random.normal(
                    dist['mean'], dist['std_dev']
                )
        
        # Pitch timing variation
        if 'pitch_timing' in distributions:
            dist = distributions['pitch_timing']
            if dist['type'] == 'normal':
                variations['pitch_timing_offset'] = np.random.normal(
                    dist['mean'], dist['std_dev']
                )
        
        # Stage delta-V variation (multiplier)
        if 'stage_delta_v' in distributions:
            dist = distributions['stage_delta_v']
            if dist['type'] == 'normal':
                variations['stage_dv_multiplier'] = np.random.normal(
                    dist['mean'], dist['std_dev']
                )
        
        # Sensor noise variations
        if 'sensor_noise' in distributions:
            sensor_noise = distributions['sensor_noise']
            variations['sensor_noise'] = {}
            
            for sensor_type, noise_dist in sensor_noise.items():
                if noise_dist['type'] == 'normal':
                    variations['sensor_noise'][sensor_type] = np.random.normal(
                        noise_dist['mean'], noise_dist['std_dev']
                    )
        
        return variations
    
    def _apply_variations_to_config(self, base_config: Dict, variations: Dict) -> Dict:
        """Apply parameter variations to mission configuration"""
        config = base_config.copy()
        
        # Apply launch azimuth variation
        if 'launch_azimuth' in variations:
            config['launch_azimuth'] = variations['launch_azimuth']
        
        # Apply gravity turn timing variation
        if 'pitch_timing_offset' in variations:
            base_gravity_turn_alt = config.get('gravity_turn_altitude', 1500)
            # Convert timing offset to altitude offset (rough approximation)
            altitude_offset = variations['pitch_timing_offset'] * 100  # 100 m/s
            config['gravity_turn_altitude'] = max(500, base_gravity_turn_alt + altitude_offset)
        
        # Apply stage performance variations
        if 'stage_dv_multiplier' in variations:
            config['stage_performance_multiplier'] = variations['stage_dv_multiplier']
        
        # Apply sensor noise
        if 'sensor_noise' in variations:
            config['sensor_noise'] = variations['sensor_noise']
        
        # Add run-specific identifiers
        config['run_id'] = variations['run_id']
        config['mc_variations'] = variations
        
        return config
    
    def _run_single_simulation(self, run_config: Tuple[int, Dict]) -> Tuple[int, Dict, Dict]:
        """Run a single Monte Carlo simulation"""
        run_id, config = run_config
        
        try:
            # Create rocket with potential variations
            rocket = create_saturn_v_rocket()
            
            # Apply stage performance variations if specified
            if 'stage_performance_multiplier' in config:
                multiplier = config['stage_performance_multiplier']
                for stage in rocket.stages:
                    # Vary propellant mass to simulate performance uncertainty
                    stage.propellant_mass *= multiplier
            
            # Create and run mission
            mission = rocket_simulation_main.Mission(rocket, config)
            results = mission.simulate(
                duration=config.get("simulation_duration", 10 * 24 * 3600),
                dt=config.get("time_step", 0.1)
            )
            
            # Add variation info to results
            results['mc_variations'] = config.get('mc_variations', {})
            results['run_id'] = run_id
            
            return run_id, results, config
            
        except Exception as e:
            # Handle simulation failures
            error_result = {
                'mission_success': False,
                'final_phase': 'simulation_error',
                'abort_reason': f'Simulation error: {str(e)}',
                'run_id': run_id,
                'mc_variations': config.get('mc_variations', {})
            }
            return run_id, error_result, config
    
    def run_campaign(self, batch_start: int = 0, batch_end: int = None, resume: bool = False) -> str:
        """Run Monte Carlo campaign"""
        total_runs = self.config['monte_carlo']['num_runs']
        batch_size = self.config['monte_carlo']['batch_size']
        
        if batch_end is None:
            batch_end = total_runs
        
        # Handle campaign resumption
        if resume:
            state = self._load_campaign_state()
            if state:
                batch_start = state['completed_runs']
                np.random.set_state(state['random_state'])
                self.logger.info(f"Resuming campaign from run {batch_start}")
            else:
                self.logger.warning("No campaign state found, starting from beginning")
                resume = False
        
        batch_start = max(0, batch_start)
        batch_end = min(total_runs, batch_end)
        
        if batch_start >= batch_end:
            self.logger.info("Campaign already completed")
            return self.metrics_logger.save_summary_report()
        
        self.logger.info(f"Starting Monte Carlo campaign: runs {batch_start} to {batch_end-1}")
        self.logger.info(f"Total runs in batch: {batch_end - batch_start}")
        
        # Load base mission configuration
        try:
            with open("mission_config.json", "r") as f:
                base_mission_config = json.load(f)
        except FileNotFoundError:
            # Use default configuration
            base_mission_config = {
                "launch_latitude": 28.573,
                "launch_azimuth": 90,
                "target_parking_orbit": 185e3,
                "gravity_turn_altitude": 1500,
                "simulation_duration": 10 * 24 * 3600,
                "time_step": 0.1
            }
        
        # Generate all run configurations
        run_configs = []
        for run_id in range(batch_start, batch_end):
            variations = self._generate_parameter_variations(run_id)
            run_config = self._apply_variations_to_config(base_mission_config, variations)
            run_configs.append((run_id, run_config))
        
        # Run simulations in parallel
        start_time = time.time()
        completed_runs = 0
        
        # Determine number of workers (use system CPU count - 1)
        num_workers = max(1, mp.cpu_count() - 1)
        self.logger.info(f"Using {num_workers} parallel workers")
        
        with ProcessPoolExecutor(max_workers=num_workers) as executor:
            # Submit all jobs
            future_to_run = {
                executor.submit(self._run_single_simulation, config): config[0] 
                for config in run_configs
            }
            
            # Process completed simulations
            for future in as_completed(future_to_run):
                run_id = future_to_run[future]
                try:
                    run_id, results, config = future.result()
                    
                    # Extract and log metrics
                    metrics = extract_metrics_from_mission_results(run_id, results, config)
                    self.metrics_logger.log_mission_metrics(metrics)
                    
                    completed_runs += 1
                    total_completed = batch_start + completed_runs
                    
                    # Save campaign state periodically
                    if completed_runs % self.save_interval == 0:
                        self._save_campaign_state(total_completed)
                    
                    # Progress reporting
                    if completed_runs % 50 == 0 or completed_runs == len(run_configs):
                        elapsed = time.time() - start_time
                        rate = completed_runs / elapsed
                        eta = (len(run_configs) - completed_runs) / rate if rate > 0 else 0
                        
                        self.logger.info(
                            f"Progress: {completed_runs}/{len(run_configs)} "
                            f"({completed_runs/len(run_configs)*100:.1f}%) "
                            f"Total: {total_completed}/{total_runs} "
                            f"Rate: {rate:.1f} runs/sec, ETA: {eta/60:.1f} min"
                        )
                
                except Exception as e:
                    self.logger.error(f"Failed to process run {run_id}: {e}")
        
        # Save final state and clear state file if campaign is complete
        final_completed = batch_start + completed_runs
        if final_completed >= total_runs:
            self._clear_campaign_state()
            self.logger.info("Campaign completed - state file cleared")
        else:
            self._save_campaign_state(final_completed)
        
        # Generate summary report
        self.logger.info("Generating summary report...")
        report_path = self.metrics_logger.save_summary_report()
        
        # Calculate final statistics
        stats = self.metrics_logger.calculate_statistics()
        
        self.logger.info("="*60)
        self.logger.info("MONTE CARLO CAMPAIGN COMPLETE")
        self.logger.info("="*60)
        self.logger.info(f"Total runs: {stats['total_runs']}")
        self.logger.info(f"Successful missions: {stats['successful_runs']}")
        self.logger.info(f"Success rate: {stats['success_rate']:.1%}")
        self.logger.info(f"95% CI: [{stats['confidence_interval']['lower']:.1%}, {stats['confidence_interval']['upper']:.1%}]")
        self.logger.info(f"CI width: {stats['confidence_interval']['width']:.1%}")
        self.logger.info(f"Meets success criteria (≥90%, ≤3% CI): {'YES' if stats['meets_success_criteria'] else 'NO'}")
        self.logger.info(f"Summary report: {report_path}")
        
        return report_path

def main():
    """Main entry point for Monte Carlo simulation"""
    parser = argparse.ArgumentParser(description='Monte Carlo Rocket Simulation Campaign')
    parser.add_argument('--config', default='mc_config.json', help='Monte Carlo configuration file')
    parser.add_argument('--batch-start', type=int, default=0, help='Batch start index')
    parser.add_argument('--batch-end', type=int, help='Batch end index')
    parser.add_argument('--single-run', type=int, help='Run single simulation with given ID')
    parser.add_argument('--resume', action='store_true', help='Resume interrupted campaign from saved state')
    
    args = parser.parse_args()
    
    # Initialize orchestrator
    orchestrator = MonteCarloOrchestrator(args.config)
    
    if args.single_run is not None:
        # Run single simulation for testing
        variations = orchestrator._generate_parameter_variations(args.single_run)
        base_config = {
            "launch_latitude": 28.573,
            "launch_azimuth": 90,
            "target_parking_orbit": 185e3,
            "gravity_turn_altitude": 1500,
            "simulation_duration": 10 * 24 * 3600,
            "time_step": 0.1
        }
        run_config = orchestrator._apply_variations_to_config(base_config, variations)
        
        print(f"Running single simulation {args.single_run} with variations:")
        print(json.dumps(variations, indent=2))
        
        run_id, results, config = orchestrator._run_single_simulation((args.single_run, run_config))
        
        print(f"\nResults for run {run_id}:")
        print(f"Success: {results['mission_success']}")
        print(f"Final phase: {results['final_phase']}")
        print(f"Duration: {results.get('mission_duration', 0)/3600:.2f} hours")
        print(f"Total ΔV: {results.get('total_delta_v', 0):.0f} m/s")
        
    else:
        # Run full campaign
        try:
            report_path = orchestrator.run_campaign(args.batch_start, args.batch_end, args.resume)
            print(f"\nMonte Carlo campaign completed successfully!")
            print(f"Summary report available at: {report_path}")
            
        except KeyboardInterrupt:
            print("\nCampaign interrupted by user")
        except Exception as e:
            print(f"Campaign failed: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()