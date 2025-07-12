"""
Finite Burn Executor Module
Professor v42: Convert impulsive ΔV to realistic finite burn sequences

This module addresses the 3-5% finite burn losses ignored by impulsive assumptions
by implementing segmented burn sequences with thrust curve integration.
"""

import numpy as np
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass
import logging
from vehicle import Vector3

# Physical constants
STANDARD_GRAVITY = 9.80665  # m/s²


@dataclass
class BurnSegment:
    """Individual burn segment parameters"""
    start_time: float      # Segment start time relative to burn start [s]
    duration: float        # Segment duration [s]
    thrust_vector: np.ndarray  # Thrust direction (unit vector)
    throttle: float        # Throttle setting (0.0 to 1.0)
    thrust_magnitude: float    # Expected thrust magnitude [N]
    mass_flow_rate: float      # Expected mass flow rate [kg/s]


@dataclass
class BurnSequence:
    """Complete burn sequence definition"""
    segments: List[BurnSegment]
    total_duration: float      # Total burn duration [s]
    total_delta_v: float       # Total expected delta-V [m/s]
    initial_mass: float        # Initial spacecraft mass [kg]
    final_mass: float          # Final spacecraft mass [kg]


@dataclass
class FiniteBurnResult:
    """Results from finite burn execution"""
    achieved_delta_v: float    # Actual delta-V achieved [m/s]
    burn_efficiency: float     # Ratio of achieved to theoretical ΔV
    finite_burn_loss: float    # ΔV loss due to finite burn [m/s]
    execution_time: float      # Actual execution time [s]
    converged: bool           # Whether burn achieved targets


