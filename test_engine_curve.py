"""
Unit Tests for Engine Performance Model
Task 2-4: Regression tests with ≤2% MAE requirement
"""

import pytest
import numpy as np
from engine import EnginePerformanceModel, get_engine_model
import json
import tempfile
import os


class TestEnginePerformanceModel:
    """Test suite for engine performance model"""
    
    @pytest.fixture
    def engine_model(self):
        """Create engine model instance for testing"""
        return EnginePerformanceModel()
    
    @pytest.fixture
    def reference_data(self):
        """Reference performance data for validation"""
        return {
            'S-IC': {
                'thrust_at_sea_level': 34020000,  # N
                'thrust_at_vacuum': 35100000,     # N
                'isp_at_sea_level': 263,          # s
                'isp_at_vacuum': 289              # s
            },
            'S-II': {
                'thrust_at_sea_level': 4400000,   # N
                'thrust_at_vacuum': 5000000,      # N
                'isp_at_sea_level': 395,          # s
                'isp_at_vacuum': 421              # s
            },
            'S-IVB': {
                'thrust_at_sea_level': 825000,    # N
                'thrust_at_vacuum': 1000000,      # N
                'isp_at_sea_level': 441,          # s
                'isp_at_vacuum': 461              # s
            }
        }
    
    def test_engine_model_initialization(self, engine_model):
        """Test that engine model initializes correctly"""
        assert engine_model is not None
        assert hasattr(engine_model, 'interpolators')
        assert len(engine_model.interpolators) >= 3  # S-IC, S-II, S-IVB
    
    def test_thrust_at_sea_level(self, engine_model, reference_data):
        """Test thrust values at sea level"""
        tolerance = 0.02  # 2% tolerance
        
        for stage_name, ref_data in reference_data.items():
            thrust = engine_model.get_thrust(stage_name, 0.0)  # Sea level
            expected = ref_data['thrust_at_sea_level']
            
            relative_error = abs(thrust - expected) / expected
            assert relative_error <= tolerance, \
                f"{stage_name} thrust at sea level: {thrust:.0f}N vs expected {expected:.0f}N " \
                f"(error: {relative_error:.2%})"
    
    def test_thrust_at_vacuum(self, engine_model, reference_data):
        """Test thrust values at vacuum conditions"""
        tolerance = 0.02  # 2% tolerance
        
        for stage_name, ref_data in reference_data.items():
            thrust = engine_model.get_thrust(stage_name, 100000.0)  # 100 km altitude
            expected = ref_data['thrust_at_vacuum']
            
            relative_error = abs(thrust - expected) / expected
            assert relative_error <= tolerance, \
                f"{stage_name} thrust at vacuum: {thrust:.0f}N vs expected {expected:.0f}N " \
                f"(error: {relative_error:.2%})"
    
    def test_isp_at_sea_level(self, engine_model, reference_data):
        """Test specific impulse values at sea level"""
        tolerance = 0.02  # 2% tolerance
        
        for stage_name, ref_data in reference_data.items():
            isp = engine_model.get_specific_impulse(stage_name, 0.0)  # Sea level
            expected = ref_data['isp_at_sea_level']
            
            relative_error = abs(isp - expected) / expected
            assert relative_error <= tolerance, \
                f"{stage_name} Isp at sea level: {isp:.1f}s vs expected {expected:.1f}s " \
                f"(error: {relative_error:.2%})"
    
    def test_isp_at_vacuum(self, engine_model, reference_data):
        """Test specific impulse values at vacuum conditions"""
        tolerance = 0.02  # 2% tolerance
        
        for stage_name, ref_data in reference_data.items():
            isp = engine_model.get_specific_impulse(stage_name, 100000.0)  # 100 km altitude
            expected = ref_data['isp_at_vacuum']
            
            relative_error = abs(isp - expected) / expected
            assert relative_error <= tolerance, \
                f"{stage_name} Isp at vacuum: {isp:.1f}s vs expected {expected:.1f}s " \
                f"(error: {relative_error:.2%})"
    
    def test_thrust_monotonicity(self, engine_model):
        """Test that thrust generally increases with altitude (for most stages)"""
        altitudes = np.linspace(0, 100000, 11)
        
        for stage_name in ['S-IC', 'S-II', 'S-IVB']:
            thrust_values = [engine_model.get_thrust(stage_name, alt) for alt in altitudes]
            
            # For rocket engines, thrust generally increases with altitude
            # Check that the trend is generally upward (allowing some variation)
            thrust_at_start = thrust_values[0]
            thrust_at_end = thrust_values[-1]
            
            assert thrust_at_end >= thrust_at_start * 0.95, \
                f"{stage_name} thrust should not decrease significantly with altitude"
    
    def test_isp_monotonicity(self, engine_model):
        """Test that Isp increases with altitude"""
        altitudes = np.linspace(0, 100000, 11)
        
        for stage_name in ['S-IC', 'S-II', 'S-IVB']:
            isp_values = [engine_model.get_specific_impulse(stage_name, alt) for alt in altitudes]
            
            # Isp should generally increase with altitude
            isp_at_start = isp_values[0]
            isp_at_end = isp_values[-1]
            
            assert isp_at_end > isp_at_start, \
                f"{stage_name} Isp should increase with altitude"
    
    def test_throttle_scaling(self, engine_model):
        """Test that throttle setting correctly scales thrust"""
        altitude = 50000  # Test at 50 km
        throttle_values = [0.0, 0.5, 1.0]
        
        for stage_name in ['S-IC', 'S-II', 'S-IVB']:
            base_thrust = engine_model.get_thrust(stage_name, altitude, throttle=1.0)
            
            for throttle in throttle_values:
                thrust = engine_model.get_thrust(stage_name, altitude, throttle=throttle)
                expected = base_thrust * throttle
                
                assert abs(thrust - expected) < 1.0, \
                    f"{stage_name} throttle scaling failed: {thrust:.0f}N vs {expected:.0f}N"
    
    def test_mass_flow_rate_calculation(self, engine_model):
        """Test mass flow rate calculation"""
        altitude = 0  # Sea level
        
        for stage_name in ['S-IC', 'S-II', 'S-IVB']:
            thrust = engine_model.get_thrust(stage_name, altitude)
            isp = engine_model.get_specific_impulse(stage_name, altitude)
            mass_flow = engine_model.get_mass_flow_rate(stage_name, altitude)
            
            # Verify mass flow rate calculation: mdot = F / (Isp * g0)
            g0 = 9.80665
            expected_mass_flow = thrust / (isp * g0)
            
            relative_error = abs(mass_flow - expected_mass_flow) / expected_mass_flow
            assert relative_error < 0.001, \
                f"{stage_name} mass flow rate calculation error: {relative_error:.4%}"
    
    def test_boundary_conditions(self, engine_model):
        """Test performance at boundary conditions"""
        # Test negative altitude (should clamp to 0)
        for stage_name in ['S-IC', 'S-II', 'S-IVB']:
            thrust_neg = engine_model.get_thrust(stage_name, -1000)
            thrust_zero = engine_model.get_thrust(stage_name, 0)
            assert thrust_neg == thrust_zero, \
                f"{stage_name} should handle negative altitude"
            
            # Test very high altitude
            thrust_high = engine_model.get_thrust(stage_name, 200000)  # 200 km
            assert thrust_high > 0, \
                f"{stage_name} should provide positive thrust at high altitude"
    
    def test_model_validation(self, engine_model):
        """Test the built-in model validation"""
        validation_results = engine_model.validate_model()
        
        assert validation_results['validation_passed'], \
            "Engine model validation should pass"
        assert validation_results['stages_validated'] >= 3, \
            "Should validate at least 3 stages"
        
        # Check that error rates are reasonable
        for stage_name, errors in validation_results['mean_absolute_errors'].items():
            assert errors['thrust_error_rate'] < 0.10, \
                f"{stage_name} thrust error rate too high: {errors['thrust_error_rate']:.2%}"
            assert errors['isp_error_rate'] < 0.10, \
                f"{stage_name} Isp error rate too high: {errors['isp_error_rate']:.2%}"
    
    def test_interpolation_smoothness(self, engine_model):
        """Test that interpolation produces smooth curves"""
        altitudes = np.linspace(0, 100000, 1001)  # Fine resolution
        
        for stage_name in ['S-IC', 'S-II', 'S-IVB']:
            thrust_values = [engine_model.get_thrust(stage_name, alt) for alt in altitudes]
            isp_values = [engine_model.get_specific_impulse(stage_name, alt) for alt in altitudes]
            
            # Check for sudden jumps (derivative check)
            thrust_diffs = np.diff(thrust_values)
            isp_diffs = np.diff(isp_values)
            
            # Maximum change per 100m altitude step should be reasonable
            max_thrust_change = np.max(np.abs(thrust_diffs))
            max_isp_change = np.max(np.abs(isp_diffs))
            
            # These limits are empirical based on expected smooth curves
            assert max_thrust_change < 100000, \
                f"{stage_name} thrust curve has discontinuities: max change {max_thrust_change:.0f}N"
            assert max_isp_change < 5.0, \
                f"{stage_name} Isp curve has discontinuities: max change {max_isp_change:.1f}s"
    
    def test_fallback_functionality(self):
        """Test fallback functionality when engine data file is missing"""
        # Create temporary directory without engine curve file
        with tempfile.TemporaryDirectory() as temp_dir:
            old_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)
                
                # Initialize engine model without data file
                engine_model = EnginePerformanceModel("nonexistent_file.json")
                
                # Should still provide reasonable performance
                for stage_name in ['S-IC', 'S-II', 'S-IVB']:
                    thrust = engine_model.get_thrust(stage_name, 0)
                    isp = engine_model.get_specific_impulse(stage_name, 0)
                    
                    assert thrust > 0, f"{stage_name} fallback thrust should be positive"
                    assert isp > 100, f"{stage_name} fallback Isp should be reasonable"
            
            finally:
                os.chdir(old_cwd)
    
    def test_throttle_dependent_isp(self, engine_model):
        """Test throttle-dependent Isp functionality"""
        altitude = 50000  # Test at 50 km
        throttle_levels = [1.0, 0.8, 0.6]
        
        for stage_name in ['S-IC', 'S-II', 'S-IVB']:
            isp_values = []
            
            for throttle in throttle_levels:
                isp = engine_model.get_specific_impulse(stage_name, altitude, throttle)
                isp_values.append(isp)
                
                # Ensure Isp is reasonable
                assert isp > 100, f"{stage_name} Isp should be positive at throttle {throttle}"
            
            # Verify that Isp values are different for different throttle levels
            # (unless using legacy 1D data with throttle penalty)
            full_throttle_isp = isp_values[0]  # throttle = 1.0
            reduced_throttle_isp = isp_values[2]  # throttle = 0.6
            
            # Isp should decrease with reduced throttle
            assert reduced_throttle_isp <= full_throttle_isp, \
                f"{stage_name} Isp should decrease with reduced throttle: "\
                f"{full_throttle_isp:.1f}s (100%) vs {reduced_throttle_isp:.1f}s (60%)"
            
            # Check that the difference is reasonable (not too extreme)
            relative_change = (full_throttle_isp - reduced_throttle_isp) / full_throttle_isp
            assert relative_change <= 0.15, \
                f"{stage_name} throttle Isp change too extreme: {relative_change:.2%}"
    
    def test_mae_requirement(self, engine_model, reference_data):
        """Test that Mean Absolute Error is ≤2% as specified in requirements"""
        test_altitudes = np.linspace(0, 100000, 21)  # Test at 21 points
        
        for stage_name, ref_data in reference_data.items():
            thrust_errors = []
            isp_errors = []
            
            for altitude in test_altitudes:
                # Calculate expected values using linear interpolation
                if altitude <= 0:
                    expected_thrust = ref_data['thrust_at_sea_level']
                    expected_isp = ref_data['isp_at_sea_level']
                elif altitude >= 100000:
                    expected_thrust = ref_data['thrust_at_vacuum']
                    expected_isp = ref_data['isp_at_vacuum']
                else:
                    factor = altitude / 100000
                    expected_thrust = (ref_data['thrust_at_sea_level'] * (1 - factor) + 
                                     ref_data['thrust_at_vacuum'] * factor)
                    expected_isp = (ref_data['isp_at_sea_level'] * (1 - factor) + 
                                   ref_data['isp_at_vacuum'] * factor)
                
                # Get model predictions
                actual_thrust = engine_model.get_thrust(stage_name, altitude)
                actual_isp = engine_model.get_specific_impulse(stage_name, altitude)
                
                # Calculate relative errors
                thrust_error = abs(actual_thrust - expected_thrust) / expected_thrust
                isp_error = abs(actual_isp - expected_isp) / expected_isp
                
                thrust_errors.append(thrust_error)
                isp_errors.append(isp_error)
            
            # Calculate Mean Absolute Error
            mae_thrust = np.mean(thrust_errors)
            mae_isp = np.mean(isp_errors)
            
            # Check MAE requirement (≤2%)
            assert mae_thrust <= 0.02, \
                f"{stage_name} thrust MAE {mae_thrust:.2%} exceeds 2% requirement"
            assert mae_isp <= 0.02, \
                f"{stage_name} Isp MAE {mae_isp:.2%} exceeds 2% requirement"


