"""
Monte Carlo Simulation for Professor v42 Architecture
Target: ≥97% TLI success rate validation

This module validates the unified trajectory system using Monte Carlo analysis
with the professor's success criteria and performance metrics.
"""

import numpy as np
import json
import csv
from typing import Dict, List, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import logging
import concurrent.futures
import time

from unified_trajectory_system import (
    UnifiedTrajectorySystem, MissionParameters, SystemState, 
    create_unified_trajectory_system
)


@dataclass
class MonteCarloParameters:
    """Monte Carlo simulation parameters"""
    num_runs: int = 1000                    # Number of MC runs (Professor target)
    position_uncertainty: float = 1000.0    # Position uncertainty [m]
    velocity_uncertainty: float = 5.0       # Velocity uncertainty [m/s]
    mass_uncertainty: float = 500.0         # Mass uncertainty [kg]
    timing_uncertainty: float = 60.0        # Timing uncertainty [s]
    engine_performance_uncertainty: float = 0.02  # 2% engine performance variation
    atmospheric_uncertainty: float = 0.05   # 5% atmospheric density variation
    navigation_uncertainty: float = 0.001   # 0.1% navigation accuracy


@dataclass
class MonteCarloRun:
    """Individual Monte Carlo run result"""
    run_id: int
    success: bool
    converged: bool
    total_delta_v: float
    delta_v_error: float
    raan_error: float
    beta_angle: float
    system_efficiency: float
    finite_burn_loss: float
    burn_duration: float
    iterations: int
    meets_professor_criteria: bool
    failure_mode: str
    execution_time: float


@dataclass
class MonteCarloResults:
    """Complete Monte Carlo analysis results"""
    total_runs: int
    successful_runs: int
    converged_runs: int
    success_rate: float
    convergence_rate: float
    professor_criteria_success_rate: float
    
    # Statistical metrics
    mean_delta_v: float
    std_delta_v: float
    mean_delta_v_error: float
    std_delta_v_error: float
    mean_system_efficiency: float
    std_system_efficiency: float
    
    # Performance percentiles
    delta_v_p50: float
    delta_v_p95: float
    delta_v_p99: float
    
    # Failure analysis
    failure_modes: Dict[str, int]
    
    # Execution metrics
    total_execution_time: float
    mean_run_time: float


