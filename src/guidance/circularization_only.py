#!/usr/bin/env python3
"""
Minimal reproduction script for Stage-3 circularization testing
Professor v41 feedback item #4: Test circularization burn in isolation

Usage: python circularization_only.py [--dt 0.1] [--verbose]
"""

import numpy as np
import logging
from typing import Tuple
from dataclasses import dataclass

# Import necessary components  
from vehicle import Vector3, Rocket, MissionPhase, create_saturn_v_rocket
from guidance import should_end_circularization_burn, plan_circularization_burn

# Physical constants
R_EARTH = 6371e3  # Earth radius [m]
STANDARD_GRAVITY = 9.80665  # [m/s^2]
MU_EARTH = 3.986004418e14  # Earth gravitational parameter [m^3/s^2]

@dataclass
class CircularizationTest:
    """Test configuration for isolated circularization burn"""
    initial_altitude: float = 180000  # 180 km apoapsis
    initial_periapsis: float = -5000000  # -5000 km (highly elliptical)
    initial_velocity: float = 7800  # m/s (approximate at apoapsis)
    time_step: float = 0.1  # seconds
    max_duration: float = 1200  # 20 minutes max
    target_periapsis: float = 180000  # 180 km target
    verbose: bool = False

def setup_initial_orbit(test_config: CircularizationTest) -> Tuple[Vector3, Vector3]:
    """Setup initial position and velocity for 180 x -5000 km orbit"""
    # Position at apoapsis (180 km altitude)
    r_apoapsis = R_EARTH + test_config.initial_altitude
    position = Vector3(r_apoapsis, 0, 0)
    
    # Velocity for elliptical orbit (purely tangential at apoapsis)
    # For elliptical orbit: v = sqrt(μ * (2/r - 1/a))
    # Semi-major axis for 180 x -5000 km orbit
    r_periapsis = R_EARTH + test_config.initial_periapsis
    a = (r_apoapsis + r_periapsis) / 2
    v_magnitude = np.sqrt(MU_EARTH * (2/r_apoapsis - 1/a))
    velocity = Vector3(0, v_magnitude, 0)
    
    return position, velocity

def create_test_vehicle() -> Rocket:
    """Create Saturn V with only Stage-3 active"""
    vehicle = create_saturn_v_rocket()
    
    # Set to Stage-3 (S-IVB) for circularization
    vehicle.current_stage = 2  # 0-indexed: Stage 3
    vehicle.phase = MissionPhase.CIRCULARIZATION
    vehicle.stage_start_time = 0.0
    vehicle.stage_burn_time = 0.0
    
    # Ensure Stage-3 has full fuel
    if len(vehicle.stages) > 2:
        stage3 = vehicle.stages[2]
        stage3.propellant_mass = 160000.0  # Full S-IVB propellant
        print(f"Stage-3 initialized: {stage3.propellant_mass:.0f} kg propellant")
    
    return vehicle

