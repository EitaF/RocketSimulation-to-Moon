"""
Post-Flight Analysis Module for Saturn V LEO Mission
Professor v36: Automated validation checks for stable LEO achievement
"""

import numpy as np
import csv
import json
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import logging

@dataclass
class MissionResults:
    """Container for mission results and orbital parameters"""
    apoapsis_km: float
    periapsis_km: float
    eccentricity: float
    max_altitude_km: float
    final_velocity_ms: float
    stage3_propellant_remaining: float
    horizontal_velocity_at_220km: float
    time_to_apoapsis: float
    mission_success: bool
    failure_reason: Optional[str] = None

class PostFlightAnalyzer:
    """Automated post-flight analysis and validation"""
    
    def __init__(self, log_file: str = "mission_log.csv"):
        self.log_file = log_file
        self.setup_logging()
    
    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('post_flight_analysis.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def analyze_mission(self, mission_data: Dict) -> MissionResults:
        """
        Analyze mission data and validate against success criteria
        Professor v36: Automated validation for stable LEO
        """
        results = self._extract_orbital_parameters(mission_data)
        self._validate_mission_success(results)
        self._log_analysis_results(results)
        
        return results
    
    def _extract_orbital_parameters(self, mission_data: Dict) -> MissionResults:
        """Extract key orbital parameters from mission data"""
        try:
            # Extract final orbital parameters
            apoapsis_km = mission_data.get('final_apoapsis_km', 0)
            periapsis_km = mission_data.get('final_periapsis_km', 0)
            eccentricity = mission_data.get('final_eccentricity', 1.0)
            max_altitude_km = mission_data.get('max_altitude_km', 0)
            final_velocity_ms = mission_data.get('final_velocity_ms', 0)
            stage3_propellant = mission_data.get('stage3_propellant_remaining', 0)
            horizontal_velocity_220km = mission_data.get('horizontal_velocity_at_220km', 0)
            time_to_apoapsis = mission_data.get('time_to_apoapsis', 0)
            
            return MissionResults(
                apoapsis_km=apoapsis_km,
                periapsis_km=periapsis_km,
                eccentricity=eccentricity,
                max_altitude_km=max_altitude_km,
                final_velocity_ms=final_velocity_ms,
                stage3_propellant_remaining=stage3_propellant,
                horizontal_velocity_at_220km=horizontal_velocity_220km,
                time_to_apoapsis=time_to_apoapsis,
                mission_success=False  # Will be determined by validation
            )
        except Exception as e:
            self.logger.error(f"Error extracting orbital parameters: {e}")
            return MissionResults(0, 0, 1.0, 0, 0, 0, 0, 0, False, f"Data extraction error: {e}")
    
    def _validate_mission_success(self, results: MissionResults):
        """
        Validate mission success against Professor v36 criteria
        Target: Stable 160×160 km LEO with e < 0.05
        """
        success_criteria = []
        failure_reasons = []
        
        # Professor v36 Success Criteria
        
        # 1. Periapsis > 150 km
        periapsis_success = results.periapsis_km > 150.0
        success_criteria.append(periapsis_success)
        if not periapsis_success:
            failure_reasons.append(f"Periapsis too low: {results.periapsis_km:.1f} km < 150 km")
        
        # 2. Eccentricity < 0.05
        eccentricity_success = results.eccentricity < 0.05
        success_criteria.append(eccentricity_success)
        if not eccentricity_success:
            failure_reasons.append(f"Eccentricity too high: {results.eccentricity:.4f} > 0.05")
        
        # 3. Stage 3 propellant margin ≥ 5%
        propellant_success = results.stage3_propellant_remaining >= 0.05
        success_criteria.append(propellant_success)
        if not propellant_success:
            failure_reasons.append(f"Stage 3 propellant too low: {results.stage3_propellant_remaining:.1%} < 5%")
        
        # 4. Horizontal velocity ≥ 7.4 km/s by 220 km altitude
        velocity_success = results.horizontal_velocity_at_220km >= 7400
        success_criteria.append(velocity_success)
        if not velocity_success:
            failure_reasons.append(f"Horizontal velocity too low: {results.horizontal_velocity_at_220km:.0f} m/s < 7400 m/s")
        
        # Overall mission success
        results.mission_success = all(success_criteria)
        results.failure_reason = "; ".join(failure_reasons) if failure_reasons else None
        
        # Log validation results
        self.logger.info(f"Mission Validation Results:")
        self.logger.info(f"  Periapsis: {results.periapsis_km:.1f} km ({'✅' if periapsis_success else '❌'})")
        self.logger.info(f"  Eccentricity: {results.eccentricity:.4f} ({'✅' if eccentricity_success else '❌'})")
        self.logger.info(f"  Stage 3 propellant: {results.stage3_propellant_remaining:.1%} ({'✅' if propellant_success else '❌'})")
        self.logger.info(f"  Horizontal velocity: {results.horizontal_velocity_at_220km:.0f} m/s ({'✅' if velocity_success else '❌'})")
        self.logger.info(f"  Overall success: {'✅' if results.mission_success else '❌'}")
        
        if not results.mission_success:
            self.logger.warning(f"Mission failed: {results.failure_reason}")
    
    def _log_analysis_results(self, results: MissionResults):
        """Log detailed analysis results"""
        self.logger.info("=== POST-FLIGHT ANALYSIS SUMMARY ===")
        self.logger.info(f"Max altitude: {results.max_altitude_km:.1f} km")
        self.logger.info(f"Final apoapsis: {results.apoapsis_km:.1f} km")
        self.logger.info(f"Final periapsis: {results.periapsis_km:.1f} km")
        self.logger.info(f"Final eccentricity: {results.eccentricity:.4f}")
        self.logger.info(f"Final velocity: {results.final_velocity_ms:.0f} m/s")
        self.logger.info(f"Time to apoapsis: {results.time_to_apoapsis:.1f} s")
        self.logger.info("===================================")
    
    def run_automated_checks(self, mission_data: Dict) -> bool:
        """
        Run automated validation checks as specified in Professor v36
        Returns True if mission meets all success criteria
        """
        results = self.analyze_mission(mission_data)
        
        # Professor v36 automated assertions
        try:
            assert results.periapsis_km > 150, f"Periapsis {results.periapsis_km:.1f} km <= 150 km"
            assert results.eccentricity < 0.05, f"Eccentricity {results.eccentricity:.4f} >= 0.05"
            
            self.logger.info("✅ All automated checks passed!")
            return True
            
        except AssertionError as e:
            self.logger.error(f"❌ Automated check failed: {e}")
            return False
    
    def generate_plots(self, mission_data: Dict):
        """
        Generate validation plots as specified in Professor v36
        - velocity_vs_time.png
        - flight_path_angle.png
        """
        try:
            import matplotlib.pyplot as plt
            
            # Extract time series data
            times = mission_data.get('times', [])
            velocities = mission_data.get('velocities', [])
            flight_path_angles = mission_data.get('flight_path_angles', [])
            
            if not times or not velocities:
                self.logger.warning("Insufficient data for plotting")
                return
            
            # Velocity vs Time plot
            plt.figure(figsize=(12, 8))
            plt.subplot(2, 1, 1)
            plt.plot(times, velocities, 'b-', linewidth=2)
            plt.xlabel('Time (s)')
            plt.ylabel('Velocity (m/s)')
            plt.title('Velocity vs Time')
            plt.grid(True, alpha=0.3)
            
            # Flight Path Angle plot
            plt.subplot(2, 1, 2)
            if flight_path_angles:
                plt.plot(times, flight_path_angles, 'r-', linewidth=2)
            plt.xlabel('Time (s)')
            plt.ylabel('Flight Path Angle (degrees)')
            plt.title('Flight Path Angle vs Time')
            plt.grid(True, alpha=0.3)
            
            plt.tight_layout()
            plt.savefig('velocity_vs_time.png', dpi=300, bbox_inches='tight')
            plt.close()
            
            # Separate flight path angle plot
            plt.figure(figsize=(10, 6))
            if flight_path_angles:
                plt.plot(times, flight_path_angles, 'r-', linewidth=2)
            plt.xlabel('Time (s)')
            plt.ylabel('Flight Path Angle (degrees)')
            plt.title('Flight Path Angle vs Time')
            plt.grid(True, alpha=0.3)
            plt.savefig('flight_path_angle.png', dpi=300, bbox_inches='tight')
            plt.close()
            
            self.logger.info("✅ Validation plots generated successfully")
            
        except ImportError:
            self.logger.warning("matplotlib not available, skipping plot generation")
        except Exception as e:
            self.logger.error(f"Error generating plots: {e}")
    
    def save_results_to_csv(self, results: MissionResults, filename: str = "sweep_results.csv"):
        """Save analysis results to CSV file for parameter sweep"""
        try:
            # Check if file exists to determine if we need headers
            file_exists = False
            try:
                with open(filename, 'r'):
                    file_exists = True
            except FileNotFoundError:
                pass
            
            with open(filename, 'a', newline='') as csvfile:
                fieldnames = [
                    'apoapsis_km', 'periapsis_km', 'eccentricity', 'max_altitude_km',
                    'final_velocity_ms', 'stage3_propellant_remaining', 
                    'horizontal_velocity_at_220km', 'time_to_apoapsis', 'mission_success'
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                if not file_exists:
                    writer.writeheader()
                
                writer.writerow({
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
            
            self.logger.info(f"Results saved to {filename}")
            
        except Exception as e:
            self.logger.error(f"Error saving results to CSV: {e}")

def main():
    """Main function for standalone post-flight analysis"""
    analyzer = PostFlightAnalyzer()
    
    # Example usage
    try:
        # Load mission data (would come from simulation)
        mission_data = {
            'final_apoapsis_km': 280.0,
            'final_periapsis_km': -50.0,  # Example failure case
            'final_eccentricity': 0.15,
            'max_altitude_km': 280.0,
            'final_velocity_ms': 7800.0,
            'stage3_propellant_remaining': 0.08,
            'horizontal_velocity_at_220km': 7200.0,
            'time_to_apoapsis': 45.0
        }
        
        # Run analysis
        results = analyzer.analyze_mission(mission_data)
        analyzer.run_automated_checks(mission_data)
        analyzer.save_results_to_csv(results)
        
    except Exception as e:
        logging.error(f"Error in post-flight analysis: {e}")

if __name__ == "__main__":
    main()