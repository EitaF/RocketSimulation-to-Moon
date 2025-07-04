"""
Trans-Lunar Injection (TLI) Guidance Module
Professor v29: Implementation of TLI guidance for Earth-Moon transfer

This module provides the guidance logic for performing the Trans-Lunar Injection
burn that will send the spacecraft from LEO to a lunar intercept trajectory.
"""

import numpy as np
from dataclasses import dataclass
from typing import Tuple, Optional
from vehicle import Vector3, MissionPhase

# Physical constants
G = 6.67430e-11  # Gravitational constant [m^3/kg/s^2]
M_EARTH = 5.972e24  # Earth mass [kg]
M_MOON = 7.34767309e22  # Moon mass [kg]
R_EARTH = 6371e3  # Earth radius [m]
R_MOON = 1737e3  # Moon radius [m]
EARTH_MOON_DIST = 384400e3  # Earth-Moon distance [m]
MOON_ORBIT_PERIOD = 27.321661 * 24 * 3600  # Moon orbital period [s]
STANDARD_GRAVITY = 9.80665  # Standard gravity [m/s^2]


@dataclass
class TLIParameters:
    """TLI burn parameters and requirements"""
    target_c3_energy: float = 0.0  # Characteristic energy [m^2/s^2]
    burn_duration: float = 0.0  # Estimated burn duration [s]
    delta_v_required: float = 0.0  # Required delta-V [m/s]
    optimal_burn_time: float = 0.0  # Optimal time to start burn [s]
    moon_phase_angle: float = 0.0  # Moon phase angle for intercept [rad]


@dataclass
class TLIState:
    """Current TLI burn state"""
    burn_started: bool = False
    burn_elapsed_time: float = 0.0
    delta_v_applied: float = 0.0
    current_c3: float = 0.0
    trajectory_converged: bool = False


