"""
Fault Detection System for Mission Abort Framework
Task 3-2: Real-time fault detection with 95% accuracy requirement
"""

import numpy as np
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from collections import deque


class FaultType(Enum):
    """Types of faults that can be detected"""
    THRUST_DEFICIT = "thrust_deficit"
    ATTITUDE_DEVIATION = "attitude_deviation"
    SENSOR_DROPOUT = "sensor_dropout"
    PROPELLANT_DEPLETION = "propellant_depletion"
    STRUCTURAL_FAILURE = "structural_failure"
    GUIDANCE_FAILURE = "guidance_failure"
    STAGE_SEPARATION_FAILURE = "stage_separation_failure"


class FaultSeverity(Enum):
    """Severity levels for detected faults"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class FaultEvent:
    """Container for fault detection events"""
    fault_type: FaultType
    severity: FaultSeverity
    detection_time: float
    description: str
    confidence: float  # 0.0 to 1.0
    parameters: Dict
    recommended_action: str


class FaultDetector:
    """
    Real-time fault detection system for rocket missions
    Monitors telemetry data and detects various failure modes
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.logger = logging.getLogger(__name__)
        self.config = config or self._get_default_config()
        
        # Fault detection thresholds
        self.thresholds = self.config.get('fault_thresholds', {})
        
        # Historical data buffers for trend analysis
        self.history_size = self.config.get('history_buffer_size', 100)
        self.thrust_history = deque(maxlen=self.history_size)
        self.attitude_history = deque(maxlen=self.history_size)
        self.sensor_history = deque(maxlen=self.history_size)
        self.propellant_history = deque(maxlen=self.history_size)
        
        # Fault state tracking
        self.active_faults: List[FaultEvent] = []
        self.fault_history: List[FaultEvent] = []
        self.last_sensor_update = 0.0
        
        # Statistics
        self.detection_stats = {
            'total_checks': 0,
            'faults_detected': 0,
            'false_positives': 0,
            'missed_detections': 0
        }
        
        self.logger.info("Fault detection system initialized")
    
    def _get_default_config(self) -> Dict:
        """Get default configuration for fault detection"""
        return {
            'fault_thresholds': {
                'thrust_deficit_percent': 15.0,      # 15% thrust loss
                'attitude_deviation_deg': 5.0,       # 5 degree attitude error
                'sensor_timeout_sec': 1.0,           # 1 second sensor dropout
                'propellant_critical_percent': 98.0, # 98% propellant consumed
                'structural_g_limit': 8.0,           # 8g structural limit
                'guidance_error_threshold': 1000.0   # 1000m guidance error
            },
            'detection_confidence_threshold': 0.8,   # 80% confidence required
            'history_buffer_size': 100,
            'enable_predictive_detection': True
        }
    
    def update_telemetry(self, telemetry: Dict, current_time: float) -> List[FaultEvent]:
        """
        Update telemetry data and perform fault detection
        
        Args:
            telemetry: Dictionary containing current telemetry data
            current_time: Mission elapsed time [s]
            
        Returns:
            List of newly detected fault events
        """
        self.detection_stats['total_checks'] += 1
        newly_detected_faults = []
        
        # Store historical data
        self._update_history(telemetry, current_time)
        
        # Perform various fault checks
        faults = []
        faults.extend(self._check_thrust_deficit(telemetry, current_time))
        faults.extend(self._check_attitude_deviation(telemetry, current_time))
        faults.extend(self._check_sensor_dropout(telemetry, current_time))
        faults.extend(self._check_propellant_depletion(telemetry, current_time))
        faults.extend(self._check_structural_limits(telemetry, current_time))
        faults.extend(self._check_guidance_errors(telemetry, current_time))
        
        # Filter by confidence threshold and add new faults
        confidence_threshold = self.config.get('detection_confidence_threshold', 0.8)
        
        for fault in faults:
            if fault.confidence >= confidence_threshold:
                # Check if this is a new fault (not already active)
                if not self._is_fault_active(fault):
                    self.active_faults.append(fault)
                    self.fault_history.append(fault)
                    newly_detected_faults.append(fault)
                    self.detection_stats['faults_detected'] += 1
                    
                    self.logger.warning(
                        f"FAULT DETECTED: {fault.fault_type.value} - {fault.description} "
                        f"(Confidence: {fault.confidence:.1%})"
                    )
        
        # Clean up resolved faults
        self._cleanup_resolved_faults(telemetry, current_time)
        
        return newly_detected_faults
    
    def _update_history(self, telemetry: Dict, current_time: float):
        """Update historical data buffers"""
        # Thrust history
        thrust_data = {
            'time': current_time,
            'actual_thrust': telemetry.get('actual_thrust', 0),
            'expected_thrust': telemetry.get('expected_thrust', 0),
            'thrust_efficiency': telemetry.get('thrust_efficiency', 1.0)
        }
        self.thrust_history.append(thrust_data)
        
        # Attitude history
        attitude_data = {
            'time': current_time,
            'pitch': telemetry.get('pitch_angle', 0),
            'yaw': telemetry.get('yaw_angle', 0),
            'roll': telemetry.get('roll_angle', 0),
            'target_pitch': telemetry.get('target_pitch', 0),
            'attitude_error': telemetry.get('attitude_error', 0)
        }
        self.attitude_history.append(attitude_data)
        
        # Sensor history
        sensor_data = {
            'time': current_time,
            'altitude_valid': telemetry.get('altitude_sensor_valid', True),
            'velocity_valid': telemetry.get('velocity_sensor_valid', True),
            'attitude_valid': telemetry.get('attitude_sensor_valid', True),
            'gps_valid': telemetry.get('gps_valid', True)
        }
        self.sensor_history.append(sensor_data)
        
        # Propellant history
        propellant_data = {
            'time': current_time,
            'stage': telemetry.get('current_stage', 0),
            'propellant_mass': telemetry.get('propellant_mass', 0),
            'initial_propellant': telemetry.get('initial_propellant_mass', 1),
            'mass_flow_rate': telemetry.get('mass_flow_rate', 0)
        }
        self.propellant_history.append(propellant_data)
        
        self.last_sensor_update = current_time
    
    def _check_thrust_deficit(self, telemetry: Dict, current_time: float) -> List[FaultEvent]:
        """Detect thrust deficit conditions"""
        faults = []
        
        actual_thrust = telemetry.get('actual_thrust', 0)
        expected_thrust = telemetry.get('expected_thrust', 0)
        
        if expected_thrust > 0:
            thrust_deficit_percent = (expected_thrust - actual_thrust) / expected_thrust * 100
            threshold = self.thresholds.get('thrust_deficit_percent', 15.0)
            
            if thrust_deficit_percent > threshold:
                # Analyze trend using historical data
                confidence = self._calculate_thrust_deficit_confidence(thrust_deficit_percent)
                
                severity = FaultSeverity.MEDIUM
                if thrust_deficit_percent > 30:
                    severity = FaultSeverity.CRITICAL
                elif thrust_deficit_percent > 20:
                    severity = FaultSeverity.HIGH
                
                fault = FaultEvent(
                    fault_type=FaultType.THRUST_DEFICIT,
                    severity=severity,
                    detection_time=current_time,
                    description=f"Thrust deficit of {thrust_deficit_percent:.1f}% detected",
                    confidence=confidence,
                    parameters={
                        'actual_thrust': actual_thrust,
                        'expected_thrust': expected_thrust,
                        'deficit_percent': thrust_deficit_percent
                    },
                    recommended_action="Abort mission or switch to backup engine"
                )
                faults.append(fault)
        
        return faults
    
    def _check_attitude_deviation(self, telemetry: Dict, current_time: float) -> List[FaultEvent]:
        """Detect attitude control failures"""
        faults = []
        
        attitude_error = telemetry.get('attitude_error', 0)  # degrees
        threshold = self.thresholds.get('attitude_deviation_deg', 5.0)
        
        if attitude_error > threshold:
            # Check if this is a persistent problem
            confidence = self._calculate_attitude_confidence(attitude_error)
            
            severity = FaultSeverity.LOW
            if attitude_error > 15:
                severity = FaultSeverity.CRITICAL
            elif attitude_error > 10:
                severity = FaultSeverity.HIGH
            elif attitude_error > 7:
                severity = FaultSeverity.MEDIUM
            
            fault = FaultEvent(
                fault_type=FaultType.ATTITUDE_DEVIATION,
                severity=severity,
                detection_time=current_time,
                description=f"Attitude deviation of {attitude_error:.1f}° detected",
                confidence=confidence,
                parameters={
                    'attitude_error': attitude_error,
                    'pitch': telemetry.get('pitch_angle', 0),
                    'yaw': telemetry.get('yaw_angle', 0),
                    'roll': telemetry.get('roll_angle', 0)
                },
                recommended_action="Engage attitude hold mode or abort"
            )
            faults.append(fault)
        
        return faults
    
    def _check_sensor_dropout(self, telemetry: Dict, current_time: float) -> List[FaultEvent]:
        """Detect sensor failures and communication dropouts"""
        faults = []
        
        timeout_threshold = self.thresholds.get('sensor_timeout_sec', 1.0)
        time_since_update = current_time - self.last_sensor_update
        
        # Check for sensor timeouts
        if time_since_update > timeout_threshold:
            confidence = min(1.0, time_since_update / timeout_threshold)
            
            fault = FaultEvent(
                fault_type=FaultType.SENSOR_DROPOUT,
                severity=FaultSeverity.HIGH,
                detection_time=current_time,
                description=f"Sensor dropout detected: {time_since_update:.1f}s since last update",
                confidence=confidence,
                parameters={
                    'timeout_duration': time_since_update,
                    'last_update_time': self.last_sensor_update
                },
                recommended_action="Switch to backup sensors or safe mode"
            )
            faults.append(fault)
        
        # Check individual sensor validity
        sensors = {
            'altitude': telemetry.get('altitude_sensor_valid', True),
            'velocity': telemetry.get('velocity_sensor_valid', True),
            'attitude': telemetry.get('attitude_sensor_valid', True),
            'gps': telemetry.get('gps_valid', True)
        }
        
        for sensor_name, is_valid in sensors.items():
            if not is_valid:
                fault = FaultEvent(
                    fault_type=FaultType.SENSOR_DROPOUT,
                    severity=FaultSeverity.MEDIUM,
                    detection_time=current_time,
                    description=f"{sensor_name.capitalize()} sensor failure detected",
                    confidence=0.95,  # High confidence for explicit sensor flags
                    parameters={'failed_sensor': sensor_name},
                    recommended_action=f"Switch to backup {sensor_name} sensor"
                )
                faults.append(fault)
        
        return faults
    
    def _check_propellant_depletion(self, telemetry: Dict, current_time: float) -> List[FaultEvent]:
        """Detect propellant depletion conditions"""
        faults = []
        
        propellant_mass = telemetry.get('propellant_mass', 0)
        initial_propellant = telemetry.get('initial_propellant_mass', 1)
        
        if initial_propellant > 0:
            propellant_usage_percent = (1 - propellant_mass / initial_propellant) * 100
            threshold = self.thresholds.get('propellant_critical_percent', 98.0)
            
            if propellant_usage_percent > threshold:
                confidence = min(1.0, (propellant_usage_percent - threshold) / 2.0 + 0.8)
                
                fault = FaultEvent(
                    fault_type=FaultType.PROPELLANT_DEPLETION,
                    severity=FaultSeverity.HIGH,
                    detection_time=current_time,
                    description=f"Propellant critically low: {propellant_usage_percent:.1f}% consumed",
                    confidence=confidence,
                    parameters={
                        'remaining_propellant': propellant_mass,
                        'usage_percent': propellant_usage_percent,
                        'current_stage': telemetry.get('current_stage', 0)
                    },
                    recommended_action="Prepare for stage separation or mission abort"
                )
                faults.append(fault)
        
        return faults
    
    def _check_structural_limits(self, telemetry: Dict, current_time: float) -> List[FaultEvent]:
        """Detect structural overload conditions"""
        faults = []
        
        acceleration_magnitude = telemetry.get('total_acceleration', 0)  # m/s²
        g_force = acceleration_magnitude / 9.80665  # Convert to g's
        g_limit = self.thresholds.get('structural_g_limit', 8.0)
        
        if g_force > g_limit:
            confidence = min(1.0, (g_force - g_limit) / g_limit + 0.7)
            
            fault = FaultEvent(
                fault_type=FaultType.STRUCTURAL_FAILURE,
                severity=FaultSeverity.CRITICAL,
                detection_time=current_time,
                description=f"Structural g-force limit exceeded: {g_force:.1f}g",
                confidence=confidence,
                parameters={
                    'g_force': g_force,
                    'acceleration': acceleration_magnitude,
                    'limit': g_limit
                },
                recommended_action="Immediate thrust reduction or abort"
            )
            faults.append(fault)
        
        return faults
    
    def _check_guidance_errors(self, telemetry: Dict, current_time: float) -> List[FaultEvent]:
        """Detect guidance system failures"""
        faults = []
        
        guidance_error = telemetry.get('guidance_error_magnitude', 0)  # meters
        threshold = self.thresholds.get('guidance_error_threshold', 1000.0)
        
        if guidance_error > threshold:
            confidence = min(1.0, guidance_error / threshold * 0.8)
            
            fault = FaultEvent(
                fault_type=FaultType.GUIDANCE_FAILURE,
                severity=FaultSeverity.HIGH,
                detection_time=current_time,
                description=f"Guidance error exceeds threshold: {guidance_error:.0f}m",
                confidence=confidence,
                parameters={
                    'guidance_error': guidance_error,
                    'threshold': threshold
                },
                recommended_action="Switch to backup guidance or manual control"
            )
            faults.append(fault)
        
        return faults
    
    def _calculate_thrust_deficit_confidence(self, deficit_percent: float) -> float:
        """Calculate confidence for thrust deficit detection"""
        # Higher deficit = higher confidence
        base_confidence = 0.6
        trend_factor = 0.0
        
        # Analyze trend in thrust history
        if len(self.thrust_history) >= 3:
            recent_deficits = []
            for data in list(self.thrust_history)[-3:]:
                if data['expected_thrust'] > 0:
                    deficit = (data['expected_thrust'] - data['actual_thrust']) / data['expected_thrust'] * 100
                    recent_deficits.append(deficit)
            
            if len(recent_deficits) >= 2:
                # Consistent deficit increases confidence
                if all(d > 10 for d in recent_deficits):
                    trend_factor = 0.3
                elif all(d > 5 for d in recent_deficits):
                    trend_factor = 0.2
        
        # Magnitude factor
        magnitude_factor = min(0.3, deficit_percent / 100)
        
        return min(1.0, base_confidence + trend_factor + magnitude_factor)
    
    def _calculate_attitude_confidence(self, attitude_error: float) -> float:
        """Calculate confidence for attitude deviation detection"""
        base_confidence = 0.5
        
        # Check consistency in attitude history
        if len(self.attitude_history) >= 5:
            recent_errors = [data['attitude_error'] for data in list(self.attitude_history)[-5:]]
            avg_error = np.mean(recent_errors)
            
            # Consistent high error increases confidence
            if avg_error > 3.0:
                base_confidence += 0.3
            
        # Magnitude factor
        magnitude_factor = min(0.4, attitude_error / 20)
        
        return min(1.0, base_confidence + magnitude_factor)
    
    def _is_fault_active(self, new_fault: FaultEvent) -> bool:
        """Check if a similar fault is already active"""
        for active_fault in self.active_faults:
            if (active_fault.fault_type == new_fault.fault_type and
                active_fault.severity == new_fault.severity):
                # Same type and severity - consider it the same fault
                return True
        return False
    
    def _cleanup_resolved_faults(self, telemetry: Dict, current_time: float):
        """Remove faults that have been resolved"""
        resolved_faults = []
        
        for fault in self.active_faults:
            if self._is_fault_resolved(fault, telemetry, current_time):
                resolved_faults.append(fault)
                self.logger.info(f"Fault resolved: {fault.fault_type.value}")
        
        for fault in resolved_faults:
            self.active_faults.remove(fault)
    
    def _is_fault_resolved(self, fault: FaultEvent, telemetry: Dict, current_time: float) -> bool:
        """Check if a fault condition has been resolved"""
        # Simple resolution logic - could be enhanced
        fault_age = current_time - fault.detection_time
        
        if fault.fault_type == FaultType.THRUST_DEFICIT:
            actual_thrust = telemetry.get('actual_thrust', 0)
            expected_thrust = telemetry.get('expected_thrust', 0)
            if expected_thrust > 0:
                deficit = (expected_thrust - actual_thrust) / expected_thrust * 100
                return deficit < 5.0  # Resolved if deficit < 5%
        
        elif fault.fault_type == FaultType.ATTITUDE_DEVIATION:
            attitude_error = telemetry.get('attitude_error', 0)
            return attitude_error < 2.0  # Resolved if error < 2°
        
        elif fault.fault_type == FaultType.SENSOR_DROPOUT:
            # Assume resolved if we're still getting telemetry
            return fault_age > 10.0  # Auto-resolve after 10 seconds
        
        return False
    
    def get_active_faults(self) -> List[FaultEvent]:
        """Get list of currently active faults"""
        return self.active_faults.copy()
    
    def get_fault_history(self) -> List[FaultEvent]:
        """Get complete fault detection history"""
        return self.fault_history.copy()
    
    def get_detection_statistics(self) -> Dict:
        """Get fault detection performance statistics"""
        stats = self.detection_stats.copy()
        
        if stats['total_checks'] > 0:
            stats['detection_rate'] = stats['faults_detected'] / stats['total_checks']
            stats['false_positive_rate'] = stats['false_positives'] / stats['total_checks']
        else:
            stats['detection_rate'] = 0.0
            stats['false_positive_rate'] = 0.0
        
        return stats
    
    def reset(self):
        """Reset fault detector state"""
        self.active_faults.clear()
        self.fault_history.clear()
        self.thrust_history.clear()
        self.attitude_history.clear()
        self.sensor_history.clear()
        self.propellant_history.clear()
        
        self.detection_stats = {
            'total_checks': 0,
            'faults_detected': 0,
            'false_positives': 0,
            'missed_detections': 0
        }
        
        self.logger.info("Fault detection system reset")


