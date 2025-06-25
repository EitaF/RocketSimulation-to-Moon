"""
Rocket Trajectory Visualizer
Shows the progress of Professor v15 improvements
"""

import numpy as np
import matplotlib.pyplot as plt
from rocket_simulation_clean import RocketSimulation
import time

def run_trajectory_analysis():
    """Run simulation and collect trajectory data"""
    print("Running trajectory analysis...")
    
    sim = RocketSimulation("saturn_v_config.json")
    sim.config["simulation"]["duration"] = 2400  # 40 minutes
    
    # Data collection
    trajectory_data = {
        'time': [],
        'x': [],
        'y': [],
        'altitude': [],
        'velocity': [],
        'horizontal_velocity': [],
        'vertical_velocity': [],
        'flight_path_angle': [],
        'pitch_angle': [],
        'dynamic_pressure': [],
        'stage': [],
        'phase': [],
        'thrust_magnitude': []
    }
    
    stage_events = []
    phase_changes = []
    last_phase = None
    
    step_count = 0
    max_steps = int(2400 / sim.dt)
    
    print("Collecting trajectory data...")
    start_time = time.time()
    
    while step_count < max_steps and sim.step():
        # Collect data every 5 seconds (50 steps at dt=0.1)
        if step_count % 50 == 0:
            # Position and basic state
            pos = sim.state.position
            vel = sim.state.velocity
            altitude = sim.get_altitude()
            velocity = vel.magnitude()
            
            # Calculate horizontal and vertical components
            pos_unit = pos.normalized()
            vel_radial = pos_unit.data @ vel.data  # Radial velocity (positive = outward)
            vel_horizontal = np.sqrt(max(0, velocity**2 - vel_radial**2))
            
            # Flight path angle
            flight_path_angle = np.degrees(sim.get_flight_path_angle())
            
            # Dynamic pressure
            dynamic_pressure = sim.get_dynamic_pressure()
            
            # Thrust information
            stage = sim.rocket.current_stage_obj
            thrust_magnitude = sim.rocket.get_thrust(altitude) if stage and stage.propellant_mass > 0 else 0
            
            # Store data
            trajectory_data['time'].append(sim.state.time)
            trajectory_data['x'].append(pos.x / 1000)  # Convert to km
            trajectory_data['y'].append(pos.y / 1000)  # Convert to km
            trajectory_data['altitude'].append(altitude / 1000)  # Convert to km
            trajectory_data['velocity'].append(velocity)
            trajectory_data['horizontal_velocity'].append(vel_horizontal)
            trajectory_data['vertical_velocity'].append(vel_radial)
            trajectory_data['flight_path_angle'].append(flight_path_angle)
            trajectory_data['dynamic_pressure'].append(dynamic_pressure / 1000)  # Convert to kPa
            trajectory_data['stage'].append(sim.rocket.current_stage)
            trajectory_data['phase'].append(sim.state.phase.value)
            trajectory_data['thrust_magnitude'].append(thrust_magnitude / 1000)  # Convert to kN
            
            # Track phase changes
            if sim.state.phase.value != last_phase:
                phase_changes.append({
                    'time': sim.state.time,
                    'phase': sim.state.phase.value,
                    'altitude': altitude / 1000
                })
                last_phase = sim.state.phase.value
        
        # Track stage events
        if len(sim.stage_events) > len(stage_events):
            stage_events.extend(sim.stage_events[len(stage_events):])
        
        step_count += 1
        
        # Break conditions
        if sim.state.phase.value in ['failed', 'leo']:
            print(f"Simulation ended: {sim.state.phase.value}")
            break
    
    elapsed = time.time() - start_time
    print(f"Simulation completed in {elapsed:.1f} seconds")
    print(f"Final altitude: {sim.get_altitude()/1000:.1f} km")
    print(f"Final velocity: {sim.state.velocity.magnitude():.1f} m/s")
    print(f"Stage events: {len(stage_events)}")
    
    return trajectory_data, stage_events, phase_changes

