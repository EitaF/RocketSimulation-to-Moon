#!/usr/bin/env python3
"""
LEO State Schema Definition
Professor v44 Feedback: Standardized state vector hand-over

This module defines the LEO state schema for handoff between launch and lunar phases.
Units: km, km/s, kg, rad (as specified by professor)
"""

from pydantic import BaseModel, Field, field_validator
from typing import List
import json
import numpy as np


class LEOStateSchema(BaseModel):
    """
    LEO (Low Earth Orbit) state schema for mission handoff
    
    Units as specified by professor:
    - Position: km
    - Velocity: km/s  
    - Mass: kg
    - Angles: rad
    """
    
    time: float = Field(
        ..., 
        description="UTC timestamp when state was captured",
        ge=0.0
    )
    
    position: List[float] = Field(
        ...,
        description="Position vector [x, y, z] in Earth-centered inertial frame (km)",
        min_items=3,
        max_items=3
    )
    
    velocity: List[float] = Field(
        ...,
        description="Velocity vector [vx, vy, vz] in Earth-centered inertial frame (km/s)",
        min_items=3,
        max_items=3
    )
    
    mass: float = Field(
        ...,
        description="Total spacecraft mass including fuel (kg)",
        gt=0.0
    )
    
    RAAN: float = Field(
        ...,
        description="Right Ascension of Ascending Node (rad)",
        ge=0.0,
        le=2*np.pi
    )
    
    eccentricity: float = Field(
        ...,
        description="Orbital eccentricity (dimensionless)",
        ge=0.0,
        lt=1.0
    )
    
    @field_validator('position')
    @classmethod
    def validate_position(cls, v):
        """Validate position is reasonable for LEO"""
        r = np.linalg.norm(v)
        earth_radius_km = 6371.0
        
        if r < earth_radius_km + 150:
            raise ValueError(f"Position too low: {r:.1f} km radius (minimum ~6521 km for 150km altitude)")
        
        if r > earth_radius_km + 2000:
            raise ValueError(f"Position too high: {r:.1f} km radius (maximum ~8371 km for 2000km altitude)")
        
        return v
    
    @field_validator('velocity')
    @classmethod
    def validate_velocity(cls, v):
        """Validate velocity is reasonable for LEO"""
        speed = np.linalg.norm(v)
        
        if speed < 6.5:  # km/s
            raise ValueError(f"Velocity too low: {speed:.2f} km/s (minimum ~6.5 km/s for LEO)")
        
        if speed > 11.2:  # km/s
            raise ValueError(f"Velocity too high: {speed:.2f} km/s (maximum ~11.2 km/s escape velocity)")
        
        return v
    
    @field_validator('eccentricity')
    @classmethod
    def validate_eccentricity_for_leo(cls, v):
        """Validate eccentricity meets professor's LEO criteria"""
        if v > 0.01:
            raise ValueError(f"Eccentricity too high: {v:.4f} (LEO requirement: ecc < 0.01)")
        
        return v
    
    @field_validator('mass')
    @classmethod
    def validate_mass_range(cls, v):
        """Validate mass is in reasonable range for launch vehicle"""
        if v < 10000:  # 10 tons minimum
            raise ValueError(f"Mass too low: {v:.0f} kg (minimum 10,000 kg)")
        
        if v > 100000:  # 100 tons maximum  
            raise ValueError(f"Mass too high: {v:.0f} kg (maximum 100,000 kg)")
        
        return v
    
    def get_altitude_km(self) -> float:
        """Calculate altitude above Earth surface in km"""
        earth_radius_km = 6371.0
        return np.linalg.norm(self.position) - earth_radius_km
    
    def get_orbital_velocity_km_s(self) -> float:
        """Calculate orbital velocity magnitude in km/s"""
        return np.linalg.norm(self.velocity)
    
    def validate_leo_criteria(self) -> dict:
        """
        Validate state meets LEO criteria from professor feedback
        Returns validation results
        """
        altitude = self.get_altitude_km()
        results = {
            'altitude_ok': 180 <= altitude <= 200,  # Target: 185 ± 5 km
            'altitude_value': altitude,
            'eccentricity_ok': self.eccentricity < 0.01,
            'eccentricity_value': self.eccentricity,
            'meets_criteria': True
        }
        
        results['meets_criteria'] = results['altitude_ok'] and results['eccentricity_ok']
        
        return results
    
    def to_meters_and_mps(self) -> dict:
        """
        Convert to meters and m/s for use with physics simulation
        Returns dictionary with converted units
        """
        return {
            'time': self.time,
            'position': [p * 1000 for p in self.position],  # km -> m
            'velocity': [v * 1000 for v in self.velocity],  # km/s -> m/s
            'mass': self.mass,  # kg (no conversion)
            'RAAN': self.RAAN,  # rad (no conversion)
            'eccentricity': self.eccentricity  # dimensionless (no conversion)
        }


def validate_leo_state_json(json_data) -> tuple[bool, str, LEOStateSchema]:
    """
    Validate LEO state JSON data against schema
    
    Args:
        json_data: JSON string or dictionary
        
    Returns:
        Tuple of (is_valid, error_message, parsed_state)
    """
    try:
        if isinstance(json_data, str):
            data = json.loads(json_data)
        else:
            data = json_data
        
        leo_state = LEOStateSchema(**data)
        
        # Additional validation
        validation_results = leo_state.validate_leo_criteria()
        
        if not validation_results['meets_criteria']:
            error_msg = f"LEO criteria not met: altitude={validation_results['altitude_value']:.1f}km, ecc={validation_results['eccentricity_value']:.4f}"
            return False, error_msg, None
        
        return True, "Validation successful", leo_state
        
    except Exception as e:
        return False, f"Validation failed: {str(e)}", None


def create_demo_leo_state() -> LEOStateSchema:
    """Create demo LEO state for testing"""
    return LEOStateSchema(
        time=1704067200.0,  # 2024-01-01 00:00:00 UTC
        position=[6556.0, 0.0, 0.0],  # 185 km altitude circular orbit
        velocity=[0.0, 7.788, 0.0],  # Circular orbital velocity
        mass=45000.0,  # 45 tons total mass
        RAAN=0.5,  # ~28.6 degrees
        eccentricity=0.005  # Nearly circular
    )


if __name__ == "__main__":
    # Test the schema
    demo_state = create_demo_leo_state()
    print("Demo LEO State:")
    print(demo_state.model_dump_json(indent=2))
    
    validation = demo_state.validate_leo_criteria()
    print(f"\nValidation: {validation}")
    
    # Test JSON validation
    json_str = demo_state.model_dump_json()
    is_valid, message, parsed = validate_leo_state_json(json_str)
    print(f"\nJSON Validation: {is_valid}, {message}")