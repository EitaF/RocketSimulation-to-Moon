import numpy as np
from dataclasses import dataclass
from typing import Tuple, List, Optional
import math

@dataclass
class MCCBurn:
    """
    Represents a Mid-Course Correction burn.
    """
    burn_time: float  # Time to execute the burn [s]
    delta_v_vector: np.ndarray  # Delta-V vector [m/s]
    burn_duration: float  # Duration of the burn [s]
    description: str  # Description of the burn purpose
    executed: bool = False  # Whether the burn has been executed
    
class MidCourseCorrection:
    """
    Mid-Course Correction module for trajectory adjustments.
    
    This module provides capabilities to:
    1. Execute impulsive delta-V burns
    2. Calculate corrective burns to reduce miss distances
    3. Schedule multiple MCC burns during a mission
    """
    
    def __init__(self):
        """Initialize the MCC module."""
        self.scheduled_burns: List[MCCBurn] = []
        self.executed_burns: List[MCCBurn] = []
        
    def execute_mcc_burn(self, spacecraft_state: Tuple[np.ndarray, np.ndarray], 
                        delta_v_vector: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Execute an instantaneous Mid-Course Correction burn.
        
        Args:
            spacecraft_state: Tuple of (position, velocity) vectors in m and m/s
            delta_v_vector: Delta-V vector to apply in m/s
            
        Returns:
            Tuple of (new_position, new_velocity) after the burn
        """
        position, velocity = spacecraft_state
        
        # Position remains unchanged for instantaneous burn
        new_position = position.copy()
        
        # Apply delta-V to velocity
        new_velocity = velocity + delta_v_vector
        
        return new_position, new_velocity
    
    def schedule_burn(self, burn_time: float, delta_v_vector: np.ndarray, 
                     burn_duration: float = 0.0, description: str = "MCC Burn") -> None:
        """
        Schedule a Mid-Course Correction burn.
        
        Args:
            burn_time: Time to execute the burn [s]
            delta_v_vector: Delta-V vector [m/s]
            burn_duration: Duration of the burn [s] (0 for instantaneous)
            description: Description of the burn purpose
        """
        burn = MCCBurn(
            burn_time=burn_time,
            delta_v_vector=delta_v_vector.copy(),
            burn_duration=burn_duration,
            description=description,
            executed=False
        )
        
        self.scheduled_burns.append(burn)
        # Sort burns by time
        self.scheduled_burns.sort(key=lambda x: x.burn_time)
    
    def check_and_execute_burns(self, current_time: float, spacecraft_state: Tuple[np.ndarray, np.ndarray]) -> Tuple[np.ndarray, np.ndarray]:
        """
        Check if any burns should be executed at the current time and execute them.
        
        Args:
            current_time: Current simulation time [s]
            spacecraft_state: Current spacecraft state (position, velocity)
            
        Returns:
            Updated spacecraft state after any burns
        """
        position, velocity = spacecraft_state
        
        # Check for burns that should be executed
        burns_to_execute = []
        for burn in self.scheduled_burns:
            if not burn.executed and current_time >= burn.burn_time:
                burns_to_execute.append(burn)
        
        # Execute burns
        for burn in burns_to_execute:
            position, velocity = self.execute_mcc_burn((position, velocity), burn.delta_v_vector)
            burn.executed = True
            self.executed_burns.append(burn)
            
        # Remove executed burns from scheduled list
        self.scheduled_burns = [burn for burn in self.scheduled_burns if not burn.executed]
        
        return position, velocity
    
    def calculate_corrective_burn(self, current_state: Tuple[np.ndarray, np.ndarray],
                                target_position: np.ndarray, target_time: float,
                                current_time: float) -> np.ndarray:
        """
        Calculate a corrective burn to reach a target position at a specific time.
        
        This is a simplified calculation assuming the burn happens immediately
        and uses basic orbital mechanics.
        
        Args:
            current_state: Current spacecraft state (position, velocity)
            target_position: Target position vector [m]
            target_time: Time to reach target [s]
            current_time: Current simulation time [s]
            
        Returns:
            Delta-V vector required for correction [m/s]
        """
        position, velocity = current_state
        time_to_target = target_time - current_time
        
        if time_to_target <= 0:
            return np.zeros(3)
        
        # Simple approach: calculate required velocity change
        # This is a simplified model - real MCC calculations are much more complex
        displacement_needed = target_position - position
        required_velocity = displacement_needed / time_to_target
        
        # Delta-V is the difference between required and current velocity
        delta_v = required_velocity - velocity
        
        return delta_v
    
    def calculate_miss_distance_correction(self, current_state: Tuple[np.ndarray, np.ndarray],
                                         target_position: np.ndarray, 
                                         predicted_closest_approach: np.ndarray) -> np.ndarray:
        """
        Calculate a corrective burn to reduce miss distance.
        
        Args:
            current_state: Current spacecraft state (position, velocity)
            target_position: Target position (e.g., Moon center) [m]
            predicted_closest_approach: Predicted closest approach position [m]
            
        Returns:
            Delta-V vector to reduce miss distance [m/s]
        """
        position, velocity = current_state
        
        # Calculate miss vector (from target to closest approach)
        miss_vector = predicted_closest_approach - target_position
        miss_distance = np.linalg.norm(miss_vector)
        
        if miss_distance < 1000:  # Close enough, no correction needed
            return np.zeros(3)
        
        # Calculate correction direction (opposite to miss vector)
        correction_direction = -miss_vector / miss_distance
        
        # Simple correction magnitude (this is a simplified approach)
        # In reality, this would involve complex trajectory propagation
        correction_magnitude = min(miss_distance * 0.001, 100.0)  # Limit to 100 m/s
        
        delta_v = correction_direction * correction_magnitude
        
        return delta_v
    
    def get_burn_summary(self) -> dict:
        """
        Get summary of all burns (scheduled and executed).
        
        Returns:
            Dictionary with burn summary information
        """
        total_delta_v_scheduled = sum(np.linalg.norm(burn.delta_v_vector) for burn in self.scheduled_burns)
        total_delta_v_executed = sum(np.linalg.norm(burn.delta_v_vector) for burn in self.executed_burns)
        
        return {
            'scheduled_burns': len(self.scheduled_burns),
            'executed_burns': len(self.executed_burns),
            'total_delta_v_scheduled': total_delta_v_scheduled,
            'total_delta_v_executed': total_delta_v_executed,
            'burns_history': [
                {
                    'time': burn.burn_time,
                    'delta_v_magnitude': np.linalg.norm(burn.delta_v_vector),
                    'description': burn.description,
                    'executed': burn.executed
                }
                for burn in self.executed_burns + self.scheduled_burns
            ]
        }
    
    def clear_all_burns(self) -> None:
        """Clear all scheduled and executed burns."""
        self.scheduled_burns.clear()
        self.executed_burns.clear()