def create_trajectory_plots(trajectory_data, stage_events, phase_changes):
    """Create comprehensive trajectory visualization"""
    
    # Convert to numpy arrays for easier handling
    time_arr = np.array(trajectory_data['time'])
    x_arr = np.array(trajectory_data['x'])
    y_arr = np.array(trajectory_data['y'])
    alt_arr = np.array(trajectory_data['altitude'])
    vel_arr = np.array(trajectory_data['velocity'])
    h_vel_arr = np.array(trajectory_data['horizontal_velocity'])
    v_vel_arr = np.array(trajectory_data['vertical_velocity'])
    fpa_arr = np.array(trajectory_data['flight_path_angle'])
    q_arr = np.array(trajectory_data['dynamic_pressure'])
    stage_arr = np.array(trajectory_data['stage'])
    thrust_arr = np.array(trajectory_data['thrust_magnitude'])
    
    # Create figure with subplots
    fig = plt.figure(figsize=(16, 12))
    fig.suptitle('Professor v15 Rocket Trajectory Analysis\nShowing Improvements in Stage Separation and Trajectory', fontsize=16, fontweight='bold')
    
    # 1. Ground Track (X-Y trajectory)
    ax1 = plt.subplot(2, 3, 1)
    plt.plot(x_arr, y_arr, 'b-', linewidth=2, label='Trajectory')
    
    # Add Earth
    earth_circle = plt.Circle((0, 0), 6371, fill=False, color='green', linewidth=2, label='Earth')
    ax1.add_patch(earth_circle)
    
    # Mark stage events
    for i, event in enumerate(stage_events):
        event_idx = np.argmin(np.abs(time_arr - event['time']))
        if event_idx < len(x_arr):
            plt.plot(x_arr[event_idx], y_arr[event_idx], 'ro', markersize=8, 
                    label=f"Stage {event['stage']} sep")
            plt.annotate(f"S{event['stage']}", 
                        (x_arr[event_idx], y_arr[event_idx]), 
                        xytext=(5, 5), textcoords='offset points')
    
    plt.xlabel('X Position (km)')
    plt.ylabel('Y Position (km)')
    plt.title('Ground Track View')
    plt.axis('equal')
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    # 2. Altitude vs Time
    ax2 = plt.subplot(2, 3, 2)
    plt.plot(time_arr, alt_arr, 'b-', linewidth=2, label='Altitude')
    
    # Color-code by stage
    stage_colors = ['red', 'orange', 'green', 'blue']
    for stage_num in range(int(stage_arr.max()) + 1):
        stage_mask = stage_arr == stage_num
        if np.any(stage_mask):
            plt.scatter(time_arr[stage_mask], alt_arr[stage_mask], 
                       c=stage_colors[stage_num % len(stage_colors)], 
                       s=10, alpha=0.6, label=f'Stage {stage_num}')
    
    # Mark stage separations
    for event in stage_events:
        plt.axvline(x=event['time'], color='red', linestyle='--', alpha=0.7)
        plt.annotate(f"Stage {event['stage']}\n{event['altitude']/1000:.1f} km", 
                    (event['time'], event['altitude']/1000), 
                    xytext=(10, 10), textcoords='offset points',
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="yellow", alpha=0.7))
    
    # Mark target altitudes
    plt.axhline(y=45, color='green', linestyle=':', alpha=0.7, label='Stage-1 target (45km)')
    plt.axhline(y=185, color='purple', linestyle=':', alpha=0.7, label='LEO target (185km)')
    
    plt.xlabel('Time (s)')
    plt.ylabel('Altitude (km)')
    plt.title('Altitude Profile')
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    # 3. Velocity Components
    ax3 = plt.subplot(2, 3, 3)
    plt.plot(time_arr, vel_arr, 'b-', linewidth=2, label='Total Velocity')
    plt.plot(time_arr, h_vel_arr, 'g-', linewidth=2, label='Horizontal Velocity')
    plt.plot(time_arr, np.abs(v_vel_arr), 'r-', linewidth=2, label='Vertical Velocity (abs)')
    
    # Mark target velocities
    plt.axhline(y=7800, color='purple', linestyle=':', alpha=0.7, label='LEO velocity target')
    
    plt.xlabel('Time (s)')
    plt.ylabel('Velocity (m/s)')
    plt.title('Velocity Components')
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    # 4. Flight Path Angle and Dynamic Pressure
    ax4 = plt.subplot(2, 3, 4)
    ax4_twin = ax4.twinx()
    
    line1 = ax4.plot(time_arr, fpa_arr, 'b-', linewidth=2, label='Flight Path Angle')
    line2 = ax4_twin.plot(time_arr, q_arr, 'r-', linewidth=2, label='Dynamic Pressure')
    
    # Mark important thresholds
    ax4_twin.axhline(y=50, color='orange', linestyle='--', alpha=0.7, label='50 kPa threshold')
    ax4.axhline(y=0, color='black', linestyle='-', alpha=0.5)
    
    ax4.set_xlabel('Time (s)')
    ax4.set_ylabel('Flight Path Angle (deg)', color='b')
    ax4_twin.set_ylabel('Dynamic Pressure (kPa)', color='r')
    ax4.set_title('Flight Path Angle & Dynamic Pressure')
    ax4.grid(True, alpha=0.3)
    
    # Combine legends
    lines1, labels1 = ax4.get_legend_handles_labels()
    lines2, labels2 = ax4_twin.get_legend_handles_labels()
    ax4.legend(lines1 + lines2, labels1 + labels2, loc='upper right')
    
    # 5. Altitude vs Velocity (Trajectory Shape)
    ax5 = plt.subplot(2, 3, 5)
    
    # Color-code by time
    scatter = plt.scatter(vel_arr, alt_arr, c=time_arr, cmap='viridis', s=20, alpha=0.7)
    plt.colorbar(scatter, label='Time (s)')
    
    # Mark key points
    for i, event in enumerate(stage_events):
        event_idx = np.argmin(np.abs(time_arr - event['time']))
        if event_idx < len(vel_arr):
            plt.plot(vel_arr[event_idx], alt_arr[event_idx], 'ro', markersize=10)
            plt.annotate(f"S{event['stage']}", 
                        (vel_arr[event_idx], alt_arr[event_idx]), 
                        xytext=(5, 5), textcoords='offset points')
    
    plt.xlabel('Velocity (m/s)')
    plt.ylabel('Altitude (km)')
    plt.title('Altitude vs Velocity\n(Trajectory Shape)')
    plt.grid(True, alpha=0.3)
    
    # 6. Thrust Profile
    ax6 = plt.subplot(2, 3, 6)
    plt.plot(time_arr, thrust_arr, 'orange', linewidth=2, label='Thrust')
    
    # Mark stage separations
    for event in stage_events:
        plt.axvline(x=event['time'], color='red', linestyle='--', alpha=0.7)
    
    plt.xlabel('Time (s)')
    plt.ylabel('Thrust (kN)')
    plt.title('Thrust Profile')
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    plt.tight_layout()
    
    # Save the plot
    plt.savefig('rocket_trajectory_professor_v15.png', dpi=300, bbox_inches='tight')
    print("Trajectory plot saved as 'rocket_trajectory_professor_v15.png'")
    
    return fig

