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
        # Professor v19: Improved standard gravity turn for better horizontal velocity
        if altitude < 500:  # Below 500m - stay vertical for clearance
            return 90.0
        elif altitude < 2000:  # 500m-2km - start gravity turn more aggressively
            return 90.0 - (altitude - 500) / 100  # 10° per km decrease (was 3°)
        elif altitude < 15000:  # 2-15km - aggressive turn to build horizontal velocity
            return max(30, 75.0 - (altitude - 2000) / 400)  # From 75° at 2km to 30° at 15km
        elif altitude < 50000:  # 15-50km - continue toward horizontal
            return max(15, 30.0 - (altitude - 15000) / 2500)  # From 30° at 15km to 15° at 50km
        elif velocity < 3000:  # Low velocity - maintain some vertical component
            return max(10, 25.0 - altitude / 4000)
        elif velocity < 6000:  # Medium velocity - more horizontal
            return max(5, 15.0 - altitude / 8000)
        else:  # High velocity - nearly horizontal for orbital insertion
            return max(2, 8.0 - altitude / 20000)

def compute_thrust_direction(rocket, thrust_magnitude: float) -> Vector3:
    """
    Compute thrust direction vector based on current flight state
    Professor v17: Enhanced with PEG guidance integration
    Action A3: Added prograde thrust for circularization
    """
    from rocket_simulation_main import MissionPhase
    
    if not rocket.is_thrusting:
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
    altitude = rocket.get_altitude()
    velocity = rocket.velocity.magnitude()
    
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
        pitch_deg = get_target_pitch_angle(altitude, velocity, rocket.stage_burn_time)
    
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