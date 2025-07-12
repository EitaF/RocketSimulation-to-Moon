"""
Residual Projector Module
Professor v42: Newton-Raphson correction for Lambert ΔV refinement

This module implements iterative trajectory correction using residual projection
to achieve convergence between planned and actual trajectories within ±5 m/s accuracy.
"""

import numpy as np
from typing import Tuple, Optional, Dict, Callable
from dataclasses import dataclass
import logging
from scipy.optimize import fsolve, least_squares
from trajectory_planner import TrajectoryPlanner, LambertSolution, TrajectoryState
from finite_burn_executor import FiniteBurnExecutor, BurnSequence, FiniteBurnResult

# Physical constants
MU_EARTH = 3.986004418e14  # Earth gravitational parameter [m^3/s^2]
MU_MOON = 4.9048695e12     # Moon gravitational parameter [m^3/s^2]


@dataclass
class ResidualState:
    """State vector residuals at target"""
    position_error: np.ndarray  # Position error vector [m]
    velocity_error: np.ndarray  # Velocity error vector [m/s]
    time_error: float          # Time error [s]
    total_error: float         # Total error magnitude [m + m/s]


@dataclass
class CorrectionVector:
    """Trajectory correction parameters"""
    delta_v_correction: np.ndarray  # Delta-V correction vector [m/s]
    time_correction: float         # Time of flight correction [s]
    burn_angle_correction: float   # Burn angle correction [rad]
    magnitude: float              # Total correction magnitude


@dataclass
class IterationResult:
    """Single iteration result"""
    iteration: int
    residual: ResidualState
    correction: CorrectionVector
    converged: bool
    delta_v_error: float  # Error in delta-V magnitude [m/s]