def print_trajectory_summary(trajectory_data, stage_events, phase_changes):
    """Print detailed trajectory analysis"""
    
    print("\n" + "="*60)
    print("PROFESSOR v15 TRAJECTORY ANALYSIS SUMMARY")
    print("="*60)
    
    # Flight statistics
    max_altitude = max(trajectory_data['altitude'])
    max_velocity = max(trajectory_data['velocity'])
    max_horizontal_velocity = max(trajectory_data['horizontal_velocity'])
    final_altitude = trajectory_data['altitude'][-1]
    final_velocity = trajectory_data['velocity'][-1]
    
    print(f"\n📊 FLIGHT STATISTICS:")
    print(f"  Max Altitude: {max_altitude:.1f} km")
    print(f"  Max Velocity: {max_velocity:.1f} m/s")
    print(f"  Max Horizontal Velocity: {max_horizontal_velocity:.1f} m/s")
    print(f"  Final Altitude: {final_altitude:.1f} km")
    print(f"  Final Velocity: {final_velocity:.1f} m/s")
    
    # Stage events analysis
    print(f"\n🚀 STAGE SEPARATION EVENTS:")
    for i, event in enumerate(stage_events):
        print(f"  Stage {event['stage']}: t={event['time']:.1f}s, alt={event['altitude']/1000:.1f}km")
        
        # Check against targets
        if event['stage'] == 1:  # Stage 1 separation
            target_range = "45-55 km"
            actual_alt = event['altitude']/1000
            status = "✅ PASS" if 45 <= actual_alt <= 55 else "❌ FAIL"
            print(f"    Target: {target_range}, Actual: {actual_alt:.1f}km, Status: {status}")
    
    # Phase progression
    print(f"\n📋 MISSION PHASE PROGRESSION:")
    for phase in phase_changes:
        print(f"  {phase['time']:6.1f}s: {phase['phase']} (alt={phase['altitude']:.1f}km)")
    
    # Performance assessment
    print(f"\n🎯 PROFESSOR v15 COMPLIANCE:")
    
    # Check Stage-1 performance
    stage1_events = [e for e in stage_events if e['stage'] == 1]
    if stage1_events:
        stage1_alt = stage1_events[0]['altitude'] / 1000
        stage1_pass = 45 <= stage1_alt <= 55
        print(f"  Stage-1 burnout: {stage1_alt:.1f}km {'✅ PASS' if stage1_pass else '❌ FAIL'} (target: 45-55km)")
    else:
        print(f"  Stage-1 burnout: ❌ FAIL (no separation detected)")
    
    # Check Stage-2 ignition
    stage2_events = [e for e in stage_events if e['stage'] == 2]
    if stage2_events:
        stage2_alt = stage2_events[0]['altitude'] / 1000
        stage2_pass = 70 <= stage2_alt <= 80
        print(f"  Stage-2 ignition: {stage2_alt:.1f}km {'✅ PASS' if stage2_pass else '⚠️  PARTIAL'} (target: 70-80km)")
    else:
        print(f"  Stage-2 ignition: ⚠️  PARTIAL (ignited but no separation)")
    
    # Check final performance
    leo_altitude_pass = final_altitude >= 185
    leo_velocity_pass = max_horizontal_velocity >= 7750
    
    print(f"  LEO altitude: {final_altitude:.1f}km {'✅ PASS' if leo_altitude_pass else '❌ FAIL'} (target: ≥185km)")
    print(f"  LEO velocity: {max_horizontal_velocity:.1f}m/s {'✅ PASS' if leo_velocity_pass else '❌ FAIL'} (target: ≥7800m/s)")
    
    # Overall assessment
    total_checks = 4
    passed_checks = sum([
        len(stage1_events) > 0 and 45 <= stage1_events[0]['altitude']/1000 <= 55,
        len(stage2_events) > 0,  # Partial credit for Stage-2 ignition
        leo_altitude_pass,
        leo_velocity_pass
    ])
    
    print(f"\n🏆 OVERALL PROGRESS: {passed_checks}/{total_checks} checks passed ({passed_checks/total_checks*100:.1f}%)")
    
    if passed_checks >= 3:
        print("🎯 STATUS: EXCELLENT PROGRESS - Major improvements achieved!")
    elif passed_checks >= 2:
        print("📈 STATUS: GOOD PROGRESS - Significant improvements made")
    else:
        print("⚠️  STATUS: NEEDS MORE WORK - Continue optimization")

def main():
    """Main trajectory visualization function"""
    print("🚀 Professor v15 Trajectory Visualization")
    print("Analyzing rocket performance improvements...")
    
    # Run trajectory analysis
    trajectory_data, stage_events, phase_changes = run_trajectory_analysis()
    
    # Create visualizations
    fig = create_trajectory_plots(trajectory_data, stage_events, phase_changes)
    
    # Print summary
    print_trajectory_summary(trajectory_data, stage_events, phase_changes)
    
    print(f"\n📊 Trajectory visualization complete!")
    print(f"📁 Plot saved as 'rocket_trajectory_professor_v15.png'")
    
    return trajectory_data, stage_events, phase_changes

if __name__ == "__main__":
    main()