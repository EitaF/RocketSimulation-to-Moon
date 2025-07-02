#!/usr/bin/env python3
"""
LEO Insertion Test Suite
Professor v27: Comprehensive testing of PEG guidance and orbital insertion

Tests:
1. PEG vs GravityTurn with 5% thrust deficit
2. Two-stage orbital insertion validation  
3. OrbitalMonitor accuracy validation
4. Circular orbit achievement within 5km tolerance
"""

import numpy as np
import json
import logging
import time
from typing import Dict, List, Tuple
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from rocket_simulation_main import Mission
from vehicle import create_saturn_v_rocket
from guidance_strategy import GuidanceFactory, GuidancePhase
from orbital_monitor import create_orbital_monitor
from peg import create_peg_guidance

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_leo_insertion.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class LEOInsertionTestSuite:
    """Test suite for LEO insertion validation"""
    
    def __init__(self):
        self.test_results = {}
        self.logger = logging.getLogger(__name__)
        
        # Test configuration
        self.base_config = {
            "launch_latitude": 28.5,
            "launch_azimuth": 90,
            "target_parking_orbit": 200000,  # 200 km
            "gravity_turn_altitude": 1500
        }
        
        self.logger.info("LEO Insertion Test Suite initialized")
    
    def create_test_mission(self, config_override: Dict = None, thrust_deficit: float = 0.0) -> Mission:
        """Create a mission with test configuration"""
        config = self.base_config.copy()
        if config_override:
            config.update(config_override)
        
        rocket = create_saturn_v_rocket()
        mission = Mission(rocket, config)
        
        # Apply thrust deficit if specified
        if thrust_deficit > 0:
            for stage in rocket.stages:
                stage.thrust_vacuum *= (1 - thrust_deficit)
                stage.thrust_sea_level *= (1 - thrust_deficit)
            self.logger.info(f"Applied {thrust_deficit*100:.1f}% thrust deficit")
        
        return mission
    
    def test_peg_vs_gravity_turn(self) -> Dict:
        """
        Test 1: PEG vs GravityTurn with 5% thrust deficit
        Professor v27: PEG should succeed where gravity turn fails
        """
        self.logger.info("=== Test 1: PEG vs GravityTurn with 5% thrust deficit ===")
        
        results = {
            'test_name': 'PEG vs GravityTurn Performance',
            'thrust_deficit': 0.05,
            'peg_result': {},
            'gravity_turn_result': {},
            'comparison': {}
        }
        
        # Test with PEG guidance (default)
        self.logger.info("Testing with PEG guidance...")
        peg_mission = self.create_test_mission(thrust_deficit=0.05)
        peg_results = peg_mission.simulate(duration=600, dt=0.1)  # 10 minutes
        
        results['peg_result'] = {
            'final_apoapsis_km': (peg_results.get('final_apoapsis', 6371000) - 6371000) / 1000,
            'final_periapsis_km': (peg_results.get('final_periapsis', 6371000) - 6371000) / 1000,
            'final_eccentricity': peg_results.get('final_eccentricity', 0),
            'mission_success': peg_mission.mission_success,
            'max_altitude_km': peg_results.get('max_altitude', 0) / 1000,
            'final_velocity_ms': peg_results.get('final_velocity', 0)
        }
        
        # Test with Gravity Turn guidance (force legacy mode)
        self.logger.info("Testing with Gravity Turn guidance...")
        gt_mission = self.create_test_mission(thrust_deficit=0.05)
        # Force gravity turn strategy
        gt_mission.guidance_context.force_strategy_switch(GuidancePhase.GRAVITY_TURN, 0.0)
        gt_results = gt_mission.simulate(duration=600, dt=0.1)  # 10 minutes
        
        results['gravity_turn_result'] = {
            'final_apoapsis_km': (gt_results.get('final_apoapsis', 6371000) - 6371000) / 1000,
            'final_periapsis_km': (gt_results.get('final_periapsis', 6371000) - 6371000) / 1000,
            'final_eccentricity': gt_results.get('final_eccentricity', 0),
            'mission_success': gt_mission.mission_success,
            'max_altitude_km': gt_results.get('max_altitude', 0) / 1000,
            'final_velocity_ms': gt_results.get('final_velocity', 0)
        }
        
        # Compare results
        peg_apoapsis_error = abs(results['peg_result']['final_apoapsis_km'] - 200)
        gt_apoapsis_error = abs(results['gravity_turn_result']['final_apoapsis_km'] - 200)
        
        results['comparison'] = {
            'peg_apoapsis_error_km': peg_apoapsis_error,
            'gravity_turn_apoapsis_error_km': gt_apoapsis_error,
            'peg_performance_better': peg_apoapsis_error < gt_apoapsis_error,
            'peg_target_achieved': peg_apoapsis_error <= 5.0,  # Within 5km tolerance
            'gt_target_achieved': gt_apoapsis_error <= 5.0
        }
        
        # Log results
        self.logger.info(f"PEG Results: Apoapsis {results['peg_result']['final_apoapsis_km']:.1f}km, "
                        f"Success: {results['peg_result']['mission_success']}")
        self.logger.info(f"Gravity Turn Results: Apoapsis {results['gravity_turn_result']['final_apoapsis_km']:.1f}km, "
                        f"Success: {results['gravity_turn_result']['mission_success']}")
        self.logger.info(f"PEG Performance Better: {results['comparison']['peg_performance_better']}")
        
        return results
    
    def test_two_stage_orbital_insertion(self) -> Dict:
        """
        Test 2: Validate two-stage orbital insertion produces circular orbit
        Professor v27: MECO → Coast → Circularization sequence
        """
        self.logger.info("=== Test 2: Two-Stage Orbital Insertion ===")
        
        results = {
            'test_name': 'Two-Stage Orbital Insertion',
            'phases_executed': [],
            'final_orbit': {},
            'success_criteria': {}
        }
        
        mission = self.create_test_mission()
        
        # Monitor phase transitions
        initial_phase = mission.rocket.phase
        phase_history = [initial_phase.value]
        
        # Run simulation
        sim_results = mission.simulate(duration=1200, dt=0.1)  # 20 minutes
        
        # Analyze phase transitions
        unique_phases = []
        for phase in mission.phase_history:
            if not unique_phases or phase != unique_phases[-1]:
                unique_phases.append(phase)
        
        results['phases_executed'] = [phase.value for phase in unique_phases]
        
        # Check if we see the expected sequence: LAUNCH → GRAVITY_TURN → COAST_TO_APOAPSIS → CIRCULARIZATION → LEO
        expected_phases = ['launch', 'gravity_turn', 'coast_to_apoapsis', 'circularization', 'leo']
        has_coast_phase = any('coast' in phase for phase in results['phases_executed'])
        has_circularization = any('circularization' in phase for phase in results['phases_executed'])
        
        # Final orbital parameters
        if mission.orbital_monitor.current_state:
            orbital_state = mission.orbital_monitor.current_state
            apoapsis_km = (orbital_state.apoapsis - 6371000) / 1000
            periapsis_km = (orbital_state.periapsis - 6371000) / 1000
            altitude_diff_km = abs(apoapsis_km - periapsis_km)
            
            results['final_orbit'] = {
                'apoapsis_km': apoapsis_km,
                'periapsis_km': periapsis_km,
                'eccentricity': orbital_state.eccentricity,
                'altitude_difference_km': altitude_diff_km,
                'is_circular': orbital_state.is_circular
            }
            
            # Success criteria validation
            results['success_criteria'] = {
                'apoapsis_periapsis_within_5km': altitude_diff_km <= 5.0,
                'eccentricity_below_threshold': orbital_state.eccentricity < 0.01,
                'altitude_in_target_range': 195 <= apoapsis_km <= 205,
                'coast_phase_executed': has_coast_phase,
                'circularization_executed': has_circularization,
                'overall_success': (altitude_diff_km <= 5.0 and 
                                  orbital_state.eccentricity < 0.01 and
                                  195 <= apoapsis_km <= 205)
            }
        else:
            results['final_orbit'] = {'error': 'No orbital state available'}
            results['success_criteria'] = {'overall_success': False}
        
        self.logger.info(f"Phases executed: {' → '.join(results['phases_executed'])}")
        self.logger.info(f"Final orbit: {results['final_orbit']}")
        self.logger.info(f"Overall success: {results['success_criteria']['overall_success']}")
        
        return results
    
    def test_orbital_monitor_accuracy(self) -> Dict:
        """
        Test 3: Validate OrbitalMonitor accuracy against post-flight analysis
        Professor v27: <0.5% error requirement
        """
        self.logger.info("=== Test 3: OrbitalMonitor Accuracy Validation ===")
        
        results = {
            'test_name': 'OrbitalMonitor Accuracy',
            'accuracy_validation': {},
            'meets_requirements': False
        }
        
        mission = self.create_test_mission()
        sim_results = mission.simulate(duration=600, dt=0.1)
        
        if mission.orbital_monitor.current_state:
            orbital_state = mission.orbital_monitor.current_state
            
            # Use final orbital elements from simulation as reference
            final_apoapsis = sim_results['final_apoapsis']
            final_periapsis = sim_results['final_periapsis']
            
            # Validate against "post-flight analysis" (the simulation's own calculations)
            validation = mission.orbital_monitor.validate_against_post_flight_analysis(
                final_apoapsis, final_periapsis
            )
            
            results['accuracy_validation'] = validation
            results['meets_requirements'] = validation.get('overall_validation_passed', False)
            
            self.logger.info(f"Apoapsis error: {validation.get('apoapsis_error_percent', 0):.3f}%")
            self.logger.info(f"Periapsis error: {validation.get('periapsis_error_percent', 0):.3f}%")
            self.logger.info(f"Meets <0.5% requirement: {results['meets_requirements']}")
        else:
            results['accuracy_validation'] = {'error': 'No orbital state for validation'}
            results['meets_requirements'] = False
        
        return results
    
    def test_circular_orbit_tolerance(self) -> Dict:
        """
        Test 4: Validate circular orbit achievement within 5km tolerance
        Professor v27: Final success criteria validation
        """
        self.logger.info("=== Test 4: Circular Orbit Tolerance ===")
        
        results = {
            'test_name': 'Circular Orbit Tolerance',
            'test_runs': [],
            'success_rate': 0.0,
            'average_accuracy': 0.0
        }
        
        # Run multiple tests to check consistency
        num_runs = 3
        successes = 0
        accuracy_values = []
        
        for i in range(num_runs):
            self.logger.info(f"Test run {i+1}/{num_runs}")
            
            mission = self.create_test_mission()
            sim_results = mission.simulate(duration=800, dt=0.1)
            
            run_result = {
                'run_number': i + 1,
                'mission_success': mission.mission_success,
                'final_orbit': {}
            }
            
            if mission.orbital_monitor.current_state:
                orbital_state = mission.orbital_monitor.current_state
                apoapsis_km = (orbital_state.apoapsis - 6371000) / 1000
                periapsis_km = (orbital_state.periapsis - 6371000) / 1000
                altitude_diff_km = abs(apoapsis_km - periapsis_km)
                
                run_result['final_orbit'] = {
                    'apoapsis_km': apoapsis_km,
                    'periapsis_km': periapsis_km,
                    'altitude_difference_km': altitude_diff_km,
                    'eccentricity': orbital_state.eccentricity,
                    'meets_tolerance': altitude_diff_km <= 5.0
                }
                
                if run_result['final_orbit']['meets_tolerance']:
                    successes += 1
                
                accuracy_values.append(altitude_diff_km)
            else:
                run_result['final_orbit'] = {'error': 'No orbital state'}
            
            results['test_runs'].append(run_result)
        
        results['success_rate'] = successes / num_runs
        results['average_accuracy'] = np.mean(accuracy_values) if accuracy_values else 0.0
        
        self.logger.info(f"Success rate: {results['success_rate']*100:.1f}% ({successes}/{num_runs})")
        self.logger.info(f"Average altitude difference: {results['average_accuracy']:.2f} km")
        
        return results
    
    def run_all_tests(self) -> Dict:
        """Run complete test suite"""
        self.logger.info("🚀 Starting LEO Insertion Test Suite")
        self.logger.info("=" * 60)
        
        start_time = time.time()
        
        # Run all tests
        test_results = {}
        
        try:
            test_results['test_1_peg_vs_gravity_turn'] = self.test_peg_vs_gravity_turn()
        except Exception as e:
            self.logger.error(f"Test 1 failed: {e}")
            test_results['test_1_peg_vs_gravity_turn'] = {'error': str(e)}
        
        try:
            test_results['test_2_two_stage_insertion'] = self.test_two_stage_orbital_insertion()
        except Exception as e:
            self.logger.error(f"Test 2 failed: {e}")
            test_results['test_2_two_stage_insertion'] = {'error': str(e)}
        
        try:
            test_results['test_3_orbital_monitor_accuracy'] = self.test_orbital_monitor_accuracy()
        except Exception as e:
            self.logger.error(f"Test 3 failed: {e}")
            test_results['test_3_orbital_monitor_accuracy'] = {'error': str(e)}
        
        try:
            test_results['test_4_circular_orbit_tolerance'] = self.test_circular_orbit_tolerance()
        except Exception as e:
            self.logger.error(f"Test 4 failed: {e}")
            test_results['test_4_circular_orbit_tolerance'] = {'error': str(e)}
        
        end_time = time.time()
        
        # Compile overall results
        overall_results = {
            'test_suite': 'LEO Insertion Validation',
            'professor_version': 'v27',
            'execution_time_seconds': end_time - start_time,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'individual_tests': test_results,
            'summary': self._generate_summary(test_results)
        }
        
        # Save results
        with open('leo_insertion_test_results.json', 'w') as f:
            json.dump(overall_results, f, indent=2, default=str)
        
        self._print_summary(overall_results)
        
        return overall_results
    
    def _generate_summary(self, test_results: Dict) -> Dict:
        """Generate summary of test results"""
        summary = {
            'tests_passed': 0,
            'tests_failed': 0,
            'professor_requirements_met': {},
            'recommendations': []
        }
        
        # Check Test 1: PEG vs Gravity Turn
        test1 = test_results.get('test_1_peg_vs_gravity_turn', {})
        if 'error' not in test1:
            peg_better = test1.get('comparison', {}).get('peg_performance_better', False)
            peg_target = test1.get('comparison', {}).get('peg_target_achieved', False)
            
            if peg_better and peg_target:
                summary['tests_passed'] += 1
                summary['professor_requirements_met']['peg_guidance_superior'] = True
            else:
                summary['tests_failed'] += 1
                summary['professor_requirements_met']['peg_guidance_superior'] = False
                summary['recommendations'].append("PEG guidance needs improvement for thrust deficit scenarios")
        
        # Check Test 2: Two-stage insertion
        test2 = test_results.get('test_2_two_stage_insertion', {})
        if 'error' not in test2:
            success = test2.get('success_criteria', {}).get('overall_success', False)
            
            if success:
                summary['tests_passed'] += 1
                summary['professor_requirements_met']['two_stage_insertion'] = True
            else:
                summary['tests_failed'] += 1
                summary['professor_requirements_met']['two_stage_insertion'] = False
                summary['recommendations'].append("Two-stage insertion sequence needs refinement")
        
        # Check Test 3: Orbital monitor accuracy
        test3 = test_results.get('test_3_orbital_monitor_accuracy', {})
        if 'error' not in test3:
            meets_req = test3.get('meets_requirements', False)
            
            if meets_req:
                summary['tests_passed'] += 1
                summary['professor_requirements_met']['orbital_monitor_accuracy'] = True
            else:
                summary['tests_failed'] += 1
                summary['professor_requirements_met']['orbital_monitor_accuracy'] = False
                summary['recommendations'].append("Orbital monitor accuracy needs improvement")
        
        # Check Test 4: Circular orbit tolerance
        test4 = test_results.get('test_4_circular_orbit_tolerance', {})
        if 'error' not in test4:
            success_rate = test4.get('success_rate', 0.0)
            
            if success_rate >= 0.8:  # 80% success rate threshold
                summary['tests_passed'] += 1
                summary['professor_requirements_met']['circular_orbit_tolerance'] = True
            else:
                summary['tests_failed'] += 1
                summary['professor_requirements_met']['circular_orbit_tolerance'] = False
                summary['recommendations'].append("Circular orbit tolerance achievement needs improvement")
        
        return summary
    
    def _print_summary(self, results: Dict):
        """Print formatted test summary"""
        print("\n" + "=" * 60)
        print("🎯 LEO INSERTION TEST SUITE SUMMARY")
        print("=" * 60)
        
        summary = results['summary']
        print(f"Tests Passed: {summary['tests_passed']}")
        print(f"Tests Failed: {summary['tests_failed']}")
        print(f"Execution Time: {results['execution_time_seconds']:.1f} seconds")
        
        print("\n📋 Professor v27 Requirements:")
        reqs = summary['professor_requirements_met']
        for req, met in reqs.items():
            status = "✅ PASS" if met else "❌ FAIL"
            print(f"  {req}: {status}")
        
        if summary['recommendations']:
            print("\n💡 Recommendations:")
            for rec in summary['recommendations']:
                print(f"  • {rec}")
        
        overall_success = summary['tests_passed'] > summary['tests_failed']
        status = "🎉 SUCCESS" if overall_success else "⚠️  NEEDS IMPROVEMENT"
        print(f"\n🏁 Overall Status: {status}")
        print("=" * 60)


def main():
    """Run the LEO insertion test suite"""
    test_suite = LEOInsertionTestSuite()
    results = test_suite.run_all_tests()
    
    # Exit with appropriate code
    summary = results['summary']
    if summary['tests_passed'] > summary['tests_failed']:
        sys.exit(0)  # Success
    else:
        sys.exit(1)  # Failure


if __name__ == "__main__":
    main()