class FiniteBurnExecutor:
    """
    Finite burn executor for realistic propulsion modeling
    
    Converts impulsive delta-V commands into finite burn sequences,
    accounting for:
    - Thrust vector changes during burn
    - Mass depletion effects
    - Engine throttling constraints
    - Gravity losses during burn
    """
    
    def __init__(self, engine_model=None):
        """
        Initialize finite burn executor
        
        Args:
            engine_model: Engine performance model for thrust/Isp calculations
        """
        self.engine_model = engine_model
        self.logger = logging.getLogger(__name__)
        
        # Default engine parameters (if no model provided)
        self.default_thrust = 1000000  # 1 MN default thrust
        self.default_isp = 450  # 450s default specific impulse
        
    def create_burn_sequence(self, delta_v_impulsive: float, 
                           thrust_direction: np.ndarray,
                           initial_mass: float,
                           engine_stage: str = "S-IVB",
                           num_segments: int = 10,
                           altitude: float = 185000) -> BurnSequence:
        """
        Create finite burn sequence from impulsive delta-V requirement
        
        Args:
            delta_v_impulsive: Required impulsive delta-V [m/s]
            thrust_direction: Desired thrust direction (unit vector)
            initial_mass: Initial spacecraft mass [kg]
            engine_stage: Engine stage identifier
            num_segments: Number of burn segments for discretization
            altitude: Current altitude for engine performance [m]
            
        Returns:
            BurnSequence object with detailed burn plan
        """
        # Get engine performance parameters
        if self.engine_model:
            max_thrust = self.engine_model.get_thrust(engine_stage, altitude, 1.0)
            isp = self.engine_model.get_specific_impulse(engine_stage, altitude, 1.0)
        else:
            max_thrust = self.default_thrust
            isp = self.default_isp
            
        # Calculate required propellant mass using rocket equation
        # Δv = Isp * g₀ * ln(m₀/m₁)
        mass_ratio = np.exp(delta_v_impulsive / (isp * STANDARD_GRAVITY))
        final_mass = initial_mass / mass_ratio
        propellant_mass = initial_mass - final_mass
        
        # Calculate total burn time
        mass_flow_rate = max_thrust / (isp * STANDARD_GRAVITY)
        total_burn_time = propellant_mass / mass_flow_rate
        
        # Create burn segments
        segments = []
        segment_duration = total_burn_time / num_segments
        
        for i in range(num_segments):
            # Calculate segment properties
            segment_start_time = i * segment_duration
            
            # Mass at segment start (accounting for previous propellant consumption)
            consumed_mass = mass_flow_rate * segment_start_time
            segment_mass = initial_mass - consumed_mass
            
            # Thrust magnitude (could vary with throttle in future)
            thrust_magnitude = max_thrust
            throttle = 1.0  # Full throttle for now
            
            # Create burn segment
            segment = BurnSegment(
                start_time=segment_start_time,
                duration=segment_duration,
                thrust_vector=np.array(thrust_direction) / np.linalg.norm(thrust_direction),
                throttle=throttle,
                thrust_magnitude=thrust_magnitude,
                mass_flow_rate=mass_flow_rate
            )
            segments.append(segment)
        
        return BurnSequence(
            segments=segments,
            total_duration=total_burn_time,
            total_delta_v=delta_v_impulsive,
            initial_mass=initial_mass,
            final_mass=final_mass
        )
    
    def create_variable_thrust_sequence(self, delta_v_impulsive: float,
                                      thrust_direction: np.ndarray,
                                      initial_mass: float,
                                      thrust_profile: Dict[float, float],
                                      engine_stage: str = "S-IVB",
                                      altitude: float = 185000) -> BurnSequence:
        """
        Create burn sequence with variable thrust profile
        
        Args:
            delta_v_impulsive: Required impulsive delta-V [m/s]
            thrust_direction: Desired thrust direction (unit vector)
            initial_mass: Initial spacecraft mass [kg]
            thrust_profile: Dict mapping time ratios (0-1) to throttle settings
            engine_stage: Engine stage identifier
            altitude: Current altitude [m]
            
        Returns:
            BurnSequence with variable thrust profile
        """
        # Get base engine performance
        if self.engine_model:
            max_thrust = self.engine_model.get_thrust(engine_stage, altitude, 1.0)
            base_isp = self.engine_model.get_specific_impulse(engine_stage, altitude, 1.0)
        else:
            max_thrust = self.default_thrust
            base_isp = self.default_isp
        
        # Estimate burn time using average throttle
        avg_throttle = np.mean(list(thrust_profile.values()))
        avg_thrust = max_thrust * avg_throttle
        
        # Use variable Isp if available
        if self.engine_model and hasattr(self.engine_model, 'get_specific_impulse'):
            avg_isp = self.engine_model.get_specific_impulse(engine_stage, altitude, avg_throttle)
        else:
            avg_isp = base_isp * (0.95 + 0.05 * avg_throttle)  # Simple throttle penalty
        
        # Calculate propellant requirements
        mass_ratio = np.exp(delta_v_impulsive / (avg_isp * STANDARD_GRAVITY))
        final_mass = initial_mass / mass_ratio
        propellant_mass = initial_mass - final_mass
        
        # Estimate total burn time
        avg_mass_flow = avg_thrust / (avg_isp * STANDARD_GRAVITY)
        total_burn_time = propellant_mass / avg_mass_flow
        
        # Create segments based on thrust profile
        segments = []
        time_points = sorted(thrust_profile.keys())
        
        for i in range(len(time_points) - 1):
            # Segment timing
            start_ratio = time_points[i]
            end_ratio = time_points[i + 1]
            
            segment_start_time = start_ratio * total_burn_time
            segment_duration = (end_ratio - start_ratio) * total_burn_time
            
            # Throttle setting (linear interpolation between points)
            start_throttle = thrust_profile[start_ratio]
            end_throttle = thrust_profile[end_ratio]
            avg_throttle_segment = (start_throttle + end_throttle) / 2
            
            # Segment thrust and Isp
            segment_thrust = max_thrust * avg_throttle_segment
            if self.engine_model:
                segment_isp = self.engine_model.get_specific_impulse(
                    engine_stage, altitude, avg_throttle_segment)
            else:
                segment_isp = base_isp * (0.95 + 0.05 * avg_throttle_segment)
            
            segment_mass_flow = segment_thrust / (segment_isp * STANDARD_GRAVITY)
            
            # Create segment
            segment = BurnSegment(
                start_time=segment_start_time,
                duration=segment_duration,
                thrust_vector=np.array(thrust_direction) / np.linalg.norm(thrust_direction),
                throttle=avg_throttle_segment,
                thrust_magnitude=segment_thrust,
                mass_flow_rate=segment_mass_flow
            )
            segments.append(segment)
        
        return BurnSequence(
            segments=segments,
            total_duration=total_burn_time,
            total_delta_v=delta_v_impulsive,
            initial_mass=initial_mass,
            final_mass=final_mass
        )
    
    def execute_burn_sequence(self, burn_sequence: BurnSequence,
                            initial_state: Dict,
                            gravity_field_func=None) -> FiniteBurnResult:
        """
        Execute burn sequence and calculate achieved delta-V
        
        Args:
            burn_sequence: BurnSequence to execute
            initial_state: Initial spacecraft state (position, velocity, mass)
            gravity_field_func: Function to calculate gravity acceleration
            
        Returns:
            FiniteBurnResult with execution results
        """
        # Extract initial conditions
        position = np.array(initial_state.get('position', [0, 0, 0]))
        velocity = np.array(initial_state.get('velocity', [0, 0, 0]))
        mass = initial_state.get('mass', burn_sequence.initial_mass)
        
        initial_velocity = velocity.copy()
        
        # Integrate through burn sequence
        for segment in burn_sequence.segments:
            # Calculate average acceleration during segment
            avg_mass = mass - (segment.mass_flow_rate * segment.duration / 2)
            thrust_acceleration = segment.thrust_magnitude / avg_mass
            
            # Apply thrust impulse
            thrust_impulse = thrust_acceleration * segment.duration
            velocity += segment.thrust_vector * thrust_impulse
            
            # Account for gravity losses (if gravity function provided)
            if gravity_field_func:
                gravity_acc = gravity_field_func(position)
                gravity_impulse = gravity_acc * segment.duration
                velocity += gravity_impulse
            
            # Update mass
            mass -= segment.mass_flow_rate * segment.duration
            
            # Update position (simplified - assume constant velocity during segment)
            position += velocity * segment.duration
        
        # Calculate results
        achieved_delta_v = np.linalg.norm(velocity - initial_velocity)
        burn_efficiency = achieved_delta_v / burn_sequence.total_delta_v
        finite_burn_loss = burn_sequence.total_delta_v - achieved_delta_v
        
        # Convergence check (within 5% of target)
        converged = abs(achieved_delta_v - burn_sequence.total_delta_v) < 0.05 * burn_sequence.total_delta_v
        
        return FiniteBurnResult(
            achieved_delta_v=achieved_delta_v,
            burn_efficiency=burn_efficiency,
            finite_burn_loss=finite_burn_loss,
            execution_time=burn_sequence.total_duration,
            converged=converged
        )
    
    def optimize_burn_segments(self, delta_v_target: float,
                             thrust_direction: np.ndarray,
                             initial_mass: float,
                             constraints: Dict,
                             engine_stage: str = "S-IVB") -> BurnSequence:
        """
        Optimize burn segmentation for minimum finite burn losses
        
        Args:
            delta_v_target: Target delta-V [m/s]
            thrust_direction: Desired thrust direction
            initial_mass: Initial spacecraft mass [kg]
            constraints: Burn constraints (max_duration, min_throttle, etc.)
            engine_stage: Engine stage identifier
            
        Returns:
            Optimized BurnSequence
        """
        max_duration = constraints.get('max_duration', 1000)  # seconds
        min_throttle = constraints.get('min_throttle', 0.6)   # 60% minimum
        max_segments = constraints.get('max_segments', 20)    # Maximum segments
        
        best_sequence = None
        best_efficiency = 0.0
        
        # Try different segment counts and throttle profiles
        for num_segments in range(5, max_segments + 1, 2):
            # Try constant throttle first
            sequence = self.create_burn_sequence(
                delta_v_target, thrust_direction, initial_mass,
                engine_stage, num_segments
            )
            
            # Evaluate efficiency (simplified - would use full integration in practice)
            # For now, assume efficiency decreases with longer burns due to gravity losses
            gravity_loss_factor = 1.0 - (sequence.total_duration / 3600) * 0.02  # 2% per hour
            efficiency_estimate = gravity_loss_factor
            
            if efficiency_estimate > best_efficiency:
                best_efficiency = efficiency_estimate
                best_sequence = sequence
        
        if best_sequence is None:
            # Fallback to basic sequence
            best_sequence = self.create_burn_sequence(
                delta_v_target, thrust_direction, initial_mass,
                engine_stage, 10
            )
        
        self.logger.info(f"Optimized burn sequence: {len(best_sequence.segments)} segments, "
                        f"{best_sequence.total_duration:.1f}s duration, "
                        f"estimated efficiency: {best_efficiency:.3f}")
        
        return best_sequence


