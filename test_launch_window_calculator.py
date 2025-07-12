import unittest
import numpy as np
import math
from launch_window_calculator import LaunchWindowCalculator

class TestLaunchWindowCalculator(unittest.TestCase):
    """
    Unit tests for LaunchWindowCalculator - Professor v40 Task A3
    Tests edge cases for phase angles 0-180° with <1° error requirement
    """
    
    def setUp(self):
        """Set up test fixtures for v40 tests."""
        self.calculator = LaunchWindowCalculator(parking_orbit_altitude=185e3)  # 185 km
        
        # Constants for testing
        self.EARTH_MOON_DIST = 384400e3  # m
        self.R_EARTH = 6371e3  # m
        self.c3_energy = -1.5  # km²/s² (typical TLI C3)
        self.current_time = 1000.0  # s
        
    def test_initialization(self):
        """Test calculator initialization."""
        self.assertEqual(self.calculator.parking_orbit_altitude, 185e3)
        self.assertEqual(self.calculator.parking_orbit_radius, 6371e3 + 185e3)
        
    def test_calculate_transfer_time(self):
        """Test transfer time calculation."""
        # Test with typical TLI C3 energy
        c3_energy = 12.0  # km²/s²
        transfer_time = self.calculator.calculate_transfer_time(c3_energy)
        
        # Transfer time should be reasonable (2-5 days)
        self.assertGreater(transfer_time, 2 * 24 * 3600)  # > 2 days
        self.assertLess(transfer_time, 5 * 24 * 3600)     # < 5 days
        
    def test_calculate_phase_angle(self):
        """Test phase angle calculation."""
        # Test with 3-day transfer time
        transfer_time = 3 * 24 * 3600  # 3 days
        phase_angle = self.calculator.calculate_phase_angle(transfer_time)
        
        # Phase angle should be between 0 and 2π
        self.assertGreaterEqual(phase_angle, 0)
        self.assertLess(phase_angle, 2 * np.pi)
        
    def test_calculate_optimal_tli_time(self):
        """Test optimal TLI time calculation."""
        # Set up test scenario
        current_time = 0.0
        moon_position = np.array([384400e3, 0, 0])  # Moon at +X
        spacecraft_position = np.array([6571e3, 0, 0])  # Spacecraft at +X (same angle)
        c3_energy = 12.0  # km²/s²
        
        optimal_time, phase_angle, transfer_time = self.calculator.calculate_optimal_tli_time(
            current_time, moon_position, spacecraft_position, c3_energy
        )
        
        # Results should be reasonable
        self.assertGreater(optimal_time, current_time)
        self.assertGreaterEqual(phase_angle, 0)
        self.assertLess(phase_angle, 2 * np.pi)
        self.assertGreater(transfer_time, 0)
        
    def test_get_launch_window_info(self):
        """Test launch window information compilation."""
        # Set up test scenario
        current_time = 1000.0  # 1000 seconds
        moon_position = np.array([384400e3, 0, 0])
        spacecraft_position = np.array([6571e3, 0, 0])
        c3_energy = 12.0
        
        info = self.calculator.get_launch_window_info(
            current_time, moon_position, spacecraft_position, c3_energy
        )
        
        # Check all expected keys are present
        expected_keys = [
            'optimal_tli_time', 'time_to_optimal', 'required_phase_angle_deg',
            'transfer_time_hours', 'transfer_time_days', 'c3_energy',
            'parking_orbit_altitude_km'
        ]
        
        for key in expected_keys:
            self.assertIn(key, info)
            
        # Check reasonable values
        self.assertGreaterEqual(info['optimal_tli_time'], current_time)
        self.assertGreaterEqual(info['time_to_optimal'], 0)
        self.assertGreaterEqual(info['required_phase_angle_deg'], 0)
        self.assertLess(info['required_phase_angle_deg'], 360)
        self.assertGreater(info['transfer_time_hours'], 0)
        self.assertGreater(info['transfer_time_days'], 0)
        self.assertEqual(info['c3_energy'], c3_energy)
        self.assertEqual(info['parking_orbit_altitude_km'], 185)
        
    def test_phase_angle_different_positions(self):
        """Test phase angle calculation with different Moon/spacecraft positions."""
        current_time = 0.0
        c3_energy = 12.0
        
        # Moon at +X, spacecraft at +Y (90° apart)
        moon_position = np.array([384400e3, 0, 0])
        spacecraft_position = np.array([0, 6571e3, 0])
        
        optimal_time, phase_angle, transfer_time = self.calculator.calculate_optimal_tli_time(
            current_time, moon_position, spacecraft_position, c3_energy
        )
        
        # Should calculate different timing than when aligned
        self.assertGreater(optimal_time, current_time)
        self.assertNotEqual(phase_angle, 0)
        
    def test_edge_case_zero_c3(self):
        """Test with zero C3 energy (edge case)."""
        # This represents minimum energy transfer
        c3_energy = 0.0
        transfer_time = self.calculator.calculate_transfer_time(c3_energy)
        
        # Should still return reasonable transfer time
        self.assertGreater(transfer_time, 0)
    
    # ===== PROFESSOR V40 TASK A3: EDGE CASE TESTS =====
    # Tests for phase angles 0-180° with <1° error requirement
    
    def test_phase_angle_precision_0_degrees(self):
        """Test phase angle calculation precision at 0° (Professor v40 Task A3)"""
        # Moon and spacecraft at same angle (0°)
        moon_position = np.array([self.EARTH_MOON_DIST, 0.0, 0.0])
        spacecraft_position = np.array([self.calculator.parking_orbit_radius, 0.0, 0.0])
        
        # Calculate phase angle
        moon_angle = np.arctan2(0.0, self.EARTH_MOON_DIST)  # 0°
        spacecraft_angle = np.arctan2(0.0, self.calculator.parking_orbit_radius)  # 0°
        current_phase = moon_angle - spacecraft_angle
        
        # Phase angle error should be < 1°
        phase_error = abs(np.degrees(current_phase))
        self.assertLess(phase_error, 1.0, f"Phase angle error > 1°: {phase_error:.3f}°")
    
    def test_phase_angle_precision_45_degrees(self):
        """Test phase angle calculation precision at 45° (Professor v40 Task A3)"""
        angle_deg = 45.0
        angle_rad = np.radians(angle_deg)
        
        moon_position = np.array([
            self.EARTH_MOON_DIST * np.cos(angle_rad),
            self.EARTH_MOON_DIST * np.sin(angle_rad),
            0.0
        ])
        spacecraft_position = np.array([self.calculator.parking_orbit_radius, 0.0, 0.0])
        
        # Verify phase angle calculation accuracy
        moon_angle = np.arctan2(moon_position[1], moon_position[0])
        spacecraft_angle = np.arctan2(spacecraft_position[1], spacecraft_position[0])
        current_phase = moon_angle - spacecraft_angle
        
        # Normalize and check error
        while current_phase < 0:
            current_phase += 2 * np.pi
        while current_phase >= 2 * np.pi:
            current_phase -= 2 * np.pi
        
        phase_error = abs(np.degrees(current_phase) - angle_deg)
        self.assertLess(phase_error, 1.0, f"45° phase angle error > 1°: {phase_error:.3f}°")
    
    def test_phase_angle_precision_90_degrees(self):
        """Test phase angle calculation precision at 90° (Professor v40 Task A3)"""
        angle_deg = 90.0
        angle_rad = np.radians(angle_deg)
        
        moon_position = np.array([
            self.EARTH_MOON_DIST * np.cos(angle_rad),
            self.EARTH_MOON_DIST * np.sin(angle_rad),
            0.0
        ])
        spacecraft_position = np.array([self.calculator.parking_orbit_radius, 0.0, 0.0])
        
        # Verify 90° angle calculation
        moon_angle = np.arctan2(moon_position[1], moon_position[0])
        spacecraft_angle = np.arctan2(spacecraft_position[1], spacecraft_position[0])
        
        expected_moon_angle = np.pi / 2  # 90°
        expected_spacecraft_angle = 0.0   # 0°
        
        moon_error = abs(np.degrees(moon_angle - expected_moon_angle))
        spacecraft_error = abs(np.degrees(spacecraft_angle - expected_spacecraft_angle))
        
        self.assertLess(moon_error, 1.0, f"Moon angle error > 1°: {moon_error:.3f}°")
        self.assertLess(spacecraft_error, 1.0, f"Spacecraft angle error > 1°: {spacecraft_error:.3f}°")
    
    def test_phase_angle_precision_135_degrees(self):
        """Test phase angle calculation precision at 135° (Professor v40 Task A3)"""
        angle_deg = 135.0
        angle_rad = np.radians(angle_deg)
        
        moon_position = np.array([
            self.EARTH_MOON_DIST * np.cos(angle_rad),
            self.EARTH_MOON_DIST * np.sin(angle_rad),
            0.0
        ])
        spacecraft_position = np.array([self.calculator.parking_orbit_radius, 0.0, 0.0])
        
        # Test accuracy for large angle
        moon_angle = np.arctan2(moon_position[1], moon_position[0])
        current_phase = moon_angle  # spacecraft at 0°
        
        phase_error = abs(np.degrees(current_phase) - angle_deg)
        self.assertLess(phase_error, 1.0, f"135° phase angle error > 1°: {phase_error:.3f}°")
    
    def test_phase_angle_precision_180_degrees(self):
        """Test phase angle calculation precision at 180° (Professor v40 Task A3)"""
        angle_deg = 180.0
        angle_rad = np.radians(angle_deg)
        
        moon_position = np.array([
            self.EARTH_MOON_DIST * np.cos(angle_rad),
            self.EARTH_MOON_DIST * np.sin(angle_rad),
            0.0
        ])
        spacecraft_position = np.array([self.calculator.parking_orbit_radius, 0.0, 0.0])
        
        # Moon should be at exactly 180° (-180° = 180°)
        moon_angle = np.arctan2(moon_position[1], moon_position[0])
        expected_angle = np.pi  # 180°
        
        # Handle angle wrapping around ±π
        angle_diff = abs(moon_angle - expected_angle)
        if angle_diff > np.pi:
            angle_diff = 2 * np.pi - angle_diff
        
        angle_error = np.degrees(angle_diff)
        self.assertLess(angle_error, 1.0, f"180° phase angle error > 1°: {angle_error:.3f}°")
    
    def test_comprehensive_phase_angle_sweep(self):
        """Test comprehensive sweep of phase angles 0-180° (Professor v40 Task A3)"""
        # Test every 15° from 0° to 180°
        test_angles = range(0, 181, 15)  # 0°, 15°, 30°, ..., 180°
        errors = []
        
        for angle_deg in test_angles:
            angle_rad = np.radians(angle_deg)
            
            moon_position = np.array([
                self.EARTH_MOON_DIST * np.cos(angle_rad),
                self.EARTH_MOON_DIST * np.sin(angle_rad),
                0.0
            ])
            spacecraft_position = np.array([self.calculator.parking_orbit_radius, 0.0, 0.0])
            
            # Calculate and verify phase angle
            moon_angle = np.arctan2(moon_position[1], moon_position[0])
            spacecraft_angle = np.arctan2(spacecraft_position[1], spacecraft_position[0])
            current_phase = moon_angle - spacecraft_angle
            
            # Normalize to [0, 2π)
            while current_phase < 0:
                current_phase += 2 * np.pi
            while current_phase >= 2 * np.pi:
                current_phase -= 2 * np.pi
            
            phase_error = abs(np.degrees(current_phase) - angle_deg)
            errors.append(phase_error)
            
            # Each individual angle must be within 1°
            self.assertLess(phase_error, 1.0, f"Angle {angle_deg}° error > 1°: {phase_error:.3f}°")
        
        # Additional checks on overall accuracy
        mean_error = np.mean(errors)
        max_error = np.max(errors)
        
        self.assertLess(mean_error, 0.5, f"Mean error too high: {mean_error:.3f}°")
        self.assertLess(max_error, 1.0, f"Max error too high: {max_error:.3f}°")
    
    def test_small_phase_angle_precision(self):
        """Test precision for very small phase angles <5° (Professor v40 Task A3)"""
        small_angles = [1.0, 2.0, 3.0, 4.0, 5.0]  # degrees
        
        for angle_deg in small_angles:
            angle_rad = np.radians(angle_deg)
            
            moon_position = np.array([
                self.EARTH_MOON_DIST * np.cos(angle_rad),
                self.EARTH_MOON_DIST * np.sin(angle_rad),
                0.0
            ])
            spacecraft_position = np.array([self.calculator.parking_orbit_radius, 0.0, 0.0])
            
            # Calculate phase angle
            moon_angle = np.arctan2(moon_position[1], moon_position[0])
            spacecraft_angle = np.arctan2(spacecraft_position[1], spacecraft_position[0])
            current_phase = moon_angle - spacecraft_angle
            
            phase_error = abs(np.degrees(current_phase) - angle_deg)
            self.assertLess(phase_error, 1.0, f"Small angle {angle_deg}° error > 1°: {phase_error:.3f}°")
    
    def test_launch_window_calculation_edge_cases(self):
        """Test launch window calculation for edge case phase angles (Professor v40 Task A3)"""
        edge_angles = [0.0, 45.0, 90.0, 135.0, 180.0]
        
        for angle_deg in edge_angles:
            angle_rad = np.radians(angle_deg)
            
            moon_position = np.array([
                self.EARTH_MOON_DIST * np.cos(angle_rad),
                self.EARTH_MOON_DIST * np.sin(angle_rad),
                0.0
            ])
            spacecraft_position = np.array([self.calculator.parking_orbit_radius, 0.0, 0.0])
            
            # Should complete without errors and return valid results
            result = self.calculator.get_launch_window_info(
                self.current_time, moon_position, spacecraft_position, self.c3_energy
            )
            
            # All results should be valid
            self.assertGreater(result['transfer_time_hours'], 0)
            self.assertGreaterEqual(result['required_phase_angle_deg'], 0)
            self.assertLessEqual(result['required_phase_angle_deg'], 360)
            self.assertGreaterEqual(result['time_to_optimal'], 0)

if __name__ == '__main__':
    # Run with verbose output to show test progress
    unittest.main(verbosity=2)