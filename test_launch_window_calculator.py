import unittest
import numpy as np
import math
from launch_window_calculator import LaunchWindowCalculator

class TestLaunchWindowCalculator(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures."""
        self.calculator = LaunchWindowCalculator(parking_orbit_altitude=200e3)
        
    def test_initialization(self):
        """Test calculator initialization."""
        self.assertEqual(self.calculator.parking_orbit_altitude, 200e3)
        self.assertEqual(self.calculator.parking_orbit_radius, 6371e3 + 200e3)
        
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
        self.assertEqual(info['parking_orbit_altitude_km'], 200)
        
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
        
if __name__ == '__main__':
    unittest.main()