class TLIGuidance:
    """
    Trans-Lunar Injection Guidance System
    
    This class implements the guidance logic for TLI burns, including:
    - Optimal burn timing calculation
    - Delta-V requirements for lunar intercept
    - Real-time trajectory monitoring
    - Burn termination criteria
    """
    
    def __init__(self, parking_orbit_altitude: float = 185000):
        """
        Initialize TLI guidance system
        
        Args:
            parking_orbit_altitude: LEO parking orbit altitude [m]
        """
        self.parking_orbit_altitude = parking_orbit_altitude
        self.parking_orbit_radius = R_EARTH + parking_orbit_altitude
        self.tli_params = TLIParameters()
        self.tli_state = TLIState()
        
        # Calculate basic orbital parameters
        self.parking_orbit_velocity = np.sqrt(G * M_EARTH / self.parking_orbit_radius)
        self.escape_velocity = np.sqrt(2 * G * M_EARTH / self.parking_orbit_radius)
        
        # Calculate TLI requirements
        self._calculate_tli_requirements()
    
    def _calculate_tli_requirements(self) -> None:
        """Calculate TLI delta-V and energy requirements"""
        # For a minimum energy transfer to the Moon, we need to achieve
        # a C3 energy of approximately 0 m^2/s^2 (parabolic escape)
        # However, for lunar intercept, we need a hyperbolic trajectory
        
        # Calculate the velocity needed at LEO to reach lunar distance
        # Using vis-viva equation: v^2 = μ(2/r - 1/a)
        # For lunar intercept, semi-major axis a ≈ EARTH_MOON_DIST/2
        
        # Professor v30: Target C3 energy between -2.0 and -1.5 km^2/s^2
        # C3 = v_infinity^2 where v_infinity is hyperbolic excess velocity
        self.tli_params.target_c3_energy = -1.75 * 1e6  # -1.75 km^2/s^2 (middle of range)
        
        # Calculate required velocity at parking orbit for target C3
        # C3 = v^2 - v_escape^2, so v^2 = C3 + v_escape^2
        v_required_squared = self.tli_params.target_c3_energy + self.escape_velocity**2
        v_required = np.sqrt(v_required_squared)
        
        # Delta-V required for TLI
        self.tli_params.delta_v_required = v_required - self.parking_orbit_velocity
        
        # Estimate burn duration (will be refined based on actual thrust)
        # This is a placeholder - actual duration depends on S-IVB thrust
        self.tli_params.burn_duration = 360.0  # Approximately 6 minutes
        
        # Calculate optimal burn timing
        self._calculate_optimal_burn_timing()
    
    def _calculate_optimal_burn_timing(self) -> None:
        """Calculate optimal time to start TLI burn for lunar intercept"""
        # For a Hohmann-type transfer, the optimal burn time is when
        # the spacecraft is at a specific phase angle relative to the Moon
        
        # The Moon leads the spacecraft by approximately 65 degrees
        # for a 3-day transfer (simplified calculation)
        target_phase_angle = np.radians(65)  # 65 degrees lead
        
        # Calculate Moon's angular position
        moon_angular_velocity = 2 * np.pi / MOON_ORBIT_PERIOD
        
        # For now, set optimal burn time to immediate (can be refined)
        self.tli_params.optimal_burn_time = 0.0
        self.tli_params.moon_phase_angle = target_phase_angle
    
    def get_guidance_command(self, position: Vector3, velocity: Vector3, 
                           mission_time: float) -> Tuple[Vector3, float]:
        """
        Get TLI guidance command
        
        Args:
            position: Current spacecraft position [m]
            velocity: Current spacecraft velocity [m/s]
            mission_time: Current mission time [s]
            
        Returns:
            Tuple of (thrust_direction, thrust_magnitude_fraction)
        """
        # For TLI, we want to burn prograde (in the direction of orbital motion)
        # to add energy to the orbit and achieve escape velocity
        
        # Calculate prograde direction (tangent to orbit)
        position_unit = position.normalized()
        velocity_unit = velocity.normalized()
        
        # For circular orbit, prograde is perpendicular to position vector
        # We'll use velocity direction as prograde
        thrust_direction = velocity_unit
        
        # Full thrust for TLI burn
        thrust_magnitude = 1.0
        
        # Update TLI state
        if not self.tli_state.burn_started:
            self.tli_state.burn_started = True
            self.tli_state.burn_elapsed_time = 0.0
        
        return thrust_direction, thrust_magnitude
    
    def update_burn_state(self, dt: float, current_velocity: Vector3) -> None:
        """
        Update TLI burn state
        
        Args:
            dt: Time step [s]
            current_velocity: Current spacecraft velocity [m/s]
        """
        if self.tli_state.burn_started:
            self.tli_state.burn_elapsed_time += dt
            
            # Calculate current C3 energy
            current_speed = current_velocity.magnitude()
            self.tli_state.current_c3 = current_speed**2 - self.escape_velocity**2
            
            # Check if burn should terminate
            if self.should_terminate_burn(current_velocity):
                self.tli_state.trajectory_converged = True
    
    def should_terminate_burn(self, current_velocity: Vector3) -> bool:
        """
        Determine if TLI burn should terminate
        
        Args:
            current_velocity: Current spacecraft velocity [m/s]
            
        Returns:
            True if burn should terminate
        """
        # Terminate burn when we achieve the required C3 energy
        current_speed = current_velocity.magnitude()
        current_c3 = current_speed**2 - self.escape_velocity**2
        
        # Professor v30: Target C3 energy between -2.0 and -1.5 km^2/s^2
        c3_min = -2.0 * 1e6  # -2.0 km^2/s^2
        c3_max = -1.5 * 1e6  # -1.5 km^2/s^2
        c3_achieved = (current_c3 >= c3_min) and (current_c3 <= c3_max)
        
        # Also terminate if maximum burn time exceeded
        max_burn_time = self.tli_params.burn_duration * 1.2  # 20% margin
        burn_time_exceeded = self.tli_state.burn_elapsed_time > max_burn_time
        
        return c3_achieved or burn_time_exceeded
    
    def get_trajectory_status(self) -> dict:
        """
        Get current TLI trajectory status
        
        Returns:
            Dictionary containing trajectory information
        """
        return {
            'burn_started': self.tli_state.burn_started,
            'burn_elapsed_time': self.tli_state.burn_elapsed_time,
            'current_c3': self.tli_state.current_c3,
            'target_c3': self.tli_params.target_c3_energy,
            'delta_v_required': self.tli_params.delta_v_required,
            'trajectory_converged': self.tli_state.trajectory_converged,
            'burn_progress': min(1.0, self.tli_state.burn_elapsed_time / self.tli_params.burn_duration)
        }
    
    def calculate_lunar_intercept_trajectory(self, position: Vector3, velocity: Vector3, 
                                          moon_position: Vector3, moon_velocity: Vector3) -> dict:
        """
        Calculate trajectory to lunar intercept
        
        Args:
            position: Current spacecraft position [m]
            velocity: Current spacecraft velocity [m/s]
            moon_position: Current Moon position [m]
            moon_velocity: Current Moon velocity [m/s]
            
        Returns:
            Dictionary with trajectory parameters
        """
        # This is a simplified calculation for demonstration
        # In practice, this would involve solving the patched conic problem
        
        # Calculate relative position and velocity
        relative_position = moon_position - position
        relative_velocity = moon_velocity - velocity
        
        # Estimate time to intercept (simplified)
        distance_to_moon = relative_position.magnitude()
        relative_speed = relative_velocity.magnitude()
        
        # Simple estimate: time = distance / relative_speed
        if relative_speed > 0:
            time_to_intercept = distance_to_moon / relative_speed
        else:
            time_to_intercept = float('inf')
        
        # Calculate required velocity change for intercept
        # This is a very simplified calculation
        required_delta_v = self.tli_params.delta_v_required
        
        return {
            'time_to_intercept': time_to_intercept,
            'distance_to_moon': distance_to_moon,
            'required_delta_v': required_delta_v,
            'intercept_feasible': time_to_intercept < 5 * 24 * 3600  # 5 days
        }


