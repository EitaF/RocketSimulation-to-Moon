"""
Strategy Pattern Guidance Architecture
Task 3-6: Modular guidance system using Strategy pattern for cleaner fault handling
"""

import numpy as np
import logging
from abc import ABC, abstractmethod
from typing import Dict, Tuple, Optional, List
from dataclasses import dataclass
from enum import Enum
from vehicle import Vector3, MissionPhase
from peg import PEGGuidance
from circularize import CircularizationBurn


class GuidancePhase(Enum):
    """Guidance phases for mission"""
    PEG = "peg"           # Powered Explicit Guidance (Professor v27)
    GRAVITY_TURN = "gravity_turn"
    COAST = "coast"
    CIRCULARIZATION = "circularization"  # Professor v27: Apoapsis circularization burn
    TLI = "tli"           # Trans-Lunar Injection
    LOI = "loi"           # Lunar Orbit Insertion
    PDI = "pdi"           # Powered Descent Initiation


@dataclass
class GuidanceCommand:
    """Output from guidance strategy"""
    thrust_direction: Vector3
    thrust_magnitude: float
    guidance_phase: GuidancePhase
    target_pitch: float  # degrees
    target_yaw: float    # degrees
    estimated_error: float  # meters
    next_phase_trigger: Optional[str] = None


@dataclass
class VehicleState:
    """Current vehicle state for guidance"""
    position: Vector3
    velocity: Vector3
    altitude: float
    mass: float
    mission_phase: MissionPhase
    time: float


class IGuidanceStrategy(ABC):
    """Interface for guidance strategies"""
    
    @abstractmethod
    def compute_guidance(self, vehicle_state: VehicleState, 
                        target_state: Dict, config: Dict) -> GuidanceCommand:
        """Compute guidance command for current state"""
        pass
    
    @abstractmethod
    def is_phase_complete(self, vehicle_state: VehicleState, 
                         target_state: Dict) -> bool:
        """Check if current guidance phase is complete"""
        pass
    
    @abstractmethod
    def get_phase_name(self) -> GuidancePhase:
        """Get the guidance phase this strategy handles"""
        pass


