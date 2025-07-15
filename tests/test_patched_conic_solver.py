import unittest
import numpy as np
from patched_conic_solver import check_soi_transition, convert_to_lunar_frame, R_SOI_MOON_KM

class TestPatchedConicSolver(unittest.TestCase):

    def test_check_soi_transition(self):
        """Test the Sphere of Influence transition check."""
        moon_pos_eci = np.array([384400, 0, 0])

        # Case 1: Spacecraft is inside the SOI
        sc_pos_inside = moon_pos_eci + np.array([R_SOI_MOON_KM - 1, 0, 0])
        self.assertTrue(check_soi_transition(sc_pos_inside, moon_pos_eci), 
                        "Should return True when spacecraft is inside SOI")

        # Case 2: Spacecraft is just at the boundary of the SOI
        sc_pos_boundary = moon_pos_eci + np.array([R_SOI_MOON_KM, 0, 0])
        self.assertTrue(check_soi_transition(sc_pos_boundary, moon_pos_eci), 
                        "Should return True when spacecraft is at the SOI boundary")

        # Case 3: Spacecraft is outside the SOI
        sc_pos_outside = moon_pos_eci + np.array([R_SOI_MOON_KM + 1, 0, 0])
        self.assertFalse(check_soi_transition(sc_pos_outside, moon_pos_eci), 
                         "Should return False when spacecraft is outside SOI")

    def test_convert_to_lunar_frame(self):
        """Test the conversion of state vectors to the lunar frame."""
        # ECI state vectors
        moon_pos_eci = np.array([384400, 0, 0])
        moon_vel_eci = np.array([0, 1.022, 0]) # Moon's orbital velocity around Earth
        moon_state_eci = (moon_pos_eci, moon_vel_eci)

        sc_pos_eci = np.array([384400 + 5000, 3000, 0])
        sc_vel_eci = np.array([0, 1.022 + 1.5, 0.5]) # Relative velocity of 1.5 km/s in y
        sc_state_eci = (sc_pos_eci, sc_vel_eci)

        # Expected LCI state vectors
        expected_pos_lci = np.array([5000, 3000, 0])
        expected_vel_lci = np.array([0, 1.5, 0.5])

        # Perform conversion
        pos_lci, vel_lci = convert_to_lunar_frame(sc_state_eci, moon_state_eci)

        # Assertions
        np.testing.assert_array_almost_equal(pos_lci, expected_pos_lci, decimal=5)
        np.testing.assert_array_almost_equal(vel_lci, expected_vel_lci, decimal=5)

if __name__ == '__main__':
    unittest.main()
