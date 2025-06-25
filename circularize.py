"""
Circularisation Burn Module
Professor v16: Automatic circularization when approaching apoapsis
"""

import numpy as np
from typing import Tuple, Optional
from vehicle import Vector3

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