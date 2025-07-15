"""
Circularisation Burn Module
Professor v27: Enhanced circularization with orbital monitor integration
"""

import numpy as np
import logging
from typing import Tuple, Optional, Dict
from vehicle import Vector3
from orbital_monitor import OrbitalMonitor, OrbitalState

# Physical constants
G = 6.67430e-11  # Gravitational constant [m^3/kg/s^2]
M_EARTH = 5.972e24  # Earth mass [kg]
R_EARTH = 6371e3  # Earth radius [m]
MU_EARTH = G * M_EARTH  # Standard gravitational parameter [m^3/s^2]


def calculate_time_to_apoapsis(position: Vector3, velocity: Vector3) -> float:
    """
    Calculate time to apoapsis for current orbit
    
    Args:
        position: Current position vector [m]
        velocity: Current velocity vector [m/s]
        
    Returns:
        Time to apoapsis in seconds (or -1 if error)
    """
    try:
        r = position.magnitude()
        v = velocity.magnitude()
        
        # Calculate orbital elements
        specific_energy = 0.5 * v * v - MU_EARTH / r
        
        if specific_energy >= 0:
            return -1  # Hyperbolic trajectory
        
        # Semi-major axis
        a = -MU_EARTH / (2 * specific_energy)
        
        # Angular momentum vector (cross product)
        h_vec = Vector3(
            position.y * velocity.z - position.z * velocity.y,
            position.z * velocity.x - position.x * velocity.z,
            position.x * velocity.y - position.y * velocity.x
        )
        h = h_vec.magnitude()
        
        # Eccentricity
        if a > 0 and h > 0:
            e = np.sqrt(1 + 2 * specific_energy * h * h / (MU_EARTH * MU_EARTH))
        else:
            return -1
        
        # Current radial velocity (dot product)
        pos_unit = position.normalized()
        radial_velocity = velocity.data @ pos_unit.data
        
        # True anomaly calculation
        cos_nu = (a * (1 - e * e) / r - 1) / e if e > 1e-6 else 0
        cos_nu = np.clip(cos_nu, -1, 1)
        
        true_anomaly = np.arccos(cos_nu)
        if radial_velocity < 0:  # Moving away from periapsis
            true_anomaly = 2 * np.pi - true_anomaly
        
        # Eccentric anomaly
        cos_E = (e + np.cos(true_anomaly)) / (1 + e * np.cos(true_anomaly))
        cos_E = np.clip(cos_E, -1, 1)
        E = np.arccos(cos_E)
        if true_anomaly > np.pi:
            E = 2 * np.pi - E
        
        # Mean anomaly
        M = E - e * np.sin(E)
        
        # Time from periapsis
        n = np.sqrt(MU_EARTH / (a * a * a))  # Mean motion
        t_from_periapsis = M / n
        
        # Orbital period
        T = 2 * np.pi / n
        
        # Time to apoapsis (half period from periapsis)
        time_to_apoapsis = T / 2 - t_from_periapsis
        
        # Handle negative time (past apoapsis)
        if time_to_apoapsis < 0:
            time_to_apoapsis += T
        
        return time_to_apoapsis
        
    except (ZeroDivisionError, ValueError, RuntimeError):
        return -1


def should_start_circularization(position: Vector3, velocity: Vector3, 
                               trigger_time: float = 30.0) -> bool:
    """
    Determine if circularization burn should start
    
    Args:
        position: Current position vector
        velocity: Current velocity vector  
        trigger_time: Time before apoapsis to start burn [s]
        
    Returns:
        True if circularization should start now
    """
    time_to_apo = calculate_time_to_apoapsis(position, velocity)
    
    if time_to_apo < 0:
        return False  # Invalid orbit
    
    # Professor v16: Start burn when apoapsis_time - t < 30s
    return time_to_apo <= trigger_time


