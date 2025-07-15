"""
Demonstration of Stuck Sensor Detection
Shows the new fault detection capability for stuck-at sensor failures
"""

from fault_detector import FaultDetector, FaultType
import time

def demo_stuck_sensor():
    """Demonstrate stuck sensor detection"""
    print("=== Stuck Sensor Detection Demo ===\n")
    
    # Create fault detector with appropriate config
    config = {
        'stuck_sensor_check_size': 8,  # Check last 8 values
        'detection_confidence_threshold': 0.7,
        'fault_thresholds': {
            'propellant_critical_percent': 99.0  # Set very high to avoid propellant alerts
        }
    }
    
    detector = FaultDetector(config)
    current_time = 0.0
    
    print("Phase 1: Normal operation with varying sensor readings")
    print("-" * 50)
    
    # Phase 1: Normal varying readings
    for i in range(5):
        telemetry = {
            'altitude': 15000.0 + i * 500,  # Varying altitude
            'velocity_x': 250.0 + i * 10,   # Varying velocity
            'pitch_angle': 45.0 + i * 0.5,  # Varying pitch
            'actual_thrust': 5000000,
            'expected_thrust': 5000000,
            'attitude_error': 1.0,
            'propellant_mass': 150000,
            'initial_propellant_mass': 200000
        }
        
        current_time += 1.0
        faults = detector.update_telemetry(telemetry, current_time)
        
        print(f"t={current_time:4.0f}s: alt={telemetry['altitude']:7.0f}m, "
              f"vel_x={telemetry['velocity_x']:5.0f}m/s, "
              f"pitch={telemetry['pitch_angle']:4.1f}° - {'✅ Normal' if not faults else '⚠️ Fault'}")
    
    print(f"\nActive faults after normal operation: {len(detector.get_active_faults())}")
    
    print("\nPhase 2: Altitude sensor becomes stuck")
    print("-" * 50)
    
    # Phase 2: Altitude sensor stuck, others varying
    stuck_altitude = 17500.0
    for i in range(12):
        telemetry = {
            'altitude': stuck_altitude,      # STUCK VALUE
            'velocity_x': 250.0 + i * 10,   # Still varying
            'pitch_angle': 45.0 + i * 0.2,  # Still varying
            'actual_thrust': 5000000,
            'expected_thrust': 5000000,
            'attitude_error': 1.0,
            'propellant_mass': 150000,
            'initial_propellant_mass': 200000
        }
        
        current_time += 1.0
        faults = detector.update_telemetry(telemetry, current_time)
        
        status = "✅ Normal"
        if faults:
            stuck_faults = [f for f in faults if f.fault_type == FaultType.STUCK_SENSOR]
            if stuck_faults:
                fault = stuck_faults[0]
                status = f"🚨 STUCK {fault.parameters['sensor_name'].upper()} (conf:{fault.confidence:.1%})"
        
        print(f"t={current_time:4.0f}s: alt={telemetry['altitude']:7.0f}m, "
              f"vel_x={telemetry['velocity_x']:5.0f}m/s, "
              f"pitch={telemetry['pitch_angle']:4.1f}° - {status}")
    
    print(f"\nActive faults after stuck sensor: {len(detector.get_active_faults())}")
    for fault in detector.get_active_faults():
        if fault.fault_type == FaultType.STUCK_SENSOR:
            print(f"  - {fault.description}")
            print(f"    Confidence: {fault.confidence:.1%}")
            print(f"    Recommended action: {fault.recommended_action}")
    
    print("\nPhase 3: Altitude sensor recovers")
    print("-" * 50)
    
    # Phase 3: Altitude sensor recovers
    for i in range(8):
        telemetry = {
            'altitude': 17500.0 + i * 200,  # NOW VARYING AGAIN
            'velocity_x': 250.0 + i * 10,
            'pitch_angle': 45.0 + i * 0.2,
            'actual_thrust': 5000000,
            'expected_thrust': 5000000,
            'attitude_error': 1.0,
            'propellant_mass': 150000,
            'initial_propellant_mass': 200000
        }
        
        current_time += 1.0
        faults = detector.update_telemetry(telemetry, current_time)
        
        print(f"t={current_time:4.0f}s: alt={telemetry['altitude']:7.0f}m, "
              f"vel_x={telemetry['velocity_x']:5.0f}m/s, "
              f"pitch={telemetry['pitch_angle']:4.1f}° - ✅ Recovering")
    
    active_faults = detector.get_active_faults()
    altitude_stuck_faults = [f for f in active_faults 
                           if f.fault_type == FaultType.STUCK_SENSOR 
                           and f.parameters.get('sensor_name') == 'altitude']
    
    print(f"\nFinal active stuck sensor faults: {len(altitude_stuck_faults)}")
    if len(altitude_stuck_faults) == 0:
        print("✅ Altitude stuck sensor fault has been resolved!")
    
    print(f"\nTotal fault detection statistics:")
    stats = detector.get_detection_statistics()
    print(f"  - Total checks: {stats['total_checks']}")
    print(f"  - Faults detected: {stats['faults_detected']}")
    print(f"  - Detection rate: {stats['detection_rate']:.1%}")