def create_finite_burn_executor(engine_model=None) -> FiniteBurnExecutor:
    """
    Factory function to create finite burn executor
    
    Args:
        engine_model: Optional engine performance model
        
    Returns:
        Configured FiniteBurnExecutor instance
    """
    return FiniteBurnExecutor(engine_model)


# Example usage and testing
if __name__ == "__main__":
    # Create finite burn executor
    executor = create_finite_burn_executor()
    
    print("Testing Finite Burn Executor")
    print("=" * 40)
    
    # Test burn sequence creation
    delta_v = 3200  # m/s (typical TLI delta-V)
    thrust_dir = np.array([0, 1, 0])  # Prograde direction
    initial_mass = 45000  # kg (S-IVB + payload mass)
    
    sequence = executor.create_burn_sequence(
        delta_v, thrust_dir, initial_mass, "S-IVB", 10
    )
    
    print(f"Created burn sequence:")
    print(f"  Total duration: {sequence.total_duration:.1f} s")
    print(f"  Number of segments: {len(sequence.segments)}")
    print(f"  Initial mass: {sequence.initial_mass:.0f} kg")
    print(f"  Final mass: {sequence.final_mass:.0f} kg")
    print(f"  Propellant mass: {sequence.initial_mass - sequence.final_mass:.0f} kg")
    
    # Test variable thrust profile
    thrust_profile = {
        0.0: 1.0,    # 100% throttle at start
        0.3: 0.8,    # 80% throttle at 30% through burn
        0.7: 0.9,    # 90% throttle at 70% through burn
        1.0: 1.0     # 100% throttle at end
    }
    
    var_sequence = executor.create_variable_thrust_sequence(
        delta_v, thrust_dir, initial_mass, thrust_profile, "S-IVB"
    )
    
    print(f"\nVariable thrust sequence:")
    print(f"  Total duration: {var_sequence.total_duration:.1f} s")
    print(f"  Number of segments: {len(var_sequence.segments)}")
    
    # Test execution simulation
    initial_state = {
        'position': [6556000, 0, 0],  # LEO position
        'velocity': [0, 7800, 0],     # LEO velocity
        'mass': initial_mass
    }
    
    result = executor.execute_burn_sequence(sequence, initial_state)
    
    print(f"\nBurn execution results:")
    print(f"  Target delta-V: {delta_v:.1f} m/s")
    print(f"  Achieved delta-V: {result.achieved_delta_v:.1f} m/s")
    print(f"  Burn efficiency: {result.burn_efficiency:.3f}")
    print(f"  Finite burn loss: {result.finite_burn_loss:.1f} m/s")
    print(f"  Converged: {result.converged}")