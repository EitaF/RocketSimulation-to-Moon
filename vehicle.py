"""
Vehicle Definitions - Single Source of Truth for Physics Classes
Consolidates Vector3, RocketStage, and Rocket classes to eliminate duplication
Professor v13: Remove duplicate definitions across modules
"""

import numpy as np
import json
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum

# Physical constants
STANDARD_GRAVITY = 9.80665  # Standard gravity acceleration [m/s^2]


class MissionPhase(Enum):
    """Mission phases for rocket flight"""
    PRE_LAUNCH = "pre_launch"
    LAUNCH = "launch"
    GRAVITY_TURN = "gravity_turn"
    STAGE_SEPARATION = "stage_separation"
    APOAPSIS_RAISE = "apoapsis_raise"
    COAST_TO_APOAPSIS = "coast_to_apoapsis"
    CIRCULARIZATION = "circularization"
    LEO = "leo"
    TLI_BURN = "tli_burn"
    COAST_TO_MOON = "coast_to_moon"
    MID_COURSE_CORRECTION = "mid_course_correction"
    LOI_BURN = "loi_burn"
    LUNAR_ORBIT = "lunar_orbit"
    PDI = "pdi"
    TERMINAL_DESCENT = "terminal_descent"
    LUNAR_TOUCHDOWN = "lunar_touchdown"
    LANDED = "landed"
    FAILED = "failed"


class Vector3:
    """3D vector class for physics calculations"""
    
    def __init__(self, x: float, y: float, z: float = 0.0):
        self.data = np.array([x, y, z])
    
    @property
    def x(self) -> float:
        return self.data[0]
    
    @property
    def y(self) -> float:
        return self.data[1]
    
    @property
    def z(self) -> float:
        return self.data[2]
    
    def magnitude(self) -> float:
        return np.linalg.norm(self.data)
    
    def normalized(self) -> 'Vector3':
        mag = self.magnitude()
        if mag == 0:
            return Vector3(0, 0, 0)
        return Vector3(*(self.data / mag))
    
    def __add__(self, other: 'Vector3') -> 'Vector3':
        return Vector3(*(self.data + other.data))
    
    def __sub__(self, other: 'Vector3') -> 'Vector3':
        return Vector3(*(self.data - other.data))
    
    def __mul__(self, scalar: float) -> 'Vector3':
        return Vector3(*(self.data * scalar))
    
    def __repr__(self) -> str:
        return f"Vector3({self.x:.2e}, {self.y:.2e}, {self.z:.2e})"


@dataclass
class RocketStage:
    """Rocket stage data and methods"""
    name: str
    dry_mass: float  # Dry mass [kg]
    propellant_mass: float  # Propellant mass [kg]
    thrust_sea_level: float  # Sea level thrust [N]
    thrust_vacuum: float  # Vacuum thrust [N]
    specific_impulse_sea_level: float  # Sea level specific impulse [s]
    specific_impulse_vacuum: float  # Vacuum specific impulse [s]
    burn_time: float  # Burn time [s]
    
    @property
    def total_mass(self) -> float:
        return self.dry_mass + self.propellant_mass
    
    def get_thrust(self, altitude: float, throttle: float = 1.0) -> float:
        """Get thrust based on altitude using enhanced engine model if available"""
        try:
            # Try to use enhanced engine model
            from engine import get_engine_model
            engine_model = get_engine_model()
            
            # Map stage name to engine model stage identifier
            stage_id = self._get_stage_identifier()
            if stage_id:
                return engine_model.get_thrust(stage_id, altitude, throttle)
        except (ImportError, Exception):
            # Fallback to linear interpolation
            pass
        
        # Fallback linear interpolation
        if altitude < 0:
            base_thrust = self.thrust_sea_level
        elif altitude > 100e3:  # Above 100km is vacuum
            base_thrust = self.thrust_vacuum
        else:
            # Linear interpolation between 0-100km
            factor = altitude / 100e3
            base_thrust = self.thrust_sea_level * (1 - factor) + self.thrust_vacuum * factor
        
        return base_thrust * throttle
    
    def get_specific_impulse(self, altitude: float) -> float:
        """Get specific impulse based on altitude using enhanced engine model if available"""
        try:
            # Try to use enhanced engine model
            from engine import get_engine_model
            engine_model = get_engine_model()
            
            # Map stage name to engine model stage identifier
            stage_id = self._get_stage_identifier()
            if stage_id:
                return engine_model.get_specific_impulse(stage_id, altitude)
        except (ImportError, Exception):
            # Fallback to linear interpolation
            pass
        
        # Fallback linear interpolation
        if altitude < 0:
            return self.specific_impulse_sea_level
        elif altitude > 100e3:  # Above 100km is vacuum
            return self.specific_impulse_vacuum
        else:
            # Linear interpolation between 0-100km
            factor = altitude / 100e3
            return self.specific_impulse_sea_level * (1 - factor) + self.specific_impulse_vacuum * factor
    
    def _get_stage_identifier(self) -> str:
        """Map stage name to engine model identifier"""
        name_lower = self.name.lower()
        if 's-ic' in name_lower or '1st' in name_lower or 'first' in name_lower:
            return 'S-IC'
        elif 's-ii' in name_lower or '2nd' in name_lower or 'second' in name_lower:
            return 'S-II'
        elif 's-ivb' in name_lower or '3rd' in name_lower or 'third' in name_lower:
            return 'S-IVB'
        return None
    
    def get_mass_flow_rate(self, altitude: float) -> float:
        """Get mass flow rate [kg/s] based on altitude"""
        thrust = self.get_thrust(altitude)
        isp = self.get_specific_impulse(altitude)
        return thrust / (isp * STANDARD_GRAVITY)

    def get_mass_at_time(self, burn_duration: float, altitude: float) -> float:
        """Gets the mass of the stage after a given burn duration."""
        if burn_duration <= 0:
            return self.total_mass
        if burn_duration >= self.burn_time:
            return self.dry_mass
        
        mass_flow = self.get_mass_flow_rate(altitude)
        propellant_consumed = mass_flow * burn_duration
        return self.total_mass - propellant_consumed