class MonteCarloAnalyzer:
    """
    Monte Carlo analyzer for Professor v42 trajectory system
    
    Validates system performance against the 97% success rate target
    with comprehensive uncertainty modeling and failure analysis.
    """
    
    def __init__(self, mc_params: MonteCarloParameters = None):
        """
        Initialize Monte Carlo analyzer
        
        Args:
            mc_params: Monte Carlo simulation parameters
        """
        self.mc_params = mc_params or MonteCarloParameters()
        self.logger = logging.getLogger(__name__)
        
        # Base mission parameters
        self.base_mission_params = MissionParameters()
        
        # Random number generator for reproducibility
        self.rng = np.random.RandomState(42)
        
        self.logger.info(f"Monte Carlo Analyzer initialized for {self.mc_params.num_runs} runs")
    
    def generate_uncertainty_sample(self) -> Dict:
        """
        Generate random uncertainty sample for one MC run
        
        Returns:
            Dictionary with uncertainty parameters
        """
        return {
            'position_error': self.rng.normal(0, self.mc_params.position_uncertainty, 3),
            'velocity_error': self.rng.normal(0, self.mc_params.velocity_uncertainty, 3),
            'mass_error': self.rng.normal(0, self.mc_params.mass_uncertainty),
            'timing_error': self.rng.normal(0, self.mc_params.timing_uncertainty),
            'engine_performance_factor': 1.0 + self.rng.normal(0, self.mc_params.engine_performance_uncertainty),
            'atmospheric_factor': 1.0 + self.rng.normal(0, self.mc_params.atmospheric_uncertainty),
            'navigation_factor': 1.0 + self.rng.normal(0, self.mc_params.navigation_uncertainty)
        }
    
    def apply_uncertainties(self, base_state: SystemState, uncertainties: Dict) -> SystemState:
        """
        Apply uncertainties to base system state
        
        Args:
            base_state: Nominal system state
            uncertainties: Uncertainty sample
            
        Returns:
            Perturbed system state
        """
        perturbed_position = base_state.position + uncertainties['position_error']
        perturbed_velocity = base_state.velocity + uncertainties['velocity_error']
        perturbed_mass = base_state.mass + uncertainties['mass_error']
        perturbed_time = base_state.time + uncertainties['timing_error']
        
        return SystemState(
            position=perturbed_position,
            velocity=perturbed_velocity,
            mass=max(10000, perturbed_mass),  # Minimum mass constraint
            time=perturbed_time,
            phase=base_state.phase
        )
    
    def run_single_monte_carlo(self, run_id: int, base_state: SystemState) -> MonteCarloRun:
        """
        Execute single Monte Carlo run
        
        Args:
            run_id: Run identifier
            base_state: Base system state
            
        Returns:
            MonteCarloRun result
        """
        start_time = time.time()
        
        try:
            # Generate uncertainties for this run
            uncertainties = self.generate_uncertainty_sample()
            
            # Apply uncertainties to system state
            perturbed_state = self.apply_uncertainties(base_state, uncertainties)
            
            # Create perturbed mission parameters
            perturbed_mission_params = MissionParameters(
                launch_site_lat=self.base_mission_params.launch_site_lat,
                launch_site_lon=self.base_mission_params.launch_site_lon,
                parking_orbit_altitude=self.base_mission_params.parking_orbit_altitude,
                target_inclination=self.base_mission_params.target_inclination,
                transfer_time_days=self.base_mission_params.transfer_time_days,
                spacecraft_mass=perturbed_state.mass,
                engine_stage=self.base_mission_params.engine_stage
            )
            
            # Create unified trajectory system for this run
            unified_system = create_unified_trajectory_system(perturbed_mission_params)
            
            # Run mission optimization
            start_date = datetime.now() + timedelta(hours=run_id % 24)  # Vary start time
            mission_result = unified_system.optimize_complete_mission(start_date, perturbed_state)
            
            # Extract results
            success = mission_result.get('success', False)
            
            if success:
                trajectory = mission_result['trajectory']
                optimization = mission_result['optimization']
                launch_window = mission_result['launch_window']
                performance = mission_result['performance_metrics']
                
                result = MonteCarloRun(
                    run_id=run_id,
                    success=success,
                    converged=optimization['converged'],
                    total_delta_v=trajectory['total_delta_v'],
                    delta_v_error=trajectory['delta_v_error'],
                    raan_error=abs(launch_window['raan_error']),
                    beta_angle=abs(launch_window['beta_angle']),
                    system_efficiency=optimization['system_efficiency'],
                    finite_burn_loss=trajectory['finite_burn_loss'],
                    burn_duration=trajectory['burn_duration'],
                    iterations=optimization['iterations'],
                    meets_professor_criteria=performance['meets_professor_criteria'],
                    failure_mode="none",
                    execution_time=time.time() - start_time
                )
            else:
                # Failed run
                result = MonteCarloRun(
                    run_id=run_id,
                    success=False,
                    converged=False,
                    total_delta_v=0.0,
                    delta_v_error=float('inf'),
                    raan_error=float('inf'),
                    beta_angle=float('inf'),
                    system_efficiency=0.0,
                    finite_burn_loss=0.0,
                    burn_duration=0.0,
                    iterations=0,
                    meets_professor_criteria=False,
                    failure_mode=mission_result.get('reason', 'unknown'),
                    execution_time=time.time() - start_time
                )
            
        except Exception as e:
            # Exception during run
            self.logger.warning(f"Run {run_id} failed with exception: {e}")
            result = MonteCarloRun(
                run_id=run_id,
                success=False,
                converged=False,
                total_delta_v=0.0,
                delta_v_error=float('inf'),
                raan_error=float('inf'),
                beta_angle=float('inf'),
                system_efficiency=0.0,
                finite_burn_loss=0.0,
                burn_duration=0.0,
                iterations=0,
                meets_professor_criteria=False,
                failure_mode=f"exception: {str(e)[:50]}",
                execution_time=time.time() - start_time
            )
        
        return result
    
    def run_monte_carlo_analysis(self, base_state: SystemState, 
                                parallel: bool = True) -> MonteCarloResults:
        """
        Run complete Monte Carlo analysis
        
        Args:
            base_state: Base system state for analysis
            parallel: Whether to use parallel processing
            
        Returns:
            Complete Monte Carlo results
        """
        self.logger.info(f"Starting Monte Carlo analysis with {self.mc_params.num_runs} runs")
        start_time = time.time()
        
        runs = []
        
        if parallel and self.mc_params.num_runs >= 10:
            # Parallel execution for large run counts
            max_workers = min(8, self.mc_params.num_runs // 10)
            self.logger.info(f"Using parallel execution with {max_workers} workers")
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all runs
                future_to_run = {
                    executor.submit(self.run_single_monte_carlo, run_id, base_state): run_id 
                    for run_id in range(self.mc_params.num_runs)
                }
                
                # Collect results
                completed = 0
                for future in concurrent.futures.as_completed(future_to_run):
                    run_result = future.result()
                    runs.append(run_result)
                    completed += 1
                    
                    # Progress logging
                    if completed % 100 == 0 or completed == self.mc_params.num_runs:
                        self.logger.info(f"Completed {completed}/{self.mc_params.num_runs} runs")
        else:
            # Sequential execution
            for run_id in range(self.mc_params.num_runs):
                run_result = self.run_single_monte_carlo(run_id, base_state)
                runs.append(run_result)
                
                if (run_id + 1) % 50 == 0:
                    self.logger.info(f"Completed {run_id + 1}/{self.mc_params.num_runs} runs")
        
        # Analyze results
        total_execution_time = time.time() - start_time
        results = self._analyze_monte_carlo_results(runs, total_execution_time)
        
        self.logger.info(f"Monte Carlo analysis complete in {total_execution_time:.1f}s")
        self.logger.info(f"Success rate: {results.success_rate:.1%}")
        self.logger.info(f"Professor criteria success rate: {results.professor_criteria_success_rate:.1%}")
        
        return results
    
    def _analyze_monte_carlo_results(self, runs: List[MonteCarloRun], 
                                   total_time: float) -> MonteCarloResults:
        """Analyze Monte Carlo run results"""
        
        # Basic statistics
        total_runs = len(runs)
        successful_runs = sum(1 for run in runs if run.success)
        converged_runs = sum(1 for run in runs if run.converged)
        professor_criteria_runs = sum(1 for run in runs if run.meets_professor_criteria)
        
        # Success rates
        success_rate = successful_runs / total_runs
        convergence_rate = converged_runs / total_runs
        professor_criteria_success_rate = professor_criteria_runs / total_runs
        
        # Extract successful run data for statistics
        successful_data = [run for run in runs if run.success]
        
        if successful_data:
            delta_vs = [run.total_delta_v for run in successful_data]
            delta_v_errors = [run.delta_v_error for run in successful_data if run.delta_v_error != float('inf')]
            efficiencies = [run.system_efficiency for run in successful_data]
            
            # Statistical metrics
            mean_delta_v = np.mean(delta_vs)
            std_delta_v = np.std(delta_vs)
            mean_delta_v_error = np.mean(delta_v_errors) if delta_v_errors else float('inf')
            std_delta_v_error = np.std(delta_v_errors) if delta_v_errors else float('inf')
            mean_system_efficiency = np.mean(efficiencies)
            std_system_efficiency = np.std(efficiencies)
            
            # Percentiles
            delta_v_p50 = np.percentile(delta_vs, 50)
            delta_v_p95 = np.percentile(delta_vs, 95)
            delta_v_p99 = np.percentile(delta_vs, 99)
        else:
            # No successful runs
            mean_delta_v = std_delta_v = 0.0
            mean_delta_v_error = std_delta_v_error = float('inf')
            mean_system_efficiency = std_system_efficiency = 0.0
            delta_v_p50 = delta_v_p95 = delta_v_p99 = 0.0
        
        # Failure mode analysis
        failure_modes = {}
        for run in runs:
            if not run.success:
                mode = run.failure_mode
                failure_modes[mode] = failure_modes.get(mode, 0) + 1
        
        # Execution timing
        run_times = [run.execution_time for run in runs]
        mean_run_time = np.mean(run_times)
        
        return MonteCarloResults(
            total_runs=total_runs,
            successful_runs=successful_runs,
            converged_runs=converged_runs,
            success_rate=success_rate,
            convergence_rate=convergence_rate,
            professor_criteria_success_rate=professor_criteria_success_rate,
            mean_delta_v=mean_delta_v,
            std_delta_v=std_delta_v,
            mean_delta_v_error=mean_delta_v_error,
            std_delta_v_error=std_delta_v_error,
            mean_system_efficiency=mean_system_efficiency,
            std_system_efficiency=std_system_efficiency,
            delta_v_p50=delta_v_p50,
            delta_v_p95=delta_v_p95,
            delta_v_p99=delta_v_p99,
            failure_modes=failure_modes,
            total_execution_time=total_time,
            mean_run_time=mean_run_time
        )
    
    def save_results(self, results: MonteCarloResults, runs: List[MonteCarloRun], 
                    output_prefix: str = "mc_v42") -> Dict[str, str]:
        """
        Save Monte Carlo results to files
        
        Args:
            results: Monte Carlo analysis results
            runs: Individual run results
            output_prefix: File prefix for outputs
            
        Returns:
            Dictionary of saved file paths
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Summary JSON
        summary_file = f"{output_prefix}_summary_{timestamp}.json"
        summary_data = asdict(results)
        summary_data['analysis_timestamp'] = timestamp
        summary_data['professor_v42_target_met'] = results.professor_criteria_success_rate >= 0.97
        
        with open(summary_file, 'w') as f:
            json.dump(summary_data, f, indent=2, default=str)
        
        # Detailed CSV
        csv_file = f"{output_prefix}_detailed_{timestamp}.csv"
        with open(csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'run_id', 'success', 'converged', 'total_delta_v', 'delta_v_error',
                'raan_error', 'beta_angle', 'system_efficiency', 'finite_burn_loss',
                'burn_duration', 'iterations', 'meets_professor_criteria',
                'failure_mode', 'execution_time'
            ])
            writer.writeheader()
            for run in runs:
                writer.writerow(asdict(run))
        
        # Analysis report
        report_file = f"{output_prefix}_report_{timestamp}.md"
        self._generate_analysis_report(results, report_file)
        
        saved_files = {
            'summary': summary_file,
            'detailed': csv_file,
            'report': report_file
        }
        
        self.logger.info(f"Results saved to: {saved_files}")
        return saved_files
    
    def _generate_analysis_report(self, results: MonteCarloResults, filename: str):
        """Generate markdown analysis report"""
        
        professor_target_met = results.professor_criteria_success_rate >= 0.97
        
        report_content = f"""# Monte Carlo Analysis Report - Professor v42 Architecture

## Analysis Summary
- **Analysis Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **Total Runs**: {results.total_runs:,}
- **Execution Time**: {results.total_execution_time:.1f} seconds
- **Average Run Time**: {results.mean_run_time:.3f} seconds/run

## Success Metrics
- **Overall Success Rate**: {results.success_rate:.1%} ({results.successful_runs:,}/{results.total_runs:,})
- **Convergence Rate**: {results.convergence_rate:.1%} ({results.converged_runs:,}/{results.total_runs:,})
- **Professor v42 Criteria Success**: {results.professor_criteria_success_rate:.1%} ({sum(1 for i in range(results.total_runs) if True)})

### Professor v42 Target Assessment
- **Target**: ≥97% success rate
- **Achieved**: {results.professor_criteria_success_rate:.1%}
- **Status**: {'✅ TARGET MET' if professor_target_met else '❌ TARGET NOT MET'}

## Performance Statistics (Successful Runs Only)

### Delta-V Analysis
- **Mean Total ΔV**: {results.mean_delta_v:.1f} ± {results.std_delta_v:.1f} m/s
- **Mean ΔV Error**: {results.mean_delta_v_error:.2f} ± {results.std_delta_v_error:.2f} m/s
- **ΔV Percentiles**:
  - P50 (Median): {results.delta_v_p50:.1f} m/s
  - P95: {results.delta_v_p95:.1f} m/s  
  - P99: {results.delta_v_p99:.1f} m/s

### System Performance
- **Mean System Efficiency**: {results.mean_system_efficiency:.1%} ± {results.std_system_efficiency:.1%}

## Failure Analysis
"""
        
        if results.failure_modes:
            report_content += "\n### Failure Mode Distribution\n"
            total_failures = sum(results.failure_modes.values())
            for mode, count in sorted(results.failure_modes.items(), key=lambda x: x[1], reverse=True):
                percentage = count / total_failures * 100
                report_content += f"- **{mode}**: {count:,} ({percentage:.1f}%)\n"
        else:
            report_content += "\n### No Failures Detected\nAll runs completed successfully.\n"
        
        report_content += f"""
## Recommendations

### Professor v42 Architecture Assessment
{'The unified trajectory system successfully meets the Professor v42 target of ≥97% success rate.' if professor_target_met else 'The system requires further optimization to meet the 97% success rate target.'}

### Key Findings
- Lambert+Finite Burn+Residual Projection architecture demonstrates {'excellent' if results.success_rate > 0.95 else 'good' if results.success_rate > 0.9 else 'moderate'} reliability
- Average ΔV error of ±{results.mean_delta_v_error:.1f} m/s {'meets' if results.mean_delta_v_error <= 5.0 else 'exceeds'} the ±5 m/s tolerance requirement
- System efficiency of {results.mean_system_efficiency:.1%} indicates {'optimal' if results.mean_system_efficiency > 0.9 else 'good' if results.mean_system_efficiency > 0.8 else 'adequate'} performance

### Next Steps
{'Continue with current architecture for production missions.' if professor_target_met else 'Implement additional robustness measures and re-run Monte Carlo analysis.'}

---
*Generated by Monte Carlo Analyzer for Professor v42 Unified Trajectory System*
"""
        
        with open(filename, 'w') as f:
            f.write(report_content)


# Example usage and testing
if __name__ == "__main__":
    print("Monte Carlo Analysis for Professor v42 Architecture")
    print("=" * 60)
    
    # Create Monte Carlo analyzer with reduced run count for testing
    mc_params = MonteCarloParameters(
        num_runs=100,  # Reduced for testing (normally 1000)
        position_uncertainty=1000.0,
        velocity_uncertainty=5.0,
        mass_uncertainty=500.0,
        timing_uncertainty=60.0
    )
    
    analyzer = MonteCarloAnalyzer(mc_params)
    
    # Define base system state
    base_state = SystemState(
        position=np.array([6556000, 0, 0]),  # LEO position
        velocity=np.array([0, 7800, 0]),     # LEO velocity
        mass=45000,                          # Nominal mass
        time=0.0,                           # Mission start
        phase="LEO"
    )
    
    print(f"Running {mc_params.num_runs} Monte Carlo simulations...")
    
    # Run Monte Carlo analysis
    results = analyzer.run_monte_carlo_analysis(base_state, parallel=True)
    
    print(f"\nMonte Carlo Results:")
    print(f"Success Rate: {results.success_rate:.1%}")
    print(f"Professor v42 Criteria Success: {results.professor_criteria_success_rate:.1%}")
    print(f"Target Met (≥97%): {'✅ YES' if results.professor_criteria_success_rate >= 0.97 else '❌ NO'}")
    print(f"Mean ΔV: {results.mean_delta_v:.1f} ± {results.std_delta_v:.1f} m/s")
    print(f"Mean ΔV Error: {results.mean_delta_v_error:.2f} ± {results.std_delta_v_error:.2f} m/s")
    print(f"System Efficiency: {results.mean_system_efficiency:.1%} ± {results.std_system_efficiency:.1%}")
    
    if results.failure_modes:
        print(f"\nFailure Modes:")
        for mode, count in results.failure_modes.items():
            print(f"  {mode}: {count} ({count/results.total_runs:.1%})")
    
    # Save results (commented out for testing)
    # saved_files = analyzer.save_results(results, [], "test_mc_v42")
    # print(f"\nResults saved to: {saved_files}")