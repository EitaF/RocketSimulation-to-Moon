import numpy as np
import math

# Constants
G = 6.67430e-11  # Gravitational constant [m^3/kg/s^2]
M_EARTH = 5.972e24  # Earth mass [kg]
M_MOON = 7.34767309e22  # Moon mass [kg]
R_EARTH = 6371e3  # Earth radius [m]
R_MOON = 1737e3  # Moon radius [m]
EARTH_MOON_DIST = 384400e3  # Earth-Moon distance [m]
MOON_ORBIT_PERIOD = 27.321661 * 24 * 3600  # Moon orbital period [s]

class LaunchWindowCalculator:
    """
    Calculates optimal launch window for Trans-Lunar Injection (TLI) burn
    to achieve lunar intercept trajectory.
    """
    
    def __init__(self, parking_orbit_altitude=200e3):
        """
        Initialize the launch window calculator.
        
        Args:
            parking_orbit_altitude (float): Altitude of parking orbit in meters
        """
        self.parking_orbit_altitude = parking_orbit_altitude
        self.parking_orbit_radius = R_EARTH + parking_orbit_altitude
        
    def calculate_transfer_time(self, c3_energy):
        """
        Calculate approximate transfer time for trans-lunar trajectory.
        
        Args:
            c3_energy (float): C3 energy (km²/s²)
            
        Returns:
            float: Transfer time in seconds
        """
        # Convert C3 from km²/s² to m²/s²
        c3_m2_s2 = c3_energy * 1e6
        
        # Calculate departure velocity from parking orbit
        v_circular = np.sqrt(G * M_EARTH / self.parking_orbit_radius)
        v_departure = np.sqrt(v_circular**2 + c3_m2_s2)
        
        # Simplified Hohmann transfer approximation
        # Semi-major axis of transfer orbit
        a_transfer = (self.parking_orbit_radius + EARTH_MOON_DIST) / 2
        
        # Transfer time (half of elliptical orbit period)
        transfer_time = np.pi * np.sqrt(a_transfer**3 / (G * M_EARTH))
        
        return transfer_time
    
    def calculate_phase_angle(self, transfer_time):
        """
        Calculate required phase angle between spacecraft and Moon at TLI.
        
        Args:
            transfer_time (float): Transfer time in seconds
            
        Returns:
            float: Required phase angle in radians
        """
        # Moon's angular velocity
        omega_moon = 2 * np.pi / MOON_ORBIT_PERIOD
        
        # Angle Moon travels during transfer
        moon_travel_angle = omega_moon * transfer_time
        
        # Required phase angle (Moon should be this angle ahead)
        # Subtracting pi because we want Moon to be at intercept point
        required_phase_angle = np.pi - moon_travel_angle
        
        # Normalize to [0, 2π)
        while required_phase_angle < 0:
            required_phase_angle += 2 * np.pi
        while required_phase_angle >= 2 * np.pi:
            required_phase_angle -= 2 * np.pi
            
        return required_phase_angle
    
    def calculate_optimal_tli_time(self, current_time, moon_position, spacecraft_position, c3_energy):
        """
        Calculate optimal time to initiate TLI burn for lunar intercept.
        
        Args:
            current_time (float): Current simulation time [s]
            moon_position (np.ndarray): Moon position vector [m]
            spacecraft_position (np.ndarray): Spacecraft position vector [m]
            c3_energy (float): Target C3 energy [km²/s²]
            
        Returns:
            tuple: (optimal_time, phase_angle, transfer_time)
        """
        # Calculate transfer time
        transfer_time = self.calculate_transfer_time(c3_energy)
        
        # Calculate required phase angle
        required_phase_angle = self.calculate_phase_angle(transfer_time)
        
        # Current positions in orbital plane
        moon_angle = np.arctan2(moon_position[1], moon_position[0])
        spacecraft_angle = np.arctan2(spacecraft_position[1], spacecraft_position[0])
        
        # Current phase angle (Moon ahead of spacecraft)
        current_phase_angle = moon_angle - spacecraft_angle
        while current_phase_angle < 0:
            current_phase_angle += 2 * np.pi
        while current_phase_angle >= 2 * np.pi:
            current_phase_angle -= 2 * np.pi
        
        # Calculate angular difference needed
        angle_diff = required_phase_angle - current_phase_angle
        while angle_diff < 0:
            angle_diff += 2 * np.pi
        while angle_diff >= 2 * np.pi:
            angle_diff -= 2 * np.pi
        
        # Time to achieve required phase angle
        # Spacecraft in parking orbit moves faster than Moon
        omega_spacecraft = np.sqrt(G * M_EARTH / self.parking_orbit_radius**3)
        omega_moon = 2 * np.pi / MOON_ORBIT_PERIOD
        omega_relative = omega_spacecraft - omega_moon
        
        if omega_relative > 0:
            time_to_optimal = angle_diff / omega_relative
        else:
            # If Moon is moving faster (should not happen in LEO)
            time_to_optimal = angle_diff / abs(omega_relative)
        
        optimal_time = current_time + time_to_optimal
        
        return optimal_time, required_phase_angle, transfer_time
    
    def get_launch_window_info(self, current_time, moon_position, spacecraft_position, c3_energy):
        """
        Get comprehensive launch window information.
        
        Args:
            current_time (float): Current simulation time [s]
            moon_position (np.ndarray): Moon position vector [m]
            spacecraft_position (np.ndarray): Spacecraft position vector [m]
            c3_energy (float): Target C3 energy [km²/s²]
            
        Returns:
            dict: Launch window information
        """
        optimal_time, phase_angle, transfer_time = self.calculate_optimal_tli_time(
            current_time, moon_position, spacecraft_position, c3_energy
        )
        
        return {
            'optimal_tli_time': optimal_time,
            'time_to_optimal': optimal_time - current_time,
            'required_phase_angle_deg': np.degrees(phase_angle),
            'transfer_time_hours': transfer_time / 3600,
            'transfer_time_days': transfer_time / (24 * 3600),
            'c3_energy': c3_energy,
            'parking_orbit_altitude_km': self.parking_orbit_altitude / 1000
        }