@dataclass
class Rocket:
    """Multi-stage rocket with flight state"""
    stages: List[RocketStage]
    payload_mass: float  # Payload mass [kg]
    drag_coefficient: float
    cross_sectional_area: float  # [m^2]
    current_stage: int = 0
    stage_start_time: float = 0.0
    phase: MissionPhase = MissionPhase.PRE_LAUNCH
    position: Vector3 = field(default_factory=lambda: Vector3(0, 0, 0))
    velocity: Vector3 = field(default_factory=lambda: Vector3(0, 0, 0))
    
    @property
    def total_mass(self) -> float:
        """Calculate total rocket mass including all remaining stages and payload"""
        # This property should not be used for time-dependent mass calculations
        # during the simulation. It is primarily for initialization.
        # The time-dependent mass is calculated in the Mission class.
        return self.payload_mass + sum(s.total_mass for s in self.stages)
    
    def get_current_mass(self, current_time: float, altitude: float) -> float:
        """
        Calculate current total mass accounting for propellant consumption
        
        Args:
            current_time: Current simulation time [s]
            altitude: Current altitude [m] for calculating mass flow rate
            
        Returns:
            Current total mass [kg] including consumed propellant
        """
        total_mass = self.payload_mass
        
        # Add mass from all stages after current stage (not yet used)
        for i in range(self.current_stage + 1, len(self.stages)):
            total_mass += self.stages[i].total_mass
        
        # Add mass from current stage, accounting for propellant consumption
        if self.current_stage < len(self.stages):
            current_stage = self.stages[self.current_stage]
            stage_elapsed_time = current_time - self.stage_start_time
            
            # Calculate current stage mass using get_mass_at_time
            current_stage_mass = current_stage.get_mass_at_time(stage_elapsed_time, altitude)
            total_mass += current_stage_mass
        
        # Add dry mass from all previous stages (already consumed)
        for i in range(self.current_stage):
            total_mass += self.stages[i].dry_mass
        
        return total_mass
    
    @property
    def current_stage_obj(self) -> Optional[RocketStage]:
        """Get current active stage object"""
        if self.current_stage < len(self.stages):
            return self.stages[self.current_stage]
        return None
    
    def get_thrust(self, altitude: float) -> float:
        """Get current thrust based on altitude"""
        stage = self.current_stage_obj
        if stage and stage.propellant_mass > 0:
            return stage.get_thrust(altitude)
        return 0.0
    
    def get_mass_flow_rate(self, altitude: float) -> float:
        """Get current mass flow rate [kg/s]"""
        stage = self.current_stage_obj
        if stage and self.is_thrusting(0, altitude):
            return stage.get_mass_flow_rate(altitude)
        return 0.0

    def is_thrusting(self, current_time: float, altitude: float) -> bool:
        stage = self.current_stage_obj
        if not stage:
            return False
        
        stage_elapsed_time = current_time - self.stage_start_time
        return stage_elapsed_time < stage.burn_time and stage.propellant_mass > 0
    
    def separate_stage(self, current_time: float) -> bool:
        """Separate current stage and activate next stage"""
        if self.current_stage < len(self.stages) - 1:
            self.current_stage += 1
            self.stage_start_time = current_time
            return True
        return False
    
    def update_stage(self, dt: float):
        """
        Update stage burn time and handle automatic stage separation
        Called every simulation time step to manage stage transitions
        """
        if not hasattr(self, 'stage_burn_time'):
            self.stage_burn_time = 0.0
        
        # Update burn time for current stage
        stage = self.current_stage_obj
        if stage and self.is_thrusting(self.stage_burn_time + self.stage_start_time, 0):
            self.stage_burn_time += dt
            
            # Check if stage should separate (burn time exceeded)
            if self.stage_burn_time >= stage.burn_time:
                if self.current_stage < len(self.stages) - 1:
                    # Auto-separate to next stage
                    self.separate_stage(self.stage_burn_time + self.stage_start_time)
                    self.stage_burn_time = 0.0


