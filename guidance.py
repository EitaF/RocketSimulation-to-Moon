"""
Rocket Guidance System
Implements altitude-based pitch program and thrust vector control
Based on professor's feedback for Saturn V simulation
"""

import numpy as np


class Vector3:
    """3次元ベクトルクラス（guidance用ローカル実装）"""
    
    def __init__(self, x: float, y: float, z: float = 0.0):
        self.data = np.array([x, y, z])
    
    @property
    def x(self) -> float:
        return self.data[0]
    
    @property
    def y(self) -> float:
        return self.data[1]
    
    @property
    def z(self) -> float:
        return self.data[2]
    
    def magnitude(self) -> float:
        return np.linalg.norm(self.data)
    
    def normalized(self) -> 'Vector3':
        mag = self.magnitude()
        if mag == 0:
            return Vector3(0, 0, 0)
        return Vector3(*(self.data / mag))
    
    def __add__(self, other: 'Vector3') -> 'Vector3':
        return Vector3(*(self.data + other.data))
    
    def __sub__(self, other: 'Vector3') -> 'Vector3':
        return Vector3(*(self.data - other.data))
    
    def __mul__(self, scalar: float) -> 'Vector3':
        return Vector3(*(self.data * scalar))


def compute_thrust_direction(rocket, thrust_magnitude: float) -> Vector3:
    """
    Compute thrust direction based on mission phase and guidance laws
    
    Args:
        rocket: Rocket object with position, velocity, phase
        thrust_magnitude: Magnitude of thrust force [N]
    
    Returns:
        Vector3: Thrust vector
    """
    if thrust_magnitude <= 0:
        return Vector3(0, 0)
    
    # Get current state
    altitude = rocket.get_altitude()
    velocity = rocket.velocity.magnitude()
    
    # Convert main Vector3 to local Vector3
    pos = Vector3(rocket.position.x, rocket.position.y, rocket.position.z)
    vel = Vector3(rocket.velocity.x, rocket.velocity.y, rocket.velocity.z)
    
    # Phase-specific guidance
    phase_name = rocket.phase.value if hasattr(rocket.phase, 'value') else str(rocket.phase)
    
    if phase_name == "launch":
        # Vertical ascent until gravity turn
        up = pos.normalized()
        result = up * thrust_magnitude
        
    elif phase_name == "gravity_turn":
        # Professor's recommended altitude-based pitch program
        thrust_direction = compute_pitch_program(pos, vel, altitude, velocity, rocket)
        result = thrust_direction * thrust_magnitude
        
    elif phase_name == "apoapsis_raise":
        # Prograde (velocity direction) thrust
        if velocity > 0:
            result = vel.normalized() * thrust_magnitude
        else:
            # Fallback: tangential direction
            radial = pos.normalized()
            tangent = Vector3(-radial.y, radial.x)
            result = tangent * thrust_magnitude
            
    elif phase_name == "circularization":
        # Professor's circularization: burn prograde until e < 1e-3
        apoapsis, periapsis, eccentricity = rocket.get_orbital_elements()
        altitude = rocket.get_altitude()
        
        # Check if at apoapsis (within 1 km)
        apoapsis_altitude = (apoapsis - 6371e3) if apoapsis != float('inf') else altitude
        if altitude < apoapsis_altitude - 1e3:
            # Still coasting to apoapsis - no thrust
            result = Vector3(0, 0)
        elif eccentricity > 1e-3 and rocket.current_stage < len(rocket.stages):
            # Burn prograde to circularize
            if velocity > 0:
                result = vel.normalized() * thrust_magnitude
            else:
                radial = pos.normalized()
                tangent = Vector3(-radial.y, radial.x)
                result = tangent * thrust_magnitude
        else:
            # Circularization complete
            result = Vector3(0, 0)
            
    elif phase_name == "trans_lunar_injection":
        # TLI: prograde thrust
        if velocity > 0:
            result = vel.normalized() * thrust_magnitude
        else:
            radial = pos.normalized()
            tangent = Vector3(-radial.y, radial.x)
            result = tangent * thrust_magnitude
            
    elif phase_name == "lunar_orbit_insertion":
        # LOI: retrograde thrust
        result = vel.normalized() * (-thrust_magnitude)
    else:
        result = Vector3(0, 0)
    
    # Convert back to main Vector3 type
    from rocket_simulation_main import Vector3 as MainVector3
    return MainVector3(result.x, result.y, result.z)