def main():
    """Test the fault detection system"""
    print("Fault Detection System Test")
    print("=" * 40)
    
    # Create fault detector
    detector = FaultDetector()
    
    # Simulate some telemetry data
    test_cases = [
        # Normal operation
        {
            'actual_thrust': 5000000,
            'expected_thrust': 5000000,
            'attitude_error': 1.0,
            'altitude_sensor_valid': True,
            'propellant_mass': 100000,
            'initial_propellant_mass': 200000,
            'total_acceleration': 30.0
        },
        # Thrust deficit
        {
            'actual_thrust': 4000000,
            'expected_thrust': 5000000,
            'attitude_error': 1.0,
            'altitude_sensor_valid': True,
            'propellant_mass': 90000,
            'initial_propellant_mass': 200000,
            'total_acceleration': 25.0
        },
        # Attitude deviation
        {
            'actual_thrust': 5000000,
            'expected_thrust': 5000000,
            'attitude_error': 8.0,
            'altitude_sensor_valid': True,
            'propellant_mass': 80000,
            'initial_propellant_mass': 200000,
            'total_acceleration': 30.0
        },
        # Sensor failure
        {
            'actual_thrust': 5000000,
            'expected_thrust': 5000000,
            'attitude_error': 1.0,
            'altitude_sensor_valid': False,
            'propellant_mass': 70000,
            'initial_propellant_mass': 200000,
            'total_acceleration': 30.0
        }
    ]
    
    current_time = 0.0
    
    for i, telemetry in enumerate(test_cases):
        current_time += 10.0  # 10 second intervals
        
        print(f"\nTest Case {i+1} (t={current_time}s):")
        print(f"  Thrust: {telemetry['actual_thrust']/1000:.0f}kN / {telemetry['expected_thrust']/1000:.0f}kN")
        print(f"  Attitude error: {telemetry['attitude_error']:.1f}°")
        print(f"  Sensors valid: {telemetry['altitude_sensor_valid']}")
        
        faults = detector.update_telemetry(telemetry, current_time)
        
        if faults:
            for fault in faults:
                print(f"  ⚠️  FAULT: {fault.fault_type.value} ({fault.severity.value})")
                print(f"      {fault.description}")
                print(f"      Confidence: {fault.confidence:.1%}")
                print(f"      Action: {fault.recommended_action}")
        else:
            print("  ✅ No faults detected")
    
    # Print summary
    print(f"\nDetection Summary:")
    stats = detector.get_detection_statistics()
    print(f"  Total checks: {stats['total_checks']}")
    print(f"  Faults detected: {stats['faults_detected']}")
    print(f"  Detection rate: {stats['detection_rate']:.1%}")
    
    active_faults = detector.get_active_faults()
    print(f"  Active faults: {len(active_faults)}")


if __name__ == "__main__":
    main()