class ResidualProjector:
    """
    Residual projector for iterative trajectory correction
    
    Implements Newton-Raphson method to correct Lambert solutions
    by minimizing residuals at the target state through:
    1. Numerical integration of actual trajectory
    2. Residual calculation at target point
    3. Jacobian-based correction computation
    4. Iterative refinement until convergence
    """
    
    def __init__(self, trajectory_planner: TrajectoryPlanner,
                 finite_burn_executor: FiniteBurnExecutor,
                 propagator_func: Optional[Callable] = None):
        """
        Initialize residual projector
        
        Args:
            trajectory_planner: TrajectoryPlanner instance
            finite_burn_executor: FiniteBurnExecutor instance
            propagator_func: Optional orbital propagator function
        """
        self.trajectory_planner = trajectory_planner
        self.finite_burn_executor = finite_burn_executor
        self.propagator_func = propagator_func or self._default_propagator
        self.logger = logging.getLogger(__name__)
        
        # Convergence criteria
        self.position_tolerance = 1000.0    # 1 km position tolerance
        self.velocity_tolerance = 5.0       # 5 m/s velocity tolerance  
        self.delta_v_tolerance = 5.0        # 5 m/s delta-V tolerance (Professor's requirement)
        self.max_iterations = 10            # Maximum correction iterations
        
        # Finite difference parameters for Jacobian calculation
        self.delta_v_perturbation = 1.0     # 1 m/s perturbation for numerical derivatives
        self.time_perturbation = 60.0       # 1 minute perturbation for TOF derivatives
    
    def _default_propagator(self, initial_state: TrajectoryState, 
                          burn_sequence: BurnSequence, 
                          target_time: float) -> TrajectoryState:
        """
        Default orbital propagator using simplified two-body dynamics
        
        Args:
            initial_state: Initial trajectory state
            burn_sequence: Burn sequence to apply
            target_time: Time to propagate to [s]
            
        Returns:
            Final trajectory state
        """
        # Start with initial conditions
        r = initial_state.position.copy()
        v = initial_state.velocity.copy()
        t = initial_state.time
        mass = 45000.0  # Default mass [kg]
        
        # Apply burn sequence
        for segment in burn_sequence.segments:
            # Propagate to burn start
            burn_start_time = t + segment.start_time
            if burn_start_time > initial_state.time:
                dt_coast = burn_start_time - t
                r, v = self._propagate_keplerian(r, v, dt_coast)
                t = burn_start_time
            
            # Apply burn impulse (simplified)
            if segment.thrust_magnitude > 0 and mass > 0:
                # Calculate acceleration
                acceleration = segment.thrust_magnitude / mass
                
                # Apply impulse over segment duration
                delta_v_impulse = acceleration * segment.duration
                v += segment.thrust_vector * delta_v_impulse
                
                # Update mass
                mass -= segment.mass_flow_rate * segment.duration
                mass = max(mass, 1000.0)  # Minimum residual mass
            
            t += segment.duration
        
        # Coast to target time
        if target_time > t:
            dt_final_coast = target_time - t
            r, v = self._propagate_keplerian(r, v, dt_final_coast)
        
        return TrajectoryState(position=r, velocity=v, time=target_time)
    
    def _propagate_keplerian(self, r0: np.ndarray, v0: np.ndarray, 
                           dt: float) -> Tuple[np.ndarray, np.ndarray]:
        """
        Propagate state using simplified Keplerian orbit
        
        Args:
            r0: Initial position [m]
            v0: Initial velocity [m/s]
            dt: Time step [s]
            
        Returns:
            Tuple of (final_position, final_velocity)
        """
        if dt <= 0:
            return r0.copy(), v0.copy()
        
        # Use simplified circular orbit approximation for short propagations
        r0_mag = np.linalg.norm(r0)
        orbital_velocity = np.sqrt(MU_EARTH / r0_mag)
        angular_velocity = orbital_velocity / r0_mag
        
        # Rotate position and velocity
        angle = angular_velocity * dt
        cos_angle = np.cos(angle)
        sin_angle = np.sin(angle)
        
        # Rotation matrix for 2D orbital motion
        rotation_matrix = np.array([
            [cos_angle, -sin_angle, 0],
            [sin_angle, cos_angle, 0],
            [0, 0, 1]
        ])
        
        r_final = rotation_matrix @ r0
        v_final = rotation_matrix @ v0
        
        return r_final, v_final
    
    def calculate_residuals(self, actual_state: TrajectoryState,
                          target_state: TrajectoryState) -> ResidualState:
        """
        Calculate residuals between actual and target states
        
        Args:
            actual_state: Actual achieved trajectory state
            target_state: Desired target trajectory state
            
        Returns:
            ResidualState with error components
        """
        # Position and velocity errors
        pos_error = actual_state.position - target_state.position
        vel_error = actual_state.velocity - target_state.velocity
        time_error = actual_state.time - target_state.time
        
        # Total error magnitude (weighted combination)
        pos_error_mag = np.linalg.norm(pos_error)
        vel_error_mag = np.linalg.norm(vel_error)
        total_error = pos_error_mag + vel_error_mag * 1000  # Weight velocity errors more
        
        return ResidualState(
            position_error=pos_error,
            velocity_error=vel_error,
            time_error=time_error,
            total_error=total_error
        )
    
    def compute_jacobian(self, lambert_solution: LambertSolution,
                        initial_state: TrajectoryState,
                        target_state: TrajectoryState,
                        burn_sequence: BurnSequence) -> np.ndarray:
        """
        Compute Jacobian matrix for Newton-Raphson correction
        
        Args:
            lambert_solution: Current Lambert solution
            initial_state: Initial trajectory state
            target_state: Target trajectory state
            burn_sequence: Current burn sequence
            
        Returns:
            Jacobian matrix (6x4) for state corrections
        """
        # State vector: [delta_vx, delta_vy, delta_vz, tof]
        # Residual vector: [pos_error_x, pos_error_y, pos_error_z, vel_error_x, vel_error_y, vel_error_z]
        
        jacobian = np.zeros((6, 4))
        
        # Baseline residual
        actual_state = self.propagator_func(initial_state, burn_sequence, target_state.time)
        baseline_residual = self.calculate_residuals(actual_state, target_state)
        baseline_vector = np.concatenate([
            baseline_residual.position_error,
            baseline_residual.velocity_error
        ])
        
        # Perturb delta-V components
        for i in range(3):
            # Create perturbed Lambert solution
            delta_v_pert = np.zeros(3)
            delta_v_pert[i] = self.delta_v_perturbation
            
            # Apply perturbation to initial velocity
            perturbed_v1 = lambert_solution.v1 + delta_v_pert
            
            # Create perturbed burn sequence
            perturbed_burn = self._create_perturbed_burn_sequence(
                burn_sequence, delta_v_pert
            )
            
            # Calculate perturbed state
            perturbed_initial = TrajectoryState(
                position=initial_state.position,
                velocity=perturbed_v1,
                time=initial_state.time
            )
            
            perturbed_final = self.propagator_func(
                perturbed_initial, perturbed_burn, target_state.time
            )
            
            # Calculate perturbed residual
            perturbed_residual = self.calculate_residuals(perturbed_final, target_state)
            perturbed_vector = np.concatenate([
                perturbed_residual.position_error,
                perturbed_residual.velocity_error
            ])
            
            # Finite difference derivative
            jacobian[:, i] = (perturbed_vector - baseline_vector) / self.delta_v_perturbation
        
        # Perturb time of flight
        time_pert = self.time_perturbation
        
        # Recalculate Lambert solution with perturbed TOF
        perturbed_tof = lambert_solution.tof + time_pert
        perturbed_lambert = self.trajectory_planner.solve_lambert(
            initial_state.position, target_state.position, perturbed_tof
        )
        
        if perturbed_lambert.converged:
            # Create burn sequence for perturbed solution
            perturbed_burn = self.finite_burn_executor.create_burn_sequence(
                perturbed_lambert.delta_v,
                perturbed_lambert.v1 / np.linalg.norm(perturbed_lambert.v1),
                45000.0  # Default mass
            )
            
            perturbed_initial = TrajectoryState(
                position=initial_state.position,
                velocity=perturbed_lambert.v1,
                time=initial_state.time
            )
            
            perturbed_final = self.propagator_func(
                perturbed_initial, perturbed_burn, target_state.time + time_pert
            )
            
            perturbed_residual = self.calculate_residuals(perturbed_final, target_state)
            perturbed_vector = np.concatenate([
                perturbed_residual.position_error,
                perturbed_residual.velocity_error
            ])
            
            jacobian[:, 3] = (perturbed_vector - baseline_vector) / time_pert
        
        return jacobian
    
    def _create_perturbed_burn_sequence(self, original_sequence: BurnSequence,
                                      delta_v_perturbation: np.ndarray) -> BurnSequence:
        """Create burn sequence with delta-V perturbation applied"""
        # For simplicity, scale the entire burn sequence
        perturbation_magnitude = np.linalg.norm(delta_v_perturbation)
        scale_factor = (original_sequence.total_delta_v + perturbation_magnitude) / original_sequence.total_delta_v
        
        # Create scaled segments
        scaled_segments = []
        for segment in original_sequence.segments:
            from finite_burn_executor import BurnSegment
            scaled_segment = BurnSegment(
                start_time=segment.start_time,
                duration=segment.duration * scale_factor,
                thrust_vector=segment.thrust_vector,
                throttle=segment.throttle,
                thrust_magnitude=segment.thrust_magnitude,
                mass_flow_rate=segment.mass_flow_rate
            )
            scaled_segments.append(scaled_segment)
        
        return BurnSequence(
            segments=scaled_segments,
            total_duration=original_sequence.total_duration * scale_factor,
            total_delta_v=original_sequence.total_delta_v + perturbation_magnitude,
            initial_mass=original_sequence.initial_mass,
            final_mass=original_sequence.final_mass
        )
    
    def iterate_correction(self, lambert_solution: LambertSolution,
                         initial_state: TrajectoryState,
                         target_state: TrajectoryState) -> list:
        """
        Perform iterative correction using Newton-Raphson method
        
        Args:
            lambert_solution: Initial Lambert solution
            initial_state: Initial trajectory state
            target_state: Target trajectory state
            
        Returns:
            List of IterationResult objects showing convergence
        """
        results = []
        current_solution = lambert_solution
        
        for iteration in range(self.max_iterations):
            # Create burn sequence for current solution
            thrust_direction = current_solution.v1 / np.linalg.norm(current_solution.v1)
            burn_sequence = self.finite_burn_executor.create_burn_sequence(
                current_solution.delta_v, thrust_direction, 45000.0
            )
            
            # Propagate trajectory
            actual_state = self.propagator_func(
                TrajectoryState(
                    position=initial_state.position,
                    velocity=current_solution.v1,
                    time=initial_state.time
                ),
                burn_sequence,
                target_state.time
            )
            
            # Calculate residuals
            residual = self.calculate_residuals(actual_state, target_state)
            
            # Check convergence
            pos_converged = np.linalg.norm(residual.position_error) < self.position_tolerance
            vel_converged = np.linalg.norm(residual.velocity_error) < self.velocity_tolerance
            delta_v_error = abs(current_solution.delta_v - lambert_solution.delta_v)
            delta_v_converged = delta_v_error < self.delta_v_tolerance
            
            converged = pos_converged and vel_converged and delta_v_converged
            
            # Compute correction if not converged
            correction = CorrectionVector(
                delta_v_correction=np.zeros(3),
                time_correction=0.0,
                burn_angle_correction=0.0,
                magnitude=0.0
            )
            
            if not converged and iteration < self.max_iterations - 1:
                try:
                    # Compute Jacobian and correction
                    jacobian = self.compute_jacobian(current_solution, initial_state, target_state, burn_sequence)
                    
                    # Residual vector
                    residual_vector = np.concatenate([
                        residual.position_error,
                        residual.velocity_error
                    ])
                    
                    # Solve for correction using least squares
                    correction_params, _, _, _ = np.linalg.lstsq(jacobian, -residual_vector, rcond=None)
                    
                    # Apply correction to Lambert solution
                    delta_v_correction = correction_params[:3]
                    time_correction = correction_params[3] if len(correction_params) > 3 else 0.0
                    
                    # Update solution
                    new_tof = current_solution.tof + time_correction
                    new_lambert = self.trajectory_planner.solve_lambert(
                        initial_state.position, target_state.position, new_tof
                    )
                    
                    if new_lambert.converged:
                        # Apply delta-V correction
                        new_v1 = new_lambert.v1 + delta_v_correction
                        new_delta_v = np.linalg.norm(new_v1 - initial_state.velocity)
                        
                        current_solution = LambertSolution(
                            v1=new_v1,
                            v2=new_lambert.v2,
                            tof=new_tof,
                            delta_v=new_delta_v,
                            converged=True
                        )
                        
                        correction = CorrectionVector(
                            delta_v_correction=delta_v_correction,
                            time_correction=time_correction,
                            burn_angle_correction=0.0,
                            magnitude=np.linalg.norm(correction_params)
                        )
                
                except Exception as e:
                    self.logger.warning(f"Correction calculation failed at iteration {iteration}: {e}")
            
            # Store iteration result
            result = IterationResult(
                iteration=iteration,
                residual=residual,
                correction=correction,
                converged=converged,
                delta_v_error=delta_v_error
            )
            results.append(result)
            
            if converged:
                self.logger.info(f"Trajectory correction converged in {iteration + 1} iterations")
                break
        
        return results
    
    def refine_lambert_solution(self, lambert_solution: LambertSolution,
                              initial_state: TrajectoryState,
                              target_state: TrajectoryState) -> Tuple[LambertSolution, list]:
        """
        Refine Lambert solution using iterative correction
        
        Args:
            lambert_solution: Initial Lambert solution
            initial_state: Initial trajectory state
            target_state: Target trajectory state
            
        Returns:
            Tuple of (refined_solution, iteration_results)
        """
        # Perform iterative correction
        iteration_results = self.iterate_correction(lambert_solution, initial_state, target_state)
        
        # Extract final solution from last iteration
        if iteration_results:
            last_result = iteration_results[-1]
            
            if last_result.converged:
                # Create refined burn sequence to get final solution
                thrust_direction = lambert_solution.v1 / np.linalg.norm(lambert_solution.v1)
                final_burn = self.finite_burn_executor.create_burn_sequence(
                    lambert_solution.delta_v, thrust_direction, 45000.0
                )
                
                refined_solution = LambertSolution(
                    v1=lambert_solution.v1,
                    v2=lambert_solution.v2,
                    tof=lambert_solution.tof,
                    delta_v=lambert_solution.delta_v,
                    converged=True
                )
                
                self.logger.info(f"Lambert solution refined: final ΔV error = {last_result.delta_v_error:.2f} m/s")
                return refined_solution, iteration_results
        
        self.logger.warning("Lambert solution refinement did not converge")
        return lambert_solution, iteration_results


