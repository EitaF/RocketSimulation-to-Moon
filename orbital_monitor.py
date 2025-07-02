"""
Orbital Monitor Module
Professor v27: Real-time orbital parameter calculation and mission event triggering
"""

import numpy as np
import logging
from typing import Dict, Tuple, Optional
from dataclasses import dataclass
from vehicle import Vector3

# Physical constants
G = 6.67430e-11  # Gravitational constant [m^3/kg/s^2]
M_EARTH = 5.972e24  # Earth mass [kg]
R_EARTH = 6371e3  # Earth radius [m]
MU_EARTH = G * M_EARTH  # Standard gravitational parameter [m^3/s^2]


@dataclass
class OrbitalState:
    """Complete orbital state information"""
    # Position and velocity
    position: Vector3
    velocity: Vector3
    altitude: float
    
    # Classical orbital elements
    semi_major_axis: float  # a [m]
    eccentricity: float     # e [dimensionless]
    inclination: float      # i [degrees]
    longitude_of_ascending_node: float  # Ω [degrees]
    argument_of_periapsis: float       # ω [degrees]
    true_anomaly: float     # ν [degrees]
    
    # Derived parameters
    apoapsis: float         # [m]
    periapsis: float        # [m]
    orbital_period: float   # [s]
    current_altitude: float # [m]
    
    # Mission-critical parameters
    time_to_apoapsis: float    # [s]
    time_to_periapsis: float   # [s]
    orbital_energy: float      # [J/kg]
    angular_momentum: float    # [m^2/s]
    
    # State flags
    is_elliptical: bool
    is_circular: bool
    is_hyperbolic: bool
    is_escape_trajectory: bool


