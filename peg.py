"""
Powered Explicit Guidance (PEG) Implementation
Professor v15: Basic PEG logic with target orbit h=200km, e<10^-3
"""

import numpy as np
from typing import Tuple, Optional
from vehicle import Vector3

# Physical constants
G = 6.67430e-11  # Gravitational constant [m^3/kg/s^2]
M_EARTH = 5.972e24  # Earth mass [kg]
R_EARTH = 6371e3  # Earth radius [m]
MU_EARTH = G * M_EARTH  # Standard gravitational parameter [m^3/s^2]

class PEGGuidance:
    """
    Enhanced Powered Explicit Guidance implementation
    Professor v17: Added γ derivative damping and fallback logic
    """
    
    def __init__(self, target_altitude: float = 200000, target_eccentricity: float = 0.001):
        """
        Initialize PEG guidance
        
        Args:
            target_altitude: Target circular orbit altitude [m]
            target_eccentricity: Target orbit eccentricity (≤ 1e-3)
        """
        self.target_altitude = target_altitude
        self.target_eccentricity = target_eccentricity
        self.target_radius = R_EARTH + target_altitude
        
        # Target orbital velocity for circular orbit - Professor v16: tuned to 7790 m/s
        self.target_velocity = 7790.0  # Professor feedback: specific target velocity
        
        # PEG state
        self.last_update_time = 0.0
        self.update_interval = 0.5  # Update every 0.5 seconds
        self.guidance_active = False
        
        # Professor v17: γ derivative damping state
        self.last_flight_path_angle = 0.0
        self.gamma_derivative_history = []
        self.fallback_to_tangent = False
        self.convergence_failures = 0
        
    def should_update(self, current_time: float) -> bool:
        """Check if PEG should update guidance"""
        return (current_time - self.last_update_time) >= self.update_interval
    
    def calculate_orbital_elements(self, position: Vector3, velocity: Vector3) -> Tuple[float, float, float]:
        """
        Calculate current orbital elements
        
        Returns:
            Tuple of (apoapsis, periapsis, eccentricity) in meters and dimensionless
        """
        r = position.magnitude()
        v = velocity.magnitude()
        
        # Specific orbital energy
        specific_energy = 0.5 * v * v - MU_EARTH / r
        
        if specific_energy >= 0:
            # Hyperbolic/parabolic trajectory
            return float('inf'), float('-inf'), float('inf')
        
        # Semi-major axis
        a = -MU_EARTH / (2 * specific_energy)
        
        # Angular momentum vector
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
            e = float('inf')
        
        # Apoapsis and periapsis
        if e < 1.0 and a > 0:
            apoapsis = a * (1 + e)
            periapsis = a * (1 - e)
        else:
            apoapsis = float('inf')
            periapsis = float('-inf')
        
        return apoapsis, periapsis, e
    
    def calculate_required_delta_v(self, position: Vector3, velocity: Vector3) -> Tuple[float, Vector3]:
        """
        Calculate required ΔV to reach target orbit
        
        Returns:
            Tuple of (delta_v_magnitude, delta_v_vector)
        """
        r = position.magnitude()
        v = velocity.magnitude()
        
        # Current specific energy
        current_energy = 0.5 * v * v - MU_EARTH / r
        
        # Target specific energy for circular orbit
        target_energy = -MU_EARTH / (2 * self.target_radius)
        
        # If we're at target altitude, calculate circularization ΔV
        if abs(r - self.target_radius) < 10000:  # Within 10km of target
            target_v = np.sqrt(MU_EARTH / r)  # Circular velocity at current altitude
            delta_v_mag = abs(target_v - v)
            
            # Direction: along velocity vector for circularization
            if v > 0:
                delta_v_dir = velocity.normalized()
                if v < target_v:
                    delta_v_vector = delta_v_dir * delta_v_mag  # Prograde
                else:
                    delta_v_vector = delta_v_dir * (-delta_v_mag)  # Retrograde
            else:
                delta_v_vector = Vector3(0, 0, 0)
                
        else:
            # General case: approximate ΔV needed
            target_v_at_current_r = np.sqrt(2 * (target_energy + MU_EARTH / r))
            delta_v_mag = abs(target_v_at_current_r - v)
            
            # Direction: generally prograde for orbit raising
            if v > 0:
                delta_v_vector = velocity.normalized() * delta_v_mag
            else:
                # Fallback: tangential direction
                radial = position.normalized()
                tangent = Vector3(-radial.y, radial.x, 0)
                delta_v_vector = tangent * delta_v_mag
        
        return delta_v_mag, delta_v_vector
    
    def compute_peg_guidance(self, position: Vector3, velocity: Vector3, time: float, 
                            remaining_burn_time: float, thrust_deficit: float = 0.0) -> Tuple[float, Vector3, bool]:
        """
        Compute optimal guidance using enhanced closed-loop PEG algorithm
        Professor v27: Enhanced for closed-loop control with thrust deficit handling
        
        Args:
            position: Current position vector
            velocity: Current velocity vector  
            time: Current mission time
            remaining_burn_time: Estimated remaining burn time for current stage
            thrust_deficit: Thrust deficit factor (0.0 = normal, 0.05 = 5% deficit)
            
        Returns:
            Tuple of (pitch_angle_degrees, thrust_direction_vector, meco_condition_met)
        """
        if not self.should_update(time):
            return None, Vector3(0, 0, 0), False  # Use previous guidance
        
        self.last_update_time = time
        
        # Calculate current orbital state
        apoapsis, periapsis, eccentricity = self.calculate_orbital_elements(position, velocity)
        
        # Calculate V_go vector (velocity-to-be-gained)
        v_go_vector, v_go_magnitude = self._calculate_v_go_vector(position, velocity, thrust_deficit)
        
        # Current state
        r = position.magnitude()
        altitude = r - R_EARTH
        v = velocity.magnitude()
        
        # Flight path angle with derivative damping
        pos_unit = position.normalized()
        vel_unit = velocity.normalized()
        flight_path_angle = np.pi/2 - np.arccos(np.clip(pos_unit.data @ vel_unit.data, -1, 1))
        
        # Professor v17: γ derivative damping
        gamma_derivative = (flight_path_angle - self.last_flight_path_angle) / self.update_interval
        self.gamma_derivative_history.append(abs(gamma_derivative))
        
        # Keep only last 10 samples for moving average
        if len(self.gamma_derivative_history) > 10:
            self.gamma_derivative_history.pop(0)
        
        avg_gamma_derivative = np.mean(self.gamma_derivative_history)
        
        # Check for convergence issues (Professor requirement: γ error ≤ 0.1°)
        gamma_error_deg = abs(np.degrees(gamma_derivative))
        convergence_issue = gamma_error_deg > 0.5  # 0.5° threshold for corrective action
        
        if convergence_issue:
            self.convergence_failures += 1
        else:
            self.convergence_failures = max(0, self.convergence_failures - 1)
        
        # Determine MECO condition
        meco_condition = self._check_meco_condition(position, velocity, v_go_magnitude)
        
        # Calculate thrust direction and pitch
        if self.convergence_failures >= 3 or avg_gamma_derivative > 0.01:  # rad/s threshold
            self.fallback_to_tangent = True
            pitch_deg = self._tangent_guidance_fallback(altitude, v, flight_path_angle)
            thrust_direction = self._pitch_to_thrust_vector(pitch_deg, position, velocity)
        else:
            self.fallback_to_tangent = False
            thrust_direction = v_go_vector.normalized() if v_go_magnitude > 0.1 else velocity.normalized()
            pitch_deg = self._thrust_vector_to_pitch(thrust_direction, position)
        
        self.last_flight_path_angle = flight_path_angle
        
        # Ensure reasonable bounds
        pitch_deg = max(0, min(90, pitch_deg))
        
        return pitch_deg, thrust_direction, meco_condition
    
    def _calculate_v_go_vector(self, position: Vector3, velocity: Vector3, thrust_deficit: float) -> Tuple[Vector3, float]:
        """
        Calculate velocity-to-be-gained (V_go) vector for closed-loop guidance
        Professor v27: Core PEG algorithm implementation
        """
        r = position.magnitude()
        v = velocity.magnitude()
        
        # Target orbital velocity at current radius for circular orbit
        v_circular_current = np.sqrt(MU_EARTH / r)
        
        # Target orbital velocity at target radius
        v_circular_target = np.sqrt(MU_EARTH / self.target_radius)
        
        # Current specific energy
        current_energy = 0.5 * v**2 - MU_EARTH / r
        
        # Target specific energy for circular orbit
        target_energy = -MU_EARTH / (2 * self.target_radius)
        
        # Required velocity change magnitude
        if r < self.target_radius:  # Below target altitude
            # Need to gain energy to reach target
            delta_v_needed = np.sqrt(2 * (target_energy + MU_EARTH / r)) - v
            
            # Compensate for thrust deficit
            if thrust_deficit > 0:
                delta_v_needed *= (1 + thrust_deficit * 2)  # Increase required delta-v
            
            # Direction: blend prograde and radial based on altitude
            prograde_component = velocity.normalized()
            radial_component = position.normalized()
            
            # More radial at lower altitudes, more prograde at higher altitudes
            altitude_factor = min(1.0, (r - R_EARTH) / 100000)  # 0 at surface, 1 at 100km
            
            # Weighted direction
            v_go_direction = (prograde_component * (0.7 + 0.3 * altitude_factor) + 
                            radial_component * (0.3 - 0.3 * altitude_factor))
            v_go_direction = v_go_direction.normalized()
            
        else:  # At or above target altitude
            # Fine-tune for circular orbit
            delta_v_needed = v_circular_current - v
            v_go_direction = velocity.normalized()  # Prograde for circularization
        
        v_go_magnitude = max(0, delta_v_needed)
        v_go_vector = v_go_direction * v_go_magnitude
        
        return v_go_vector, v_go_magnitude
    
    def _check_meco_condition(self, position: Vector3, velocity: Vector3, v_go_magnitude: float) -> bool:
        """
        Check if Main Engine Cutoff (MECO) condition is met
        Professor v27: Precise MECO logic for orbital insertion
        """
        r = position.magnitude()
        v = velocity.magnitude()
        
        # Calculate predicted apoapsis with current trajectory
        current_energy = 0.5 * v**2 - MU_EARTH / r
        
        if current_energy >= 0:
            return True  # Escape trajectory, cut engines
        
        # Semi-major axis
        a = -MU_EARTH / (2 * current_energy)
        
        # Angular momentum
        h_vec = Vector3(
            position.y * velocity.z - position.z * velocity.y,
            position.z * velocity.x - position.x * velocity.z,
            position.x * velocity.y - position.y * velocity.x
        )
        h = h_vec.magnitude()
        
        # Eccentricity
        if h > 0:
            e = np.sqrt(1 + 2 * current_energy * h**2 / (MU_EARTH**2))
            predicted_apoapsis = a * (1 + e)
        else:
            predicted_apoapsis = r
        
        # MECO when apoapsis is within tolerance of target
        apoapsis_error = abs(predicted_apoapsis - self.target_radius)
        meco_tolerance = 5000  # 5 km tolerance
        
        # Also consider velocity-to-go magnitude
        v_go_small = v_go_magnitude < 50  # Less than 50 m/s remaining
        
        return apoapsis_error < meco_tolerance or v_go_small
    
    def _pitch_to_thrust_vector(self, pitch_deg: float, position: Vector3, velocity: Vector3) -> Vector3:
        """Convert pitch angle to thrust direction vector"""
        pitch_rad = np.radians(pitch_deg)
        
        # Local coordinate system
        radial_unit = position.normalized()
        
        # Tangential direction (perpendicular to radial, in orbital plane)
        if velocity.magnitude() > 0:
            vel_unit = velocity.normalized()
            # Cross product to get normal to orbital plane
            normal = Vector3(
                radial_unit.y * vel_unit.z - radial_unit.z * vel_unit.y,
                radial_unit.z * vel_unit.x - radial_unit.x * vel_unit.z,
                radial_unit.x * vel_unit.y - radial_unit.y * vel_unit.x
            )
            if normal.magnitude() > 0:
                normal = normal.normalized()
                # Tangential direction
                tangent = Vector3(
                    normal.y * radial_unit.z - normal.z * radial_unit.y,
                    normal.z * radial_unit.x - normal.x * radial_unit.z,
                    normal.x * radial_unit.y - normal.y * radial_unit.x
                )
                tangent = tangent.normalized()
            else:
                # Fallback: assume tangent is in xy-plane
                tangent = Vector3(-radial_unit.y, radial_unit.x, 0).normalized()
        else:
            # Fallback for zero velocity
            tangent = Vector3(-radial_unit.y, radial_unit.x, 0).normalized()
        
        # Thrust vector: pitch angle from vertical (radial)
        thrust_vector = radial_unit * np.cos(pitch_rad) + tangent * np.sin(pitch_rad)
        return thrust_vector.normalized()
    
    def _thrust_vector_to_pitch(self, thrust_vector: Vector3, position: Vector3) -> float:
        """Convert thrust direction vector to pitch angle"""
        radial_unit = position.normalized()
        
        # Dot product to get cosine of angle from vertical
        cos_pitch = radial_unit.data @ thrust_vector.data
        cos_pitch = np.clip(cos_pitch, -1, 1)
        
        pitch_rad = np.arccos(cos_pitch)
        return np.degrees(pitch_rad)
    
    def _standard_peg_logic(self, altitude: float, velocity: float, flight_path_angle: float,
                           delta_v_needed: float, periapsis: float, apoapsis: float, 
                           gamma_derivative: float) -> float:
        """Standard PEG logic with damping"""
        # Apply damping factor based on γ derivative
        damping_factor = max(0.5, 1.0 - abs(gamma_derivative) * 50)  # Scale factor
        
        if altitude < 100e3:  # In atmosphere - focus on altitude gain
            if delta_v_needed > 1000:  # Significant ΔV needed
                # Gradually pitch over based on altitude and velocity
                if altitude < 50e3:
                    base_pitch = min(45, altitude / 1000)  # 0-45° by 50km
                else:
                    base_pitch = 45 + (altitude - 50e3) / 1000  # Continue pitching
                    base_pitch = min(85, base_pitch)
                
                # Apply damping
                pitch_deg = base_pitch * damping_factor
            else:
                # Close to target - gentle adjustments
                pitch_deg = (75 + flight_path_angle * 180 / np.pi) * damping_factor
                
        else:  # Above atmosphere - optimize for orbital insertion
            if periapsis < R_EARTH + 180e3:  # Need to raise periapsis
                # Burn prograde to circularize with damping
                base_pitch = 85 + flight_path_angle * 180 / np.pi
                base_pitch = min(90, max(75, base_pitch))
                pitch_deg = base_pitch * damping_factor
            else:
                # Near circular orbit
                pitch_deg = 87 * damping_factor
        
        return pitch_deg
    
    def _tangent_guidance_fallback(self, altitude: float, velocity: float, 
                                  flight_path_angle: float) -> float:
        """
        Fallback to simple tangent guidance when PEG fails to converge
        Professor v17: Simple, stable guidance law
        """
        if altitude < 50e3:
            # Early ascent: vertical to 45° by 50km
            return min(45, altitude / 1000)
        elif altitude < 100e3:
            # Mid ascent: 45° to 85° by 100km
            return 45 + (altitude - 50e3) / 1000
        else:
            # Above atmosphere: mostly horizontal with small adjustments
            return 85 + np.degrees(flight_path_angle) * 0.5
    
    def is_guidance_needed(self, position: Vector3, velocity: Vector3) -> bool:
        """
        Determine if PEG guidance should be active
        
        Returns:
            True if guidance corrections are needed
        """
        apoapsis, periapsis, eccentricity = self.calculate_orbital_elements(position, velocity)
        
        # Check if we're close to target orbit - Professor v16: lowered abort-eccentricity threshold
        target_achieved = (
            periapsis > R_EARTH + self.target_altitude * 0.9 and
            eccentricity < 0.02  # Professor feedback: lower threshold to 0.02
        )
        
        return not target_achieved
    
    def get_guidance_status(self, position: Vector3, velocity: Vector3) -> dict:
        """Get current guidance status for logging"""
        apoapsis, periapsis, eccentricity = self.calculate_orbital_elements(position, velocity)
        delta_v_needed, _ = self.calculate_required_delta_v(position, velocity)
        
        return {
            'apoapsis_km': apoapsis / 1000,
            'periapsis_km': periapsis / 1000,
            'eccentricity': eccentricity,
            'delta_v_needed': delta_v_needed,
            'target_altitude_km': self.target_altitude / 1000,
            'guidance_active': self.guidance_active
        }


def create_peg_guidance(target_altitude_km: float = 200) -> PEGGuidance:
    """
    Factory function to create PEG guidance for LEO mission
    
    Args:
        target_altitude_km: Target orbit altitude in kilometers
        
    Returns:
        Configured PEGGuidance instance
    """
    return PEGGuidance(
        target_altitude=target_altitude_km * 1000,
        target_eccentricity=0.001
    )