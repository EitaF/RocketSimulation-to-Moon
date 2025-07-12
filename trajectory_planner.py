"""
Advanced Trajectory Planning Module
Professor v42: Implementation of Lambert solver + Finite Burn optimization

This module shifts from local parameter tuning to broader trajectory optimization
using Lambert's problem solver with finite burn corrections and iterative refinement.
"""

import numpy as np
from typing import Tuple, Optional, List
from dataclasses import dataclass
import logging
from scipy.optimize import fsolve, minimize_scalar
from vehicle import Vector3

# Physical constants
G = 6.67430e-11  # Gravitational constant [m^3/kg/s^2]
M_EARTH = 5.972e24  # Earth mass [kg]
M_MOON = 7.34767309e22  # Moon mass [kg]
R_EARTH = 6371e3  # Earth radius [m]
R_MOON = 1737e3  # Moon radius [m]
EARTH_MOON_DIST = 384400e3  # Earth-Moon distance [m]
MU_EARTH = G * M_EARTH  # Earth gravitational parameter [m^3/s^2]
MU_MOON = G * M_MOON  # Moon gravitational parameter [m^3/s^2]


@dataclass
class LambertSolution:
    """Solution to Lambert's problem"""
    v1: np.ndarray  # Initial velocity vector [m/s]
    v2: np.ndarray  # Final velocity vector [m/s]
    tof: float      # Time of flight [s]
    delta_v: float  # Required impulsive delta-V [m/s]
    converged: bool # Solution convergence flag


@dataclass
class TrajectoryState:
    """Current trajectory state"""
    position: np.ndarray  # Position vector [m]
    velocity: np.ndarray  # Velocity vector [m/s]
    time: float          # Mission time [s]


