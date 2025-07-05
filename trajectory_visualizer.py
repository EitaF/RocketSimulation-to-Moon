"""
Rocket Trajectory Visualizer
Enhanced for lunar intercept visualization (Professor v32)
Shows spacecraft and Moon trajectories in the same reference frame
"""

import numpy as np
import matplotlib.pyplot as plt
import rocket_simulation_main
from rocket_simulation_main import Mission, create_saturn_v_rocket
import time

def run_trajectory_analysis(duration=7*24*3600):
    """Run simulation and collect trajectory data for lunar mission"""
    print("Running trajectory analysis...")
    
    sim = Mission(create_saturn_v_rocket("saturn_v_config.json"), {"simulation": {"duration": duration}})
    sim.config["simulation"]["duration"] = duration  # Extended for lunar mission
    
    results = sim.simulate()
    
    return results, [], []

def create_trajectory_plots(trajectory_data, stage_events, phase_changes):
    """Create comprehensive trajectory visualization including lunar intercept"""
    
    # Convert to numpy arrays for easier handling
    time_arr = np.array(trajectory_data['time_history'])
    alt_arr = np.array(trajectory_data['altitude_history'])
    vel_arr = np.array([np.sqrt(v[0]**2 + v[1]**2) for v in trajectory_data['velocity_history']])
    x_arr = np.array([p[0] for p in trajectory_data['position_history']])
    y_arr = np.array([p[1] for p in trajectory_data['position_history']])
    
    # Extract Moon trajectory data if available
    moon_x_arr = np.array([p[0] for p in trajectory_data.get('moon_position_history', [])])
    moon_y_arr = np.array([p[1] for p in trajectory_data.get('moon_position_history', [])])

    # Create figure with subplots
    fig = plt.figure(figsize=(20, 14))
    fig.suptitle('Lunar Intercept Trajectory Analysis', fontsize=16, fontweight='bold')
    
    # 1. Complete Earth-Moon System View
    ax1 = plt.subplot(2, 3, 1)
    plt.plot(x_arr / 1000, y_arr / 1000, 'b-', linewidth=2, label='Spacecraft')
    
    # Add Earth
    earth_circle = plt.Circle((0, 0), 6371, fill=False, color='green', linewidth=3, label='Earth')
    ax1.add_patch(earth_circle)
    
    # Add Moon trajectory if available
    if len(moon_x_arr) > 0:
        plt.plot(moon_x_arr / 1000, moon_y_arr / 1000, 'gray', linewidth=1, alpha=0.7, label='Moon Orbit')
        # Show Moon position at key points
        if len(moon_x_arr) > 1:
            plt.plot(moon_x_arr[0] / 1000, moon_y_arr[0] / 1000, 'yo', markersize=8, label='Moon Start')
            plt.plot(moon_x_arr[-1] / 1000, moon_y_arr[-1] / 1000, 'orange', marker='o', markersize=8, label='Moon End')
    
    # Show Moon's SOI at intercept if spacecraft reaches it
    max_distance = np.sqrt((x_arr[-1])**2 + (y_arr[-1])**2)
    if max_distance > 300000e3:  # If spacecraft travels far enough
        moon_soi_circle = plt.Circle((moon_x_arr[-1] / 1000, moon_y_arr[-1] / 1000), 66100, 
                                   fill=False, color='orange', linewidth=1, linestyle='--', alpha=0.7, label='Moon SOI')
        ax1.add_patch(moon_soi_circle)
    
    plt.xlabel('X Position (km)')
    plt.ylabel('Y Position (km)')
    plt.title('Earth-Moon System View')
    plt.axis('equal')
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    # 2. Zoomed Launch Phase
    ax2 = plt.subplot(2, 3, 2)
    # Show first portion of trajectory (launch and LEO)
    launch_indices = time_arr < 3600  # First hour
    plt.plot(x_arr[launch_indices] / 1000, y_arr[launch_indices] / 1000, 'b-', linewidth=2, label='Launch Phase')
    
    # Add Earth
    earth_circle = plt.Circle((0, 0), 6371, fill=False, color='green', linewidth=3, label='Earth')
    ax2.add_patch(earth_circle)
    
    plt.xlabel('X Position (km)')
    plt.ylabel('Y Position (km)')
    plt.title('Launch Phase (First Hour)')
    plt.axis('equal')
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    # 3. Altitude vs Time
    ax3 = plt.subplot(2, 3, 3)
    plt.plot(time_arr / 3600, alt_arr / 1000, 'b-', linewidth=2, label='Altitude')
    
    plt.xlabel('Time (hours)')
    plt.ylabel('Altitude (km)')
    plt.title('Altitude Profile')
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    # 4. Velocity vs. Time
    ax4 = plt.subplot(2, 3, 4)
    plt.plot(time_arr / 3600, vel_arr / 1000, 'b-', linewidth=2, label='Total Velocity')
    
    plt.xlabel('Time (hours)')
    plt.ylabel('Velocity (km/s)')
    plt.title('Velocity Profile')
    plt.grid(True, alpha=0.3)
    plt.legend()

    # 5. Distance from Earth vs Time
    ax5 = plt.subplot(2, 3, 5)
    distance_arr = np.sqrt(x_arr**2 + y_arr**2)
    plt.plot(time_arr / 3600, distance_arr / 1000, 'b-', linewidth=2, label='Distance from Earth')
    
    # Add Moon distance reference
    plt.axhline(y=384400, color='orange', linestyle='--', alpha=0.7, label='Moon Distance')
    
    plt.xlabel('Time (hours)')
    plt.ylabel('Distance (km)')
    plt.title('Distance from Earth')
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    # 6. Mission Phase Timeline
    ax6 = plt.subplot(2, 3, 6)
    phase_arr = np.array(trajectory_data.get('phase_history', []))
    if len(phase_arr) > 0:
        plt.plot(time_arr / 3600, phase_arr, 'r-', linewidth=2, label='Mission Phase')
        plt.xlabel('Time (hours)')
        plt.ylabel('Phase Number')
        plt.title('Mission Phase Timeline')
        plt.grid(True, alpha=0.3)
        plt.legend()
    else:
        plt.text(0.5, 0.5, 'Phase data not available', ha='center', va='center', transform=ax6.transAxes)
        plt.title('Mission Phase Timeline')
    
    plt.tight_layout()
    
    # Save the plot
    plt.savefig('lunar_intercept_trajectory.png', dpi=300, bbox_inches='tight')
    print("Lunar intercept trajectory plot saved as 'lunar_intercept_trajectory.png'")
    
    return fig

def main():
    """Main trajectory visualization function"""
    print("🚀 Trajectory Visualization")
    
    # Run trajectory analysis
    trajectory_data, stage_events, phase_changes = run_trajectory_analysis()
    
    # Create visualizations
    fig = create_trajectory_plots(trajectory_data, stage_events, phase_changes)
    
    print(f"\n📊 Lunar intercept trajectory visualization complete!")
    print(f"📁 Plot saved as 'lunar_intercept_trajectory.png'")
    
    return trajectory_data, stage_events, phase_changes

if __name__ == "__main__":
    main()