def calculate_circularization_delta_v(position: Vector3, velocity: Vector3) -> Tuple[float, Vector3]:
    """
    Calculate required ΔV for circularization at current apoapsis
    
    Args:
        position: Current position vector
        velocity: Current velocity vector
        
    Returns:
        Tuple of (delta_v_magnitude, delta_v_direction_vector)
    """
    try:
        r = position.magnitude()
        v = velocity.magnitude()
        
        # Calculate current orbital elements
        specific_energy = 0.5 * v * v - MU_EARTH / r
        
        if specific_energy >= 0:
            return 0.0, Vector3(0, 0)  # Hyperbolic trajectory
        
        # Semi-major axis
        a = -MU_EARTH / (2 * specific_energy)
        
        # Angular momentum
        h_vec = Vector3(
            position.y * velocity.z - position.z * velocity.y,
            position.z * velocity.x - position.x * velocity.z,
            position.x * velocity.y - position.y * velocity.x
        )
        h = h_vec.magnitude()
        
        # Eccentricity
        if a > 0 and h > 0:
            e = np.sqrt(1 + 2 * specific_energy * h * h / (MU_EARTH * MU_EARTH))
        else:
            return 0.0, Vector3(0, 0)
        
        # Apoapsis radius
        r_apo = a * (1 + e)
        
        # Velocity at apoapsis for current elliptical orbit
        v_apo_elliptical = np.sqrt(MU_EARTH * (2 / r_apo - 1 / a))
        
        # Velocity for circular orbit at apoapsis radius
        v_apo_circular = np.sqrt(MU_EARTH / r_apo)
        
        # ΔV needed (raise periapsis to apoapsis)
        delta_v_magnitude = v_apo_circular - v_apo_elliptical
        
        # Direction: prograde (along velocity vector)
        if velocity.magnitude() > 0:
            delta_v_direction = velocity.normalized()
        else:
            # Fallback: tangential direction
            radial = position.normalized()
            delta_v_direction = Vector3(-radial.y, radial.x)
        
        return delta_v_magnitude, delta_v_direction
        
    except (ZeroDivisionError, ValueError, RuntimeError):
        return 0.0, Vector3(0, 0)


def compute_circularization_thrust(position: Vector3, velocity: Vector3, 
                                 thrust_magnitude: float) -> Vector3:
    """
    Compute thrust vector for circularization burn
    
    Args:
        position: Current position vector
        velocity: Current velocity vector
        thrust_magnitude: Available thrust magnitude [N]
        
    Returns:
        Thrust vector for circularization
    """
    # Calculate required ΔV
    delta_v_mag, delta_v_dir = calculate_circularization_delta_v(position, velocity)
    
    if delta_v_mag <= 0:
        return Vector3(0, 0)
    
    # Apply thrust in ΔV direction
    return delta_v_dir * thrust_magnitude


def get_circularization_status(position: Vector3, velocity: Vector3) -> dict:
    """
    Get current circularization status for logging
    
    Returns:
        Dictionary with circularization parameters
    """
    time_to_apo = calculate_time_to_apoapsis(position, velocity)
    delta_v_mag, _ = calculate_circularization_delta_v(position, velocity)
    should_burn = should_start_circularization(position, velocity)
    
    # Calculate current orbital elements for context
    r = position.magnitude()
    v = velocity.magnitude()
    specific_energy = 0.5 * v * v - MU_EARTH / r
    
    if specific_energy < 0:
        a = -MU_EARTH / (2 * specific_energy)
        h_vec = Vector3(
            position.y * velocity.z - position.z * velocity.y,
            position.z * velocity.x - position.x * velocity.z,
            position.x * velocity.y - position.y * velocity.x
        )
        h = h_vec.magnitude()
        e = np.sqrt(1 + 2 * specific_energy * h * h / (MU_EARTH * MU_EARTH)) if a > 0 and h > 0 else 0
        
        apoapsis = a * (1 + e) if e < 1 else float('inf')
        periapsis = a * (1 - e) if e < 1 else float('-inf')
    else:
        apoapsis = float('inf')
        periapsis = float('-inf')
        e = float('inf')
    
    return {
        'time_to_apoapsis_s': time_to_apo,
        'should_circularize': should_burn,
        'delta_v_needed_ms': delta_v_mag,
        'apoapsis_km': (apoapsis - R_EARTH) / 1000 if apoapsis != float('inf') else float('inf'),
        'periapsis_km': (periapsis - R_EARTH) / 1000 if periapsis != float('-inf') else float('-inf'),
        'eccentricity': e
    }


