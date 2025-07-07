"""
Guidance and Control Module for Saturn V Simulation
Professor v17: Enhanced guidance with feature flag support
Professor v23: Added pitch rate limiting for Max-Q protection
"""

import numpy as np
from vehicle import Vector3
from config_flags import is_enabled

# Global state for pitch rate limiting
_last_pitch_angle = None
_last_time = None
MAX_PITCH_RATE = 0.7  # degrees per second (Professor v23 requirement)

# Professor v23: Global guidance timing offset for Monte Carlo variation
_guidance_timing_offset = 0.0

def set_guidance_timing_offset(offset: float):
    """Set guidance timing offset for Monte Carlo variation"""
    global _guidance_timing_offset
    _guidance_timing_offset = offset

def reset_guidance_state():
    """Reset guidance state for new simulation"""
    global _last_pitch_angle, _last_time, _guidance_timing_offset
    _last_pitch_angle = None
    _last_time = None
    _guidance_timing_offset = 0.0

def apply_pitch_rate_limiting(target_pitch: float, current_time: float, altitude: float) -> float:
    """
    Apply pitch rate limiting to prevent aggressive maneuvers during Max-Q
    Professor v23: Limit pitch rate to 0.7°/s below 20km altitude
    """
    global _last_pitch_angle, _last_time
    
    # Initialize on first call
    if _last_pitch_angle is None or _last_time is None:
        _last_pitch_angle = target_pitch
        _last_time = current_time
        return target_pitch
    
    dt = current_time - _last_time
    if dt <= 0:
        return _last_pitch_angle
    
    # Calculate maximum allowed pitch change
    max_pitch_change = MAX_PITCH_RATE * dt
    
    # Apply stricter limiting below 20km (Max-Q region)
    if altitude < 20000:
        max_pitch_change *= 0.5  # Even more conservative in thick atmosphere
    
    # Limit the pitch change
    pitch_change = target_pitch - _last_pitch_angle
    if abs(pitch_change) > max_pitch_change:
        limited_pitch = _last_pitch_angle + np.sign(pitch_change) * max_pitch_change
    else:
        limited_pitch = target_pitch
    
    # Update state
    _last_pitch_angle = limited_pitch
    _last_time = current_time
    
    return limited_pitch

def get_target_pitch_angle(altitude: float, velocity: float, time: float = 0) -> float:
    """
    Calculate target pitch angle based on a balanced pitch-over maneuver.
    """
    # Initial vertical ascent for 20 seconds
    if time < 20:
        return 90.0
    # Gradual pitch-over
    elif time < 120:
        return 90.0 - (time - 20) * 0.75  # 0.75 deg/s pitch rate
    # Continue to horizontal
    else:
        return 15.0

def compute_thrust_direction(mission, t: float, thrust_magnitude: float) -> Vector3:
    """
    Compute thrust direction vector based on current flight state
    Professor v17: Enhanced with PEG guidance integration
    Action A3: Added prograde thrust for circularization
    """
    from vehicle import MissionPhase
    
    rocket = mission.rocket
    altitude = mission.get_altitude()

    if not rocket.is_thrusting(t, altitude):
        return Vector3(0, 0)
    
    # Action A3: Add dedicated logic for circularization phase
    if rocket.phase == MissionPhase.CIRCULARIZATION:
        # Thrust should be perfectly prograde (aligned with the velocity vector).
        # This maximizes the energy added to the orbit to raise the periapsis.
        if rocket.velocity.magnitude() > 0:
            thrust_direction = rocket.velocity.normalized()
            return thrust_direction * thrust_magnitude
        else:
            # Fallback for zero velocity case
            return Vector3(0, 0, 0)

    # --- Existing Guidance Logic for other phases ---
    velocity = rocket.velocity.magnitude()
    stage_elapsed_time = t - rocket.stage_start_time
    
    # Use PEG guidance for orbital insertion phases
    if (is_enabled("PEG_GAMMA_DAMPING") and 
        rocket.phase in [MissionPhase.APOAPSIS_RAISE] and
        altitude > 50000):  # Above 50km
        
        # Use PEG guidance
        try:
            from peg import create_peg_guidance
            peg = create_peg_guidance(target_altitude_km=185)
            
            # Estimate remaining burn time
            if rocket.current_stage < len(rocket.stages):
                current_stage = rocket.stages[rocket.current_stage]
                remaining_burn_time = max(0, current_stage.burn_time - rocket.stage_burn_time)
            else:
                remaining_burn_time = 0
            
            # Get PEG pitch recommendation
            peg_pitch = peg.compute_peg_pitch(
                rocket.position, rocket.velocity, 
                rocket.stage_burn_time, remaining_burn_time
            )
            
            if peg_pitch is not None:
                pitch_deg = peg_pitch
            else:
                # Fallback to standard guidance
                pitch_deg = get_target_pitch_angle(altitude, velocity, rocket.stage_burn_time)
        except:
            # Fallback if PEG fails
            pitch_deg = get_target_pitch_angle(altitude, velocity, rocket.stage_burn_time)
    else:
        # Standard guidance for early flight
        # Professor v23: Apply guidance timing offset for Monte Carlo variation
        adjusted_stage_time = stage_elapsed_time + _guidance_timing_offset
        pitch_deg = get_target_pitch_angle(altitude, velocity, adjusted_stage_time)
    
    # Professor v23: Apply pitch rate limiting to prevent Max-Q violations
    pitch_deg = apply_pitch_rate_limiting(pitch_deg, t, altitude)
    
    # Convert to radians and calculate thrust vector
    pitch_rad = np.radians(pitch_deg)
    
    # In 2D polar coordinates relative to Earth center
    # x = radial (outward from Earth), y = tangential (eastward)
    thrust_radial = thrust_magnitude * np.sin(pitch_rad)      # Radial component
    thrust_tangential = thrust_magnitude * np.cos(pitch_rad)  # Tangential component
    
    # Transform to Cartesian coordinates
    # Get current position unit vector
    pos_unit = rocket.position.normalized()
    
    # Tangent vector (perpendicular to radial, in orbital plane)
    tangent_x = -pos_unit.y
    tangent_y = pos_unit.x
    
    # Combine radial and tangential components
    thrust_x = thrust_radial * pos_unit.x + thrust_tangential * tangent_x
    thrust_y = thrust_radial * pos_unit.y + thrust_tangential * tangent_y
    
    return Vector3(thrust_x, thrust_y, 0)

def get_guidance_mode() -> str:
    """Get current guidance mode for telemetry"""
    if is_enabled("PEG_GAMMA_DAMPING"):
        return "PEG_ENHANCED"
    elif is_enabled("PITCH_OPTIMIZATION"):
        return "OPTIMIZED_PITCH"
    else:
        return "STANDARD_GRAVITY_TURN"