def test_singleton_engine_model():
    """Test that get_engine_model returns singleton instance"""
    model1 = get_engine_model()
    model2 = get_engine_model()
    
    assert model1 is model2, "get_engine_model should return singleton instance"


if __name__ == "__main__":
    # Run tests directly
    import sys
    
    print("Running Engine Performance Model Tests")
    print("=" * 50)
    
    # Create test instance
    test_instance = TestEnginePerformanceModel()
    engine_model = EnginePerformanceModel()
    
    # Create reference data
    reference_data = {
        'S-IC': {
            'thrust_at_sea_level': 34020000,
            'thrust_at_vacuum': 35100000,
            'isp_at_sea_level': 263,
            'isp_at_vacuum': 289
        },
        'S-II': {
            'thrust_at_sea_level': 4400000,
            'thrust_at_vacuum': 5000000,
            'isp_at_sea_level': 395,
            'isp_at_vacuum': 421
        },
        'S-IVB': {
            'thrust_at_sea_level': 825000,
            'thrust_at_vacuum': 1000000,
            'isp_at_sea_level': 441,
            'isp_at_vacuum': 461
        }
    }
    
    # Run key tests
    try:
        test_instance.test_engine_model_initialization(engine_model)
        print("✅ Engine model initialization test passed")
        
        test_instance.test_mae_requirement(engine_model, reference_data)
        print("✅ MAE requirement test passed (≤2%)")
        
        test_instance.test_model_validation(engine_model)
        print("✅ Model validation test passed")
        
        test_instance.test_interpolation_smoothness(engine_model)
        print("✅ Interpolation smoothness test passed")
        
        test_instance.test_throttle_dependent_isp(engine_model)
        print("✅ Throttle-dependent Isp test passed")
        
        print("\n🎉 All engine tests passed successfully!")
        
    except AssertionError as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"💥 Test error: {e}")
        sys.exit(1)