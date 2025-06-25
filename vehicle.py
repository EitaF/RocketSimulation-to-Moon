"""
Vehicle Definitions - Single Source of Truth for Physics Classes
Consolidates Vector3, RocketStage, and Rocket classes to eliminate duplication
Professor v13: Remove duplicate definitions across modules
"""

import numpy as np
import json
from dataclasses import dataclass
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
    
    def get_thrust(self, altitude: float) -> float:
        """Get thrust based on altitude"""
        if altitude < 0:
            return self.thrust_sea_level
        elif altitude > 100e3:  # Above 100km is vacuum
            return self.thrust_vacuum
        else:
            # Linear interpolation between 0-100km
            factor = altitude / 100e3
            return self.thrust_sea_level * (1 - factor) + self.thrust_vacuum * factor
    
    def get_specific_impulse(self, altitude: float) -> float:
        """Get specific impulse based on altitude"""
        if altitude < 0:
            return self.specific_impulse_sea_level
        elif altitude > 100e3:  # Above 100km is vacuum
            return self.specific_impulse_vacuum
        else:
            # Linear interpolation between 0-100km
            factor = altitude / 100e3
            return self.specific_impulse_sea_level * (1 - factor) + self.specific_impulse_vacuum * factor
    
    def get_mass_flow_rate(self, altitude: float) -> float:
        """Get mass flow rate [kg/s] based on altitude"""
        thrust = self.get_thrust(altitude)
        isp = self.get_specific_impulse(altitude)
        return thrust / (isp * STANDARD_GRAVITY)


@dataclass
class Rocket:
    """Multi-stage rocket with flight state"""
    stages: List[RocketStage]
    payload_mass: float  # Payload mass [kg]
    drag_coefficient: float
    cross_sectional_area: float  # [m^2]
    current_stage: int = 0
    stage_start_time: float = 0.0
    
    @property
    def total_mass(self) -> float:
        """Calculate total rocket mass including all remaining stages and payload"""
        remaining_mass = self.payload_mass
        for i in range(self.current_stage, len(self.stages)):
            remaining_mass += self.stages[i].total_mass
        return remaining_mass
    
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
        if stage and stage.propellant_mass > 0:
            return stage.get_mass_flow_rate(altitude)
        return 0.0
    
    def is_stage_complete(self, current_time: float, dynamic_pressure: float = 0, altitude: float = 0) -> bool:
        """
        Check if current stage burn is complete
        Professor v15: Stage-1 cutoff requires altitude > 45km AND dynamic pressure < 50 kPa
        """
        stage = self.current_stage_obj
        if not stage:
            return True
        
        stage_elapsed_time = current_time - self.stage_start_time
        propellant_remaining_pct = stage.propellant_mass / (stage.propellant_mass + 1e-6) * 100
        
        # Professor v15: Stage-1 specific logic with altitude requirement
        if self.current_stage == 0:  # Stage 1 (S-IC)
            # Stage-1 cutoff when: (dynamic pressure < 50 kPa AND altitude > 45km AND time > 120s) OR propellant < 1%
            altitude_condition = altitude > 45000  # Professor v15: Must reach 45km altitude
            dynamic_pressure_condition = (dynamic_pressure < 50000 and stage_elapsed_time > 120 and altitude_condition)
            propellant_condition = (propellant_remaining_pct < 1.0 or stage.propellant_mass <= 0.1)
            return dynamic_pressure_condition or propellant_condition
        else:
            # Other stages: conventional logic
            return (stage.propellant_mass <= 0.1 or 
                   stage_elapsed_time >= stage.burn_time)
    
    def separate_stage(self, current_time: float) -> bool:
        """Separate current stage and activate next stage"""
        if self.current_stage < len(self.stages) - 1:
            self.current_stage += 1
            self.stage_start_time = current_time
            return True
        return False


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