class OrbitalMonitor:
    """
    Real-time orbital parameter calculation and mission event detection
    Professor v27: On-board orbit determination module
    """
    
    def __init__(self, update_interval: float = 0.1):
        """
        Initialize orbital monitor
        
        Args:
            update_interval: Update interval in seconds
        """
        self.logger = logging.getLogger(__name__)
        self.update_interval = update_interval
        self.last_update_time = 0.0
        
        # Current orbital state
        self.current_state: Optional[OrbitalState] = None
        self.previous_state: Optional[OrbitalState] = None
        
        # Circular orbit criteria
        self.circular_eccentricity_threshold = 0.01  # e < 0.01 for circular
        self.apoapsis_periapsis_tolerance = 5000     # 5 km tolerance
        
        # Event detection
        self.apoapsis_approach_threshold = 60.0  # seconds
        self.periapsis_approach_threshold = 60.0  # seconds
        
        self.logger.info("Orbital Monitor initialized")
    
    def should_update(self, current_time: float) -> bool:
        """Check if monitor should update"""
        return (current_time - self.last_update_time) >= self.update_interval
    
    def update_state(self, position: Vector3, velocity: Vector3, time: float) -> bool:
        """
        Update orbital state with current position and velocity
        
        Args:
            position: Current position vector [m]
            velocity: Current velocity vector [m/s]
            time: Current mission time [s]
            
        Returns:
            True if state was updated, False if using cached values
        """
        if not self.should_update(time):
            return False
        
        self.last_update_time = time
        
        # Store previous state
        self.previous_state = self.current_state
        
        # Calculate new orbital state
        self.current_state = self._calculate_orbital_state(position, velocity, time)
        
        return True
    
    def _calculate_orbital_state(self, position: Vector3, velocity: Vector3, time: float) -> OrbitalState:
        """Calculate complete orbital state from position and velocity"""
        
        # Basic parameters
        r = position.magnitude()
        v = velocity.magnitude()
        altitude = r - R_EARTH
        
        # Orbital energy (specific energy)
        orbital_energy = 0.5 * v**2 - MU_EARTH / r
        
        # Angular momentum vector
        h_vec = Vector3(
            position.y * velocity.z - position.z * velocity.y,
            position.z * velocity.x - position.x * velocity.z,
            position.x * velocity.y - position.y * velocity.x
        )
        angular_momentum = h_vec.magnitude()
        
        # Classify trajectory type
        is_escape_trajectory = orbital_energy >= 0
        is_hyperbolic = orbital_energy > 0
        
        if is_escape_trajectory:
            # Hyperbolic/parabolic trajectory
            semi_major_axis = float('inf') if orbital_energy == 0 else -MU_EARTH / (2 * orbital_energy)
            eccentricity = float('inf') if angular_momentum == 0 else np.sqrt(1 + 2 * orbital_energy * angular_momentum**2 / MU_EARTH**2)
            apoapsis = float('inf')
            periapsis = float('-inf')
            orbital_period = float('inf')
            time_to_apoapsis = float('inf')
            time_to_periapsis = float('inf')
            is_elliptical = False
            is_circular = False
        else:
            # Elliptical orbit
            semi_major_axis = -MU_EARTH / (2 * orbital_energy)
            
            if angular_momentum > 0:
                eccentricity = np.sqrt(1 + 2 * orbital_energy * angular_momentum**2 / MU_EARTH**2)
            else:
                eccentricity = 0.0
            
            # Apoapsis and periapsis
            apoapsis = semi_major_axis * (1 + eccentricity)
            periapsis = semi_major_axis * (1 - eccentricity)
            
            # Orbital period
            orbital_period = 2 * np.pi * np.sqrt(semi_major_axis**3 / MU_EARTH)
            
            # Time to apoapsis and periapsis
            time_to_apoapsis, time_to_periapsis = self._calculate_time_to_apsides(
                position, velocity, semi_major_axis, eccentricity
            )
            
            is_elliptical = True
            is_circular = eccentricity < self.circular_eccentricity_threshold
        
        # Classical orbital elements (simplified calculation)
        inclination, longitude_of_ascending_node, argument_of_periapsis, true_anomaly = (
            self._calculate_classical_elements(position, velocity, h_vec)
        )
        
        return OrbitalState(
            position=position,
            velocity=velocity,
            altitude=altitude,
            semi_major_axis=semi_major_axis,
            eccentricity=eccentricity,
            inclination=inclination,
            longitude_of_ascending_node=longitude_of_ascending_node,
            argument_of_periapsis=argument_of_periapsis,
            true_anomaly=true_anomaly,
            apoapsis=apoapsis,
            periapsis=periapsis,
            orbital_period=orbital_period,
            current_altitude=altitude,
            time_to_apoapsis=time_to_apoapsis,
            time_to_periapsis=time_to_periapsis,
            orbital_energy=orbital_energy,
            angular_momentum=angular_momentum,
            is_elliptical=is_elliptical,
            is_circular=is_circular,
            is_hyperbolic=is_hyperbolic,
            is_escape_trajectory=is_escape_trajectory
        )
    
    def _calculate_time_to_apsides(self, position: Vector3, velocity: Vector3, 
                                  semi_major_axis: float, eccentricity: float) -> Tuple[float, float]:
        """Calculate time to apoapsis and periapsis"""
        
        if eccentricity >= 1.0:
            return float('inf'), float('inf')
        
        # Mean motion
        n = np.sqrt(MU_EARTH / semi_major_axis**3)
        
        # Current radius and radial velocity
        r = position.magnitude()
        r_dot = (position.data @ velocity.data) / r
        
        # Eccentric anomaly from position
        cos_E = (1 - r / semi_major_axis) / eccentricity if eccentricity > 0 else 0
        cos_E = np.clip(cos_E, -1, 1)
        
        # Determine quadrant based on radial velocity
        if r_dot >= 0:  # Moving away from Earth
            E = np.arccos(cos_E)  # 0 to π
        else:  # Moving toward Earth
            E = 2 * np.pi - np.arccos(cos_E)  # π to 2π
        
        # Mean anomaly
        M = E - eccentricity * np.sin(E)
        
        # Time to apoapsis (E = π)
        M_apoapsis = np.pi - eccentricity * np.sin(np.pi)  # = π
        if M < M_apoapsis:
            time_to_apoapsis = (M_apoapsis - M) / n
        else:
            time_to_apoapsis = (2 * np.pi + M_apoapsis - M) / n
        
        # Time to periapsis (E = 0 or 2π)
        M_periapsis = 0
        if M > M_periapsis:
            time_to_periapsis = (2 * np.pi + M_periapsis - M) / n
        else:
            time_to_periapsis = (M_periapsis - M) / n
        
        return time_to_apoapsis, time_to_periapsis
    
    def _calculate_classical_elements(self, position: Vector3, velocity: Vector3, 
                                    h_vec: Vector3) -> Tuple[float, float, float, float]:
        """Calculate classical orbital elements (simplified)"""
        
        # Inclination
        h_magnitude = h_vec.magnitude()
        if h_magnitude > 0:
            inclination = np.degrees(np.arccos(np.clip(h_vec.z / h_magnitude, -1, 1)))
        else:
            inclination = 0.0
        
        # For simplified implementation, set other elements to zero
        # In a full implementation, these would be calculated properly
        longitude_of_ascending_node = 0.0
        argument_of_periapsis = 0.0
        
        # True anomaly (angle from periapsis)
        r = position.magnitude()
        v = velocity.magnitude()
        r_dot = (position.data @ velocity.data) / r
        
        # Simplified true anomaly calculation
        if h_magnitude > 0 and r > 0:
            cos_nu = (h_magnitude**2 / (MU_EARTH * r) - 1) / self.current_state.eccentricity if hasattr(self, 'current_state') and self.current_state and self.current_state.eccentricity > 0 else 0
            cos_nu = np.clip(cos_nu, -1, 1)
            true_anomaly = np.degrees(np.arccos(cos_nu))
            if r_dot < 0:  # Moving toward periapsis
                true_anomaly = 360 - true_anomaly
        else:
            true_anomaly = 0.0
        
        return inclination, longitude_of_ascending_node, argument_of_periapsis, true_anomaly
    
    def get_current_state(self) -> Optional[OrbitalState]:
        """Get current orbital state"""
        return self.current_state
    
    def is_approaching_apoapsis(self, threshold_seconds: float = None) -> bool:
        """Check if vehicle is approaching apoapsis"""
        if not self.current_state or self.current_state.is_escape_trajectory:
            return False
        
        threshold = threshold_seconds or self.apoapsis_approach_threshold
        return self.current_state.time_to_apoapsis <= threshold
    
    def is_approaching_periapsis(self, threshold_seconds: float = None) -> bool:
        """Check if vehicle is approaching periapsis"""
        if not self.current_state or self.current_state.is_escape_trajectory:
            return False
        
        threshold = threshold_seconds or self.periapsis_approach_threshold
        return self.current_state.time_to_periapsis <= threshold
    
    def is_at_apoapsis(self, tolerance_seconds: float = 5.0) -> bool:
        """Check if vehicle is at apoapsis"""
        if not self.current_state or self.current_state.is_escape_trajectory:
            return False
        
        return self.current_state.time_to_apoapsis <= tolerance_seconds
    
    def is_at_periapsis(self, tolerance_seconds: float = 5.0) -> bool:
        """Check if vehicle is at periapsis"""
        if not self.current_state or self.current_state.is_escape_trajectory:
            return False
        
        return self.current_state.time_to_periapsis <= tolerance_seconds
    
    def is_orbit_circular(self, tolerance_km: float = None) -> bool:
        """
        Check if current orbit is circular within tolerance
        Professor v27: Success criteria - circular orbit within 5km tolerance
        """
        if not self.current_state or self.current_state.is_escape_trajectory:
            return False
        
        tolerance = (tolerance_km or 5.0) * 1000  # Convert to meters
        
        # Check both eccentricity and apoapsis-periapsis difference
        eccentricity_ok = self.current_state.eccentricity < self.circular_eccentricity_threshold
        apoapsis_periapsis_diff = abs(self.current_state.apoapsis - self.current_state.periapsis)
        altitude_diff_ok = apoapsis_periapsis_diff < tolerance
        
        return eccentricity_ok and altitude_diff_ok
    
    def get_orbital_summary(self) -> Dict:
        """Get summary of orbital parameters for logging"""
        if not self.current_state:
            return {'status': 'no_data'}
        
        state = self.current_state
        
        return {
            'altitude_km': state.altitude / 1000,
            'apoapsis_km': state.apoapsis / 1000 if state.apoapsis != float('inf') else 'inf',
            'periapsis_km': state.periapsis / 1000 if state.periapsis != float('-inf') else '-inf',
            'eccentricity': state.eccentricity,
            'inclination_deg': state.inclination,
            'orbital_period_min': state.orbital_period / 60 if state.orbital_period != float('inf') else 'inf',
            'time_to_apoapsis_min': state.time_to_apoapsis / 60 if state.time_to_apoapsis != float('inf') else 'inf',
            'time_to_periapsis_min': state.time_to_periapsis / 60 if state.time_to_periapsis != float('inf') else 'inf',
            'orbital_energy': state.orbital_energy,
            'is_circular': state.is_circular,
            'is_escape_trajectory': state.is_escape_trajectory
        }
    
    def validate_against_post_flight_analysis(self, reference_apoapsis: float, 
                                            reference_periapsis: float) -> Dict:
        """
        Validate orbital monitor accuracy against post-flight analysis
        Professor v27: <0.5% error requirement
        """
        if not self.current_state:
            return {'error': 'no_current_state'}
        
        # Calculate percentage errors
        apoapsis_error = abs(self.current_state.apoapsis - reference_apoapsis) / reference_apoapsis * 100
        periapsis_error = abs(self.current_state.periapsis - reference_periapsis) / reference_periapsis * 100
        
        # Check if within tolerance
        tolerance_percent = 0.5  # 0.5% as required by Professor
        apoapsis_within_tolerance = apoapsis_error <= tolerance_percent
        periapsis_within_tolerance = periapsis_error <= tolerance_percent
        
        return {
            'apoapsis_error_percent': apoapsis_error,
            'periapsis_error_percent': periapsis_error,
            'apoapsis_within_tolerance': apoapsis_within_tolerance,
            'periapsis_within_tolerance': periapsis_within_tolerance,
            'overall_validation_passed': apoapsis_within_tolerance and periapsis_within_tolerance,
            'tolerance_percent': tolerance_percent
        }


def create_orbital_monitor(update_interval: float = 0.1) -> OrbitalMonitor:
    """
    Factory function to create orbital monitor
    
    Args:
        update_interval: Update interval in seconds
        
    Returns:
        Configured OrbitalMonitor instance
    """
    return OrbitalMonitor(update_interval=update_interval)