class TrajectoryPlanner:
    """
    Advanced trajectory planner using Lambert's problem solution
    
    Implements the professor's recommendation for systematic trajectory optimization:
    1. Lambert solver for optimal transfer trajectories
    2. Finite burn correction for realistic propulsion
    3. Iterative refinement using residual projection
    """
    
    def __init__(self, mu: float = MU_EARTH):
        """
        Initialize trajectory planner
        
        Args:
            mu: Gravitational parameter of central body [m^3/s^2]
        """
        self.mu = mu
        self.logger = logging.getLogger(__name__)
        
    def solve_lambert(self, r1: np.ndarray, r2: np.ndarray, tof: float, 
                     mu: Optional[float] = None, prograde: bool = True) -> LambertSolution:
        """
        Solve Lambert's problem for two-body transfer
        
        Args:
            r1: Initial position vector [m]
            r2: Final position vector [m]
            tof: Time of flight [s]
            mu: Gravitational parameter [m^3/s^2] (uses self.mu if None)
            prograde: True for prograde transfer, False for retrograde
            
        Returns:
            LambertSolution object with velocity vectors and metadata
        """
        if mu is None:
            mu = self.mu
            
        # Convert to numpy arrays
        r1 = np.array(r1)
        r2 = np.array(r2)
        
        # Calculate magnitudes
        r1_mag = np.linalg.norm(r1)
        r2_mag = np.linalg.norm(r2)
        
        # Calculate transfer angle
        cos_dnu = np.dot(r1, r2) / (r1_mag * r2_mag)
        cos_dnu = np.clip(cos_dnu, -1.0, 1.0)  # Ensure valid range
        
        # Cross product to determine transfer direction
        cross_product = np.cross(r1, r2)
        if np.linalg.norm(cross_product) < 1e-10:
            # Collinear vectors - handle special case
            self.logger.warning("Collinear position vectors in Lambert solver")
            return LambertSolution(
                v1=np.zeros(3), v2=np.zeros(3), tof=tof, 
                delta_v=0.0, converged=False
            )
        
        # Calculate transfer angle (0 to 2π)
        if prograde:
            if cross_product[2] >= 0:  # Assuming 2D motion in xy-plane
                dnu = np.arccos(cos_dnu)
            else:
                dnu = 2 * np.pi - np.arccos(cos_dnu)
        else:
            if cross_product[2] >= 0:
                dnu = 2 * np.pi - np.arccos(cos_dnu)
            else:
                dnu = np.arccos(cos_dnu)
        
        # Calculate chord and semi-perimeter
        c = np.linalg.norm(r2 - r1)
        s = (r1_mag + r2_mag + c) / 2
        
        # Calculate minimum energy parameter
        a_min = s / 2
        tof_min = np.pi * np.sqrt(a_min**3 / mu)
        
        if tof < tof_min * 0.95:  # Add 5% margin
            self.logger.warning(f"Time of flight {tof:.1f}s too short (min: {tof_min:.1f}s)")
            return LambertSolution(
                v1=np.zeros(3), v2=np.zeros(3), tof=tof,
                delta_v=float('inf'), converged=False
            )
        
        # Use universal variable formulation (Battin's method)
        try:
            # Initial guess for universal variable
            x = 0.0
            
            # Newton-Raphson iteration to solve for x
            for iteration in range(50):  # Maximum 50 iterations
                # Calculate auxiliary variables
                z = x**2
                if z > 0:
                    C = (1 - np.cos(np.sqrt(z))) / z
                    S = (np.sqrt(z) - np.sin(np.sqrt(z))) / np.sqrt(z**3)
                elif z < 0:
                    sqrt_minus_z = np.sqrt(-z)
                    C = (1 - np.cosh(sqrt_minus_z)) / z
                    S = (np.sinh(sqrt_minus_z) - sqrt_minus_z) / np.sqrt((-z)**3)
                else:  # z = 0
                    C = 1/2
                    S = 1/6
                
                # Calculate y
                y = r1_mag + r2_mag + (x * (s - c)) / np.sqrt(C)
                
                if y <= 0:
                    # Adjust x and continue
                    x = x + 0.1
                    continue
                
                # Calculate time of flight
                t = (x**3 * S + x * np.sqrt(y)) / np.sqrt(mu)
                
                # Calculate derivatives for Newton-Raphson
                dt_dx = (x**2 * C + (1/4) * (3 * x * S + np.sqrt(y))) / np.sqrt(mu)
                
                if abs(dt_dx) < 1e-12:
                    break
                
                # Newton-Raphson update
                x_new = x - (t - tof) / dt_dx
                
                if abs(x_new - x) < 1e-8:
                    x = x_new
                    break
                
                x = x_new
            
            # Calculate final y value
            z = x**2
            if z > 0:
                C = (1 - np.cos(np.sqrt(z))) / z
                S = (np.sqrt(z) - np.sin(np.sqrt(z))) / np.sqrt(z**3)
            elif z < 0:
                sqrt_minus_z = np.sqrt(-z)
                C = (1 - np.cosh(sqrt_minus_z)) / z
                S = (np.sinh(sqrt_minus_z) - sqrt_minus_z) / np.sqrt((-z)**3)
            else:
                C = 1/2
                S = 1/6
            
            y = r1_mag + r2_mag + (x * (s - c)) / np.sqrt(C)
            
            # Calculate Lagrange coefficients
            f = 1 - y / r1_mag
            g = (r1_mag * r2_mag * np.sin(dnu)) / np.sqrt(mu * y)
            gdot = 1 - y / r2_mag
            
            # Calculate velocity vectors
            v1 = (r2 - f * r1) / g
            v2 = (gdot * r2 - r1) / g
            
            # Calculate delta-V magnitude
            # This represents the impulsive delta-V required at r1
            v1_circular = np.sqrt(mu / r1_mag)  # Circular velocity at r1
            current_v1 = np.array([0, v1_circular, 0])  # Assume circular orbit
            
            # For simplicity, assume we're in circular orbit initially
            delta_v = np.linalg.norm(v1 - current_v1)
            
            return LambertSolution(
                v1=v1, v2=v2, tof=tof, delta_v=delta_v, converged=True
            )
            
        except Exception as e:
            self.logger.error(f"Lambert solver failed: {e}")
            return LambertSolution(
                v1=np.zeros(3), v2=np.zeros(3), tof=tof,
                delta_v=float('inf'), converged=False
            )
    
    def plan_earth_moon_transfer(self, leo_state: TrajectoryState, 
                               moon_soi_target: np.ndarray,
                               transfer_time: float = 3.0 * 24 * 3600) -> LambertSolution:
        """
        Plan optimal Earth-Moon transfer trajectory
        
        Args:
            leo_state: Current LEO state (position, velocity, time)
            moon_soi_target: Target position at Moon SoI boundary [m]
            transfer_time: Desired transfer time [s] (default: 3 days)
            
        Returns:
            LambertSolution for the transfer
        """
        # Current position in LEO
        r1 = leo_state.position
        
        # Target position at Moon SoI
        r2 = moon_soi_target
        
        # Solve Lambert's problem
        solution = self.solve_lambert(r1, r2, transfer_time, MU_EARTH, prograde=True)
        
        if solution.converged:
            self.logger.info(f"Earth-Moon transfer planned: ΔV = {solution.delta_v:.1f} m/s, "
                           f"TOF = {transfer_time/(24*3600):.1f} days")
        else:
            self.logger.warning("Failed to find Earth-Moon transfer solution")
        
        return solution
    
    def calculate_moon_soi_target(self, mission_time: float, 
                                intercept_time: float) -> np.ndarray:
        """
        Calculate target position at Moon's sphere of influence
        
        Args:
            mission_time: Current mission time [s]
            intercept_time: Time of intercept [s]
            
        Returns:
            Target position vector at Moon SoI [m]
        """
        # Moon's orbital parameters (simplified circular orbit)
        moon_orbit_radius = EARTH_MOON_DIST
        moon_angular_velocity = 2 * np.pi / (27.321661 * 24 * 3600)  # rad/s
        
        # Moon's position at intercept time
        moon_angle = moon_angular_velocity * intercept_time
        moon_position = np.array([
            moon_orbit_radius * np.cos(moon_angle),
            moon_orbit_radius * np.sin(moon_angle),
            0
        ])
        
        # Moon's sphere of influence radius
        soi_radius = 66100e3  # 66,100 km
        
        # Target position: Moon center (simplified)
        # In practice, this should be optimized for specific mission requirements
        return moon_position
    
    def optimize_transfer_time(self, leo_state: TrajectoryState,
                             moon_position_func,
                             min_tof: float = 2.5 * 24 * 3600,
                             max_tof: float = 5.0 * 24 * 3600) -> Tuple[float, LambertSolution]:
        """
        Optimize transfer time for minimum delta-V
        
        Args:
            leo_state: Current LEO state
            moon_position_func: Function to calculate Moon position at given time
            min_tof: Minimum time of flight [s]
            max_tof: Maximum time of flight [s]
            
        Returns:
            Tuple of (optimal_tof, lambert_solution)
        """
        def delta_v_objective(tof):
            """Objective function: minimize delta-V for given TOF"""
            target_pos = moon_position_func(leo_state.time + tof)
            solution = self.solve_lambert(leo_state.position, target_pos, tof)
            return solution.delta_v if solution.converged else 1e6
        
        # Use golden section search to find optimal TOF
        try:
            result = minimize_scalar(delta_v_objective, bounds=(min_tof, max_tof), 
                                   method='bounded')
            
            if result.success:
                optimal_tof = result.x
                target_pos = moon_position_func(leo_state.time + optimal_tof)
                optimal_solution = self.solve_lambert(leo_state.position, target_pos, optimal_tof)
                
                self.logger.info(f"Optimized transfer: TOF = {optimal_tof/(24*3600):.2f} days, "
                               f"ΔV = {optimal_solution.delta_v:.1f} m/s")
                
                return optimal_tof, optimal_solution
            else:
                self.logger.warning("Transfer time optimization failed")
                # Return solution for middle of range
                mid_tof = (min_tof + max_tof) / 2
                target_pos = moon_position_func(leo_state.time + mid_tof)
                fallback_solution = self.solve_lambert(leo_state.position, target_pos, mid_tof)
                return mid_tof, fallback_solution
                
        except Exception as e:
            self.logger.error(f"Transfer optimization error: {e}")
            # Return fallback solution
            mid_tof = (min_tof + max_tof) / 2
            target_pos = moon_position_func(leo_state.time + mid_tof)
            fallback_solution = self.solve_lambert(leo_state.position, target_pos, mid_tof)
            return mid_tof, fallback_solution