def calculate_burn_time(propellant_mass: float, thrust_vacuum: float, isp_vacuum: float) -> float:
    """
    Calculate burn time programmatically from propellant, thrust, and Isp
    Professor v10: mdot = thrust_vac / (isp_vac * STANDARD_GRAVITY)
                   burn_time = propellant_mass / mdot
    """
    mass_flow_rate = thrust_vacuum / (isp_vacuum * STANDARD_GRAVITY)
    burn_time = propellant_mass / mass_flow_rate
    return burn_time


def create_saturn_v_rocket(config_path: str = "saturn_v_config.json") -> Rocket:
    """
    Create Saturn V rocket from configuration file
    Professor v13: Use config files instead of hard-coded values
    """
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        # Fallback to default configuration if file not found
        config = get_default_saturn_v_config()
    
    stages = []
    for stage_config in config["stages"]:
        stage = RocketStage(
            name=stage_config["name"],
            dry_mass=stage_config["dry_mass"],
            propellant_mass=stage_config["propellant_mass"],
            thrust_sea_level=stage_config["thrust_sea_level"],
            thrust_vacuum=stage_config["thrust_vacuum"],
            specific_impulse_sea_level=stage_config["specific_impulse_sea_level"],
            specific_impulse_vacuum=stage_config["specific_impulse_vacuum"],
            burn_time=stage_config["burn_time"]
        )
        stages.append(stage)
    
    rocket = Rocket(
        stages=stages,
        payload_mass=config["rocket"]["payload_mass"],
        drag_coefficient=config["rocket"]["drag_coefficient"],
        cross_sectional_area=config["rocket"]["cross_sectional_area"]
    )
    
    return rocket


def get_default_saturn_v_config() -> dict:
    """Default Saturn V configuration if config file is missing"""
    return {
        "stages": [
            {
                "name": "S-IC (1st Stage)",
                "dry_mass": 130000,
                "propellant_mass": 2150000,
                "thrust_sea_level": 34020000,
                "thrust_vacuum": 35100000,
                "specific_impulse_sea_level": 263,
                "specific_impulse_vacuum": 289,
                "burn_time": 168
            },
            {
                "name": "S-II (2nd Stage)",
                "dry_mass": 40000,
                "propellant_mass": 480000,
                "thrust_sea_level": 4400000,
                "thrust_vacuum": 5000000,
                "specific_impulse_sea_level": 395,
                "specific_impulse_vacuum": 421,
                "burn_time": 420
            },
            {
                "name": "S-IVB (3rd Stage)",
                "dry_mass": 13500,
                "propellant_mass": 160000,
                "thrust_sea_level": 825000,
                "thrust_vacuum": 1000000,
                "specific_impulse_sea_level": 395,
                "specific_impulse_vacuum": 421,
                "burn_time": 900
            }
        ],
        "rocket": {
            "name": "Saturn V",
            "payload_mass": 45000,
            "drag_coefficient": 0.3,
            "cross_sectional_area": 80.0
        }
    }