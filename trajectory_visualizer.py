"""
Rocket Trajectory Visualizer
Shows the progress of Professor v15 improvements
"""

import numpy as np
import matplotlib.pyplot as plt
import rocket_simulation_main
from rocket_simulation_main import Mission, create_saturn_v_rocket
import time

def run_trajectory_analysis():
    """Run simulation and collect trajectory data"""
    print("Running trajectory analysis...")
    
    sim = Mission(create_saturn_v_rocket("saturn_v_config.json"), {"simulation": {"duration": 2400}})
    sim.config["simulation"]["duration"] = 2400  # 40 minutes
    
    results = sim.simulate()
    
    return results, [], []

def create_trajectory_plots(trajectory_data, stage_events, phase_changes):
    """Create comprehensive trajectory visualization"""
    
    # Convert to numpy arrays for easier handling
    time_arr = np.array(trajectory_data['time_history'])
    alt_arr = np.array(trajectory_data['altitude_history'])
    vel_arr = np.array([np.sqrt(v[0]**2 + v[1]**2) for v in trajectory_data['velocity_history']])
    x_arr = np.array([p[0] for p in trajectory_data['position_history']])
    y_arr = np.array([p[1] for p in trajectory_data['position_history']])

    # Create figure with subplots
    fig = plt.figure(figsize=(16, 12))
    fig.suptitle('Rocket Trajectory Analysis', fontsize=16, fontweight='bold')
    
    # 1. Ground Track (X-Y trajectory)
    ax1 = plt.subplot(2, 2, 1)
    plt.plot(x_arr / 1000, y_arr / 1000, 'b-', linewidth=2, label='Trajectory')
    
    # Add Earth
    earth_circle = plt.Circle((0, 0), 6371, fill=False, color='green', linewidth=2, label='Earth')
    ax1.add_patch(earth_circle)
    
    plt.xlabel('X Position (km)')
    plt.ylabel('Y Position (km)')
    plt.title('Ground Track View')
    plt.axis('equal')
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    # 2. Altitude vs Time
    ax2 = plt.subplot(2, 2, 2)
    plt.plot(time_arr, alt_arr / 1000, 'b-', linewidth=2, label='Altitude')
    
    plt.xlabel('Time (s)')
    plt.ylabel('Altitude (km)')
    plt.title('Altitude Profile')
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    # 3. Velocity vs. Time
    ax3 = plt.subplot(2, 2, 3)
    plt.plot(time_arr, vel_arr, 'b-', linewidth=2, label='Total Velocity')
    
    plt.xlabel('Time (s)')
    plt.ylabel('Velocity (m/s)')
    plt.title('Velocity Profile')
    plt.grid(True, alpha=0.3)
    plt.legend()

    # 4. Altitude vs Velocity (Trajectory Shape)
    ax4 = plt.subplot(2, 2, 4)
    plt.plot(vel_arr, alt_arr / 1000, 'b-', linewidth=2, label='Trajectory')
    plt.xlabel('Velocity (m/s)')
    plt.ylabel('Altitude (km)')
    plt.title('Altitude vs. Velocity')
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    plt.tight_layout()
    
    # Save the plot
    plt.savefig('rocket_trajectory.png', dpi=300, bbox_inches='tight')
    print("Trajectory plot saved as 'rocket_trajectory.png'")
    
    return fig

def main():
    """Main trajectory visualization function"""
    print("🚀 Trajectory Visualization")
    
    # Run trajectory analysis
    trajectory_data, stage_events, phase_changes = run_trajectory_analysis()
    
    # Create visualizations
    fig = create_trajectory_plots(trajectory_data, stage_events, phase_changes)
    
    print(f"\n📊 Trajectory visualization complete!")
    print(f"📁 Plot saved as 'rocket_trajectory.png'")
    
    return trajectory_data, stage_events, phase_changes

if __name__ == "__main__":
    main()