def create_tli_guidance(parking_orbit_altitude: float = 185000) -> TLIGuidance:
    """
    Factory function to create TLI guidance system
    
    Args:
        parking_orbit_altitude: LEO parking orbit altitude [m]
        
    Returns:
        Configured TLI guidance system
    """
    return TLIGuidance(parking_orbit_altitude)


# Example usage and testing
if __name__ == "__main__":
    # Create TLI guidance system
    tli_guidance = create_tli_guidance(185000)  # 185 km parking orbit
    
    print("TLI Guidance System Initialized")
    print(f"Parking orbit altitude: {tli_guidance.parking_orbit_altitude/1000:.1f} km")
    print(f"Parking orbit velocity: {tli_guidance.parking_orbit_velocity:.1f} m/s")
    print(f"Escape velocity: {tli_guidance.escape_velocity:.1f} m/s")
    print(f"Required delta-V: {tli_guidance.tli_params.delta_v_required:.1f} m/s")
    print(f"Estimated burn duration: {tli_guidance.tli_params.burn_duration:.1f} s")
    
    # Test guidance command
    test_position = Vector3(R_EARTH + 185000, 0, 0)
    test_velocity = Vector3(0, 7800, 0)  # Approximate LEO velocity
    
    thrust_dir, thrust_mag = tli_guidance.get_guidance_command(test_position, test_velocity, 0)
    print(f"Thrust direction: {thrust_dir}")
    print(f"Thrust magnitude: {thrust_mag}")
    
    # Test trajectory status
    status = tli_guidance.get_trajectory_status()
    print(f"Trajectory status: {status}")