def compute_pitch_program(pos: Vector3, vel: Vector3, altitude: float, velocity: float, rocket) -> Vector3:
    """
    Professor's recommended altitude-based pitch program
    
    Pitch schedule:
    - 0-2 km: 0° (vertical)
    - 2-10 km: 0° → 15° (gentle start)
    - 10-50 km: 15° → 60° (aggressive turn)
    - 50 km+: 60° → 90° (horizontal)
    
    Switch to velocity-following only after h > 10 km AND v > 1 km/s
    """
    
    # Altitude-based pitch program (recommended by professor)
    if altitude < 2e3:
        pitch_angle = 0.0  # Pure vertical
    elif altitude < 10e3:
        # 2-10 km: linear from 0° to 15°
        pitch_angle = (altitude - 2e3) * 15.0 / (10e3 - 2e3)
    elif altitude < 40e3:
        # 10-40 km: linear from 15° to 45°  
        pitch_angle = 15.0 + (altitude - 10e3) * 30.0 / (40e3 - 10e3)
    elif altitude < 80e3:
        # 40-80 km: 45° → 85° (PROFESSOR'S FLATTER PROFILE)
        pitch_angle = 45.0 + (altitude - 40e3) * 40.0 / (80e3 - 40e3)
    else:
        # ≥80 km: hold 85° until velocity > 7600 m/s (PROFESSOR'S FIX)
        if velocity < 7600:
            pitch_angle = 85.0  # Hold 85°, not 90° - keeps small vertical component
        else:
            pitch_angle = 90.0  # Full horizontal only after orbital velocity
    
    # Check if we should switch to velocity-vector following
    velocity_following_threshold = (altitude > 10e3 and velocity > 1000)  # 10 km AND 1 km/s
    
    if velocity_following_threshold and velocity > 500:  # Additional safety check
        # Blend toward velocity vector with improved stability
        up = pos.normalized()
        east = Vector3(-up.y, up.x)  # Eastward (orbital direction)
        
        # Target direction from pitch program
        pitch_rad = np.radians(pitch_angle)
        target_direction = up * np.cos(pitch_rad) + east * np.sin(pitch_rad)
        
        # Current velocity direction
        velocity_direction = vel.normalized()
        
        # Flight path angle
        flight_path_angle = rocket.get_flight_path_angle()
        target_flight_path_angle = np.radians(90 - pitch_angle)
        
        # Error correction with increased clamp (professor's recommendation: ±20°)
        angle_error = target_flight_path_angle - flight_path_angle
        angle_error = max(-0.35, min(0.35, angle_error))  # ±20° = ±0.35 rad (PROFESSOR'S FIX)
        
        # Blend between programmed direction and velocity-corrected direction
        radial_unit = pos.normalized()
        correction = radial_unit * (angle_error * 0.3)  # Gentler correction
        
        # Weight the blend based on how well-established the velocity vector is
        velocity_weight = min(1.0, (velocity - 1000) / 2000)  # 0 at 1 km/s, 1 at 3 km/s
        velocity_weight = max(0.0, velocity_weight)
        
        # Final direction: blend between programmed and velocity-corrected
        corrected_velocity_dir = velocity_direction + correction
        final_direction = (target_direction * (1 - velocity_weight) + 
                         corrected_velocity_dir.normalized() * velocity_weight)
        
        return final_direction.normalized()
    else:
        # Pure altitude-based pitch program (PROFESSOR'S CORE FIX)
        up = pos.normalized()
        east = Vector3(-up.y, up.x)  # Eastward (orbital direction)
        
        pitch_rad = np.radians(pitch_angle)
        thrust_direction = up * np.cos(pitch_rad) + east * np.sin(pitch_rad)
        
        return thrust_direction.normalized()


def target_apoapsis(rocket, desired_rad: float) -> bool:
    """
    Professor's closed-loop apogee target function
    Returns True if current trajectory will reach desired apoapsis radius
    """
    # Get rocket state
    pos = Vector3(rocket.position.x, rocket.position.y, rocket.position.z)
    vel = Vector3(rocket.velocity.x, rocket.velocity.y, rocket.velocity.z)
    
    # Physical constants
    mu = 3.986004418e14  # Earth gravitational parameter [m^3/s^2]
    r = pos.magnitude()
    v = vel.magnitude()
    
    # Calculate radial velocity component
    pos_unit = pos.normalized()
    vr = pos_unit.data[0] * vel.data[0] + pos_unit.data[1] * vel.data[1] + pos_unit.data[2] * vel.data[2]
    
    # Calculate specific orbital energy
    specific_energy = 0.5 * v * v - mu / r
    
    # Check if trajectory is bound (negative energy)
    if specific_energy >= 0:
        return False  # Hyperbolic/parabolic trajectory
    
    # Calculate semi-major axis
    semi_major = -mu / (2 * specific_energy)
    
    # Calculate angular momentum magnitude
    h_vec_x = pos.data[1] * vel.data[2] - pos.data[2] * vel.data[1]
    h_vec_y = pos.data[2] * vel.data[0] - pos.data[0] * vel.data[2] 
    h_vec_z = pos.data[0] * vel.data[1] - pos.data[1] * vel.data[0]
    angular_momentum_mag = np.sqrt(h_vec_x**2 + h_vec_y**2 + h_vec_z**2)
    
    # Calculate eccentricity
    ecc_vector_mag = np.sqrt(1 + 2 * specific_energy * angular_momentum_mag**2 / (mu**2))
    
    # Calculate apoapsis radius
    apoapsis_r = semi_major * (1 + ecc_vector_mag)
    
    return apoapsis_r >= desired_rad


def get_target_pitch_angle(altitude: float, velocity: float = 0) -> float:
    """
    Get target pitch angle for given altitude (updated for professor's v5 profile)
    
    Args:
        altitude: Altitude above sea level [m]
        velocity: Current velocity [m/s] (for high-altitude logic)
    
    Returns:
        float: Pitch angle in degrees (0 = vertical, 90 = horizontal)
    """
    if altitude < 2e3:
        return 0.0
    elif altitude < 10e3:
        return (altitude - 2e3) * 15.0 / (10e3 - 2e3)
    elif altitude < 40e3:
        return 15.0 + (altitude - 10e3) * 30.0 / (40e3 - 10e3)
    elif altitude < 80e3:
        return 45.0 + (altitude - 40e3) * 40.0 / (80e3 - 40e3)
    else:
        # ≥80 km: hold 85° until velocity > 7600 m/s
        if velocity < 7600:
            return 85.0
        else:
            return 90.0