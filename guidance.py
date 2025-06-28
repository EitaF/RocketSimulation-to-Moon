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
    Calculate target pitch angle based on flight phase
    Professor v17: Enhanced with optimized pitch schedule
    Professor v23: Smoothed profile to reduce Max-Q loads
    """
    if is_enabled("PITCH_OPTIMIZATION"):
        # Use optimized pitch schedule from LHS sweep results
        # Best parameters from pitch_optimization_results.json
        INITIAL_PITCH = 14.164042243789494
        PITCH_HOLD_TIME = 25.225660429005217
        PITCH_RATE_1 = 1.3063950009515768
        PITCH_RATE_2 = 0.5342683993330313
        FINAL_PITCH = 80.85562222136585
        
        if time <= PITCH_HOLD_TIME:
            return INITIAL_PITCH
        elif time <= 60:  # First transition (60s - hold_time)
            transition_time = time - PITCH_HOLD_TIME
            return INITIAL_PITCH + PITCH_RATE_1 * transition_time
        elif time <= 120:  # Second transition
            transition_time = time - 60
            mid_pitch = INITIAL_PITCH + PITCH_RATE_1 * (60 - PITCH_HOLD_TIME)
            return mid_pitch + PITCH_RATE_2 * transition_time
        else:
            return FINAL_PITCH
    else:
        # Professor v23: Smoothed gravity turn to prevent Max-Q violations
        if altitude < 500:  # Below 500m - stay vertical for clearance
            return 90.0
        elif altitude < 2000:  # 500m-2km - very gradual start to avoid Max-Q spike
            return 90.0 - (altitude - 500) / 300  # 3.33° per km decrease (gentler)
        elif altitude < 12000:  # 2-12km - delayed turn past Max-Q region
            return max(45, 85.0 - (altitude - 2000) / 250)  # From 85° at 2km to 45° at 12km
        elif altitude < 25000:  # 12-25km - continue building horizontal velocity
            return max(20, 45.0 - (altitude - 12000) / 520)  # From 45° at 12km to 20° at 25km
        elif altitude < 60000:  # 25-60km - approach horizontal for orbital velocity
            return max(8, 20.0 - (altitude - 25000) / 2917)  # From 20° at 25km to 8° at 60km
        elif velocity < 4000:  # Low velocity - maintain vertical component
            return max(6, 12.0 - altitude / 8333)
        elif velocity < 7000:  # Medium-high velocity - more horizontal
            return max(3, 8.0 - altitude / 12500)
        else:  # High velocity - nearly horizontal for LEO insertion
            return max(1, 4.0 - altitude / 25000)

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