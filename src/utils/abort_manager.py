"""
Abort Manager State Machine
Task 3-3: State-machine for switching GNC profiles during abort scenarios
"""

import logging
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum
from fault_detector import FaultEvent, FaultType, FaultSeverity


class AbortMode(Enum):
    """Abort modes as specified in feedback (AM-I to AM-IV)"""
    AM_I_LAUNCH_ESCAPE = "am_i_launch_escape"      # Launch escape system
    AM_II_RTLS = "am_ii_rtls"                      # Return to Launch Site
    AM_III_TAL = "am_iii_tal"                      # Trans-Atlantic Landing
    AM_IV_ATO = "am_iv_ato"                        # Abort to Orbit


class AbortState(Enum):
    """States in the abort state machine"""
    NOMINAL = "nominal"
    FAULT_DETECTED = "fault_detected"
    ABORT_DECISION = "abort_decision"
    ABORT_EXECUTING = "abort_executing"
    SAFE_HOLD = "safe_hold"
    MISSION_TERMINATED = "mission_terminated"


@dataclass
class AbortDecision:
    """Container for abort decision information"""
    abort_mode: AbortMode
    reason: str
    triggering_fault: FaultEvent
    decision_time: float
    estimated_success_probability: float
    required_actions: List[str]


class AbortManager:
    """
    State machine for managing mission abort scenarios
    Implements layered abort framework with fault-tolerant paths
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.logger = logging.getLogger(__name__)
        self.config = config or self._get_default_config()
        
        # Current state
        self.current_state = AbortState.NOMINAL
        self.current_abort_mode: Optional[AbortMode] = None
        self.abort_decision: Optional[AbortDecision] = None
        
        # State transition callbacks
        self.state_callbacks: Dict[AbortState, List[Callable]] = {
            state: [] for state in AbortState
        }
        
        # Abort mode selection criteria
        self.abort_criteria = self._initialize_abort_criteria()
        
        # Mission timeline for abort mode selection
        self.mission_phases = {
            'launch': (0, 30),           # 0-30 seconds
            'early_ascent': (30, 120),   # 30-120 seconds
            'late_ascent': (120, 300),   # 120-300 seconds
            'leo_insertion': (300, 600), # 300-600 seconds
            'coast': (600, float('inf')) # 600+ seconds
        }
        
        # State transition history
        self.state_history: List[Dict] = []
        
        self.logger.info("Abort manager initialized")
    
    def _get_default_config(self) -> Dict:
        """Get default configuration for abort manager"""
        return {
            'abort_decision_timeout': 5.0,        # 5 seconds to make abort decision
            'safe_hold_timeout': 30.0,            # 30 seconds in safe hold before termination
            'abort_mode_priorities': {             # Priority order for abort modes
                AbortMode.AM_I_LAUNCH_ESCAPE: 1,
                AbortMode.AM_II_RTLS: 2,
                AbortMode.AM_III_TAL: 3,
                AbortMode.AM_IV_ATO: 4
            },
            'fault_severity_thresholds': {
                FaultSeverity.CRITICAL: 'immediate_abort',
                FaultSeverity.HIGH: 'evaluate_abort',
                FaultSeverity.MEDIUM: 'monitor',
                FaultSeverity.LOW: 'log_only'
            }
        }
    
    def _initialize_abort_criteria(self) -> Dict:
        """Initialize abort mode selection criteria"""
        return {
            AbortMode.AM_I_LAUNCH_ESCAPE: {
                'time_window': (0, 120),     # First 2 minutes
                'altitude_max': 50000,       # Below 50km
                'velocity_max': 1000,        # Below 1000 m/s
                'required_faults': [
                    FaultType.THRUST_DEFICIT,
                    FaultType.STRUCTURAL_FAILURE,
                    FaultType.PROPELLANT_DEPLETION
                ],
                'description': "Launch Escape System activation"
            },
            AbortMode.AM_II_RTLS: {
                'time_window': (60, 300),    # 1-5 minutes
                'altitude_max': 100000,      # Below 100km
                'velocity_max': 3000,        # Below 3000 m/s
                'required_faults': [
                    FaultType.THRUST_DEFICIT,
                    FaultType.GUIDANCE_FAILURE
                ],
                'description': "Return to Launch Site"
            },
            AbortMode.AM_III_TAL: {
                'time_window': (200, 600),   # 3.3-10 minutes
                'altitude_max': 200000,      # Below 200km
                'velocity_max': 7000,        # Below 7000 m/s
                'required_faults': [
                    FaultType.THRUST_DEFICIT,
                    FaultType.STAGE_SEPARATION_FAILURE
                ],
                'description': "Trans-Atlantic Landing"
            },
            AbortMode.AM_IV_ATO: {
                'time_window': (300, 800),   # 5-13.3 minutes
                'altitude_min': 100000,      # Above 100km
                'velocity_min': 6000,        # Above 6000 m/s
                'required_faults': [
                    FaultType.THRUST_DEFICIT,
                    FaultType.PROPELLANT_DEPLETION
                ],
                'description': "Abort to Orbit"
            }
        }
    
    def update_state(self, telemetry: Dict, active_faults: List[FaultEvent], 
                    current_time: float) -> Optional[AbortDecision]:
        """
        Update abort manager state based on current conditions
        
        Args:
            telemetry: Current mission telemetry
            active_faults: List of active fault events
            current_time: Mission elapsed time [s]
            
        Returns:
            AbortDecision if abort is decided, None otherwise
        """
        previous_state = self.current_state
        
        # State machine logic
        if self.current_state == AbortState.NOMINAL:
            if active_faults:
                self._transition_to_state(AbortState.FAULT_DETECTED, current_time)
        
        elif self.current_state == AbortState.FAULT_DETECTED:
            abort_decision = self._evaluate_abort_decision(telemetry, active_faults, current_time)
            if abort_decision:
                self.abort_decision = abort_decision
                self._transition_to_state(AbortState.ABORT_DECISION, current_time)
                return abort_decision
            elif not active_faults:
                # Faults cleared, return to nominal
                self._transition_to_state(AbortState.NOMINAL, current_time)
            else:
                # Stay in fault detected state, continue monitoring
                pass
        
        elif self.current_state == AbortState.ABORT_DECISION:
            # Decision made, start executing abort
            self._transition_to_state(AbortState.ABORT_EXECUTING, current_time)
        
        elif self.current_state == AbortState.ABORT_EXECUTING:
            # Monitor abort execution
            if self._is_abort_complete(telemetry, current_time):
                self._transition_to_state(AbortState.SAFE_HOLD, current_time)
            elif self._is_abort_failed(telemetry, current_time):
                self._transition_to_state(AbortState.MISSION_TERMINATED, current_time)
        
        elif self.current_state == AbortState.SAFE_HOLD:
            # Monitor safe hold conditions
            hold_duration = current_time - self._get_state_entry_time(AbortState.SAFE_HOLD)
            safe_hold_timeout = self.config.get('safe_hold_timeout', 30.0)
            
            if hold_duration > safe_hold_timeout:
                self._transition_to_state(AbortState.MISSION_TERMINATED, current_time)
        
        # Log state changes
        if previous_state != self.current_state:
            self.logger.info(f"Abort manager state: {previous_state.value} → {self.current_state.value}")
        
        return None
    
    def _evaluate_abort_decision(self, telemetry: Dict, active_faults: List[FaultEvent],
                                current_time: float) -> Optional[AbortDecision]:
        """Evaluate whether to abort and select abort mode"""
        
        if not active_faults:
            return None
        
        # Check if any fault requires immediate abort
        critical_faults = [f for f in active_faults if f.severity == FaultSeverity.CRITICAL]
        if critical_faults:
            abort_mode = self._select_abort_mode(telemetry, active_faults, current_time)
            if abort_mode:
                return AbortDecision(
                    abort_mode=abort_mode,
                    reason="Critical fault detected",
                    triggering_fault=critical_faults[0],
                    decision_time=current_time,
                    estimated_success_probability=self._estimate_abort_success(abort_mode, telemetry),
                    required_actions=self._get_abort_actions(abort_mode)
                )
        
        # Check for multiple high-severity faults (OR single high fault for certain types)
        high_faults = [f for f in active_faults if f.severity == FaultSeverity.HIGH]
        # Single high-severity fault is enough for certain critical systems
        critical_fault_types = {FaultType.THRUST_DEFICIT, FaultType.STRUCTURAL_FAILURE, 
                               FaultType.STAGE_SEPARATION_FAILURE, FaultType.PROPELLANT_DEPLETION}
        
        single_critical_high_fault = any(f.fault_type in critical_fault_types for f in high_faults)
        
        if len(high_faults) >= 2 or single_critical_high_fault:
            abort_mode = self._select_abort_mode(telemetry, active_faults, current_time)
            if abort_mode:
                reason = "Single critical high fault" if single_critical_high_fault else "Multiple high-severity faults"
                return AbortDecision(
                    abort_mode=abort_mode,
                    reason=reason,
                    triggering_fault=high_faults[0],
                    decision_time=current_time,
                    estimated_success_probability=self._estimate_abort_success(abort_mode, telemetry),
                    required_actions=self._get_abort_actions(abort_mode)
                )
        
        # Check for persistent faults (reduced threshold)
        persistent_faults = [f for f in active_faults 
                           if (current_time - f.detection_time) > 5.0]  # 5+ seconds (reduced from 10)
        if persistent_faults and any(f.severity in [FaultSeverity.HIGH, FaultSeverity.CRITICAL] 
                                   for f in persistent_faults):
            abort_mode = self._select_abort_mode(telemetry, active_faults, current_time)
            if abort_mode:
                return AbortDecision(
                    abort_mode=abort_mode,
                    reason="Persistent high-severity fault",
                    triggering_fault=persistent_faults[0],
                    decision_time=current_time,
                    estimated_success_probability=self._estimate_abort_success(abort_mode, telemetry),
                    required_actions=self._get_abort_actions(abort_mode)
                )
        
        return None
    
    def _select_abort_mode(self, telemetry: Dict, active_faults: List[FaultEvent],
                          current_time: float) -> Optional[AbortMode]:
        """Select the most appropriate abort mode"""
        
        # Get current mission state
        altitude = telemetry.get('altitude', 0)
        velocity = telemetry.get('velocity_magnitude', 0)
        fault_types = {f.fault_type for f in active_faults}
        
        # Evaluate each abort mode
        viable_modes = []
        
        for abort_mode, criteria in self.abort_criteria.items():
            if self._is_abort_mode_viable(abort_mode, criteria, current_time, 
                                        altitude, velocity, fault_types):
                priority = self.config['abort_mode_priorities'][abort_mode]
                success_prob = self._estimate_abort_success(abort_mode, telemetry)
                viable_modes.append((abort_mode, priority, success_prob))
        
        if not viable_modes:
            self.logger.error("No viable abort modes found!")
            return None
        
        # Select mode with highest priority and success probability
        viable_modes.sort(key=lambda x: (x[1], -x[2]))  # Sort by priority, then by success prob
        selected_mode = viable_modes[0][0]
        
        self.logger.info(f"Selected abort mode: {selected_mode.value}")
        return selected_mode
    
    def _is_abort_mode_viable(self, abort_mode: AbortMode, criteria: Dict,
                             current_time: float, altitude: float, velocity: float,
                             fault_types: set) -> bool:
        """Check if an abort mode is viable given current conditions"""
        
        # Check time window
        time_window = criteria.get('time_window', (0, float('inf')))
        if not (time_window[0] <= current_time <= time_window[1]):
            return False
        
        # Check altitude constraints
        if 'altitude_max' in criteria and altitude > criteria['altitude_max']:
            return False
        if 'altitude_min' in criteria and altitude < criteria['altitude_min']:
            return False
        
        # Check velocity constraints
        if 'velocity_max' in criteria and velocity > criteria['velocity_max']:
            return False
        if 'velocity_min' in criteria and velocity < criteria['velocity_min']:
            return False
        
        # Check if fault types match requirements
        required_faults = set(criteria.get('required_faults', []))
        if required_faults and not fault_types.intersection(required_faults):
            return False
        
        return True
    
    def _estimate_abort_success(self, abort_mode: AbortMode, telemetry: Dict) -> float:
        """Estimate probability of successful abort execution"""
        
        # Base success probabilities for each abort mode
        base_probabilities = {
            AbortMode.AM_I_LAUNCH_ESCAPE: 0.95,
            AbortMode.AM_II_RTLS: 0.80,
            AbortMode.AM_III_TAL: 0.85,
            AbortMode.AM_IV_ATO: 0.90
        }
        
        base_prob = base_probabilities.get(abort_mode, 0.70)
        
        # Adjust based on current conditions
        altitude = telemetry.get('altitude', 0)
        velocity = telemetry.get('velocity_magnitude', 0)
        propellant_remaining = telemetry.get('propellant_mass', 0)
        
        # Altitude factor (higher altitude generally better for abort)
        if abort_mode == AbortMode.AM_I_LAUNCH_ESCAPE:
            altitude_factor = max(0.8, 1.0 - altitude / 100000)  # Lower is better for LES
        else:
            altitude_factor = min(1.2, 0.8 + altitude / 200000)  # Higher is better for others
        
        # Propellant factor
        propellant_factor = min(1.2, 0.6 + propellant_remaining / 100000)
        
        # Calculate final probability
        final_prob = base_prob * altitude_factor * propellant_factor
        return min(1.0, max(0.1, final_prob))
    
    def _get_abort_actions(self, abort_mode: AbortMode) -> List[str]:
        """Get required actions for abort mode execution"""
        
        actions = {
            AbortMode.AM_I_LAUNCH_ESCAPE: [
                "Activate Launch Escape System",
                "Jettison Service Module",
                "Orient for parachute deployment",
                "Deploy drogue parachutes",
                "Deploy main parachutes",
                "Prepare for water landing"
            ],
            AbortMode.AM_II_RTLS: [
                "Engine shutdown and separation",
                "Flip maneuver to reverse direction",
                "Boost back burn to launch site",
                "Entry burn for atmospheric entry",
                "Landing burn for touchdown",
                "Deploy landing legs"
            ],
            AbortMode.AM_III_TAL: [
                "Continue ascent to safe abort altitude",
                "Perform abort trajectory insertion",
                "Coast to trans-Atlantic site",
                "Entry sequence for landing",
                "Deploy parachutes over landing site"
            ],
            AbortMode.AM_IV_ATO: [
                "Continue ascent with reduced performance",
                "Adjust trajectory for stable orbit",
                "Perform orbital insertion maneuver",
                "Stable orbit achievement",
                "Plan deorbit for safe return"
            ]
        }
        
        return actions.get(abort_mode, ["Execute emergency procedures"])
    
    def _is_abort_complete(self, telemetry: Dict, current_time: float) -> bool:
        """Check if abort execution is complete"""
        if not self.abort_decision:
            return False
        
        abort_mode = self.abort_decision.abort_mode
        execution_time = current_time - self.abort_decision.decision_time
        
        # Simple completion criteria based on abort mode
        if abort_mode == AbortMode.AM_I_LAUNCH_ESCAPE:
            # LES complete when altitude is decreasing and velocity is low
            altitude_rate = telemetry.get('altitude_rate', 0)
            velocity = telemetry.get('velocity_magnitude', 0)
            return altitude_rate < -10 and velocity < 50  # Descending under parachute
        
        elif abort_mode == AbortMode.AM_II_RTLS:
            # RTLS complete when landed at launch site
            altitude = telemetry.get('altitude', 0)
            return altitude < 100 and execution_time > 300  # Near ground after 5 minutes
        
        elif abort_mode == AbortMode.AM_III_TAL:
            # TAL complete when over landing site
            return execution_time > 600  # After 10 minutes
        
        elif abort_mode == AbortMode.AM_IV_ATO:
            # ATO complete when in stable orbit
            apoapsis = telemetry.get('apoapsis', 0)
            periapsis = telemetry.get('periapsis', 0)
            return apoapsis > 200000 and periapsis > 200000  # Stable orbit
        
        return False
    
    def _is_abort_failed(self, telemetry: Dict, current_time: float) -> bool:
        """Check if abort execution has failed"""
        if not self.abort_decision:
            return False
        
        execution_time = current_time - self.abort_decision.decision_time
        
        # Timeout-based failure detection
        timeout_limits = {
            AbortMode.AM_I_LAUNCH_ESCAPE: 600,   # 10 minutes
            AbortMode.AM_II_RTLS: 1200,          # 20 minutes
            AbortMode.AM_III_TAL: 1800,          # 30 minutes
            AbortMode.AM_IV_ATO: 2400            # 40 minutes
        }
        
        timeout = timeout_limits.get(self.abort_decision.abort_mode, 1800)
        if execution_time > timeout:
            return True
        
        # Specific failure conditions
        altitude = telemetry.get('altitude', 0)
        if altitude < -1000:  # Below sea level indicates failure
            return True
        
        return False
    
    def _transition_to_state(self, new_state: AbortState, current_time: float):
        """Transition to a new state and execute callbacks"""
        old_state = self.current_state
        self.current_state = new_state
        
        # Record state transition
        self.state_history.append({
            'time': current_time,
            'old_state': old_state,
            'new_state': new_state,
            'abort_mode': self.current_abort_mode
        })
        
        # Execute state entry callbacks
        for callback in self.state_callbacks.get(new_state, []):
            try:
                callback(old_state, new_state, current_time)
            except Exception as e:
                self.logger.error(f"State callback error: {e}")
    
    def _get_state_entry_time(self, state: AbortState) -> float:
        """Get the time when we entered a specific state"""
        for record in reversed(self.state_history):
            if record['new_state'] == state:
                return record['time']
        return 0.0
    
    def register_state_callback(self, state: AbortState, callback: Callable):
        """Register a callback for state transitions"""
        self.state_callbacks[state].append(callback)
    
    def get_current_state(self) -> AbortState:
        """Get current abort manager state"""
        return self.current_state
    
    def get_abort_decision(self) -> Optional[AbortDecision]:
        """Get current abort decision"""
        return self.abort_decision
    
    def get_state_history(self) -> List[Dict]:
        """Get complete state transition history"""
        return self.state_history.copy()
    
    def force_abort(self, abort_mode: AbortMode, reason: str, current_time: float) -> AbortDecision:
        """Force an abort with specified mode (for external override)"""
        
        fake_fault = FaultEvent(
            fault_type=FaultType.GUIDANCE_FAILURE,
            severity=FaultSeverity.CRITICAL,
            detection_time=current_time,
            description="Manual abort command",
            confidence=1.0,
            parameters={},
            recommended_action="Execute abort"
        )
        
        abort_decision = AbortDecision(
            abort_mode=abort_mode,
            reason=reason,
            triggering_fault=fake_fault,
            decision_time=current_time,
            estimated_success_probability=0.8,
            required_actions=self._get_abort_actions(abort_mode)
        )
        
        self.abort_decision = abort_decision
        self._transition_to_state(AbortState.ABORT_DECISION, current_time)
        
        self.logger.warning(f"FORCED ABORT: {abort_mode.value} - {reason}")
        return abort_decision
    
    def reset(self):
        """Reset abort manager to initial state"""
        self.current_state = AbortState.NOMINAL
        self.current_abort_mode = None
        self.abort_decision = None
        self.state_history.clear()
        
        self.logger.info("Abort manager reset")


def main():
    """Test the abort manager"""
    print("Abort Manager Test")
    print("=" * 30)
    
    # Create abort manager
    abort_mgr = AbortManager()
    
    # Simulate mission timeline with various fault scenarios
    from fault_detector import FaultEvent, FaultType, FaultSeverity
    
    test_scenarios = [
        # Scenario 1: Normal operation (no faults)
        {
            'time': 60,
            'telemetry': {'altitude': 20000, 'velocity_magnitude': 500},
            'faults': [],
            'description': "Normal ascent"
        },
        
        # Scenario 2: Critical thrust deficit early in flight
        {
            'time': 90,
            'telemetry': {'altitude': 35000, 'velocity_magnitude': 800},
            'faults': [
                FaultEvent(
                    fault_type=FaultType.THRUST_DEFICIT,
                    severity=FaultSeverity.CRITICAL,
                    detection_time=85,
                    description="50% thrust loss",
                    confidence=0.95,
                    parameters={'deficit_percent': 50},
                    recommended_action="Abort mission"
                )
            ],
            'description': "Critical thrust deficit"
        },
        
        # Scenario 3: High altitude guidance failure
        {
            'time': 400,
            'telemetry': {'altitude': 150000, 'velocity_magnitude': 6500},
            'faults': [
                FaultEvent(
                    fault_type=FaultType.GUIDANCE_FAILURE,
                    severity=FaultSeverity.HIGH,
                    detection_time=395,
                    description="Guidance system error",
                    confidence=0.85,
                    parameters={'guidance_error': 2000},
                    recommended_action="Switch to backup guidance"
                )
            ],
            'description': "High altitude guidance failure"
        }
    ]
    
    for scenario in test_scenarios:
        print(f"\n--- {scenario['description']} (t={scenario['time']}s) ---")
        print(f"Altitude: {scenario['telemetry']['altitude']/1000:.1f} km")
        print(f"Velocity: {scenario['telemetry']['velocity_magnitude']:.0f} m/s")
        print(f"Active faults: {len(scenario['faults'])}")
        
        # Update abort manager
        abort_decision = abort_mgr.update_state(
            scenario['telemetry'],
            scenario['faults'],
            scenario['time']
        )
        
        print(f"Abort state: {abort_mgr.get_current_state().value}")
        
        if abort_decision:
            print(f"🚨 ABORT DECISION:")
            print(f"  Mode: {abort_decision.abort_mode.value}")
            print(f"  Reason: {abort_decision.reason}")
            print(f"  Success probability: {abort_decision.estimated_success_probability:.1%}")
            print(f"  Actions required: {len(abort_decision.required_actions)}")
            for i, action in enumerate(abort_decision.required_actions[:3]):
                print(f"    {i+1}. {action}")
            if len(abort_decision.required_actions) > 3:
                print(f"    ... and {len(abort_decision.required_actions)-3} more")
    
    # Test forced abort
    print(f"\n--- Forced Abort Test ---")
    forced_decision = abort_mgr.force_abort(
        AbortMode.AM_II_RTLS,
        "Test abort command",
        500
    )
    print(f"Forced abort mode: {forced_decision.abort_mode.value}")
    print(f"Current state: {abort_mgr.get_current_state().value}")


if __name__ == "__main__":
    main()