class CircularizationBurn:
    """
    Enhanced circularization burn logic with orbital monitor integration
    Professor v27: Precise circularization for two-stage orbital insertion
    """
    
    def __init__(self, orbital_monitor: Optional[OrbitalMonitor] = None):
        """
        Initialize circularization burn controller
        
        Args:
            orbital_monitor: Optional orbital monitor for precise timing
        """
        self.logger = logging.getLogger(__name__)
        self.orbital_monitor = orbital_monitor
        
        # Burn parameters
        self.burn_trigger_time = 30.0  # Start burn 30s before apoapsis
        self.burn_active = False
        self.burn_start_time = None
        self.target_delta_v = 0.0
        self.accumulated_delta_v = 0.0
        
        # Success criteria (Professor v27)
        self.circular_eccentricity_threshold = 0.01
        self.circular_altitude_tolerance = 5000  # 5 km
        
        self.logger.info("Circularization burn controller initialized")
    
    def should_start_burn(self, position: Vector3, velocity: Vector3, current_time: float) -> bool:
        """
        Determine if circularization burn should start
        Professor v27: Uses orbital monitor for precise timing
        """
        if self.burn_active:
            return True  # Already burning
        
        if self.orbital_monitor and self.orbital_monitor.current_state:
            # Use orbital monitor for precise timing
            orbital_state = self.orbital_monitor.current_state
            
            if orbital_state.is_escape_trajectory:
                return False  # Can't circularize escape trajectory
            
            return orbital_state.time_to_apoapsis <= self.burn_trigger_time
        else:
            # Fallback to legacy timing calculation
            return should_start_circularization(position, velocity, self.burn_trigger_time)
    
    def calculate_burn_parameters(self, position: Vector3, velocity: Vector3) -> Dict:
        """
        Calculate circularization burn parameters
        Professor v27: Enhanced calculation with orbital monitor data
        """
        if self.orbital_monitor and self.orbital_monitor.current_state:
            orbital_state = self.orbital_monitor.current_state
            
            if orbital_state.is_escape_trajectory:
                return {
                    'delta_v_needed': 0.0,
                    'burn_direction': Vector3(0, 0, 0),
                    'burn_time_estimate': 0.0,
                    'is_valid': False
                }
            
            # Use orbital monitor data for precise calculation
            apoapsis_radius = orbital_state.apoapsis
            current_velocity = velocity.magnitude()
            
            # Velocity for circular orbit at apoapsis
            v_circular = np.sqrt(MU_EARTH / apoapsis_radius)
            
            # Current velocity at apoapsis (for elliptical orbit)
            semi_major_axis = orbital_state.semi_major_axis
            v_elliptical = np.sqrt(MU_EARTH * (2/apoapsis_radius - 1/semi_major_axis))
            
            # Required delta-v
            delta_v_needed = v_circular - v_elliptical
            
        else:
            # Fallback to legacy calculation
            delta_v_needed, burn_direction = calculate_circularization_delta_v(position, velocity)
            
        # Burn direction (prograde)
        if velocity.magnitude() > 0:
            burn_direction = velocity.normalized()
        else:
            # Fallback: tangential direction
            radial = position.normalized()
            burn_direction = Vector3(-radial.y, radial.x, 0).normalized()
        
        # Estimate burn time (assuming constant thrust)
        # This would need actual thrust data in real implementation
        burn_time_estimate = abs(delta_v_needed) / 100.0  # Assume 100 m/s^2 acceleration
        
        return {
            'delta_v_needed': delta_v_needed,
            'burn_direction': burn_direction,
            'burn_time_estimate': burn_time_estimate,
            'is_valid': delta_v_needed > 0
        }
    
    def start_burn(self, current_time: float, target_delta_v: float):
        """Start circularization burn"""
        if not self.burn_active:
            self.burn_active = True
            self.burn_start_time = current_time
            self.target_delta_v = target_delta_v
            self.accumulated_delta_v = 0.0
            self.logger.info(f"Circularization burn started - Target ΔV: {target_delta_v:.1f} m/s")
    
    def update_burn(self, current_time: float, applied_delta_v: float):
        """Update burn progress"""
        if self.burn_active:
            self.accumulated_delta_v += applied_delta_v
    
    def should_stop_burn(self, position: Vector3, velocity: Vector3) -> bool:
        """
        Determine if circularization burn should stop
        Professor v27: Success criteria - circular orbit within 5km tolerance
        """
        if not self.burn_active:
            return False
        
        # Check if target delta-v has been achieved
        delta_v_complete = self.accumulated_delta_v >= self.target_delta_v * 0.95  # 95% completion
        
        # Check orbital circularity
        if self.orbital_monitor and self.orbital_monitor.current_state:
            orbital_state = self.orbital_monitor.current_state
            
            # Success criteria from Professor v27
            eccentricity_ok = orbital_state.eccentricity < self.circular_eccentricity_threshold
            altitude_diff = abs(orbital_state.apoapsis - orbital_state.periapsis)
            altitude_tolerance_ok = altitude_diff < self.circular_altitude_tolerance
            
            orbit_circular = eccentricity_ok and altitude_tolerance_ok
            
            return delta_v_complete or orbit_circular
        else:
            # Fallback: just use delta-v completion
            return delta_v_complete
    
    def stop_burn(self, current_time: float):
        """Stop circularization burn"""
        if self.burn_active:
            burn_duration = current_time - self.burn_start_time if self.burn_start_time else 0
            self.burn_active = False
            self.logger.info(f"Circularization burn completed - Duration: {burn_duration:.1f}s, "
                           f"ΔV applied: {self.accumulated_delta_v:.1f} m/s")
    
    def get_burn_status(self) -> Dict:
        """Get current burn status for monitoring"""
        return {
            'burn_active': self.burn_active,
            'target_delta_v': self.target_delta_v,
            'accumulated_delta_v': self.accumulated_delta_v,
            'burn_progress_percent': (self.accumulated_delta_v / self.target_delta_v * 100) if self.target_delta_v > 0 else 0,
            'burn_start_time': self.burn_start_time
        }
    
    def validate_circular_orbit(self, position: Vector3, velocity: Vector3) -> Dict:
        """
        Validate that circularization achieved success criteria
        Professor v27: Apoapsis and periapsis within 5km of each other
        """
        if self.orbital_monitor and self.orbital_monitor.current_state:
            orbital_state = self.orbital_monitor.current_state
            
            apoapsis_km = (orbital_state.apoapsis - R_EARTH) / 1000
            periapsis_km = (orbital_state.periapsis - R_EARTH) / 1000
            altitude_difference_km = abs(apoapsis_km - periapsis_km)
            
            success = (
                orbital_state.eccentricity < self.circular_eccentricity_threshold and
                altitude_difference_km < self.circular_altitude_tolerance / 1000
            )
            
            return {
                'success': success,
                'apoapsis_km': apoapsis_km,
                'periapsis_km': periapsis_km,
                'altitude_difference_km': altitude_difference_km,
                'eccentricity': orbital_state.eccentricity,
                'tolerance_km': self.circular_altitude_tolerance / 1000,
                'eccentricity_threshold': self.circular_eccentricity_threshold
            }
        else:
            # Fallback calculation
            r = position.magnitude()
            v = velocity.magnitude()
            specific_energy = 0.5 * v * v - MU_EARTH / r
            
            if specific_energy >= 0:
                return {'success': False, 'reason': 'escape_trajectory'}
            
            a = -MU_EARTH / (2 * specific_energy)
            h_vec = Vector3(
                position.y * velocity.z - position.z * velocity.y,
                position.z * velocity.x - position.x * velocity.z,
                position.x * velocity.y - position.y * velocity.x
            )
            h = h_vec.magnitude()
            e = np.sqrt(1 + 2 * specific_energy * h * h / (MU_EARTH * MU_EARTH)) if a > 0 and h > 0 else 0
            
            apoapsis_km = (a * (1 + e) - R_EARTH) / 1000 if e < 1 else float('inf')
            periapsis_km = (a * (1 - e) - R_EARTH) / 1000 if e < 1 else float('-inf')
            altitude_difference_km = abs(apoapsis_km - periapsis_km) if e < 1 else float('inf')
            
            success = e < self.circular_eccentricity_threshold and altitude_difference_km < self.circular_altitude_tolerance / 1000
            
            return {
                'success': success,
                'apoapsis_km': apoapsis_km,
                'periapsis_km': periapsis_km,
                'altitude_difference_km': altitude_difference_km,
                'eccentricity': e,
                'tolerance_km': self.circular_altitude_tolerance / 1000,
                'eccentricity_threshold': self.circular_eccentricity_threshold
            }


def create_circularization_burn(orbital_monitor: Optional[OrbitalMonitor] = None) -> CircularizationBurn:
    """
    Factory function to create circularization burn controller
    
    Args:
        orbital_monitor: Optional orbital monitor for enhanced precision
        
    Returns:
        Configured CircularizationBurn instance
    """
    return CircularizationBurn(orbital_monitor=orbital_monitor)