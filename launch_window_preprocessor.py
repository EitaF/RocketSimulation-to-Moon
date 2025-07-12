"""
Launch Window Preprocessor
Professor v42: Advanced plane-targeting with RAAN alignment for optimal launch windows

This module implements systematic launch window calculation based on β-angle theory
to minimize orbital plane mismatch and achieve RAAN alignment within ±5°.
"""

import numpy as np
from datetime import datetime, timedelta
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass
import logging

# Constants
EARTH_ROTATION_RATE = 7.2921159e-5  # rad/s
MOON_ORBITAL_PERIOD = 27.321661  # days
SIDEREAL_DAY = 86164.0905  # seconds
J2000_EPOCH = datetime(2000, 1, 1, 12, 0, 0)  # J2000 epoch


@dataclass
class LaunchOpportunity:
    """Enhanced launch opportunity with plane-targeting metrics"""
    start_time: datetime
    end_time: datetime
    launch_azimuth: float      # Launch azimuth [degrees]
    target_inclination: float  # Target orbital inclination [degrees]
    target_raan: float        # Target RAAN [degrees]
    achieved_raan: float      # Achieved RAAN [degrees]
    raan_error: float         # RAAN error [degrees]
    beta_angle: float         # β-angle for plane alignment [degrees]
    delta_v_penalty: float    # ΔV penalty for plane change [m/s]
    moon_phase_angle: float   # Moon phase angle [degrees]
    lunar_ascending_node: float  # Lunar ascending node angle [degrees]
    quality_score: float      # Overall window quality [0-1]


@dataclass
class PlanetTargetingResult:
    """Results from plane-targeting analysis"""
    opportunities: List[LaunchOpportunity]
    optimal_window: Optional[LaunchOpportunity]
    raan_alignment_windows: List[LaunchOpportunity]  # Windows with RAAN error < 5°
    total_windows_analyzed: int


