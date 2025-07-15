"""
Unified Trajectory System
Professor v42: Integrated architecture with Lambert+Finite Burn+Residual Projection

This module implements the comprehensive trajectory planning system that replaces
the previous parameter-tuning approach with systematic optimization architecture.
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

# Import our new components
from trajectory_planner import TrajectoryPlanner, LambertSolution, TrajectoryState, create_trajectory_planner
from finite_burn_executor import FiniteBurnExecutor, BurnSequence, FiniteBurnResult, create_finite_burn_executor
from residual_projector import ResidualProjector, IterationResult, create_residual_projector
from launch_window_preprocessor import LaunchWindowPreprocessor, LaunchOpportunity, create_launch_window_preprocessor
from engine import get_engine_model


@dataclass
class MissionParameters:
    """Mission configuration parameters"""
    launch_site_lat: float = 28.5      # Launch site latitude [degrees]
    launch_site_lon: float = -80.6     # Launch site longitude [degrees]
    parking_orbit_altitude: float = 185000  # LEO altitude [m]
    target_inclination: float = 28.5   # Target orbital inclination [degrees]
    transfer_time_days: float = 3.0    # Nominal transfer time [days]
    spacecraft_mass: float = 45000     # Initial spacecraft mass [kg]
    engine_stage: str = "S-IVB"        # Engine stage for TLI


@dataclass
class SystemState:
    """Current system state"""
    position: np.ndarray        # Current position [m]
    velocity: np.ndarray        # Current velocity [m/s]
    mass: float                # Current mass [kg]
    time: float               # Mission time [s]
    phase: str               # Mission phase


@dataclass
class OptimizationResult:
    """Complete trajectory optimization result"""
    lambert_solution: LambertSolution
    burn_sequence: BurnSequence
    finite_burn_result: FiniteBurnResult
    iteration_results: List[IterationResult]
    launch_opportunity: Optional[LaunchOpportunity]
    converged: bool
    total_delta_v: float
    delta_v_error: float
    system_efficiency: float


class UnifiedTrajectorySystem:
    """
    Unified trajectory planning and execution system
    
    Implements Professor v42's comprehensive architecture:
    1. Launch Window Preprocessor for plane-targeting
    2. TrajectoryPlanner with Lambert solver
    3. FiniteBurnExecutor for realistic burn modeling
    4. ResidualProjector for iterative correction
    5. Integrated feedback loops for convergence
    """
    
    def __init__(self, mission_params: MissionParameters):
        """
        Initialize unified trajectory system
        
        Args:
            mission_params: Mission configuration parameters
        """
        self.mission_params = mission_params
        self.logger = logging.getLogger(__name__)
        
        # Initialize subsystems
        self.trajectory_planner = create_trajectory_planner("Earth")
        self.engine_model = get_engine_model()
        self.finite_burn_executor = create_finite_burn_executor(self.engine_model)
        self.residual_projector = create_residual_projector(
            self.trajectory_planner, self.finite_burn_executor
        )
        self.launch_window_preprocessor = create_launch_window_preprocessor(
            mission_params.launch_site_lat, mission_params.launch_site_lon
        )
        
        # System configuration
        self.max_optimization_iterations = 6  # Professor v42: 4-6 iterations
        self.convergence_tolerance = 5.0      # ±5 m/s delta-V tolerance
        
        self.logger.info("Unified Trajectory System initialized with Professor v42 architecture")
    
    def find_optimal_launch_window(self, start_date: datetime, 
                                 search_duration_days: int = 7) -> Optional[LaunchOpportunity]:
        """
        Find optimal launch window with plane-targeting
        
        Args:
            start_date: Search start date
            search_duration_days: Duration to search [days]
            
        Returns:
            Optimal launch opportunity or None
        """
        self.logger.info(f"Searching for optimal launch window from {start_date}")
        
        # Generate launch plan with RAAN alignment
        launch_plan = self.launch_window_preprocessor.generate_launch_plan(
            start_date, search_duration_days
        )
        
        # Check if we have a viable window
        if not launch_plan['recommendations']['proceed_with_optimal']:
            self.logger.warning("No optimal launch window found within RAAN alignment criteria")
            return None
        
        # Find detailed opportunities
        opportunities = self.launch_window_preprocessor.find_raan_alignment_windows(
            start_date, search_duration_days, 65.0, self.mission_params.target_inclination, 0.5
        )
        
        result = self.launch_window_preprocessor.filter_optimal_windows(opportunities, 10)
        
        if result.optimal_window:
            self.logger.info(f"Optimal launch window found: {result.optimal_window.start_time}, "
                           f"RAAN error: {result.optimal_window.raan_error:.2f}°, "
                           f"ΔV penalty: {result.optimal_window.delta_v_penalty:.1f} m/s")
            return result.optimal_window
        
        return None
    
    def plan_trajectory(self, initial_state: SystemState, 
                       target_position: np.ndarray,
                       launch_opportunity: Optional[LaunchOpportunity] = None) -> OptimizationResult:
        """
        Plan complete trajectory using integrated system
        
        Args:
            initial_state: Initial system state
            target_position: Target position (Moon SoI boundary)
            launch_opportunity: Optional launch window constraint
            
        Returns:
            Complete optimization result
        """
        self.logger.info("Starting integrated trajectory planning")
        
        # Convert system state to trajectory state
        traj_initial = TrajectoryState(
            position=initial_state.position,
            velocity=initial_state.velocity,
            time=initial_state.time
        )
        
        # Calculate target state
        transfer_time = self.mission_params.transfer_time_days * 24 * 3600
        target_state = TrajectoryState(
            position=target_position,
            velocity=np.array([1000, 500, 0]),  # Approximate lunar approach velocity
            time=initial_state.time + transfer_time
        )
        
        # Step 1: Initial Lambert solution
        self.logger.info("Step 1: Computing initial Lambert solution")
        lambert_solution = self.trajectory_planner.solve_lambert(
            traj_initial.position, target_state.position, transfer_time
        )
        
        if not lambert_solution.converged:
            self.logger.error("Initial Lambert solution failed to converge")
            return self._create_failed_result()
        
        self.logger.info(f"Initial Lambert solution: ΔV = {lambert_solution.delta_v:.1f} m/s")
        
        # Step 2: Create finite burn sequence
        self.logger.info("Step 2: Creating finite burn sequence")
        thrust_direction = lambert_solution.v1 / np.linalg.norm(lambert_solution.v1)
        
        # Use enhanced engine model for optimal throttling
        optimal_throttle = self.engine_model.get_optimal_throttle_for_delta_v(
            self.mission_params.engine_stage,
            self.mission_params.parking_orbit_altitude,
            lambert_solution.delta_v,
            800.0,  # Approximate burn time
            initial_state.mass
        )
        
        burn_sequence = self.finite_burn_executor.create_burn_sequence(
            lambert_solution.delta_v,
            thrust_direction,
            initial_state.mass,
            self.mission_params.engine_stage,
            10,  # 10 segments for fine discretization
            self.mission_params.parking_orbit_altitude
        )
        
        self.logger.info(f"Burn sequence created: {len(burn_sequence.segments)} segments, "
                        f"{burn_sequence.total_duration:.1f}s duration, "
                        f"optimal throttle: {optimal_throttle:.1%}")
        
        # Step 3: Execute finite burn simulation
        self.logger.info("Step 3: Simulating finite burn execution")
        initial_state_dict = {
            'position': initial_state.position,
            'velocity': initial_state.velocity,
            'mass': initial_state.mass
        }
        
        finite_burn_result = self.finite_burn_executor.execute_burn_sequence(
            burn_sequence, initial_state_dict
        )
        
        self.logger.info(f"Finite burn simulation: achieved ΔV = {finite_burn_result.achieved_delta_v:.1f} m/s, "
                        f"efficiency = {finite_burn_result.burn_efficiency:.3f}, "
                        f"loss = {finite_burn_result.finite_burn_loss:.1f} m/s")
        
        # Step 4: Iterative correction using residual projection
        self.logger.info("Step 4: Starting iterative trajectory correction")
        refined_solution, iteration_results = self.residual_projector.refine_lambert_solution(
            lambert_solution, traj_initial, target_state
        )
        
        # Calculate final system performance
        final_converged = (iteration_results[-1].converged if iteration_results 
                          else finite_burn_result.converged)
        
        final_delta_v_error = (iteration_results[-1].delta_v_error if iteration_results 
                              else abs(finite_burn_result.achieved_delta_v - lambert_solution.delta_v))
        
        # System efficiency: combination of burn efficiency and convergence
        burn_efficiency = finite_burn_result.burn_efficiency
        convergence_efficiency = 1.0 - min(1.0, final_delta_v_error / self.convergence_tolerance)
        system_efficiency = (burn_efficiency + convergence_efficiency) / 2
        
        # Apply plane-targeting penalty if launch window provided
        if launch_opportunity:
            plane_change_penalty = launch_opportunity.delta_v_penalty
            system_efficiency *= (1.0 - plane_change_penalty / 200.0)  # Normalize by 200 m/s max
        
        self.logger.info(f"Trajectory optimization complete: "
                        f"converged = {final_converged}, "
                        f"ΔV error = {final_delta_v_error:.2f} m/s, "
                        f"system efficiency = {system_efficiency:.3f}")
        
        return OptimizationResult(
            lambert_solution=refined_solution,
            burn_sequence=burn_sequence,
            finite_burn_result=finite_burn_result,
            iteration_results=iteration_results,
            launch_opportunity=launch_opportunity,
            converged=final_converged,
            total_delta_v=finite_burn_result.achieved_delta_v,
            delta_v_error=final_delta_v_error,
            system_efficiency=system_efficiency
        )
    
    def optimize_complete_mission(self, start_date: datetime,
                                initial_state: SystemState) -> Dict:
        """
        Complete mission optimization from launch window to trajectory
        
        Args:
            start_date: Mission start date
            initial_state: Initial spacecraft state
            
        Returns:
            Complete mission optimization results
        """
        self.logger.info("Starting complete mission optimization")
        
        # Step 1: Find optimal launch window
        launch_opportunity = self.find_optimal_launch_window(start_date, 7)
        if not launch_opportunity:
            self.logger.warning("No suitable launch window found")
            return {'success': False, 'reason': 'No suitable launch window'}
        
        # Step 2: Calculate Moon SoI target position
        target_position = self.trajectory_planner.calculate_moon_soi_target(
            initial_state.time, initial_state.time + 3 * 24 * 3600
        )
        
        # Step 3: Optimize trajectory
        optimization_result = self.plan_trajectory(
            initial_state, target_position, launch_opportunity
        )
        
        # Step 4: Generate mission summary
        mission_summary = {
            'success': optimization_result.converged,
            'launch_window': {
                'time': launch_opportunity.start_time,
                'azimuth': launch_opportunity.launch_azimuth,
                'raan_error': launch_opportunity.raan_error,
                'beta_angle': launch_opportunity.beta_angle
            },
            'trajectory': {
                'total_delta_v': optimization_result.total_delta_v,
                'delta_v_error': optimization_result.delta_v_error,
                'burn_duration': optimization_result.burn_sequence.total_duration,
                'burn_segments': len(optimization_result.burn_sequence.segments),
                'finite_burn_loss': optimization_result.finite_burn_result.finite_burn_loss
            },
            'optimization': {
                'iterations': len(optimization_result.iteration_results),
                'converged': optimization_result.converged,
                'system_efficiency': optimization_result.system_efficiency
            },
            'performance_metrics': {
                'meets_professor_criteria': (
                    optimization_result.delta_v_error <= 5.0 and  # ±5 m/s requirement
                    abs(launch_opportunity.raan_error) <= 5.0 and  # ±5° RAAN requirement
                    optimization_result.finite_burn_result.finite_burn_loss <= 100.0  # <100 m/s loss
                ),
                'expected_success_rate': min(0.99, optimization_result.system_efficiency * 1.1)
            }
        }
        
        # Log final results
        if mission_summary['success']:
            self.logger.info("Mission optimization SUCCESS:")
            self.logger.info(f"  Launch: {launch_opportunity.start_time}")
            self.logger.info(f"  Total ΔV: {optimization_result.total_delta_v:.1f} m/s")
            self.logger.info(f"  ΔV Error: ±{optimization_result.delta_v_error:.1f} m/s")
            self.logger.info(f"  RAAN Error: ±{launch_opportunity.raan_error:.1f}°")
            self.logger.info(f"  System Efficiency: {optimization_result.system_efficiency:.1%}")
            self.logger.info(f"  Meets Professor Criteria: {mission_summary['performance_metrics']['meets_professor_criteria']}")
        else:
            self.logger.warning("Mission optimization FAILED")
        
        return mission_summary
    
    def _create_failed_result(self) -> OptimizationResult:
        """Create failed optimization result"""
        return OptimizationResult(
            lambert_solution=LambertSolution(
                v1=np.zeros(3), v2=np.zeros(3), tof=0, delta_v=float('inf'), converged=False
            ),
            burn_sequence=BurnSequence(
                segments=[], total_duration=0, total_delta_v=0, initial_mass=0, final_mass=0
            ),
            finite_burn_result=FiniteBurnResult(
                achieved_delta_v=0, burn_efficiency=0, finite_burn_loss=0, 
                execution_time=0, converged=False
            ),
            iteration_results=[],
            launch_opportunity=None,
            converged=False,
            total_delta_v=0,
            delta_v_error=float('inf'),
            system_efficiency=0.0
        )


def create_unified_trajectory_system(mission_params: Optional[MissionParameters] = None) -> UnifiedTrajectorySystem:
    """
    Factory function to create unified trajectory system
    
    Args:
        mission_params: Optional mission parameters (uses defaults if None)
        
    Returns:
        Configured UnifiedTrajectorySystem instance
    """
    if mission_params is None:
        mission_params = MissionParameters()
    
    return UnifiedTrajectorySystem(mission_params)


# Example usage and testing
if __name__ == "__main__":
    print("Testing Unified Trajectory System")
    print("=" * 50)
    
    # Create mission parameters
    mission_params = MissionParameters(
        launch_site_lat=28.5,
        launch_site_lon=-80.6,
        parking_orbit_altitude=185000,
        target_inclination=28.5,
        transfer_time_days=3.0,
        spacecraft_mass=45000,
        engine_stage="S-IVB"
    )
    
    # Create unified system
    unified_system = create_unified_trajectory_system(mission_params)
    
    # Define initial state
    initial_state = SystemState(
        position=np.array([6556000, 0, 0]),  # LEO position
        velocity=np.array([0, 7800, 0]),     # LEO velocity
        mass=45000,                          # Initial mass
        time=0.0,                           # Mission start
        phase="LEO"
    )
    
    # Run complete mission optimization
    start_date = datetime.now()
    mission_result = unified_system.optimize_complete_mission(start_date, initial_state)
    
    print("\nMission Optimization Results:")
    print(f"Success: {mission_result['success']}")
    
    if mission_result['success']:
        print(f"\nLaunch Window:")
        print(f"  Time: {mission_result['launch_window']['time']}")
        print(f"  Azimuth: {mission_result['launch_window']['azimuth']:.1f}°")
        print(f"  RAAN Error: ±{mission_result['launch_window']['raan_error']:.2f}°")
        
        print(f"\nTrajectory:")
        print(f"  Total ΔV: {mission_result['trajectory']['total_delta_v']:.1f} m/s")
        print(f"  ΔV Error: ±{mission_result['trajectory']['delta_v_error']:.1f} m/s")
        print(f"  Burn Duration: {mission_result['trajectory']['burn_duration']:.1f} s")
        print(f"  Finite Burn Loss: {mission_result['trajectory']['finite_burn_loss']:.1f} m/s")
        
        print(f"\nOptimization:")
        print(f"  Iterations: {mission_result['optimization']['iterations']}")
        print(f"  System Efficiency: {mission_result['optimization']['system_efficiency']:.1%}")
        
        print(f"\nProfessor v42 Criteria:")
        print(f"  Meets Requirements: {mission_result['performance_metrics']['meets_professor_criteria']}")
        print(f"  Expected Success Rate: {mission_result['performance_metrics']['expected_success_rate']:.1%}")
    else:
        print(f"Failure Reason: {mission_result.get('reason', 'Unknown')}")