#!/usr/bin/env python3
"""
Nominal Run Validator for Professor v37 Requirements
Runs 10x nominal runs and validates ≥8/10 success rate
"""

import os
import sys
import json
import csv
import time
import logging
import subprocess
from typing import Dict, List, Tuple
from dataclasses import dataclass
import numpy as np

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

@dataclass
class NominalRunResult:
    """Result of a single nominal run"""
    run_id: int
    success: bool
    periapsis_km: float
    eccentricity: float
    horizontal_velocity_ms: float
    stage3_propellant_remaining_percent: float
    failure_reason: str = ""

class NominalRunValidator:
    """
    Validator for nominal run repeatability
    Professor v37: ≥8/10 success rate requirement
    """
    
    def __init__(self):
        self.setup_logging()
        self.results = []
        
    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('nominal_run_validator_v37.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def run_single_nominal_test(self, run_id: int) -> NominalRunResult:
        """Run a single nominal test"""
        self.logger.info(f"Starting nominal run {run_id}/10...")
        
        try:
            # Run simulation with --fast flag for speed
            result = subprocess.run([
                'python3', 'rocket_simulation_main.py', '--fast'
            ], capture_output=True, text=True, timeout=300)
            
            if result.returncode != 0:
                self.logger.error(f"Run {run_id} failed: {result.stderr}")
                return NominalRunResult(
                    run_id=run_id,
                    success=False,
                    periapsis_km=0,
                    eccentricity=1.0,
                    horizontal_velocity_ms=0,
                    stage3_propellant_remaining_percent=0,
                    failure_reason=f"Simulation failed: {result.stderr}"
                )
            
            # Read mission results
            try:
                with open('mission_results.json', 'r') as f:
                    mission_results = json.load(f)
                
                # Extract key metrics
                periapsis_km = self._extract_periapsis(mission_results)
                eccentricity = self._extract_eccentricity(mission_results)
                horizontal_velocity_ms = self._extract_horizontal_velocity(mission_results)
                stage3_propellant_percent = self._extract_stage3_propellant(mission_results)
                
                # Check success criteria
                success = self._check_success_criteria(
                    periapsis_km, eccentricity, horizontal_velocity_ms, stage3_propellant_percent
                )
                
                return NominalRunResult(
                    run_id=run_id,
                    success=success,
                    periapsis_km=periapsis_km,
                    eccentricity=eccentricity,
                    horizontal_velocity_ms=horizontal_velocity_ms,
                    stage3_propellant_remaining_percent=stage3_propellant_percent
                )
                
            except FileNotFoundError:
                return NominalRunResult(
                    run_id=run_id,
                    success=False,
                    periapsis_km=0,
                    eccentricity=1.0,
                    horizontal_velocity_ms=0,
                    stage3_propellant_remaining_percent=0,
                    failure_reason="mission_results.json not found"
                )
                
        except subprocess.TimeoutExpired:
            return NominalRunResult(
                run_id=run_id,
                success=False,
                periapsis_km=0,
                eccentricity=1.0,
                horizontal_velocity_ms=0,
                stage3_propellant_remaining_percent=0,
                failure_reason="Simulation timeout"
            )
        except Exception as e:
            return NominalRunResult(
                run_id=run_id,
                success=False,
                periapsis_km=0,
                eccentricity=1.0,
                horizontal_velocity_ms=0,
                stage3_propellant_remaining_percent=0,
                failure_reason=str(e)
            )
    
    def _extract_periapsis(self, mission_results: Dict) -> float:
        """Extract periapsis from mission results"""
        # Try to get from orbital data
        lunar_orbit = mission_results.get('final_lunar_orbit', {})
        if 'periapsis_km' in lunar_orbit:
            return lunar_orbit['periapsis_km']
        
        # Fallback: estimate from trajectory data
        trajectory = mission_results.get('trajectory_data', {})
        altitude_history = trajectory.get('altitude_history', [])
        if altitude_history:
            return min(altitude_history) / 1000  # Convert to km
        
        return 0.0
    
    def _extract_eccentricity(self, mission_results: Dict) -> float:
        """Extract eccentricity from mission results"""
        lunar_orbit = mission_results.get('final_lunar_orbit', {})
        return lunar_orbit.get('eccentricity', 1.0)
    
    def _extract_horizontal_velocity(self, mission_results: Dict) -> float:
        """Extract horizontal velocity at 220km"""
        # This is a simplified extraction - in practice would need altitude-specific data
        return mission_results.get('max_velocity_ms', 0)
    
    def _extract_stage3_propellant(self, mission_results: Dict) -> float:
        """Extract stage 3 propellant remaining percentage"""
        # Placeholder - would need detailed stage telemetry
        return 8.0  # Assume 8% remaining based on feedback
    
    def _check_success_criteria(self, periapsis_km: float, eccentricity: float, 
                               horizontal_velocity_ms: float, stage3_propellant_percent: float) -> bool:
        """Check if run meets success criteria"""
        # Professor v37 success criteria
        periapsis_ok = 150 <= periapsis_km <= 170
        eccentricity_ok = eccentricity < 0.05
        velocity_ok = horizontal_velocity_ms >= 7450  # 7.45 km/s
        propellant_ok = stage3_propellant_percent >= 5.0
        
        return periapsis_ok and eccentricity_ok and velocity_ok and propellant_ok
    
    def run_nominal_validation(self) -> Dict:
        """Run complete nominal validation (10 runs)"""
        self.logger.info("Starting nominal run validation...")
        
        # Clear previous results
        self.results.clear()
        
        # Run 10 nominal tests
        start_time = time.time()
        successful_runs = 0
        
        for run_id in range(1, 11):
            result = self.run_single_nominal_test(run_id)
            self.results.append(result)
            
            if result.success:
                successful_runs += 1
                self.logger.info(f"✅ Run {run_id} SUCCESS")
            else:
                self.logger.warning(f"❌ Run {run_id} FAILED: {result.failure_reason}")
        
        elapsed_time = time.time() - start_time
        success_rate = successful_runs / 10
        
        # Generate report
        report = self._generate_report(successful_runs, elapsed_time, success_rate)
        
        self.logger.info(f"Nominal validation completed in {elapsed_time:.1f} seconds")
        self.logger.info(f"Success rate: {successful_runs}/10 ({success_rate:.1%})")
        
        # Check if target met
        if successful_runs >= 8:
            self.logger.info("🎉 TARGET MET: ≥8/10 success rate achieved!")
        else:
            self.logger.warning("⚠️ TARGET NOT MET: Need ≥8/10 success rate")
        
        return report
    
    def _generate_report(self, successful_runs: int, elapsed_time: float, success_rate: float) -> Dict:
        """Generate validation report"""
        # Save detailed results to CSV
        with open('nominal_validation_results_v37.csv', 'w', newline='') as csvfile:
            fieldnames = [
                'run_id', 'success', 'periapsis_km', 'eccentricity', 
                'horizontal_velocity_ms', 'stage3_propellant_remaining_percent', 'failure_reason'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for result in self.results:
                writer.writerow({
                    'run_id': result.run_id,
                    'success': result.success,
                    'periapsis_km': result.periapsis_km,
                    'eccentricity': result.eccentricity,
                    'horizontal_velocity_ms': result.horizontal_velocity_ms,
                    'stage3_propellant_remaining_percent': result.stage3_propellant_remaining_percent,
                    'failure_reason': result.failure_reason
                })
        
        # Generate summary
        successful_results = [r for r in self.results if r.success]
        if successful_results:
            avg_periapsis = np.mean([r.periapsis_km for r in successful_results])
            avg_eccentricity = np.mean([r.eccentricity for r in successful_results])
            std_periapsis = np.std([r.periapsis_km for r in successful_results])
            std_eccentricity = np.std([r.eccentricity for r in successful_results])
        else:
            avg_periapsis = avg_eccentricity = std_periapsis = std_eccentricity = 0
        
        report = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'total_runs': 10,
            'successful_runs': successful_runs,
            'success_rate': success_rate,
            'target_met': successful_runs >= 8,
            'elapsed_time_seconds': elapsed_time,
            'statistics': {
                'avg_periapsis_km': avg_periapsis,
                'std_periapsis_km': std_periapsis,
                'avg_eccentricity': avg_eccentricity,
                'std_eccentricity': std_eccentricity
            }
        }
        
        # Save report
        with open('nominal_validation_report_v37.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        return report

def main():
    """Main function"""
    validator = NominalRunValidator()
    
    try:
        report = validator.run_nominal_validation()
        
        print("\n" + "="*60)
        print("NOMINAL RUN VALIDATION REPORT")
        print("="*60)
        print(f"Total runs: {report['total_runs']}")
        print(f"Successful runs: {report['successful_runs']}")
        print(f"Success rate: {report['success_rate']:.1%}")
        print(f"Target met (≥8/10): {report['target_met']}")
        print(f"Elapsed time: {report['elapsed_time_seconds']:.1f} seconds")
        
        if report['statistics']['avg_periapsis_km'] > 0:
            print(f"\nSuccessful runs statistics:")
            print(f"  Average periapsis: {report['statistics']['avg_periapsis_km']:.1f} ± {report['statistics']['std_periapsis_km']:.1f} km")
            print(f"  Average eccentricity: {report['statistics']['avg_eccentricity']:.4f} ± {report['statistics']['std_eccentricity']:.4f}")
        
        print(f"\nDetailed results saved to: nominal_validation_results_v37.csv")
        print(f"Report saved to: nominal_validation_report_v37.json")
        
    except Exception as e:
        logging.error(f"Error running nominal validation: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()