class LaunchWindowPreprocessor:
    """
    Advanced launch window preprocessor with plane-targeting optimization
    
    Implements Professor v42 recommendations:
    1. Launch Window Solver based on β-angle theory
    2. RAAN alignment within ±5° for minimal plane change ΔV
    3. Lunar ascending node synchronization
    4. Systematic orbital plane matching
    """
    
    def __init__(self, launch_site_lat: float = 28.5, launch_site_lon: float = -80.6):
        """
        Initialize launch window preprocessor
        
        Args:
            launch_site_lat: Launch site latitude [degrees] (default: KSC)
            launch_site_lon: Launch site longitude [degrees] (default: KSC)
        """
        self.latitude = np.radians(launch_site_lat)
        self.longitude = np.radians(launch_site_lon)
        self.logger = logging.getLogger(__name__)
        
        # Plane-targeting constraints (Professor v42 requirements)
        self.max_raan_error = 5.0      # Maximum RAAN error [degrees]
        self.max_beta_angle = 5.0      # Maximum β-angle [degrees]
        self.max_plane_change_dv = 180.0  # Maximum plane change ΔV [m/s]
        
        self.logger.info(f"Launch Window Preprocessor initialized for {launch_site_lat:.1f}°N, {launch_site_lon:.1f}°W")
    
    def calculate_lunar_orbital_elements(self, time: datetime) -> Dict[str, float]:
        """
        Calculate Moon's orbital elements at given time
        
        Args:
            time: Time for calculation
            
        Returns:
            Dictionary with lunar orbital elements
        """
        # Days since J2000
        days_since_j2000 = (time - J2000_EPOCH).total_seconds() / 86400.0
        
        # Moon's mean elements (simplified but more accurate than before)
        # Based on JPL ephemeris approximations
        
        # Mean longitude
        L = np.radians(218.3164477 + 13.17639648 * days_since_j2000)
        
        # Mean anomaly
        M = np.radians(134.9633964 + 13.06499295 * days_since_j2000)
        
        # Argument of perigee
        omega = np.radians(318.0634 + 0.1643573 * days_since_j2000)
        
        # Longitude of ascending node
        Omega = np.radians(125.0445479 - 0.05295376 * days_since_j2000)
        
        # Inclination (nearly constant)
        inclination = np.radians(5.1453964)
        
        # Approximate orbital radius
        r = 384400e3  # Mean Earth-Moon distance [m]
        
        return {
            'mean_longitude': np.degrees(L),
            'mean_anomaly': np.degrees(M),
            'arg_periapsis': np.degrees(omega),
            'raan': np.degrees(Omega),
            'inclination': np.degrees(inclination),
            'radius': r,
            'angular_velocity': 360.0 / MOON_ORBITAL_PERIOD  # degrees/day
        }
    
    def calculate_beta_angle(self, launch_time: datetime, target_raan: float, 
                           target_inclination: float) -> float:
        """
        Calculate β-angle for orbital plane alignment
        
        β-angle represents the angle between the orbital plane and
        the lunar ascending node direction.
        
        Args:
            launch_time: Proposed launch time
            target_raan: Target RAAN [degrees]
            target_inclination: Target inclination [degrees]
            
        Returns:
            β-angle in degrees
        """
        # Get lunar orbital elements
        lunar_elements = self.calculate_lunar_orbital_elements(launch_time)
        lunar_raan = lunar_elements['raan']
        lunar_inclination = lunar_elements['inclination']
        
        # Calculate angle between target plane and lunar plane
        # Using spherical trigonometry
        cos_beta = (np.cos(np.radians(target_inclination)) * np.cos(np.radians(lunar_inclination)) +
                   np.sin(np.radians(target_inclination)) * np.sin(np.radians(lunar_inclination)) *
                   np.cos(np.radians(target_raan - lunar_raan)))
        
        beta_angle = np.degrees(np.arccos(np.clip(cos_beta, -1.0, 1.0)))
        
        return min(beta_angle, 180.0 - beta_angle)  # Take acute angle
    
    def calculate_launch_azimuth_for_raan(self, launch_time: datetime, 
                                        target_raan: float, 
                                        target_inclination: float) -> float:
        """
        Calculate launch azimuth to achieve specific RAAN
        
        Args:
            launch_time: Launch time
            target_raan: Desired RAAN [degrees]
            target_inclination: Desired inclination [degrees]
            
        Returns:
            Launch azimuth in degrees
        """
        # Calculate Greenwich Mean Sidereal Time
        gmst = self._calculate_gmst(launch_time)
        
        # Local sidereal time
        lst = gmst + self.longitude
        
        # Hour angle of ascending node
        han = np.radians(target_raan) - lst
        
        # Launch azimuth calculation using spherical trigonometry
        inc_rad = np.radians(target_inclination)
        lat_rad = self.latitude
        
        # Avoid gimbal lock at poles
        if abs(np.cos(lat_rad)) < 1e-6:
            return 0.0 if target_inclination >= abs(np.degrees(lat_rad)) else 90.0
        
        cos_azimuth = np.sin(inc_rad) * np.cos(han) / np.cos(lat_rad)
        
        # Check for impossible geometry
        if abs(cos_azimuth) > 1.0:
            # Cannot achieve this inclination from this latitude
            return np.nan
        
        azimuth = np.degrees(np.arccos(cos_azimuth))
        
        # Determine quadrant based on RAAN and inclination
        if np.sin(han) < 0:
            azimuth = 360.0 - azimuth
        
        return azimuth
    
    def calculate_plane_change_delta_v(self, raan_error: float, 
                                     orbital_velocity: float = 7800.0) -> float:
        """
        Calculate ΔV penalty for orbital plane change
        
        Args:
            raan_error: RAAN error [degrees]
            orbital_velocity: Orbital velocity [m/s]
            
        Returns:
            Plane change ΔV [m/s]
        """
        if abs(raan_error) < 0.1:  # Negligible error
            return 0.0
        
        # For small plane changes, ΔV ≈ V * sin(Δi)
        # RAAN error translates roughly to inclination change
        raan_error_rad = np.radians(abs(raan_error))
        
        # Simplified calculation: RAAN change ≈ plane change for small angles
        delta_v = orbital_velocity * np.sin(raan_error_rad)
        
        return delta_v
    
    def find_raan_alignment_windows(self, start_date: datetime, 
                                  duration_days: int = 30,
                                  target_lunar_raan_offset: float = 65.0,
                                  target_inclination: float = 28.5,
                                  time_step_hours: float = 1.0) -> List[LaunchOpportunity]:
        """
        Find launch windows with optimal RAAN alignment
        
        Args:
            start_date: Search start date
            duration_days: Search duration [days]
            target_lunar_raan_offset: Target offset from lunar ascending node [degrees]
            target_inclination: Target orbital inclination [degrees]
            time_step_hours: Time step for search [hours]
            
        Returns:
            List of launch opportunities with RAAN alignment data
        """
        opportunities = []
        current_time = start_date
        end_time = start_date + timedelta(days=duration_days)
        time_step = timedelta(hours=time_step_hours)
        
        self.logger.info(f"Searching for RAAN alignment windows from {start_date} to {end_time}")
        
        while current_time < end_time:
            # Get lunar orbital elements
            lunar_elements = self.calculate_lunar_orbital_elements(current_time)
            lunar_raan = lunar_elements['raan']
            
            # Calculate target RAAN based on lunar ascending node
            target_raan = (lunar_raan + target_lunar_raan_offset) % 360.0
            
            # Calculate launch azimuth for this RAAN
            launch_azimuth = self.calculate_launch_azimuth_for_raan(
                current_time, target_raan, target_inclination
            )
            
            # Skip if launch azimuth is invalid (impossible geometry)
            if np.isnan(launch_azimuth):
                current_time += time_step
                continue
            
            # Check azimuth constraints (reasonable launch corridors)
            if not (45.0 <= launch_azimuth <= 135.0):  # Eastward launches preferred
                current_time += time_step
                continue
            
            # Calculate achieved RAAN (accounting for Earth rotation during ascent)
            ascent_time = 8.5 * 60  # Typical ascent time to LEO [seconds]
            achieved_raan = (target_raan + EARTH_ROTATION_RATE * ascent_time * 180/np.pi) % 360.0
            
            # Calculate RAAN error
            raan_error = self._angle_difference(achieved_raan, target_raan)
            
            # Calculate β-angle
            beta_angle = self.calculate_beta_angle(current_time, target_raan, target_inclination)
            
            # Calculate plane change penalty
            delta_v_penalty = self.calculate_plane_change_delta_v(raan_error)
            
            # Calculate Moon phase angle
            moon_phase_angle = (lunar_elements['mean_longitude'] - target_raan) % 360.0
            
            # Calculate quality score
            raan_score = max(0, 1.0 - abs(raan_error) / self.max_raan_error)
            beta_score = max(0, 1.0 - abs(beta_angle) / self.max_beta_angle)
            dv_score = max(0, 1.0 - delta_v_penalty / self.max_plane_change_dv)
            
            quality_score = (raan_score * 0.5 + beta_score * 0.3 + dv_score * 0.2)
            
            # Create launch opportunity
            opportunity = LaunchOpportunity(
                start_time=current_time,
                end_time=current_time + timedelta(minutes=30),  # 30-minute window
                launch_azimuth=launch_azimuth,
                target_inclination=target_inclination,
                target_raan=target_raan,
                achieved_raan=achieved_raan,
                raan_error=raan_error,
                beta_angle=beta_angle,
                delta_v_penalty=delta_v_penalty,
                moon_phase_angle=moon_phase_angle,
                lunar_ascending_node=lunar_raan,
                quality_score=quality_score
            )
            
            opportunities.append(opportunity)
            current_time += time_step
        
        self.logger.info(f"Found {len(opportunities)} launch opportunities")
        return opportunities
    
    def filter_optimal_windows(self, opportunities: List[LaunchOpportunity],
                             max_windows: int = 10) -> PlanetTargetingResult:
        """
        Filter and rank launch opportunities
        
        Args:
            opportunities: List of launch opportunities
            max_windows: Maximum number of windows to return
            
        Returns:
            PlanetTargetingResult with filtered opportunities
        """
        # Filter for RAAN alignment (Professor v42 requirement: ±5°)
        raan_aligned = [op for op in opportunities if abs(op.raan_error) <= self.max_raan_error]
        
        # Sort by quality score
        sorted_opportunities = sorted(opportunities, key=lambda x: x.quality_score, reverse=True)
        sorted_raan_aligned = sorted(raan_aligned, key=lambda x: x.quality_score, reverse=True)
        
        # Select optimal window
        optimal_window = sorted_opportunities[0] if sorted_opportunities else None
        
        self.logger.info(f"RAAN alignment analysis: {len(raan_aligned)}/{len(opportunities)} "
                        f"windows meet ±{self.max_raan_error}° requirement")
        
        if optimal_window:
            self.logger.info(f"Optimal window: {optimal_window.start_time}, "
                           f"RAAN error: {optimal_window.raan_error:.2f}°, "
                           f"β-angle: {optimal_window.beta_angle:.2f}°, "
                           f"ΔV penalty: {optimal_window.delta_v_penalty:.1f} m/s")
        
        return PlanetTargetingResult(
            opportunities=sorted_opportunities[:max_windows],
            optimal_window=optimal_window,
            raan_alignment_windows=sorted_raan_aligned[:max_windows],
            total_windows_analyzed=len(opportunities)
        )
    
    def _calculate_gmst(self, time: datetime) -> float:
        """Calculate Greenwich Mean Sidereal Time [radians]"""
        days_since_j2000 = (time - J2000_EPOCH).total_seconds() / 86400.0
        
        # GMST at 0h UT (Meeus formula)
        gmst0 = np.radians(280.46061837 + 360.98564736629 * days_since_j2000 +
                          0.000387933 * days_since_j2000**2 - 
                          days_since_j2000**3 / 38710000.0)
        
        # Add time of day
        time_of_day = (time.hour + time.minute/60.0 + time.second/3600.0) / 24.0
        gmst = gmst0 + 2 * np.pi * time_of_day
        
        return gmst % (2 * np.pi)
    
    def _angle_difference(self, angle1: float, angle2: float) -> float:
        """Calculate smallest difference between two angles [degrees]"""
        diff = (angle1 - angle2 + 180) % 360 - 180
        return diff
    
    def generate_launch_plan(self, start_date: datetime,
                           mission_duration_days: int = 5) -> Dict:
        """
        Generate comprehensive launch plan with plane-targeting
        
        Args:
            start_date: Mission start date
            mission_duration_days: Mission duration for window analysis
            
        Returns:
            Dictionary with complete launch plan
        """
        # Find RAAN alignment windows
        opportunities = self.find_raan_alignment_windows(
            start_date, mission_duration_days, 65.0, 28.5, 0.5  # 30-minute steps
        )
        
        # Filter and rank
        result = self.filter_optimal_windows(opportunities, 20)
        
        # Generate summary statistics
        avg_raan_error = np.mean([op.raan_error for op in result.raan_alignment_windows]) if result.raan_alignment_windows else 0
        avg_dv_penalty = np.mean([op.delta_v_penalty for op in result.raan_alignment_windows]) if result.raan_alignment_windows else 0
        
        launch_plan = {
            'analysis_period': {
                'start': start_date,
                'duration_days': mission_duration_days,
                'total_opportunities': result.total_windows_analyzed
            },
            'optimal_window': {
                'time': result.optimal_window.start_time if result.optimal_window else None,
                'azimuth': result.optimal_window.launch_azimuth if result.optimal_window else None,
                'raan_error': result.optimal_window.raan_error if result.optimal_window else None,
                'quality_score': result.optimal_window.quality_score if result.optimal_window else None
            },
            'raan_aligned_windows': len(result.raan_alignment_windows),
            'statistics': {
                'avg_raan_error': avg_raan_error,
                'avg_dv_penalty': avg_dv_penalty,
                'success_rate': len(result.raan_alignment_windows) / max(1, result.total_windows_analyzed)
            },
            'recommendations': {
                'proceed_with_optimal': result.optimal_window is not None and 
                                      abs(result.optimal_window.raan_error) <= self.max_raan_error,
                'backup_windows': len(result.raan_alignment_windows) >= 3,
                'plane_targeting_feasible': avg_dv_penalty <= self.max_plane_change_dv
            }
        }
        
        return launch_plan


