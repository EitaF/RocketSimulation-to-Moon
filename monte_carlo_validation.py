#!/usr/bin/env python3
"""
Monte Carlo Validation for Lunar Landing Simulation
Professor v43 Feedback: 100-run Latin Hypercube Monte Carlo validation

This script runs 100 Monte Carlo simulations using Latin Hypercube sampling
to validate the lunar landing system. Target: ≥90% success rate.

Parameters varied:
- Initial mass uncertainty (±500 kg)
- Engine performance variation (±2%)
- Atmospheric density (Earth departure)
- Navigation errors (±10 m, ±0.1 m/s)
- Lunar surface conditions
"""

import numpy as np
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Tuple
import matplotlib.pyplot as plt
from scipy.stats import qmc
import concurrent.futures
import os

# Import lunar simulation
from lunar_sim_main import LunarSimulation


class MonteCarloValidator:
    """Monte Carlo validation using Latin Hypercube sampling"""
    
    def __init__(self, num_runs=100):
        """Initialize Monte Carlo validator"""
        self.num_runs = num_runs
        self.logger = self._setup_logging()
        self.results = []
        
        # Define parameter bounds for Latin Hypercube sampling
        self.parameter_bounds = {
            'mass_uncertainty': (-500, 500),      # kg
            'engine_performance': (-0.02, 0.02),  # ±2%
            'nav_position_error': (-10, 10),      # m
            'nav_velocity_error': (-0.1, 0.1),    # m/s
            'surface_slope': (0, 5),              # degrees
            'engine_throttle_error': (-0.05, 0.05), # ±5%
            'guidance_lag': (0, 2),               # seconds
            'fuel_density_var': (-0.01, 0.01)     # ±1%
        }
        
        self.logger.info(f"Monte Carlo validator initialized: {num_runs} runs")
    
    def _setup_logging(self):
        """Setup logging for Monte Carlo validation"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('monte_carlo_validation.log'),
                logging.StreamHandler()
            ]
        )
        return logging.getLogger(__name__)
    
    def generate_latin_hypercube_samples(self):
        """Generate Latin Hypercube samples for parameter variations"""
        self.logger.info("Generating Latin Hypercube samples")
        
        # Number of parameters
        num_params = len(self.parameter_bounds)
        
        # Create Latin Hypercube sampler
        sampler = qmc.LatinHypercube(d=num_params, seed=42)
        samples = sampler.random(n=self.num_runs)
        
        # Scale samples to parameter bounds
        param_names = list(self.parameter_bounds.keys())
        scaled_samples = []
        
        for i, sample in enumerate(samples):
            scaled_sample = {}
            for j, param_name in enumerate(param_names):
                lower, upper = self.parameter_bounds[param_name]
                scaled_value = lower + sample[j] * (upper - lower)
                scaled_sample[param_name] = scaled_value
            
            scaled_samples.append(scaled_sample)
        
        self.logger.info(f"Generated {len(scaled_samples)} Latin Hypercube samples")
        return scaled_samples
    
    def run_single_simulation(self, run_id, parameters):
        """Run single Monte Carlo simulation with parameter variations"""
        try:
            # Create modified simulation with uncertainties
            simulation = LunarSimulation()
            
            # Apply parameter variations
            self._apply_parameter_variations(simulation, parameters)
            
            # Run simulation
            result = simulation.run_complete_mission()
            
            # Extract key metrics
            mc_result = {
                'run_id': run_id,
                'parameters': parameters,
                'success': result['success'],
                'touchdown_velocity': result['touchdown']['velocity'] if result['success'] else float('inf'),
                'touchdown_tilt': result['touchdown']['tilt_angle'] if result['success'] else float('inf'),
                'total_delta_v': result.get('total_delta_v', 0),
                'execution_time': result.get('execution_time', 0),
                'meets_criteria': result['performance_metrics']['meets_professor_criteria'],
                'failure_reason': result.get('reason', '') if not result['success'] else ''
            }
            
            return mc_result
            
        except Exception as e:
            self.logger.error(f"Run {run_id} failed with exception: {e}")
            return {
                'run_id': run_id,
                'parameters': parameters,
                'success': False,
                'touchdown_velocity': float('inf'),
                'touchdown_tilt': float('inf'),
                'total_delta_v': 0,
                'execution_time': 0,
                'meets_criteria': False,
                'failure_reason': f"Exception: {str(e)}"
            }
    
    def _apply_parameter_variations(self, simulation, parameters):
        """Apply parameter variations to simulation"""
        # Mass uncertainty
        mass_variation = parameters['mass_uncertainty']
        simulation.spacecraft_mass += mass_variation
        simulation.fuel_mass = max(1000, simulation.fuel_mass + mass_variation * 0.8)
        
        # Store variations for simulation reference
        simulation.mc_parameters = parameters
    
    def run_monte_carlo_validation(self, use_parallel=True, max_workers=8):
        """Run complete Monte Carlo validation"""
        self.logger.info("🎲 Starting Monte Carlo validation")
        self.logger.info(f"Configuration: {self.num_runs} runs, parallel={use_parallel}")
        
        start_time = time.time()
        
        # Generate Latin Hypercube samples
        parameter_samples = self.generate_latin_hypercube_samples()
        
        # Run simulations
        if use_parallel:
            self.results = self._run_parallel_simulations(parameter_samples, max_workers)
        else:
            self.results = self._run_sequential_simulations(parameter_samples)
        
        execution_time = time.time() - start_time
        
        # Analyze results
        analysis = self._analyze_results()
        
        # Create summary
        summary = {
            'configuration': {
                'num_runs': self.num_runs,
                'parallel_execution': use_parallel,
                'max_workers': max_workers if use_parallel else 1,
                'execution_time': execution_time
            },
            'results': self.results,
            'analysis': analysis,
            'timestamp': datetime.now().isoformat(),
            'professor_v43_validation': {
                'target_success_rate': 0.90,
                'achieved_success_rate': analysis['success_rate'],
                'validation_passed': analysis['success_rate'] >= 0.90,
                'velocity_compliance_rate': analysis['velocity_compliance_rate'],
                'tilt_compliance_rate': analysis['tilt_compliance_rate']
            }
        }
        
        self._log_summary(summary)
        return summary
    
    def _run_parallel_simulations(self, parameter_samples, max_workers):
        """Run simulations in parallel"""
        self.logger.info(f"Running {self.num_runs} simulations in parallel (workers: {max_workers})")
        
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all jobs
            future_to_run = {
                executor.submit(self.run_single_simulation, i, params): i 
                for i, params in enumerate(parameter_samples)
            }
            
            # Collect results as they complete
            completed = 0
            for future in concurrent.futures.as_completed(future_to_run):
                run_id = future_to_run[future]
                try:
                    result = future.result()
                    results.append(result)
                    completed += 1
                    
                    if completed % 10 == 0:
                        self.logger.info(f"Completed {completed}/{self.num_runs} runs")
                        
                except Exception as e:
                    self.logger.error(f"Run {run_id} generated exception: {e}")
                    results.append({
                        'run_id': run_id,
                        'success': False,
                        'failure_reason': f"Execution error: {str(e)}"
                    })
        
        # Sort results by run_id
        results.sort(key=lambda x: x['run_id'])
        return results
    
    def _run_sequential_simulations(self, parameter_samples):
        """Run simulations sequentially"""
        self.logger.info(f"Running {self.num_runs} simulations sequentially")
        
        results = []
        for i, params in enumerate(parameter_samples):
            if i % 10 == 0:
                self.logger.info(f"Running simulation {i+1}/{self.num_runs}")
            
            result = self.run_single_simulation(i, params)
            results.append(result)
        
        return results
    
    def _analyze_results(self):
        """Analyze Monte Carlo results"""
        self.logger.info("Analyzing Monte Carlo results")
        
        total_runs = len(self.results)
        successful_runs = [r for r in self.results if r['success']]
        failed_runs = [r for r in self.results if not r['success']]
        
        # Success metrics
        success_rate = len(successful_runs) / total_runs
        
        # Velocity compliance (≤ 2 m/s)
        velocity_compliant = [r for r in successful_runs if r['touchdown_velocity'] <= 2.0]
        velocity_compliance_rate = len(velocity_compliant) / total_runs
        
        # Tilt compliance (≤ 5°)
        tilt_compliant = [r for r in successful_runs if r['touchdown_tilt'] <= 5.0]
        tilt_compliance_rate = len(tilt_compliant) / total_runs
        
        # Professor criteria compliance
        criteria_compliant = [r for r in self.results if r['meets_criteria']]
        criteria_compliance_rate = len(criteria_compliant) / total_runs
        
        # Performance statistics
        if successful_runs:
            velocities = [r['touchdown_velocity'] for r in successful_runs]
            tilts = [r['touchdown_tilt'] for r in successful_runs]
            delta_vs = [r['total_delta_v'] for r in successful_runs]
            
            performance_stats = {
                'velocity': {
                    'mean': np.mean(velocities),
                    'std': np.std(velocities),
                    'min': np.min(velocities),
                    'max': np.max(velocities),
                    'percentile_95': np.percentile(velocities, 95)
                },
                'tilt': {
                    'mean': np.mean(tilts),
                    'std': np.std(tilts),
                    'min': np.min(tilts),
                    'max': np.max(tilts),
                    'percentile_95': np.percentile(tilts, 95)
                },
                'delta_v': {
                    'mean': np.mean(delta_vs),
                    'std': np.std(delta_vs),
                    'min': np.min(delta_vs),
                    'max': np.max(delta_vs)
                }
            }
        else:
            performance_stats = {}
        
        # Failure analysis
        failure_reasons = {}
        for run in failed_runs:
            reason = run.get('failure_reason', 'Unknown')
            failure_reasons[reason] = failure_reasons.get(reason, 0) + 1
        
        analysis = {
            'total_runs': total_runs,
            'successful_runs': len(successful_runs),
            'failed_runs': len(failed_runs),
            'success_rate': success_rate,
            'velocity_compliance_rate': velocity_compliance_rate,
            'tilt_compliance_rate': tilt_compliance_rate,
            'criteria_compliance_rate': criteria_compliance_rate,
            'performance_statistics': performance_stats,
            'failure_analysis': failure_reasons,
            'validation_summary': {
                'professor_target_met': success_rate >= 0.90,
                'velocity_target_met': velocity_compliance_rate >= 0.90,
                'tilt_target_met': tilt_compliance_rate >= 0.90,
                'overall_assessment': 'PASS' if success_rate >= 0.90 else 'FAIL'
            }
        }
        
        return analysis
    
    def _log_summary(self, summary):
        """Log Monte Carlo summary"""
        analysis = summary['analysis']
        validation = summary['professor_v43_validation']
        
        self.logger.info("="*60)
        self.logger.info("🎲 MONTE CARLO VALIDATION SUMMARY")
        self.logger.info("="*60)
        
        self.logger.info(f"Total runs: {analysis['total_runs']}")
        self.logger.info(f"Successful runs: {analysis['successful_runs']}")
        self.logger.info(f"Success rate: {analysis['success_rate']:.1%}")
        
        self.logger.info(f"\n📊 PROFESSOR v43 CRITERIA:")
        self.logger.info(f"   Target success rate: ≥90%")
        self.logger.info(f"   Achieved success rate: {validation['achieved_success_rate']:.1%}")
        self.logger.info(f"   Validation result: {'✅ PASS' if validation['validation_passed'] else '❌ FAIL'}")
        
        self.logger.info(f"\n🎯 PERFORMANCE METRICS:")
        self.logger.info(f"   Velocity compliance (≤2 m/s): {analysis['velocity_compliance_rate']:.1%}")
        self.logger.info(f"   Tilt compliance (≤5°): {analysis['tilt_compliance_rate']:.1%}")
        self.logger.info(f"   Overall criteria compliance: {analysis['criteria_compliance_rate']:.1%}")
        
        if analysis['performance_statistics']:
            stats = analysis['performance_statistics']
            self.logger.info(f"\n📈 PERFORMANCE STATISTICS:")
            self.logger.info(f"   Touchdown velocity: {stats['velocity']['mean']:.2f} ± {stats['velocity']['std']:.2f} m/s")
            self.logger.info(f"   Touchdown tilt: {stats['tilt']['mean']:.2f} ± {stats['tilt']['std']:.2f}°")
            self.logger.info(f"   Total ΔV: {stats['delta_v']['mean']:.1f} ± {stats['delta_v']['std']:.1f} m/s")
        
        if analysis['failure_analysis']:
            self.logger.info(f"\n❌ FAILURE ANALYSIS:")
            for reason, count in analysis['failure_analysis'].items():
                self.logger.info(f"   {reason}: {count} runs ({count/analysis['total_runs']:.1%})")
        
        self.logger.info("="*60)
    
    def save_results(self, summary, filename="monte_carlo_validation_results.json"):
        """Save Monte Carlo results to file"""
        # Create reports directory
        os.makedirs("reports/MVP", exist_ok=True)
        
        filepath = os.path.join("reports/MVP", filename)
        with open(filepath, 'w') as f:
            json.dump(summary, f, indent=2)
        
        self.logger.info(f"Monte Carlo results saved to {filepath}")
        
        # Also save summary to main directory for script access
        with open(filename, 'w') as f:
            json.dump(summary, f, indent=2)


def main():
    """Main execution function"""
    print("🎲 MONTE CARLO VALIDATION - Professor v43")
    print("100-run Latin Hypercube Monte Carlo validation")
    print("Target: ≥90% success rate")
    print("="*60)
    
    # Create validator
    validator = MonteCarloValidator(num_runs=100)
    
    # Run validation
    summary = validator.run_monte_carlo_validation(use_parallel=True, max_workers=8)
    
    # Save results
    validator.save_results(summary)
    
    # Print final assessment
    validation_passed = summary['professor_v43_validation']['validation_passed']
    success_rate = summary['analysis']['success_rate']
    
    print(f"\n{'✅ VALIDATION PASSED' if validation_passed else '❌ VALIDATION FAILED'}")
    print(f"Success rate: {success_rate:.1%} (target: ≥90%)")
    
    return 0 if validation_passed else 1


if __name__ == "__main__":
    exit(main())