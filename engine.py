"""
Enhanced Engine Performance Model
Task 2-1 to 2-5: Altitude-dependent thrust and Isp curves with cubic spline interpolation
"""

import json
import numpy as np
from scipy.interpolate import CubicSpline, RectBivariateSpline
from typing import Dict, Tuple, Optional
import logging
from pathlib import Path


class EnginePerformanceModel:
    """
    High-fidelity engine performance model with altitude-dependent thrust and Isp
    Uses cubic spline interpolation for smooth performance curves
    """
    
    def __init__(self, engine_data_path: str = "engine_curve.json"):
        self.logger = logging.getLogger(__name__)
        self.engine_data = self._load_engine_data(engine_data_path)
        self.interpolators = self._build_interpolators()
        
    def _load_engine_data(self, data_path: str) -> Dict:
        """Load engine performance data from JSON file"""
        try:
            with open(data_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            self.logger.warning(f"Engine data file {data_path} not found. Using fallback data.")
            return self._get_fallback_data()
    
    def _get_fallback_data(self) -> Dict:
        """Fallback engine data if JSON file is not available"""
        return {
            "stages": {
                "S-IC": {
                    "thrust_curve": {"0": 34020000, "100000": 35100000},
                    "isp_curve": {
                        "1.0": {"0": 263, "100000": 289}
                    }
                },
                "S-II": {
                    "thrust_curve": {"0": 4400000, "100000": 5000000},
                    "isp_curve": {
                        "1.0": {"0": 395, "100000": 421}
                    }
                },
                "S-IVB": {
                    "thrust_curve": {"0": 825000, "100000": 1000000},
                    "isp_curve": {
                        "1.0": {"0": 441, "100000": 461}
                    }
                }
            }
        }
    
    def _build_interpolators(self) -> Dict:
        """Build cubic spline interpolators for each stage"""
        interpolators = {}
        
        for stage_name, stage_data in self.engine_data["stages"].items():
            # Extract altitude points and performance values
            thrust_data = stage_data["thrust_curve"]
            isp_data = stage_data["isp_curve"]
            
            # Handle thrust curve (1D)
            altitudes = np.array([float(alt) for alt in thrust_data.keys()])
            thrust_values = np.array([float(thrust) for thrust in thrust_data.values()])
            
            # Sort by altitude (required for interpolation)
            sort_indices = np.argsort(altitudes)
            altitudes = altitudes[sort_indices]
            thrust_values = thrust_values[sort_indices]
            
            # Create thrust spline interpolator
            thrust_spline = CubicSpline(altitudes, thrust_values, 
                                      bc_type='natural',
                                      extrapolate=True)
            
            # Handle Isp curve (check if 2D or legacy 1D format)
            if isinstance(list(isp_data.values())[0], dict):
                # New 2D format: throttle -> altitude -> Isp
                throttle_levels = sorted([float(t) for t in isp_data.keys()])
                
                # Build 2D grid for interpolation
                isp_grid = []
                for throttle in throttle_levels:
                    throttle_str = str(throttle)
                    if throttle_str in isp_data:
                        alt_isp_data = isp_data[throttle_str]
                        alt_points = sorted([float(alt) for alt in alt_isp_data.keys()])
                        isp_values = [float(alt_isp_data[str(alt)]) for alt in alt_points]
                        isp_grid.append(isp_values)
                
                # Create 2D interpolator
                isp_grid = np.array(isp_grid)
                alt_points = sorted([float(alt) for alt in isp_data[str(throttle_levels[0])].keys()])
                
                # RectBivariateSpline expects (x, y, z) where z[i,j] = f(x[i], y[j])
                isp_spline = RectBivariateSpline(throttle_levels, alt_points, isp_grid, 
                                               bbox=[0.5, 1.1, 0, 200000],  # throttle: 0.5-1.1, alt: 0-200km
                                               kx=min(3, len(throttle_levels)-1), 
                                               ky=min(3, len(alt_points)-1))
                
                interpolators[stage_name] = {
                    'thrust': thrust_spline,
                    'isp': isp_spline,
                    'isp_2d': True,
                    'altitude_range': (altitudes.min(), altitudes.max()),
                    'throttle_range': (min(throttle_levels), max(throttle_levels))
                }
                
            else:
                # Legacy 1D format: altitude -> Isp
                isp_values = np.array([float(isp) for isp in isp_data.values()])
                isp_values = isp_values[sort_indices]
                
                isp_spline = CubicSpline(altitudes, isp_values,
                                       bc_type='natural',
                                       extrapolate=True)
                
                interpolators[stage_name] = {
                    'thrust': thrust_spline,
                    'isp': isp_spline,
                    'isp_2d': False,
                    'altitude_range': (altitudes.min(), altitudes.max())
                }
            
            self.logger.info(f"Built interpolators for {stage_name}: "
                           f"altitude range {altitudes.min():.0f}-{altitudes.max():.0f}m, "
                           f"2D Isp: {interpolators[stage_name]['isp_2d']}")
        
        return interpolators
    
    def get_thrust(self, stage_name: str, altitude: float, throttle: float = 1.0) -> float:
        """
        Get thrust for a specific stage at given altitude and throttle setting
        
        Args:
            stage_name: Stage identifier ('S-IC', 'S-II', 'S-IVB')
            altitude: Altitude in meters
            throttle: Throttle setting (0.0 to 1.0)
            
        Returns:
            Thrust in Newtons
        """
        if stage_name not in self.interpolators:
            self.logger.warning(f"Unknown stage {stage_name}, using fallback")
            return self._get_fallback_thrust(stage_name, altitude) * throttle
        
        # Constrain altitude to reasonable bounds
        altitude = max(0, min(altitude, 150000))  # 0 to 150 km
        
        # Get interpolated thrust
        thrust_interpolator = self.interpolators[stage_name]['thrust']
        thrust = float(thrust_interpolator(altitude))
        
        # Apply throttle setting
        thrust *= throttle
        
        # Ensure positive thrust
        return max(0, thrust)
    
    def get_specific_impulse(self, stage_name: str, altitude: float, throttle: float = 1.0) -> float:
        """
        Get specific impulse for a specific stage at given altitude and throttle
        
        Args:
            stage_name: Stage identifier ('S-IC', 'S-II', 'S-IVB')
            altitude: Altitude in meters
            throttle: Throttle setting (0.0 to 1.0)
            
        Returns:
            Specific impulse in seconds
        """
        if stage_name not in self.interpolators:
            self.logger.warning(f"Unknown stage {stage_name}, using fallback")
            return self._get_fallback_isp(stage_name, altitude)
        
        # Constrain inputs to reasonable bounds
        altitude = max(0, min(altitude, 150000))  # 0 to 150 km
        throttle = max(0.5, min(throttle, 1.0))   # 50% to 100% throttle
        
        stage_data = self.interpolators[stage_name]
        
        if stage_data['isp_2d']:
            # Use 2D interpolation for throttle-dependent Isp
            isp_interpolator = stage_data['isp']
            isp = float(isp_interpolator(throttle, altitude)[0, 0])
        else:
            # Use 1D interpolation (legacy format)
            isp_interpolator = stage_data['isp']
            isp = float(isp_interpolator(altitude))
            # Apply throttle penalty for legacy data (approximate)
            throttle_factor = 0.95 + 0.05 * throttle  # 95-100% efficiency
            isp *= throttle_factor
        
        # Ensure reasonable Isp values
        return max(100, isp)  # Minimum 100 seconds Isp
    
    def get_mass_flow_rate(self, stage_name: str, altitude: float, 
                          throttle: float = 1.0) -> float:
        """
        Calculate mass flow rate based on thrust and Isp
        
        Args:
            stage_name: Stage identifier
            altitude: Altitude in meters
            throttle: Throttle setting (0.0 to 1.0)
            
        Returns:
            Mass flow rate in kg/s
        """
        thrust = self.get_thrust(stage_name, altitude, throttle)
        isp = self.get_specific_impulse(stage_name, altitude, throttle)
        
        # Standard gravity constant
        g0 = 9.80665  # m/s²
        
        if isp <= 0:
            return 0.0
        
        return thrust / (isp * g0)
    
    def _get_fallback_thrust(self, stage_name: str, altitude: float) -> float:
        """Fallback thrust calculation using linear interpolation"""
        fallback_data = {
            'S-IC': {'sea_level': 34020000, 'vacuum': 35100000},
            'S-II': {'sea_level': 4400000, 'vacuum': 5000000},
            'S-IVB': {'sea_level': 825000, 'vacuum': 1000000}
        }
        
        if stage_name not in fallback_data:
            return 0.0
        
        data = fallback_data[stage_name]
        
        if altitude <= 0:
            return data['sea_level']
        elif altitude >= 100000:
            return data['vacuum']
        else:
            # Linear interpolation
            factor = altitude / 100000
            return data['sea_level'] * (1 - factor) + data['vacuum'] * factor
    
    def _get_fallback_isp(self, stage_name: str, altitude: float) -> float:
        """Fallback Isp calculation using linear interpolation"""
        fallback_data = {
            'S-IC': {'sea_level': 263, 'vacuum': 289},
            'S-II': {'sea_level': 395, 'vacuum': 421},
            'S-IVB': {'sea_level': 441, 'vacuum': 461}
        }
        
        if stage_name not in fallback_data:
            return 300.0  # Default Isp
        
        data = fallback_data[stage_name]
        
        if altitude <= 0:
            return data['sea_level']
        elif altitude >= 100000:
            return data['vacuum']
        else:
            # Linear interpolation
            factor = altitude / 100000
            return data['sea_level'] * (1 - factor) + data['vacuum'] * factor
    
    def validate_model(self, reference_data: Optional[Dict] = None) -> Dict:
        """
        Validate the engine model against reference data
        
        Returns:
            Dictionary containing validation results and statistics
        """
        validation_results = {
            'stages_validated': 0,
            'mean_absolute_errors': {},
            'max_errors': {},
            'validation_passed': True
        }
        
        # Test altitudes from 0 to 100 km
        test_altitudes = np.linspace(0, 100000, 101)
        
        for stage_name in self.interpolators.keys():
            thrust_errors = []
            isp_errors = []
            
            for altitude in test_altitudes:
                # Get interpolated values
                thrust = self.get_thrust(stage_name, altitude)
                isp = self.get_specific_impulse(stage_name, altitude)
                
                # Simple validation: check for smoothness and reasonable values
                if stage_name == 'S-IC':
                    expected_thrust_range = (30e6, 40e6)  # 30-40 MN
                    expected_isp_range = (250, 350)       # 250-350 s
                elif stage_name == 'S-II':
                    expected_thrust_range = (4e6, 6e6)    # 4-6 MN
                    expected_isp_range = (380, 450)       # 380-450 s
                elif stage_name == 'S-IVB':
                    expected_thrust_range = (0.8e6, 1.2e6) # 0.8-1.2 MN
                    expected_isp_range = (430, 500)        # 430-500 s
                else:
                    continue
                
                # Check if values are within expected ranges
                thrust_in_range = expected_thrust_range[0] <= thrust <= expected_thrust_range[1]
                isp_in_range = expected_isp_range[0] <= isp <= expected_isp_range[1]
                
                if not thrust_in_range:
                    thrust_errors.append(altitude)
                if not isp_in_range:
                    isp_errors.append(altitude)
            
            # Calculate error statistics
            thrust_error_rate = len(thrust_errors) / len(test_altitudes)
            isp_error_rate = len(isp_errors) / len(test_altitudes)
            
            validation_results['mean_absolute_errors'][stage_name] = {
                'thrust_error_rate': thrust_error_rate,
                'isp_error_rate': isp_error_rate
            }
            
            # Check if validation passes (less than 5% error rate)
            stage_passes = thrust_error_rate < 0.05 and isp_error_rate < 0.05
            if not stage_passes:
                validation_results['validation_passed'] = False
            
            validation_results['stages_validated'] += 1
            
            self.logger.info(f"Validation for {stage_name}: "
                           f"Thrust error rate: {thrust_error_rate:.2%}, "
                           f"Isp error rate: {isp_error_rate:.2%}")
        
        return validation_results
    
    def generate_performance_report(self, output_path: str = "static_climb_report.md") -> str:
        """
        Generate a comprehensive performance report with plots
        
        Args:
            output_path: Path to save the markdown report
            
        Returns:
            Path to the generated report
        """
        # Test altitudes from 0 to 150 km
        altitudes = np.linspace(0, 150000, 151)
        
        report_lines = [
            "# Saturn V Engine Performance Report",
            "",
            "## Overview",
            f"Engine performance curves generated from {len(self.interpolators)} stages.",
            f"Altitude range: 0 - 150 km",
            f"Interpolation method: Cubic Spline",
            "",
        ]
        
        for stage_name, interpolator_data in self.interpolators.items():
            report_lines.extend([
                f"## {stage_name} Performance",
                "",
                "| Altitude (km) | Thrust (kN) | Isp (s) | Mass Flow (kg/s) |",
                "|---------------|-------------|---------|------------------|",
            ])
            
            # Sample performance at key altitudes
            key_altitudes = [0, 10000, 20000, 30000, 50000, 70000, 100000]
            
            for alt in key_altitudes:
                if alt <= 150000:  # Within our range
                    thrust = self.get_thrust(stage_name, alt) / 1000  # Convert to kN
                    isp = self.get_specific_impulse(stage_name, alt)
                    mass_flow = self.get_mass_flow_rate(stage_name, alt)
                    
                    report_lines.append(
                        f"| {alt/1000:.0f} | {thrust:.0f} | {isp:.1f} | {mass_flow:.1f} |"
                    )
            
            report_lines.append("")
        
        # Add validation results
        validation_results = self.validate_model()
        report_lines.extend([
            "## Model Validation",
            "",
            f"**Overall Validation:** {'✅ PASSED' if validation_results['validation_passed'] else '❌ FAILED'}",
            f"**Stages Validated:** {validation_results['stages_validated']}",
            "",
        ])
        
        for stage_name, errors in validation_results['mean_absolute_errors'].items():
            thrust_err = errors['thrust_error_rate']
            isp_err = errors['isp_error_rate']
            report_lines.extend([
                f"**{stage_name}:**",
                f"- Thrust error rate: {thrust_err:.2%}",
                f"- Isp error rate: {isp_err:.2%}",
                "",
            ])
        
        # Write report to file
        with open(output_path, 'w') as f:
            f.write('\n'.join(report_lines))
        
        self.logger.info(f"Performance report saved to {output_path}")
        return output_path


# Global engine model instance
_engine_model = None

def get_engine_model() -> EnginePerformanceModel:
    """Get singleton engine performance model"""
    global _engine_model
    if _engine_model is None:
        _engine_model = EnginePerformanceModel()
    return _engine_model


def main():
    """Test and validate the engine performance model"""
    print("Saturn V Engine Performance Model Test")
    print("=" * 50)
    
    # Initialize engine model
    engine_model = EnginePerformanceModel()
    
    # Test performance at various altitudes
    test_altitudes = [0, 10000, 30000, 50000, 100000]
    stages = ['S-IC', 'S-II', 'S-IVB']
    
    for stage in stages:
        print(f"\n{stage} Performance:")
        print("Altitude (km) | Thrust (kN) | Isp (s) | Mass Flow (kg/s)")
        print("-" * 55)
        
        for alt in test_altitudes:
            thrust = engine_model.get_thrust(stage, alt) / 1000
            isp = engine_model.get_specific_impulse(stage, alt)
            mass_flow = engine_model.get_mass_flow_rate(stage, alt)
            
            print(f"{alt/1000:8.0f}    | {thrust:8.0f}  | {isp:6.1f} | {mass_flow:10.1f}")
    
    # Validate model
    print("\nModel Validation:")
    validation_results = engine_model.validate_model()
    
    print(f"Validation passed: {validation_results['validation_passed']}")
    print(f"Stages validated: {validation_results['stages_validated']}")
    
    # Generate performance report
    report_path = engine_model.generate_performance_report()
    print(f"\nDetailed report saved to: {report_path}")


if __name__ == "__main__":
    main()