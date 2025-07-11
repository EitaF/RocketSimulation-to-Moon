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
    Calculate target pitch angle based on altitude/velocity triggers.
    Professor v37: Updated gravity turn profile for better horizontal velocity buildup
    Target: Horizontal velocity ≥ 7.45 km/s by 220 km altitude
    """
    # Initial vertical ascent until 10 km altitude
    if altitude < 10000:
        return 90.0
    
    # Early pitch-over phase: 10-35 km altitude
    # Professor v37: Early pitch rate → 1.65°/s (constant) from 10 km to 35 km
    elif altitude < 35000:
        # Aggressive pitch-over to build horizontal velocity
        progress = (altitude - 10000) / 25000  # 0 to 1
        return 90.0 - progress * 45.0  # 90° to 45°
    
    # Mid-flight phase: 35-120 km altitude
    # Professor v37: Linearly reduce to 0.9°/s until 120 km
    elif altitude < 120000:
        # Continue pitch-over with reduced rate
        progress = (altitude - 35000) / 85000  # 0 to 1
        return 45.0 - progress * 25.0  # 45° to 20°
    
    # High altitude phase: 120-220 km altitude
    elif altitude < 220000:
        # Final approach to target pitch
        progress = (altitude - 120000) / 100000  # 0 to 1
        return 20.0 - progress * 12.0  # 20° to 8°
    
    # Professor v37: Final target pitch → 8° at 220 km
    else:
        # Maintain final target pitch for circularization
        return 8.0

def get_current_pitch_from_velocity(velocity: float) -> float:
    """Helper function to estimate current pitch from velocity magnitude"""
    # Simple approximation based on typical ascent profile
    if velocity < 1000:
        return 90.0
    elif velocity < 3000:
        return 60.0
    elif velocity < 5000:
        return 30.0
    else:
        return 15.0

def plan_circularization_burn(state) -> float:
    """
    Plan delta-V to raise periapsis at next apoapsis.
    Professor v36: Auto-planned circularization burn implementation
    
    Args:
        state: Mission state object with orbital parameters
        
    Returns:
        Required delta-V in m/s to circularize orbit
    """
    # Earth gravitational parameter (m³/s²)
    mu = 3.986004418e14  # Earth standard gravitational parameter
    
    # Get current orbital parameters
    r_apo = state.r_apo if hasattr(state, 'r_apo') else state.apoapsis + 6.371e6
    r_peri = state.r_peri if hasattr(state, 'r_peri') else state.periapsis + 6.371e6
    
    # Current velocity at apoapsis
    v_apo_current = np.sqrt(mu * (2/r_apo - 2/(r_apo + r_peri)))
    
    # Target circular velocity at apoapsis
    v_apo_circular = np.sqrt(mu / r_apo)
    
    # Required delta-V
    dv_required = v_apo_circular - v_apo_current
    
    # Return positive delta-V only (no negative burns)
    return max(dv_required, 0.0)

def should_start_circularization_burn(mission, current_time: float) -> bool:
    """
    Determine if circularization burn should start.
    Professor v37: Start burn ~25 seconds before apoapsis (was 20s)
    
    Args:
        mission: Mission object with orbital state
        current_time: Current mission time
        
    Returns:
        True if burn should start, False otherwise
    """
    # Get time to apoapsis
    try:
        time_to_apoapsis = mission.get_time_to_apoapsis()
        
        # Professor v37: Start burn 25 seconds before apoapsis (was 20s)
        if time_to_apoapsis <= 25.0 and time_to_apoapsis > 0:
            return True
    except:
        # Fallback: use altitude-based trigger
        altitude = mission.get_altitude()
        apoapsis = mission.get_apoapsis()
        
        # Start if within 5 km of apoapsis
        if abs(altitude - apoapsis) <= 5000:
            return True
    
    return False

def should_end_circularization_burn(mission, current_time: float, burn_start_time: float) -> bool:
    """
    Determine if circularization burn should end.
    Professor v37: Add closed-loop exit condition and minimum burn time
    
    Args:
        mission: Mission object with orbital state
        current_time: Current mission time
        burn_start_time: Time when burn started
        
    Returns:
        True if burn should end, False otherwise
    """
    # Calculate burn duration
    burn_duration = current_time - burn_start_time
    
    # Professor v37: Enforce minimum burn time of 25 seconds
    if burn_duration < 25.0:
        return False
    
    # Check if targets are met
    try:
        periapsis = mission.get_periapsis()
        eccentricity = mission.get_eccentricity()
        
        # Target: periapsis > 150 km and eccentricity < 0.05
        periapsis_target_met = periapsis > 150000  # 150 km
        ecc_target_met = eccentricity < 0.05
        
        if periapsis_target_met and ecc_target_met:
            return True
    except:
        pass
    
    # Professor v39: Fixed burn termination - stop when |dv_req| < 5 m/s with orbital checks
    try:
        dv_required = plan_circularization_burn(mission)
        
        # Check if delta-V requirement is within ±5 m/s
        dv_within_tolerance = abs(dv_required) < 5.0
        
        # Additional checks: verify perigee > 150km and eccentricity < 0.05
        try:
            from constants import R_EARTH
            altitude = mission.get_altitude()
            apoapsis, periapsis, eccentricity = mission.get_orbital_elements()
            
            perigee_acceptable = (periapsis - R_EARTH) > 150000  # 150 km
            eccentricity_acceptable = eccentricity < 0.05
            
            if dv_within_tolerance and perigee_acceptable and eccentricity_acceptable:
                mission.logger.info(f"CIRCULARIZATION COMPLETE: dv_req={dv_required:.1f}m/s, "
                                  f"perigee={(periapsis-R_EARTH)/1000:.1f}km, ecc={eccentricity:.3f}")
                return True
        except:
            # Fallback to just delta-V check if orbital elements fail
            if dv_within_tolerance:
                return True
            
    except:
        pass
    
    # Maximum burn duration safety check (prevent infinite burn)
    if burn_duration > 60.0:  # 60 seconds maximum
        return True
    
    return False

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