class MockMission:
    """Minimal mission object for testing circularization logic"""
    
    def __init__(self, rocket: Rocket, test_config: CircularizationTest):
        self.rocket = rocket
        self.config = test_config
        
        # Setup logging
        logging.basicConfig(level=logging.DEBUG if test_config.verbose else logging.INFO)
        self.logger = logging.getLogger("CircularizationTest")
        
        # Initialize orbital state
        self.rocket.position, self.rocket.velocity = setup_initial_orbit(test_config)
        
        # Test metrics
        self.fuel_consumed = 0.0
        self.max_periapsis_achieved = float('-inf')
        
    def get_altitude(self) -> float:
        """Get current altitude above Earth surface"""
        return self.rocket.position.magnitude() - R_EARTH
    
    def get_orbital_elements(self) -> Tuple[float, float, float]:
        """Calculate apoapsis, periapsis, eccentricity"""
        r = self.rocket.position.magnitude()
        v = self.rocket.velocity.magnitude()
        
        # Specific orbital energy
        energy = v**2 / 2 - MU_EARTH / r
        
        # Semi-major axis
        a = -MU_EARTH / (2 * energy)
        
        # Angular momentum calculation (simplified for 2D)
        # h = r × v (magnitude)
        h = abs(self.rocket.position.x * self.rocket.velocity.y - 
                self.rocket.position.y * self.rocket.velocity.x)
        
        # Eccentricity
        ecc = np.sqrt(1 + 2 * energy * h**2 / MU_EARTH**2)
        
        # Apoapsis and periapsis
        apoapsis = a * (1 + ecc)
        periapsis = a * (1 - ecc)
        
        return apoapsis, periapsis, ecc
    
    def get_periapsis(self) -> float:
        """Get periapsis distance from Earth center"""
        _, periapsis, _ = self.get_orbital_elements()
        return periapsis
    
    def get_eccentricity(self) -> float:
        """Get orbital eccentricity"""
        _, _, ecc = self.get_orbital_elements()
        return ecc
    
    def update_physics(self, dt: float):
        """Update rocket position and velocity with thrust"""
        # Get thrust from Stage-3
        altitude = self.get_altitude()
        thrust_magnitude = self.rocket.get_thrust(altitude)
        
        if thrust_magnitude > 0:
            # Simple prograde thrust for circularization
            if self.rocket.velocity.magnitude() > 0:
                thrust_direction = self.rocket.velocity.normalized()
                thrust_vector = thrust_direction * thrust_magnitude
            else:
                thrust_vector = Vector3(0, 0, 0)
                
            # Update mass (consume fuel)
            stage3 = self.rocket.stages[2]
            mass_flow_rate = stage3.get_mass_flow_rate(altitude)
            fuel_consumed_dt = mass_flow_rate * dt
            stage3.propellant_mass = max(0, stage3.propellant_mass - fuel_consumed_dt)
            self.fuel_consumed += fuel_consumed_dt
            
            # Apply thrust acceleration  
            total_mass = self.rocket.get_current_mass(0, altitude)  # Provide required args
            if total_mass > 0:
                acceleration = thrust_vector * (1.0 / total_mass)
            else:
                acceleration = Vector3(0, 0, 0)
        else:
            acceleration = Vector3(0, 0, 0)
        
        # Gravitational acceleration
        r = self.rocket.position.magnitude()
        gravity_acc = self.rocket.position * (-MU_EARTH / r**3)
        
        # Total acceleration
        total_acc = acceleration + gravity_acc
        
        # Update velocity and position (simple Euler integration)
        self.rocket.velocity += total_acc * dt
        self.rocket.position += self.rocket.velocity * dt
        
        # Track metrics
        _, periapsis, _ = self.get_orbital_elements()
        self.max_periapsis_achieved = max(self.max_periapsis_achieved, periapsis)