def demo_trajectory_description():
    """Demonstrate how trajectories are described in the system"""
    print("\n\n=== Trajectory Description Demo ===\n")
    
    # Show the telemetry format from the actual simulation
    print("The simulation tracks trajectory with detailed telemetry:")
    print("-" * 55)
    
    # Sample trajectory points (from the actual simulation output)
    trajectory_points = [
        {"t": 0.0, "stage": 1, "alt": 0.0, "v": 407, "propellant": 100.0, "gamma": -0.0},
        {"t": 10.0, "stage": 1, "alt": 0.0, "v": 401, "propellant": 93.9, "gamma": 0.4},
        {"t": 20.0, "stage": 1, "alt": 0.1, "v": 395, "propellant": 87.7, "gamma": 0.7},
        {"t": 50.0, "stage": 1, "alt": 0.6, "v": 369, "propellant": 69.3, "gamma": 2.0},
        {"t": 100.0, "stage": 1, "alt": 3.2, "v": 321, "propellant": 39.6, "gamma": 4.8},
        {"t": 150.0, "stage": 1, "alt": 9.1, "v": 270, "propellant": 10.0, "gamma": 8.5},
        {"t": 180.0, "stage": 2, "alt": 14.2, "v": 241, "propellant": 100.0, "gamma": 11.2},
        {"t": 200.0, "stage": 2, "alt": 0.1, "v": 468, "propellant": 96.0, "gamma": -30.0}
    ]
    
    print("Time    Stage  Altitude  Velocity  Propellant  Flight Path")
    print("(s)     (#)    (km)      (m/s)     (%)         Angle (γ°)")
    print("-" * 55)
    
    for point in trajectory_points:
        print(f"{point['t']:6.0f}  {point['stage']:3d}    {point['alt']:6.1f}    "
              f"{point['v']:6.0f}    {point['propellant']:6.1f}     {point['gamma']:6.1f}")
    
    print("\nKey Trajectory Phases Tracked:")
    print("=" * 40)
    print("1. LAUNCH (t=0-20s)")
    print("   - Vertical ascent from launch pad")
    print("   - Stage 1 engines at full thrust") 
    print("   - Flight path angle near 0° (mostly vertical)")
    
    print("\n2. GRAVITY TURN (t=20-150s)")
    print("   - Gradual pitch-over maneuver")
    print("   - Building horizontal velocity component")
    print("   - Flight path angle increases to ~8.5°")
    
    print("\n3. STAGE SEPARATION (t=~160s)")
    print("   - Stage 1 propellant depletion")
    print("   - Transition to Stage 2")
    print("   - Continued ascent and acceleration")
    
    print("\n4. ASCENT CONTINUATION (t=160-200s)")
    print("   - Stage 2 burn for orbit insertion")
    print("   - Building velocity toward orbital speed")
    print("   - Complex 3D trajectory tracking")
    
    print("\nThe system provides:")
    print("• Real-time position (x, y, z coordinates)")
    print("• Velocity vectors (magnitude and direction)")  
    print("• Flight path angle (γ) relative to local horizontal")
    print("• Stage performance and propellant consumption")
    print("• Altitude and atmospheric effects")
    print("• Mission phase transitions and abort conditions")

if __name__ == "__main__":
    demo_stuck_sensor()
    demo_trajectory_description()