class GravityTurnStrategy(IGuidanceStrategy):
    """Gravity turn guidance strategy for ascent"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.gravity_turn_start_altitude = 1500  # meters
        self.target_pitch_profile = self._initialize_pitch_profile()
    
    def _initialize_pitch_profile(self) -> Dict[float, float]:
        """Initialize pitch angle profile vs altitude"""
        return {
            0: 90.0,        # Vertical launch
            1500: 90.0,     # Vertical until gravity turn
            5000: 80.0,     # Begin gravity turn
            10000: 70.0,    # Continue pitching over
            20000: 50.0,    # Shallow angle
            40000: 30.0,    # Even shallower
            60000: 15.0,    # Nearly horizontal
            80000: 5.0,     # Almost horizontal
            100000: 0.0     # Horizontal
        }
    
    def compute_guidance(self, vehicle_state: VehicleState, 
                        target_state: Dict, config: Dict) -> GuidanceCommand:
        """Compute gravity turn guidance"""
        
        # Determine target pitch based on altitude
        target_pitch = self._get_target_pitch(vehicle_state.altitude)
        
        # Simple proportional control for pitch
        current_flight_path_angle = self._get_flight_path_angle(vehicle_state)
        pitch_error = target_pitch - current_flight_path_angle
        
        # Convert to thrust direction (simplified)
        pitch_rad = np.radians(target_pitch)
        
        # Thrust direction in local coordinates (pitch from vertical)
        thrust_direction = Vector3(
            np.sin(pitch_rad),  # Horizontal component
            np.cos(pitch_rad),  # Vertical component
            0.0                 # No yaw
        )
        
        # Full thrust during gravity turn
        thrust_magnitude = 1.0  # 100% throttle
        
        # Estimate guidance error
        guidance_error = abs(pitch_error) * 100  # Convert to rough distance error
        
        return GuidanceCommand(
            thrust_direction=thrust_direction,
            thrust_magnitude=thrust_magnitude,
            guidance_phase=GuidancePhase.GRAVITY_TURN,
            target_pitch=target_pitch,
            target_yaw=0.0,
            estimated_error=guidance_error
        )
    
    def _get_target_pitch(self, altitude: float) -> float:
        """Get target pitch angle for given altitude"""
        altitudes = sorted(self.target_pitch_profile.keys())
        
        if altitude <= altitudes[0]:
            return self.target_pitch_profile[altitudes[0]]
        elif altitude >= altitudes[-1]:
            return self.target_pitch_profile[altitudes[-1]]
        
        # Linear interpolation
        for i in range(len(altitudes) - 1):
            if altitudes[i] <= altitude <= altitudes[i + 1]:
                alt1, alt2 = altitudes[i], altitudes[i + 1]
                pitch1, pitch2 = self.target_pitch_profile[alt1], self.target_pitch_profile[alt2]
                
                factor = (altitude - alt1) / (alt2 - alt1)
                return pitch1 + factor * (pitch2 - pitch1)
        
        return 0.0  # Fallback
    
    def _get_flight_path_angle(self, vehicle_state: VehicleState) -> float:
        """Calculate current flight path angle"""
        # Simplified calculation
        v_radial = vehicle_state.velocity.data @ vehicle_state.position.normalized().data
        v_total = vehicle_state.velocity.magnitude()
        
        if v_total == 0:
            return 90.0  # Vertical
        
        sin_gamma = v_radial / v_total
        sin_gamma = max(-1.0, min(1.0, sin_gamma))  # Clamp
        
        return np.degrees(np.arcsin(sin_gamma))
    
    def is_phase_complete(self, vehicle_state: VehicleState, target_state: Dict) -> bool:
        """Check if gravity turn is complete"""
        # Complete when we reach target apoapsis
        target_apoapsis = target_state.get('target_apoapsis', 200000)  # 200 km
        
        # Estimate apoapsis (simplified)
        r = vehicle_state.position.magnitude()
        v = vehicle_state.velocity.magnitude()
        
        # Simplified orbital energy calculation
        mu_earth = 3.986e14  # Earth's gravitational parameter
        energy = 0.5 * v**2 - mu_earth / r
        
        if energy >= 0:
            return True  # Escape trajectory
        
        # Semi-major axis and apoapsis
        a = -mu_earth / (2 * energy)
        apoapsis = 2 * a - r  # Rough estimate
        
        return apoapsis >= target_apoapsis
    
    def get_phase_name(self) -> GuidancePhase:
        return GuidancePhase.GRAVITY_TURN


class PEGStrategy(IGuidanceStrategy):
    """
    Powered Explicit Guidance strategy for precise orbital insertion
    Professor v27: Closed-loop guidance system to replace open-loop gravity turn
    """
    
    def __init__(self, target_altitude_km: float = 200, thrust_deficit: float = 0.0):
        self.logger = logging.getLogger(__name__)
        self.peg_guidance = PEGGuidance(target_altitude=target_altitude_km * 1000)
        self.thrust_deficit = thrust_deficit  # For testing with engine underperformance
        self.meco_triggered = False
        self.last_guidance_time = 0.0
        self.cached_pitch = 90.0  # Start vertical
        self.cached_thrust_direction = Vector3(0, 1, 0)  # Start vertical
        
        self.logger.info(f"PEG Strategy initialized - Target: {target_altitude_km}km, "
                        f"Thrust deficit: {thrust_deficit*100:.1f}%")
    
    def compute_guidance(self, vehicle_state: VehicleState, 
                        target_state: Dict, config: Dict) -> GuidanceCommand:
        """Compute PEG guidance for closed-loop control"""
        
        # Professor v27: Vertical ascent for first 1500m, then PEG guidance
        if vehicle_state.altitude < 1500:  # Below gravity turn altitude
            # Thrust vertically upward
            radial_unit = vehicle_state.position.normalized()
            thrust_direction = radial_unit  # Point away from Earth center
            pitch_deg = 90.0  # Vertical
            thrust_magnitude = 1.0  # Full thrust
            
            return GuidanceCommand(
                thrust_direction=thrust_direction,
                thrust_magnitude=thrust_magnitude,
                guidance_phase=GuidancePhase.PEG,
                target_pitch=pitch_deg,
                target_yaw=0.0,
                estimated_error=0.0
            )
        
        # Estimate remaining burn time (simplified)
        remaining_burn_time = max(10.0, 300.0 - vehicle_state.time)  # Rough estimate
        
        # Compute PEG guidance
        guidance_result = self.peg_guidance.compute_peg_guidance(
            vehicle_state.position, 
            vehicle_state.velocity, 
            vehicle_state.time,
            remaining_burn_time,
            self.thrust_deficit
        )
        
        if guidance_result[0] is not None:  # New guidance available
            pitch_deg, thrust_direction, meco_condition = guidance_result
            self.cached_pitch = pitch_deg
            self.cached_thrust_direction = thrust_direction
            self.meco_triggered = meco_condition
            self.last_guidance_time = vehicle_state.time
        else:
            # Use cached values
            pitch_deg = self.cached_pitch
            thrust_direction = self.cached_thrust_direction
        
        # Thrust magnitude - full thrust until MECO
        thrust_magnitude = 0.0 if self.meco_triggered else 1.0
        
        # Calculate guidance error (difference from target trajectory)
        orbital_status = self.peg_guidance.get_guidance_status(
            vehicle_state.position, vehicle_state.velocity
        )
        guidance_error = orbital_status.get('delta_v_needed', 0)
        
        # Determine next phase trigger
        next_phase_trigger = None
        if self.meco_triggered:
            next_phase_trigger = "MECO_triggered"
        
        return GuidanceCommand(
            thrust_direction=thrust_direction,
            thrust_magnitude=thrust_magnitude,
            guidance_phase=GuidancePhase.PEG,
            target_pitch=pitch_deg,
            target_yaw=0.0,
            estimated_error=guidance_error,
            next_phase_trigger=next_phase_trigger
        )
    
    def is_phase_complete(self, vehicle_state: VehicleState, target_state: Dict) -> bool:
        """Check if PEG phase is complete (MECO condition met)"""
        return self.meco_triggered or not self.peg_guidance.is_guidance_needed(
            vehicle_state.position, vehicle_state.velocity
        )
    
    def get_phase_name(self) -> GuidancePhase:
        return GuidancePhase.PEG
    
    def reset_meco(self):
        """Reset MECO condition for testing"""
        self.meco_triggered = False
    
    def set_thrust_deficit(self, deficit: float):
        """Set thrust deficit for testing"""
        self.thrust_deficit = deficit
        self.logger.info(f"Thrust deficit set to {deficit*100:.1f}%")
    
    def get_guidance_status(self, vehicle_state: VehicleState) -> Dict:
        """Get detailed guidance status for monitoring"""
        orbital_status = self.peg_guidance.get_guidance_status(
            vehicle_state.position, vehicle_state.velocity
        )
        
        return {
            **orbital_status,
            'thrust_deficit_percent': self.thrust_deficit * 100,
            'meco_triggered': self.meco_triggered,
            'guidance_active': not self.meco_triggered,
            'fallback_to_tangent': self.peg_guidance.fallback_to_tangent,
            'convergence_failures': self.peg_guidance.convergence_failures
        }


class CoastStrategy(IGuidanceStrategy):
    """Coast phase guidance strategy"""
    
    def compute_guidance(self, vehicle_state: VehicleState, 
                        target_state: Dict, config: Dict) -> GuidanceCommand:
        """Coast guidance - no thrust, attitude hold"""
        
        return GuidanceCommand(
            thrust_direction=Vector3(0, 0, 0),
            thrust_magnitude=0.0,
            guidance_phase=GuidancePhase.COAST,
            target_pitch=0.0,  # Maintain current attitude
            target_yaw=0.0,
            estimated_error=0.0
        )
    
    def is_phase_complete(self, vehicle_state: VehicleState, target_state: Dict) -> bool:
        """Check if coast phase is complete"""
        # Coast complete when we reach the trigger condition
        return target_state.get('coast_complete', False)
    
    def get_phase_name(self) -> GuidancePhase:
        return GuidancePhase.COAST


class CircularizationStrategy(IGuidanceStrategy):
    """
    Circularization burn strategy for orbital insertion
    Professor v27: Precise circularization at apoapsis for stable LEO
    """
    
    def __init__(self, orbital_monitor=None):
        self.logger = logging.getLogger(__name__)
        self.circularization_burn = CircularizationBurn(orbital_monitor)
        self.burn_started = False
        
        self.logger.info("Circularization strategy initialized")
    
    def compute_guidance(self, vehicle_state: VehicleState, 
                        target_state: Dict, config: Dict) -> GuidanceCommand:
        """Compute circularization burn guidance"""
        
        # Check if we should start the burn
        should_start = self.circularization_burn.should_start_burn(
            vehicle_state.position, vehicle_state.velocity, vehicle_state.time
        )
        
        if should_start and not self.burn_started:
            # Calculate burn parameters
            burn_params = self.circularization_burn.calculate_burn_parameters(
                vehicle_state.position, vehicle_state.velocity
            )
            
            if burn_params['is_valid']:
                # Start the burn
                self.circularization_burn.start_burn(
                    vehicle_state.time, burn_params['delta_v_needed']
                )
                self.burn_started = True
                thrust_direction = burn_params['burn_direction']
                thrust_magnitude = 1.0  # Full thrust
            else:
                # Invalid burn parameters
                thrust_direction = Vector3(0, 0, 0)
                thrust_magnitude = 0.0
        elif self.burn_started:
            # Continue burn or check if it should stop
            should_stop = self.circularization_burn.should_stop_burn(
                vehicle_state.position, vehicle_state.velocity
            )
            
            if should_stop:
                self.circularization_burn.stop_burn(vehicle_state.time)
                thrust_direction = Vector3(0, 0, 0)
                thrust_magnitude = 0.0
            else:
                # Continue burning prograde
                thrust_direction = vehicle_state.velocity.normalized() if vehicle_state.velocity.magnitude() > 0 else Vector3(1, 0, 0)
                thrust_magnitude = 1.0
                
                # Update burn progress (simplified)
                self.circularization_burn.update_burn(vehicle_state.time, 10.0)  # Assume 10 m/s delta-v per update
        else:
            # Not time to burn yet
            thrust_direction = Vector3(0, 0, 0)
            thrust_magnitude = 0.0
        
        # Calculate estimated error
        burn_status = self.circularization_burn.get_burn_status()
        guidance_error = burn_status.get('target_delta_v', 0) - burn_status.get('accumulated_delta_v', 0)
        
        return GuidanceCommand(
            thrust_direction=thrust_direction,
            thrust_magnitude=thrust_magnitude,
            guidance_phase=GuidancePhase.CIRCULARIZATION,
            target_pitch=0.0,  # Prograde burn
            target_yaw=0.0,
            estimated_error=abs(guidance_error)
        )
    
    def is_phase_complete(self, vehicle_state: VehicleState, target_state: Dict) -> bool:
        """Check if circularization is complete"""
        if not self.burn_started:
            return False
        
        # Check if burn is complete and orbit is circular
        validation = self.circularization_burn.validate_circular_orbit(
            vehicle_state.position, vehicle_state.velocity
        )
        
        return validation.get('success', False)
    
    def get_phase_name(self) -> GuidancePhase:
        return GuidancePhase.CIRCULARIZATION
    
    def get_circularization_status(self) -> Dict:
        """Get detailed circularization status"""
        return self.circularization_burn.get_burn_status()


class TLIStrategy(IGuidanceStrategy):
    """Trans-Lunar Injection strategy - Professor v29 enhanced with TLI guidance module"""
    
    def __init__(self):
        # Import TLI guidance module
        from tli_guidance import create_tli_guidance
        self.tli_guidance = create_tli_guidance(185000)  # 185km parking orbit
        self.burn_started = False
    
    def compute_guidance(self, vehicle_state: VehicleState, 
                        target_state: Dict, config: Dict) -> GuidanceCommand:
        """TLI burn guidance using dedicated TLI guidance module"""
        
        # Get guidance from TLI module
        thrust_direction, thrust_magnitude = self.tli_guidance.get_guidance_command(
            vehicle_state.position, 
            vehicle_state.velocity, 
            vehicle_state.time
        )
        
        # Update burn state
        if hasattr(vehicle_state, 'dt'):
            self.tli_guidance.update_burn_state(vehicle_state.dt, vehicle_state.velocity)
        
        return GuidanceCommand(
            thrust_direction=thrust_direction,
            thrust_magnitude=thrust_magnitude,
            guidance_phase=GuidancePhase.TLI,
            target_pitch=0.0,  # Prograde
            target_yaw=0.0,
            estimated_error=50.0  # TLI tolerance
        )
    
    def is_phase_complete(self, vehicle_state: VehicleState, target_state: Dict) -> bool:
        """Check if TLI is complete using TLI guidance module"""
        # Use TLI guidance module to determine burn completion
        return self.tli_guidance.should_terminate_burn(vehicle_state.velocity)
    
    def get_phase_name(self) -> GuidancePhase:
        return GuidancePhase.TLI


class LOIStrategy(IGuidanceStrategy):
    """Lunar Orbit Insertion strategy"""
    
    def compute_guidance(self, vehicle_state: VehicleState, 
                        target_state: Dict, config: Dict) -> GuidanceCommand:
        """LOI burn guidance"""
        
        # Point retrograde relative to moon for capture
        moon_position = target_state.get('moon_position', Vector3(384400e3, 0, 0))
        moon_velocity = target_state.get('moon_velocity', Vector3(0, 1022, 0))
        
        # Relative velocity to moon
        relative_velocity = vehicle_state.velocity - moon_velocity
        thrust_direction = relative_velocity.normalized() * (-1)  # Retrograde
        
        return GuidanceCommand(
            thrust_direction=thrust_direction,
            thrust_magnitude=1.0,
            guidance_phase=GuidancePhase.LOI,
            target_pitch=180.0,  # Retrograde
            target_yaw=0.0,
            estimated_error=100.0
        )
    
    def is_phase_complete(self, vehicle_state: VehicleState, target_state: Dict) -> bool:
        """Check if LOI is complete"""
        # LOI complete when captured by moon (negative orbital energy relative to moon)
        moon_position = target_state.get('moon_position', Vector3(384400e3, 0, 0))
        moon_velocity = target_state.get('moon_velocity', Vector3(0, 1022, 0))
        
        r_moon = (vehicle_state.position - moon_position).magnitude()
        v_rel = (vehicle_state.velocity - moon_velocity).magnitude()
        
        mu_moon = 4.904e12
        energy = 0.5 * v_rel**2 - mu_moon / r_moon
        
        return energy < 0  # Captured by moon
    
    def get_phase_name(self) -> GuidancePhase:
        return GuidancePhase.LOI


class PDIStrategy(IGuidanceStrategy):
    """Powered Descent Initiation strategy"""
    
    def compute_guidance(self, vehicle_state: VehicleState, 
                        target_state: Dict, config: Dict) -> GuidanceCommand:
        """PDI guidance for lunar landing"""
        
        # Point upward relative to moon surface for landing
        moon_position = target_state.get('moon_position', Vector3(384400e3, 0, 0))
        moon_radius = 1737e3  # meters
        
        # Direction from moon center to vehicle
        radial_direction = (vehicle_state.position - moon_position).normalized()
        
        # Thrust opposite to velocity for deceleration, with upward component
        moon_velocity = target_state.get('moon_velocity', Vector3(0, 1022, 0))
        relative_velocity = vehicle_state.velocity - moon_velocity
        
        # Blend retrograde and radial for landing
        thrust_direction = (radial_direction * 0.7 + relative_velocity.normalized() * (-0.3))
        thrust_direction = thrust_direction.normalized()
        
        return GuidanceCommand(
            thrust_direction=thrust_direction,
            thrust_magnitude=0.8,  # Reduced thrust for precision
            guidance_phase=GuidancePhase.PDI,
            target_pitch=0.0,
            target_yaw=0.0,
            estimated_error=10.0  # High precision required
        )
    
    def is_phase_complete(self, vehicle_state: VehicleState, target_state: Dict) -> bool:
        """Check if PDI is complete (landed)"""
        moon_position = target_state.get('moon_position', Vector3(384400e3, 0, 0))
        moon_radius = 1737e3
        
        altitude_above_moon = (vehicle_state.position - moon_position).magnitude() - moon_radius
        return altitude_above_moon < 100  # 100m above surface
    
    def get_phase_name(self) -> GuidancePhase:
        return GuidancePhase.PDI


class GuidanceContext:
    """Context class that manages guidance strategies"""
    
    def __init__(self, config: Dict = None):
        self.logger = logging.getLogger(__name__)
        self.config = config or {}
        
        # Initialize strategies
        self.strategies = {
            GuidancePhase.PEG: PEGStrategy(),  # Professor v27: Primary ascent guidance
            GuidancePhase.GRAVITY_TURN: GravityTurnStrategy(),
            GuidancePhase.COAST: CoastStrategy(),
            GuidancePhase.CIRCULARIZATION: CircularizationStrategy(),  # Professor v27: Orbital insertion
            GuidancePhase.TLI: TLIStrategy(),
            GuidancePhase.LOI: LOIStrategy(),
            GuidancePhase.PDI: PDIStrategy()
        }
        
        # Current strategy
        self.current_strategy: Optional[IGuidanceStrategy] = None
        self.current_phase = GuidancePhase.PEG  # Professor v27: Start with PEG
        
        # Strategy switching history
        self.strategy_history: List[Dict] = []
        
        self.logger.info("Guidance context initialized with Strategy pattern")
    
    def set_strategy(self, phase: GuidancePhase, mission_time: float = 0.0):
        """Switch to a specific guidance strategy"""
        if phase in self.strategies:
            old_phase = self.current_phase
            self.current_strategy = self.strategies[phase]
            self.current_phase = phase
            
            # Record strategy change
            self.strategy_history.append({
                'time': mission_time,
                'old_phase': old_phase,
                'new_phase': phase
            })
            
            self.logger.info(f"Guidance strategy switched: {old_phase.value} → {phase.value}")
        else:
            self.logger.error(f"Unknown guidance phase: {phase}")
    
    def compute_guidance(self, vehicle_state: VehicleState, 
                        target_state: Dict) -> GuidanceCommand:
        """Compute guidance using current strategy"""
        if self.current_strategy is None:
            self.set_strategy(GuidancePhase.PEG, vehicle_state.time)  # Professor v27: Default to PEG
        
        # Check if current phase is complete and auto-switch if needed
        if self.current_strategy.is_phase_complete(vehicle_state, target_state):
            next_phase = self._get_next_phase(self.current_phase, vehicle_state)
            if next_phase != self.current_phase:
                self.set_strategy(next_phase, vehicle_state.time)
        
        # Compute guidance with current strategy
        command = self.current_strategy.compute_guidance(vehicle_state, target_state, self.config)
        
        return command
    
    def _get_next_phase(self, current_phase: GuidancePhase, 
                       vehicle_state: VehicleState) -> GuidancePhase:
        """Determine next guidance phase based on mission state"""
        
        # Phase transition logic based on mission requirements
        if current_phase == GuidancePhase.PEG:
            # After PEG (MECO), coast to apoapsis
            return GuidancePhase.COAST
        elif current_phase == GuidancePhase.GRAVITY_TURN:
            # After gravity turn, coast to apoapsis
            return GuidancePhase.COAST
        elif current_phase == GuidancePhase.COAST:
            # After coast, start circularization burn at apoapsis
            return GuidancePhase.CIRCULARIZATION
        elif current_phase == GuidancePhase.CIRCULARIZATION:
            # After circularization, check if ready for TLI or stay in LEO
            if vehicle_state.mission_phase == MissionPhase.TLI_BURN:
                return GuidancePhase.TLI
            return GuidancePhase.COAST  # Stay in LEO
        elif current_phase == GuidancePhase.TLI:
            # After TLI, coast to moon
            return GuidancePhase.COAST
        elif current_phase == GuidancePhase.LOI:
            # After LOI, coast in lunar orbit
            return GuidancePhase.COAST
        elif current_phase == GuidancePhase.PDI:
            # PDI is final phase
            return GuidancePhase.PDI
        
        return current_phase  # Default: no change
    
    def force_strategy_switch(self, phase: GuidancePhase, mission_time: float = 0.0):
        """Force switch to specific strategy (for abort scenarios)"""
        self.logger.warning(f"Forced guidance strategy switch to {phase.value}")
        self.set_strategy(phase, mission_time)
    
    def get_current_phase(self) -> GuidancePhase:
        """Get current guidance phase"""
        return self.current_phase
    
    def get_strategy_history(self) -> List[Dict]:
        """Get strategy switching history"""
        return self.strategy_history.copy()
    
    def reset(self):
        """Reset guidance context to initial state"""
        self.current_strategy = None
        self.current_phase = GuidancePhase.PEG  # Professor v27: Default to PEG
        self.strategy_history.clear()
        self.logger.info("Guidance context reset")


class GuidanceFactory:
    """Factory for creating guidance strategies"""
    
    @staticmethod
    def create_strategy(phase: GuidancePhase) -> IGuidanceStrategy:
        """Create a strategy instance for the given phase"""
        strategy_map = {
            GuidancePhase.PEG: PEGStrategy,  # Professor v27: Primary guidance
            GuidancePhase.GRAVITY_TURN: GravityTurnStrategy,
            GuidancePhase.COAST: CoastStrategy,
            GuidancePhase.CIRCULARIZATION: CircularizationStrategy,  # Professor v27: Orbital insertion
            GuidancePhase.TLI: TLIStrategy,
            GuidancePhase.LOI: LOIStrategy,
            GuidancePhase.PDI: PDIStrategy
        }
        
        if phase in strategy_map:
            return strategy_map[phase]()
        else:
            raise ValueError(f"Unknown guidance phase: {phase}")
    
    @staticmethod
    def create_context(config: Dict = None) -> GuidanceContext:
        """Create a configured guidance context"""
        return GuidanceContext(config)


def main():
    """Test the guidance strategy system"""
    print("Guidance Strategy Pattern Test")
    print("=" * 40)
    
    # Create guidance context
    guidance_context = GuidanceFactory.create_context()
    
    # Test scenarios
    test_scenarios = [
        # Launch scenario
        {
            'time': 10.0,
            'vehicle_state': VehicleState(
                position=Vector3(0, 6371000, 0),  # Earth surface
                velocity=Vector3(100, 200, 0),     # Early ascent
                altitude=500,
                mass=2800000,
                mission_phase=MissionPhase.GRAVITY_TURN,
                time=10.0
            ),
            'target_state': {'target_apoapsis': 200000},
            'description': "Early gravity turn"
        },
        
        # High altitude scenario
        {
            'time': 300.0,
            'vehicle_state': VehicleState(
                position=Vector3(100000, 6471000, 0),  # 100 km altitude
                velocity=Vector3(7500, 1000, 0),        # Near orbital
                altitude=100000,
                mass=500000,
                mission_phase=MissionPhase.LEO,
                time=300.0
            ),
            'target_state': {'target_apoapsis': 200000},
            'description': "LEO scenario"
        },
        
        # TLI scenario
        {
            'time': 5000.0,
            'vehicle_state': VehicleState(
                position=Vector3(0, 6571000, 0),   # 200 km altitude
                velocity=Vector3(7800, 0, 0),       # Orbital velocity
                altitude=200000,
                mass=450000,
                mission_phase=MissionPhase.TLI_BURN,
                time=5000.0
            ),
            'target_state': {'target_apoapsis': 200000},
            'description': "TLI burn"
        }
    ]
    
    for scenario in test_scenarios:
        print(f"\n--- {scenario['description']} (t={scenario['time']}s) ---")
        
        # Force appropriate strategy for test
        if scenario['description'] == "TLI burn":
            guidance_context.force_strategy_switch(GuidancePhase.TLI, scenario['time'])
        
        # Compute guidance
        command = guidance_context.compute_guidance(
            scenario['vehicle_state'], 
            scenario['target_state']
        )
        
        print(f"Guidance phase: {command.guidance_phase.value}")
        print(f"Thrust magnitude: {command.thrust_magnitude:.1%}")
        print(f"Target pitch: {command.target_pitch:.1f}°")
        print(f"Estimated error: {command.estimated_error:.1f}m")
        print(f"Thrust direction: ({command.thrust_direction.x:.2f}, "
              f"{command.thrust_direction.y:.2f}, {command.thrust_direction.z:.2f})")
    
    # Show strategy history
    print(f"\nStrategy switching history:")
    history = guidance_context.get_strategy_history()
    for switch in history:
        print(f"  t={switch['time']:.0f}s: {switch['old_phase'].value} → {switch['new_phase'].value}")
    
    print("\n✅ Guidance strategy pattern test completed")


if __name__ == "__main__":
    main()