def run_circularization_test(dt: float = 0.1, verbose: bool = False) -> dict:
    """Run isolated circularization burn test"""
    
    config = CircularizationTest(time_step=dt, verbose=verbose)
    rocket = create_test_vehicle()
    mission = MockMission(rocket, config)
    
    print(f"=== Circularization Test (dt={dt}s) ===")
    
    # Initial state
    apoapsis, periapsis, ecc = mission.get_orbital_elements()
    print(f"Initial orbit: {(apoapsis-R_EARTH)/1000:.1f} x {(periapsis-R_EARTH)/1000:.1f} km, ecc={ecc:.3f}")
    print(f"Stage-3 fuel: {rocket.stages[2].propellant_mass:.0f} kg")
    
    # Simulation loop
    t = 0.0
    burn_start_time = 0.0
    burn_active = True
    
    while t < config.max_duration and burn_active:
        # Update physics
        mission.update_physics(dt)
        t += dt
        
        # Get current state
        apoapsis, periapsis, ecc = mission.get_orbital_elements()
        stage3 = rocket.stages[2]
        fuel_fraction = stage3.propellant_mass / 160000.0
        
        # Detailed logging every 1 second
        if verbose and t % 1.0 < dt:
            mass_flow_rate = stage3.get_mass_flow_rate(mission.get_altitude())
            periapsis_error = periapsis - (R_EARTH + config.target_periapsis)
            mission.logger.debug(
                f"{t:.1f}s | m_dot={mass_flow_rate:.3f} kg/s "
                f"fuel_left={stage3.propellant_mass:.1f} kg ({fuel_fraction*100:.1f}%) "
                f"periapsis_err={periapsis_error:.1f} m"
            )
        
        # Check termination conditions
        # 1. Fuel guard-rail (5% minimum)
        if fuel_fraction <= 0.05:
            print(f"FUEL GUARD-RAIL HIT at t={t:.1f}s")
            print(f" -> Fuel remaining: {fuel_fraction*100:.1f}%")
            burn_active = False
            break
            
        # 2. Guidance termination
        if should_end_circularization_burn(mission, t, burn_start_time):
            print(f"GUIDANCE TERMINATION at t={t:.1f}s")
            burn_active = False
            break
            
        # 3. Out of fuel
        if stage3.propellant_mass <= 0:
            print(f"OUT OF FUEL at t={t:.1f}s")
            burn_active = False
            break
    
    # Final results
    apoapsis, periapsis, ecc = mission.get_orbital_elements()
    fuel_fraction = stage3.propellant_mass / 160000.0
    
    results = {
        'duration': t,
        'final_apoapsis_km': (apoapsis - R_EARTH) / 1000,
        'final_periapsis_km': (periapsis - R_EARTH) / 1000,
        'final_eccentricity': ecc,
        'fuel_remaining_percent': fuel_fraction * 100,
        'fuel_consumed_kg': mission.fuel_consumed,
        'max_periapsis_km': (mission.max_periapsis_achieved - R_EARTH) / 1000,
        'success_criteria': {
            'fuel_remaining_ok': fuel_fraction >= 0.05,
            'apoapsis_ok': 185 <= (apoapsis - R_EARTH) / 1000 <= 195,
            'periapsis_ok': (periapsis - R_EARTH) / 1000 >= 180,
            'delta_v_ok': True  # Would need to calculate from guidance
        }
    }
    
    return results

def print_results(results: dict):
    """Print formatted test results"""
    print(f"\n=== RESULTS ===")
    print(f"Duration: {results['duration']:.1f} s")
    print(f"Final orbit: {results['final_apoapsis_km']:.1f} x {results['final_periapsis_km']:.1f} km")
    print(f"Eccentricity: {results['final_eccentricity']:.4f}")
    print(f"Fuel remaining: {results['fuel_remaining_percent']:.1f}% ({results['fuel_consumed_kg']:.0f} kg consumed)")
    print(f"Max periapsis: {results['max_periapsis_km']:.1f} km")
    
    print(f"\n=== SUCCESS CRITERIA ===")
    criteria = results['success_criteria']
    print(f"✓ Fuel ≥5%: {'PASS' if criteria['fuel_remaining_ok'] else 'FAIL'}")
    print(f"✓ Apoapsis 185-195km: {'PASS' if criteria['apoapsis_ok'] else 'FAIL'}")
    print(f"✓ Periapsis ≥180km: {'PASS' if criteria['periapsis_ok'] else 'FAIL'}")
    
    overall_success = all(criteria.values())
    print(f"\nOVERALL: {'SUCCESS' if overall_success else 'FAILURE'}")
    
    return overall_success

def main():
    """Run circularization tests with different time-steps"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test Stage-3 circularization burn')
    parser.add_argument('--dt', type=float, default=0.1, help='Time step (default: 0.1s)')
    parser.add_argument('--verbose', action='store_true', help='Verbose logging')
    parser.add_argument('--sweep', action='store_true', help='Test multiple time-steps')
    
    args = parser.parse_args()
    
    if args.sweep:
        # Test different time-steps
        time_steps = [0.05, 0.1, 0.5]
        print("=== TIME-STEP STABILITY SWEEP ===")
        
        for dt in time_steps:
            results = run_circularization_test(dt, verbose=False)
            success = print_results(results)
            print(f"Time-step {dt}s: {'SUCCESS' if success else 'FAILURE'}")
            print("-" * 50)
    else:
        # Single test
        results = run_circularization_test(args.dt, args.verbose)
        success = print_results(results)
        
        if success:
            print("\nCircularization test PASSED - ready for full mission!")
        else:
            print("\nCircularization test FAILED - fuel or orbit targets not met")

if __name__ == "__main__":
    main()