def create_launch_window_preprocessor(launch_site_lat: float = 28.5,
                                    launch_site_lon: float = -80.6) -> LaunchWindowPreprocessor:
    """
    Factory function to create launch window preprocessor
    
    Args:
        launch_site_lat: Launch site latitude [degrees]
        launch_site_lon: Launch site longitude [degrees]
        
    Returns:
        Configured LaunchWindowPreprocessor instance
    """
    return LaunchWindowPreprocessor(launch_site_lat, launch_site_lon)


# Example usage and testing
if __name__ == "__main__":
    print("Testing Launch Window Preprocessor with Plane-Targeting")
    print("=" * 60)
    
    # Create preprocessor for Kennedy Space Center
    preprocessor = create_launch_window_preprocessor(28.5, -80.6)
    
    # Test launch plan generation
    start_date = datetime.now()
    launch_plan = preprocessor.generate_launch_plan(start_date, 7)  # 7-day analysis
    
    print(f"Launch Plan Analysis Results:")
    print(f"Analysis period: {launch_plan['analysis_period']['start'].strftime('%Y-%m-%d')} "
          f"({launch_plan['analysis_period']['duration_days']} days)")
    print(f"Total opportunities analyzed: {launch_plan['analysis_period']['total_opportunities']}")
    
    if launch_plan['optimal_window']['time']:
        print(f"\nOptimal Launch Window:")
        print(f"  Time: {launch_plan['optimal_window']['time'].strftime('%Y-%m-%d %H:%M')}")
        print(f"  Azimuth: {launch_plan['optimal_window']['azimuth']:.1f}°")
        print(f"  RAAN error: {launch_plan['optimal_window']['raan_error']:.2f}°")
        print(f"  Quality score: {launch_plan['optimal_window']['quality_score']:.3f}")
    
    print(f"\nRAAN Alignment Analysis:")
    print(f"  Windows within ±5° RAAN: {launch_plan['raan_aligned_windows']}")
    print(f"  Average RAAN error: {launch_plan['statistics']['avg_raan_error']:.2f}°")
    print(f"  Average ΔV penalty: {launch_plan['statistics']['avg_dv_penalty']:.1f} m/s")
    print(f"  Success rate: {launch_plan['statistics']['success_rate']:.1%}")
    
    print(f"\nRecommendations:")
    print(f"  Proceed with optimal window: {launch_plan['recommendations']['proceed_with_optimal']}")
    print(f"  Sufficient backup windows: {launch_plan['recommendations']['backup_windows']}")
    print(f"  Plane targeting feasible: {launch_plan['recommendations']['plane_targeting_feasible']}")