"""
Guidance and Control Module for Saturn V Simulation
Professor v17: Enhanced guidance with feature flag support
"""

import numpy as np
from vehicle import Vector3
from config_flags import is_enabled

def get_target_pitch_angle(altitude: float, velocity: float, time: float = 0) -> float:
    """
    Calculate target pitch angle based on flight phase
    Professor v17: Enhanced with optimized pitch schedule
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
        # Professor v22: Optimized gravity turn to reach 6 km/s horizontal at 100km
        if altitude < 500:  # Below 500m - stay vertical for clearance
            return 90.0
        elif altitude < 1500:  # 500m-1.5km - gradual start
            return 90.0 - (altitude - 500) / 200  # 5° per km decrease
        elif altitude < 8000:  # 1.5-8km - aggressive turn for horizontal velocity
            return max(45, 85.0 - (altitude - 1500) / 162.5)  # From 85° at 1.5km to 45° at 8km
        elif altitude < 25000:  # 8-25km - continue building horizontal velocity
            return max(20, 45.0 - (altitude - 8000) / 680)  # From 45° at 8km to 20° at 25km
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
        pitch_deg = get_target_pitch_angle(altitude, velocity, stage_elapsed_time)
    
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