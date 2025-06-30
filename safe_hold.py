"""
Safe Hold Attitude Controller
Task 3-4: Safe-hold attitude controller with rate damping in <60s
"""

import numpy as np
import logging
from typing import Dict, Tuple, Optional
from dataclasses import dataclass
from vehicle import Vector3


@dataclass
class AttitudeState:
    """Current attitude state of the vehicle"""
    pitch: float      # degrees
    yaw: float        # degrees  
    roll: float       # degrees
    pitch_rate: float # deg/s
    yaw_rate: float   # deg/s
    roll_rate: float  # deg/s


@dataclass
class ControlCommand:
    """Attitude control command"""
    pitch_torque: float  # N⋅m
    yaw_torque: float    # N⋅m
    roll_torque: float   # N⋅m
    thrust_vector_angle: float  # degrees (for thrust vectoring)


class SafeHoldController:
    """
    Safe hold attitude controller for emergency situations
    Provides rate damping and attitude stabilization within 60 seconds
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.logger = logging.getLogger(__name__)
        self.config = config or self._get_default_config()
        
        # Controller gains (tuned for rocket dynamics)
        self.gains = self.config.get('controller_gains', {})
        
        # Target attitude for safe hold (typically pitch up for stability)
        self.target_attitude = AttitudeState(
            pitch=self.config.get('safe_hold_pitch', 0.0),  # degrees
            yaw=0.0,
            roll=0.0,
            pitch_rate=0.0,
            yaw_rate=0.0,
            roll_rate=0.0
        )
        
        # Controller state
        self.is_active = False
        self.activation_time = 0.0
        self.integral_errors = {'pitch': 0.0, 'yaw': 0.0, 'roll': 0.0}
        self.previous_errors = {'pitch': 0.0, 'yaw': 0.0, 'roll': 0.0}
        self.previous_time = 0.0
        
        # Performance tracking
        self.convergence_time = None
        self.max_rates_encountered = {'pitch': 0.0, 'yaw': 0.0, 'roll': 0.0}
        
        self.logger.info("Safe hold controller initialized")
    
    def _get_default_config(self) -> Dict:
        """Get default configuration for safe hold controller"""
        return {
            'controller_gains': {
                # PID gains for attitude control
                'pitch_kp': 5.0,    # Proportional gain (increased)
                'pitch_ki': 0.2,    # Integral gain (increased)  
                'pitch_kd': 2.0,    # Derivative gain (increased)
                'yaw_kp': 4.0,      # Increased
                'yaw_ki': 0.15,     # Increased
                'yaw_kd': 1.5,      # Increased
                'roll_kp': 4.5,     # Increased
                'roll_ki': 0.18,    # Increased
                'roll_kd': 1.8,     # Increased
                
                # Rate damping gains
                'pitch_rate_kd': 3.0,  # Increased
                'yaw_rate_kd': 2.5,    # Increased
                'roll_rate_kd': 2.8,   # Increased
                
                # Thrust vectoring gain
                'thrust_vector_gain': 1.0  # Increased
            },
            'control_limits': {
                'max_torque': 50000.0,     # N⋅m
                'max_thrust_angle': 5.0,   # degrees
                'max_rate_error': 10.0     # deg/s
            },
            'convergence_criteria': {
                'attitude_tolerance': 2.0,  # degrees
                'rate_tolerance': 0.5,      # deg/s
                'convergence_time': 60.0    # seconds
            },
            'safe_hold_pitch': 5.0,         # degrees (slight nose up for stability)
            'enable_thrust_vectoring': True,
            'enable_rate_damping': True
        }
    
    def activate(self, current_time: float, initial_attitude: AttitudeState):
        """
        Activate safe hold mode
        
        Args:
            current_time: Current mission time [s]
            initial_attitude: Current attitude state
        """
        self.is_active = True
        self.activation_time = current_time
        self.previous_time = current_time
        self.convergence_time = None
        
        # Reset integrator
        self.integral_errors = {'pitch': 0.0, 'yaw': 0.0, 'roll': 0.0}
        self.previous_errors = {'pitch': 0.0, 'yaw': 0.0, 'roll': 0.0}
        
        # Record initial rates
        self.max_rates_encountered = {
            'pitch': abs(initial_attitude.pitch_rate),
            'yaw': abs(initial_attitude.yaw_rate),
            'roll': abs(initial_attitude.roll_rate)
        }
        
        self.logger.info(f"Safe hold controller activated at t={current_time:.1f}s")
        self.logger.info(f"Initial attitude: pitch={initial_attitude.pitch:.1f}°, "
                        f"yaw={initial_attitude.yaw:.1f}°, roll={initial_attitude.roll:.1f}°")
        self.logger.info(f"Initial rates: pitch_rate={initial_attitude.pitch_rate:.1f}°/s, "
                        f"yaw_rate={initial_attitude.yaw_rate:.1f}°/s, "
                        f"roll_rate={initial_attitude.roll_rate:.1f}°/s")
    
    def update(self, current_time: float, current_attitude: AttitudeState,
               vehicle_properties: Dict) -> ControlCommand:
        """
        Update safe hold controller and generate control commands
        
        Args:
            current_time: Current mission time [s]
            current_attitude: Current attitude state
            vehicle_properties: Vehicle properties (mass, inertia, etc.)
            
        Returns:
            Control command for attitude control
        """
        if not self.is_active:
            return ControlCommand(0, 0, 0, 0)
        
        dt = current_time - self.previous_time
        if dt <= 0:
            dt = 0.1  # Default timestep
        
        # Update maximum rates encountered
        self._update_max_rates(current_attitude)
        
        # Calculate attitude errors
        pitch_error = self._wrap_angle(self.target_attitude.pitch - current_attitude.pitch)
        yaw_error = self._wrap_angle(self.target_attitude.yaw - current_attitude.yaw)
        roll_error = self._wrap_angle(self.target_attitude.roll - current_attitude.roll)
        
        # Calculate rate errors
        pitch_rate_error = self.target_attitude.pitch_rate - current_attitude.pitch_rate
        yaw_rate_error = self.target_attitude.yaw_rate - current_attitude.yaw_rate
        roll_rate_error = self.target_attitude.roll_rate - current_attitude.roll_rate
        
        # PID controller for each axis
        pitch_command = self._calculate_pid_command('pitch', pitch_error, pitch_rate_error, dt)
        yaw_command = self._calculate_pid_command('yaw', yaw_error, yaw_rate_error, dt)
        roll_command = self._calculate_pid_command('roll', roll_error, roll_rate_error, dt)
        
        # Apply control limits
        limits = self.config.get('control_limits', {})
        max_torque = limits.get('max_torque', 50000.0)
        
        pitch_torque = np.clip(pitch_command, -max_torque, max_torque)
        yaw_torque = np.clip(yaw_command, -max_torque, max_torque)
        roll_torque = np.clip(roll_command, -max_torque, max_torque)
        
        # Thrust vectoring for pitch control (if enabled)
        thrust_vector_angle = 0.0
        if (self.config.get('enable_thrust_vectoring', True) and 
            vehicle_properties.get('thrust_magnitude', 0) > 0):
            
            thrust_vector_gain = self.gains.get('thrust_vector_gain', 0.5)
            max_thrust_angle = limits.get('max_thrust_angle', 5.0)
            
            thrust_vector_angle = np.clip(
                -pitch_error * thrust_vector_gain,
                -max_thrust_angle,
                max_thrust_angle
            )
        
        # Check convergence
        self._check_convergence(current_time, current_attitude)
        
        # Update previous values
        self.previous_time = current_time
        self.previous_errors['pitch'] = pitch_error
        self.previous_errors['yaw'] = yaw_error
        self.previous_errors['roll'] = roll_error
        
        return ControlCommand(
            pitch_torque=pitch_torque,
            yaw_torque=yaw_torque,
            roll_torque=roll_torque,
            thrust_vector_angle=thrust_vector_angle
        )
    
    def _calculate_pid_command(self, axis: str, attitude_error: float, 
                              rate_error: float, dt: float) -> float:
        """Calculate PID command for a single axis"""
        
        # PID gains
        kp = self.gains.get(f'{axis}_kp', 1.0)
        ki = self.gains.get(f'{axis}_ki', 0.1)
        kd = self.gains.get(f'{axis}_kd', 0.5)
        rate_kd = self.gains.get(f'{axis}_rate_kd', 1.0)
        
        # Proportional term
        p_term = kp * attitude_error
        
        # Integral term (with windup protection)
        self.integral_errors[axis] += attitude_error * dt
        # Clamp integral to prevent windup
        max_integral = 100.0  # degrees⋅s
        self.integral_errors[axis] = np.clip(
            self.integral_errors[axis], -max_integral, max_integral
        )
        i_term = ki * self.integral_errors[axis]
        
        # Derivative term (attitude error derivative)
        if dt > 0:
            error_derivative = (attitude_error - self.previous_errors.get(axis, 0)) / dt
            d_term = kd * error_derivative
        else:
            d_term = 0
        
        # Rate damping term
        rate_damping = rate_kd * rate_error
        
        # Combine terms
        command = p_term + i_term + d_term + rate_damping
        
        return command
    
    def _update_max_rates(self, attitude: AttitudeState):
        """Update maximum rates encountered during safe hold"""
        self.max_rates_encountered['pitch'] = max(
            self.max_rates_encountered['pitch'], abs(attitude.pitch_rate)
        )
        self.max_rates_encountered['yaw'] = max(
            self.max_rates_encountered['yaw'], abs(attitude.yaw_rate)
        )
        self.max_rates_encountered['roll'] = max(
            self.max_rates_encountered['roll'], abs(attitude.roll_rate)
        )
    
    def _check_convergence(self, current_time: float, attitude: AttitudeState):
        """Check if attitude has converged to safe hold target"""
        if self.convergence_time is not None:
            return  # Already converged
        
        criteria = self.config.get('convergence_criteria', {})
        attitude_tol = criteria.get('attitude_tolerance', 2.0)
        rate_tol = criteria.get('rate_tolerance', 0.5)
        
        # Check attitude errors
        pitch_error = abs(self.target_attitude.pitch - attitude.pitch)
        yaw_error = abs(self.target_attitude.yaw - attitude.yaw)
        roll_error = abs(self.target_attitude.roll - attitude.roll)
        
        attitude_converged = (pitch_error < attitude_tol and 
                            yaw_error < attitude_tol and 
                            roll_error < attitude_tol)
        
        # Check rate errors
        rate_converged = (abs(attitude.pitch_rate) < rate_tol and
                         abs(attitude.yaw_rate) < rate_tol and
                         abs(attitude.roll_rate) < rate_tol)
        
        if attitude_converged and rate_converged:
            self.convergence_time = current_time - self.activation_time
            self.logger.info(f"Safe hold converged in {self.convergence_time:.1f} seconds")
            self.logger.info(f"Final attitude: pitch={attitude.pitch:.1f}°, "
                           f"yaw={attitude.yaw:.1f}°, roll={attitude.roll:.1f}°")
            self.logger.info(f"Final rates: pitch_rate={attitude.pitch_rate:.2f}°/s, "
                           f"yaw_rate={attitude.yaw_rate:.2f}°/s, "
                           f"roll_rate={attitude.roll_rate:.2f}°/s")
    
    def _wrap_angle(self, angle: float) -> float:
        """Wrap angle to [-180, 180] degrees"""
        while angle > 180:
            angle -= 360
        while angle < -180:
            angle += 360
        return angle
    
    def is_converged(self) -> bool:
        """Check if controller has converged"""
        return self.convergence_time is not None
    
    def get_convergence_time(self) -> Optional[float]:
        """Get time to convergence (None if not converged)"""
        return self.convergence_time
    
    def get_performance_metrics(self) -> Dict:
        """Get performance metrics for the safe hold controller"""
        return {
            'is_active': self.is_active,
            'is_converged': self.is_converged(),
            'convergence_time': self.convergence_time,
            'max_rates_encountered': self.max_rates_encountered.copy(),
            'target_attitude': {
                'pitch': self.target_attitude.pitch,
                'yaw': self.target_attitude.yaw,
                'roll': self.target_attitude.roll
            },
            'meets_requirement': self.convergence_time is not None and self.convergence_time <= 60.0
        }
    
    def deactivate(self):
        """Deactivate safe hold controller"""
        if self.is_active:
            self.is_active = False
            self.logger.info("Safe hold controller deactivated")
    
    def reset(self):
        """Reset controller state"""
        self.is_active = False
        self.activation_time = 0.0
        self.convergence_time = None
        self.integral_errors = {'pitch': 0.0, 'yaw': 0.0, 'roll': 0.0}
        self.previous_errors = {'pitch': 0.0, 'yaw': 0.0, 'roll': 0.0}
        self.max_rates_encountered = {'pitch': 0.0, 'yaw': 0.0, 'roll': 0.0}
        self.logger.info("Safe hold controller reset")


def simulate_attitude_dynamics(attitude: AttitudeState, control_command: ControlCommand,
                              vehicle_properties: Dict, dt: float) -> AttitudeState:
    """
    Simple attitude dynamics simulation for testing
    This would normally be part of the main simulation
    """
    
    # Vehicle properties
    mass = vehicle_properties.get('mass', 500000)  # kg
    moment_of_inertia = vehicle_properties.get('moment_of_inertia', {
        'pitch': 1e7,  # kg⋅m²
        'yaw': 1e7,
        'roll': 1e6
    })
    
    # Calculate angular accelerations from torques
    pitch_accel = control_command.pitch_torque / moment_of_inertia['pitch']
    yaw_accel = control_command.yaw_torque / moment_of_inertia['yaw']
    roll_accel = control_command.roll_torque / moment_of_inertia['roll']
    
    # Add some damping (atmospheric and structural)
    damping_factor = 0.95
    
    # Update rates
    new_pitch_rate = attitude.pitch_rate + pitch_accel * dt
    new_yaw_rate = attitude.yaw_rate + yaw_accel * dt
    new_roll_rate = attitude.roll_rate + roll_accel * dt
    
    # Apply damping
    new_pitch_rate *= damping_factor
    new_yaw_rate *= damping_factor
    new_roll_rate *= damping_factor
    
    # Update attitudes
    new_pitch = attitude.pitch + new_pitch_rate * dt
    new_yaw = attitude.yaw + new_yaw_rate * dt
    new_roll = attitude.roll + new_roll_rate * dt
    
    return AttitudeState(
        pitch=new_pitch,
        yaw=new_yaw,
        roll=new_roll,
        pitch_rate=new_pitch_rate,
        yaw_rate=new_yaw_rate,
        roll_rate=new_roll_rate
    )


def main():
    """Test the safe hold controller"""
    print("Safe Hold Attitude Controller Test")
    print("=" * 40)
    
    # Create controller
    controller = SafeHoldController()
    
    # Initial attitude with high rates (emergency scenario)
    initial_attitude = AttitudeState(
        pitch=15.0,      # degrees - off target
        yaw=-8.0,        # degrees - off target  
        roll=12.0,       # degrees - off target
        pitch_rate=5.0,  # deg/s - high rate
        yaw_rate=-3.0,   # deg/s - high rate
        roll_rate=4.0    # deg/s - high rate
    )
    
    # Vehicle properties
    vehicle_props = {
        'mass': 400000,
        'moment_of_inertia': {
            'pitch': 8e6,
            'yaw': 8e6,
            'roll': 5e5
        },
        'thrust_magnitude': 1000000  # N
    }
    
    # Activate controller
    controller.activate(0.0, initial_attitude)
    
    # Simulation parameters
    dt = 0.1  # seconds
    sim_time = 80.0  # seconds
    current_time = 0.0
    current_attitude = initial_attitude
    
    print(f"\nInitial conditions:")
    print(f"  Attitude: pitch={initial_attitude.pitch:.1f}°, yaw={initial_attitude.yaw:.1f}°, roll={initial_attitude.roll:.1f}°")
    print(f"  Rates: pitch_rate={initial_attitude.pitch_rate:.1f}°/s, yaw_rate={initial_attitude.yaw_rate:.1f}°/s, roll_rate={initial_attitude.roll_rate:.1f}°/s")
    
    print(f"\nSimulation progress:")
    
    # Simulation loop
    while current_time < sim_time:
        # Get control command
        command = controller.update(current_time, current_attitude, vehicle_props)
        
        # Simulate attitude dynamics
        current_attitude = simulate_attitude_dynamics(
            current_attitude, command, vehicle_props, dt
        )
        
        current_time += dt
        
        # Print status every 10 seconds
        if int(current_time) % 10 == 0 and abs(current_time - int(current_time)) < dt:
            print(f"t={current_time:4.0f}s: pitch={current_attitude.pitch:6.1f}°, "
                  f"yaw={current_attitude.yaw:6.1f}°, roll={current_attitude.roll:6.1f}°, "
                  f"rates: {current_attitude.pitch_rate:5.2f}/{current_attitude.yaw_rate:5.2f}/{current_attitude.roll_rate:5.2f} °/s")
        
        # Check if converged
        if controller.is_converged() and controller.get_convergence_time() < current_time - 1:
            break
    
    # Final results
    print(f"\nFinal Results:")
    metrics = controller.get_performance_metrics()
    print(f"  Converged: {metrics['is_converged']}")
    if metrics['convergence_time']:
        print(f"  Convergence time: {metrics['convergence_time']:.1f} seconds")
        print(f"  Meets requirement (<60s): {metrics['meets_requirement']}")
    else:
        print(f"  Did not converge within {sim_time} seconds")
    
    print(f"  Final attitude: pitch={current_attitude.pitch:.1f}°, yaw={current_attitude.yaw:.1f}°, roll={current_attitude.roll:.1f}°")
    print(f"  Final rates: pitch_rate={current_attitude.pitch_rate:.2f}°/s, yaw_rate={current_attitude.yaw_rate:.2f}°/s, roll_rate={current_attitude.roll_rate:.2f}°/s")
    print(f"  Maximum rates encountered: {metrics['max_rates_encountered']}")
    
    if metrics['meets_requirement']:
        print("✅ Safe hold controller meets 60-second requirement!")
    else:
        print("❌ Safe hold controller does not meet requirement")


if __name__ == "__main__":
    main()