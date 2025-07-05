import unittest
import numpy as np
from mid_course_correction import MidCourseCorrection, MCCBurn

class TestMidCourseCorrection(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures."""
        self.mcc = MidCourseCorrection()
        
    def test_initialization(self):
        """Test MCC module initialization."""
        self.assertEqual(len(self.mcc.scheduled_burns), 0)
        self.assertEqual(len(self.mcc.executed_burns), 0)
        
    def test_execute_mcc_burn(self):
        """Test execution of a single MCC burn."""
        # Initial spacecraft state
        position = np.array([7000e3, 0, 0])  # 7000 km from Earth center
        velocity = np.array([0, 7.5e3, 0])   # 7.5 km/s orbital velocity
        spacecraft_state = (position, velocity)
        
        # Delta-V burn
        delta_v = np.array([100, 0, 0])  # 100 m/s in X direction
        
        # Execute burn
        new_position, new_velocity = self.mcc.execute_mcc_burn(spacecraft_state, delta_v)
        
        # Check results
        np.testing.assert_array_equal(new_position, position)  # Position unchanged
        np.testing.assert_array_equal(new_velocity, velocity + delta_v)  # Velocity changed
        
    def test_schedule_burn(self):
        """Test scheduling of MCC burns."""
        # Schedule a burn
        burn_time = 3600.0  # 1 hour
        delta_v = np.array([50, 0, 0])
        description = "Test burn"
        
        self.mcc.schedule_burn(burn_time, delta_v, description=description)
        
        # Check burn was scheduled
        self.assertEqual(len(self.mcc.scheduled_burns), 1)
        burn = self.mcc.scheduled_burns[0]
        self.assertEqual(burn.burn_time, burn_time)
        np.testing.assert_array_equal(burn.delta_v_vector, delta_v)
        self.assertEqual(burn.description, description)
        self.assertFalse(burn.executed)
        
    def test_multiple_scheduled_burns_sorted(self):
        """Test that multiple burns are sorted by time."""
        # Schedule burns out of order
        self.mcc.schedule_burn(7200.0, np.array([10, 0, 0]), description="Second burn")
        self.mcc.schedule_burn(3600.0, np.array([20, 0, 0]), description="First burn")
        self.mcc.schedule_burn(10800.0, np.array([30, 0, 0]), description="Third burn")
        
        # Check they are sorted by time
        burn_times = [burn.burn_time for burn in self.mcc.scheduled_burns]
        self.assertEqual(burn_times, [3600.0, 7200.0, 10800.0])
        
    def test_check_and_execute_burns(self):
        """Test automatic execution of scheduled burns."""
        # Schedule burns
        self.mcc.schedule_burn(1000.0, np.array([10, 0, 0]), description="Early burn")
        self.mcc.schedule_burn(2000.0, np.array([20, 0, 0]), description="Late burn")
        
        # Initial state
        position = np.array([7000e3, 0, 0])
        velocity = np.array([0, 7.5e3, 0])
        
        # Check at time before first burn
        current_time = 500.0
        new_pos, new_vel = self.mcc.check_and_execute_burns(current_time, (position, velocity))
        
        # No burns should be executed yet
        np.testing.assert_array_equal(new_pos, position)
        np.testing.assert_array_equal(new_vel, velocity)
        self.assertEqual(len(self.mcc.scheduled_burns), 2)
        self.assertEqual(len(self.mcc.executed_burns), 0)
        
        # Check at time after first burn
        current_time = 1500.0
        new_pos, new_vel = self.mcc.check_and_execute_burns(current_time, (position, velocity))
        
        # First burn should be executed
        expected_velocity = velocity + np.array([10, 0, 0])
        np.testing.assert_array_equal(new_pos, position)
        np.testing.assert_array_equal(new_vel, expected_velocity)
        self.assertEqual(len(self.mcc.scheduled_burns), 1)
        self.assertEqual(len(self.mcc.executed_burns), 1)
        
        # Check at time after second burn
        current_time = 2500.0
        new_pos, new_vel = self.mcc.check_and_execute_burns(current_time, (new_pos, new_vel))
        
        # Second burn should be executed
        expected_velocity = velocity + np.array([10, 0, 0]) + np.array([20, 0, 0])
        np.testing.assert_array_equal(new_pos, position)
        np.testing.assert_array_equal(new_vel, expected_velocity)
        self.assertEqual(len(self.mcc.scheduled_burns), 0)
        self.assertEqual(len(self.mcc.executed_burns), 2)
        
    def test_calculate_corrective_burn(self):
        """Test calculation of corrective burns."""
        # Current state
        position = np.array([7000e3, 0, 0])
        velocity = np.array([0, 7.5e3, 0])
        current_state = (position, velocity)
        
        # Target
        target_position = np.array([384400e3, 0, 0])  # Moon distance
        current_time = 0.0
        target_time = 3600.0  # 1 hour
        
        # Calculate correction
        delta_v = self.mcc.calculate_corrective_burn(current_state, target_position, target_time, current_time)
        
        # Should return a non-zero delta-V
        self.assertGreater(np.linalg.norm(delta_v), 0)
        self.assertEqual(len(delta_v), 3)
        
    def test_calculate_miss_distance_correction(self):
        """Test calculation of miss distance corrections."""
        # Current state
        position = np.array([7000e3, 0, 0])
        velocity = np.array([0, 7.5e3, 0])
        current_state = (position, velocity)
        
        # Target and predicted closest approach
        target_position = np.array([384400e3, 0, 0])
        predicted_closest_approach = np.array([384400e3, 5000e3, 0])  # 5000 km miss
        
        # Calculate correction
        delta_v = self.mcc.calculate_miss_distance_correction(current_state, target_position, predicted_closest_approach)
        
        # Should return a correction delta-V
        self.assertGreater(np.linalg.norm(delta_v), 0)
        self.assertEqual(len(delta_v), 3)
        
    def test_miss_distance_correction_close_approach(self):
        """Test that small miss distances don't require correction."""
        # Current state
        position = np.array([7000e3, 0, 0])
        velocity = np.array([0, 7.5e3, 0])
        current_state = (position, velocity)
        
        # Target and predicted closest approach (very close)
        target_position = np.array([384400e3, 0, 0])
        predicted_closest_approach = np.array([384400e3, 500, 0])  # 500 m miss (very close)
        
        # Calculate correction
        delta_v = self.mcc.calculate_miss_distance_correction(current_state, target_position, predicted_closest_approach)
        
        # Should return zero correction for close approach
        np.testing.assert_array_almost_equal(delta_v, np.zeros(3))
        
    def test_get_burn_summary(self):
        """Test burn summary generation."""
        # Schedule and execute some burns
        self.mcc.schedule_burn(1000.0, np.array([10, 0, 0]), description="Burn 1")
        self.mcc.schedule_burn(2000.0, np.array([20, 0, 0]), description="Burn 2")
        
        # Execute one burn
        position = np.array([7000e3, 0, 0])
        velocity = np.array([0, 7.5e3, 0])
        self.mcc.check_and_execute_burns(1500.0, (position, velocity))
        
        # Get summary
        summary = self.mcc.get_burn_summary()
        
        # Check summary
        self.assertEqual(summary['scheduled_burns'], 1)
        self.assertEqual(summary['executed_burns'], 1)
        self.assertAlmostEqual(summary['total_delta_v_scheduled'], 20.0)
        self.assertAlmostEqual(summary['total_delta_v_executed'], 10.0)
        self.assertEqual(len(summary['burns_history']), 2)
        
    def test_clear_all_burns(self):
        """Test clearing all burns."""
        # Schedule some burns
        self.mcc.schedule_burn(1000.0, np.array([10, 0, 0]))
        self.mcc.schedule_burn(2000.0, np.array([20, 0, 0]))
        
        # Execute one
        position = np.array([7000e3, 0, 0])
        velocity = np.array([0, 7.5e3, 0])
        self.mcc.check_and_execute_burns(1500.0, (position, velocity))
        
        # Clear all
        self.mcc.clear_all_burns()
        
        # Check everything is cleared
        self.assertEqual(len(self.mcc.scheduled_burns), 0)
        self.assertEqual(len(self.mcc.executed_burns), 0)
        
if __name__ == '__main__':
    unittest.main()