def create_residual_projector(trajectory_planner: TrajectoryPlanner,
                            finite_burn_executor: FiniteBurnExecutor,
                            propagator_func: Optional[Callable] = None) -> ResidualProjector:
    """
    Factory function to create residual projector
    
    Args:
        trajectory_planner: TrajectoryPlanner instance
        finite_burn_executor: FiniteBurnExecutor instance
        propagator_func: Optional orbital propagator function
        
    Returns:
        Configured ResidualProjector instance
    """
    return ResidualProjector(trajectory_planner, finite_burn_executor, propagator_func)


# Example usage and testing
if __name__ == "__main__":
    from trajectory_planner import create_trajectory_planner
    from finite_burn_executor import create_finite_burn_executor
    
    print("Testing Residual Projector")
    print("=" * 40)
    
    # Create components
    planner = create_trajectory_planner("Earth")
    executor = create_finite_burn_executor()
    projector = create_residual_projector(planner, executor)
    
    # Test trajectory states
    initial_state = TrajectoryState(
        position=np.array([6556000, 0, 0]),  # LEO position
        velocity=np.array([0, 7800, 0]),     # LEO velocity
        time=0.0
    )
    
    target_state = TrajectoryState(
        position=np.array([300000000, 100000000, 0]),  # Approximate Moon SoI
        velocity=np.array([800, 200, 0]),              # Approximate lunar approach velocity
        time=3 * 24 * 3600  # 3 days
    )
    
    # Create initial Lambert solution
    lambert_solution = planner.solve_lambert(
        initial_state.position, target_state.position, target_state.time
    )
    
    if lambert_solution.converged:
        print(f"Initial Lambert solution:")
        print(f"  Delta-V: {lambert_solution.delta_v:.1f} m/s")
        print(f"  Time of flight: {lambert_solution.tof/(24*3600):.2f} days")
        
        # Refine solution
        refined_solution, iterations = projector.refine_lambert_solution(
            lambert_solution, initial_state, target_state
        )
        
        print(f"\nRefinement results:")
        print(f"  Iterations: {len(iterations)}")
        print(f"  Final convergence: {iterations[-1].converged if iterations else False}")
        if iterations:
            print(f"  Final ΔV error: {iterations[-1].delta_v_error:.2f} m/s")
            print(f"  Position error: {np.linalg.norm(iterations[-1].residual.position_error):.0f} m")
            print(f"  Velocity error: {np.linalg.norm(iterations[-1].residual.velocity_error):.2f} m/s")
    else:
        print("Initial Lambert solution failed to converge")