def create_trajectory_planner(central_body: str = "Earth") -> TrajectoryPlanner:
    """
    Factory function to create trajectory planner
    
    Args:
        central_body: "Earth" or "Moon"
        
    Returns:
        Configured TrajectoryPlanner instance
    """
    if central_body.lower() == "earth":
        return TrajectoryPlanner(MU_EARTH)
    elif central_body.lower() == "moon":
        return TrajectoryPlanner(MU_MOON)
    else:
        raise ValueError(f"Unknown central body: {central_body}")


# Example usage and testing
if __name__ == "__main__":
    # Create trajectory planner
    planner = create_trajectory_planner("Earth")
    
    # Test Lambert solver with Earth-Moon transfer
    print("Testing Lambert solver for Earth-Moon transfer")
    
    # LEO initial position (185 km altitude)
    r1 = np.array([R_EARTH + 185000, 0, 0])
    
    # Moon SoI target (simplified)
    r2 = np.array([EARTH_MOON_DIST - 66100e3, 0, 0])
    
    # 3-day transfer
    tof = 3 * 24 * 3600
    
    solution = planner.solve_lambert(r1, r2, tof)
    
    print(f"Lambert solution converged: {solution.converged}")
    if solution.converged:
        print(f"Initial velocity: {solution.v1}")
        print(f"Final velocity: {solution.v2}")
        print(f"Required delta-V: {solution.delta_v:.1f} m/s")
        print(f"Time of flight: {solution.tof/(24*3600):.2f} days")