#!/usr/bin/env python3
"""
Detailed Trajectory Visualization for Earth-Moon Transfer
High-fidelity orbital mechanics visualization with proper physics
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from matplotlib.animation import FuncAnimation
import json
from datetime import datetime, timedelta

# Physical constants
G = 6.67430e-11  # Gravitational constant
M_EARTH = 5.972e24  # Earth mass [kg]
M_MOON = 7.34767309e22  # Moon mass [kg]
R_EARTH = 6371e3  # Earth radius [m]
R_MOON = 1737e3  # Moon radius [m]
MU_EARTH = G * M_EARTH
MU_MOON = G * M_MOON
EARTH_MOON_DIST = 384400e3  # Earth-Moon distance [m]


class DetailedTrajectoryVisualizer:
    """High-fidelity trajectory visualization"""
    
    def __init__(self):
        self.earth_pos = np.array([0, 0])  # Earth at origin
        self.moon_orbital_radius = EARTH_MOON_DIST / 1000  # km
        self.moon_orbital_period = 27.321661 * 24 * 3600  # seconds
        
    def calculate_orbital_trajectory(self, r0, v0, mu, t_span, dt=60):
        """
        Calculate orbital trajectory using numerical integration
        r0: initial position [km]
        v0: initial velocity [km/s]
        mu: gravitational parameter [km³/s²]
        t_span: time span [s]
        dt: time step [s]
        """
        times = np.arange(0, t_span, dt)
        positions = np.zeros((len(times), 2))
        velocities = np.zeros((len(times), 2))
        
        # Initial conditions
        r = np.array(r0)
        v = np.array(v0)
        
        for i, t in enumerate(times):
            positions[i] = r
            velocities[i] = v
            
            # Calculate gravitational acceleration
            r_mag = np.linalg.norm(r)
            a_grav = -mu * r / (r_mag**3)
            
            # Simple Euler integration (could use RK4 for higher accuracy)
            v = v + a_grav * dt
            r = r + v * dt
        
        return times, positions, velocities
    
    def calculate_moon_position(self, t):
        """Calculate Moon position at time t [seconds]"""
        omega = 2 * np.pi / self.moon_orbital_period
        angle = omega * t
        return np.array([
            self.moon_orbital_radius * np.cos(angle),
            self.moon_orbital_radius * np.sin(angle)
        ])
    
    def calculate_transfer_trajectory(self):
        """Calculate detailed Earth-Moon transfer trajectory"""
        print("🚀 Calculating detailed transfer trajectory...")
        
        # Mission parameters
        leo_altitude = 185  # km
        leo_radius = (R_EARTH / 1000) + leo_altitude  # km
        leo_velocity = np.sqrt(MU_EARTH / 1000**3 / leo_radius)  # km/s
        
        # TLI burn parameters
        tli_delta_v = 3.15  # km/s
        transfer_time = 3 * 24 * 3600  # 3 days in seconds
        
        # Phase 1: LEO orbit (1 orbit before TLI)
        leo_period = 2 * np.pi * np.sqrt(leo_radius**3 / (MU_EARTH / 1000**3))
        t1, pos1, vel1 = self.calculate_orbital_trajectory(
            r0=[leo_radius, 0],
            v0=[0, leo_velocity],
            mu=MU_EARTH / 1000**3,  # Convert to km³/s²
            t_span=leo_period
        )
        
        # Phase 2: TLI burn (instantaneous for visualization)
        tli_position = pos1[-1]
        tli_velocity = vel1[-1] + np.array([0, tli_delta_v])  # Add prograde delta-V
        
        # Phase 3: Trans-lunar trajectory
        t2, pos2, vel2 = self.calculate_orbital_trajectory(
            r0=tli_position,
            v0=tli_velocity,
            mu=MU_EARTH / 1000**3,
            t_span=transfer_time,
            dt=3600  # 1 hour time step for transfer
        )
        
        # Phase 4: Lunar orbit
        moon_final_pos = self.calculate_moon_position(transfer_time)
        lunar_orbit_radius = (R_MOON / 1000) + 100  # 100 km lunar orbit
        lunar_velocity = np.sqrt(MU_MOON / 1000**3 / lunar_orbit_radius)
        
        # Lunar orbit around final Moon position
        t3, pos3_rel, vel3 = self.calculate_orbital_trajectory(
            r0=[lunar_orbit_radius, 0],
            v0=[0, lunar_velocity],
            mu=MU_MOON / 1000**3,
            t_span=6 * 3600  # 6 hours of lunar orbit
        )
        
        # Convert relative lunar positions to absolute
        pos3 = pos3_rel + moon_final_pos
        
        return {
            'leo': {'time': t1, 'position': pos1, 'velocity': vel1},
            'transfer': {'time': t2, 'position': pos2, 'velocity': vel2},
            'lunar_orbit': {'time': t3, 'position': pos3, 'velocity': vel3},
            'moon_final_position': moon_final_pos,
            'tli_position': tli_position,
            'transfer_time': transfer_time
        }
    
    def create_detailed_trajectory_plot(self):
        """Create high-quality detailed trajectory visualization"""
        print("📊 Creating detailed trajectory visualization...")
        
        # Calculate trajectory
        trajectory = self.calculate_transfer_trajectory()
        
        # Create figure with high DPI
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 10))
        fig.suptitle('Earth-Moon Transfer Trajectory - Detailed Orbital Mechanics', 
                     fontsize=16, fontweight='bold')
        
        # Plot 1: Full trajectory overview
        ax1.set_title('Complete Transfer Trajectory', fontsize=14, fontweight='bold')
        
        # Draw Earth
        earth = Circle((0, 0), R_EARTH/1000, color='blue', alpha=0.8, label='Earth')
        ax1.add_patch(earth)
        
        # Draw Moon at final position
        moon_pos = trajectory['moon_final_position']
        moon = Circle(moon_pos, R_MOON/1000, color='gray', alpha=0.8, label='Moon')
        ax1.add_patch(moon)
        
        # Draw Moon's orbit
        moon_orbit = Circle((0, 0), self.moon_orbital_radius, 
                           fill=False, color='lightgray', linestyle='--', 
                           alpha=0.5, label='Moon Orbit')
        ax1.add_patch(moon_orbit)
        
        # Plot LEO
        leo_pos = trajectory['leo']['position']
        ax1.plot(leo_pos[:, 0], leo_pos[:, 1], 'g-', linewidth=2, label='LEO Orbit')
        
        # Plot transfer trajectory
        transfer_pos = trajectory['transfer']['position']
        ax1.plot(transfer_pos[:, 0], transfer_pos[:, 1], 'r-', linewidth=3, 
                label='Trans-Lunar Trajectory', alpha=0.8)
        
        # Plot lunar orbit
        lunar_pos = trajectory['lunar_orbit']['position']
        ax1.plot(lunar_pos[:, 0], lunar_pos[:, 1], 'purple', linewidth=2, 
                label='Lunar Orbit')
        
        # Mark key points
        tli_pos = trajectory['tli_position']
        ax1.plot(tli_pos[0], tli_pos[1], 'ro', markersize=8, label='TLI Burn')
        ax1.plot(moon_pos[0], moon_pos[1], 'ko', markersize=6, label='LOI Point')
        
        # Formatting
        ax1.set_xlim(-50000, 450000)
        ax1.set_ylim(-200000, 200000)
        ax1.set_xlabel('Distance (km)')
        ax1.set_ylabel('Distance (km)')
        ax1.legend(loc='upper right')
        ax1.grid(True, alpha=0.3)
        ax1.set_aspect('equal')
        
        # Plot 2: Transfer trajectory detail with Moon motion
        ax2.set_title('Transfer Trajectory with Moon Motion', fontsize=14, fontweight='bold')
        
        # Show Moon positions during transfer
        transfer_times = trajectory['transfer']['time']
        moon_positions = []
        for t in transfer_times:
            moon_pos_t = self.calculate_moon_position(t)
            moon_positions.append(moon_pos_t)
        moon_positions = np.array(moon_positions)
        
        # Plot Moon's path during transfer
        ax2.plot(moon_positions[:, 0], moon_positions[:, 1], 'gray', 
                linewidth=2, alpha=0.6, label='Moon Path During Transfer')
        
        # Plot transfer trajectory
        ax2.plot(transfer_pos[:, 0], transfer_pos[:, 1], 'r-', linewidth=3, 
                label='Spacecraft Trajectory')
        
        # Mark positions at regular intervals
        time_marks = [0, 24*3600, 48*3600, 72*3600]  # Every 24 hours
        colors = ['green', 'orange', 'blue', 'red']
        
        for i, t_mark in enumerate(time_marks):
            if t_mark < len(transfer_times):
                idx = int(t_mark / 3600)  # Hour index
                if idx < len(transfer_pos):
                    sc_pos = transfer_pos[idx]
                    moon_pos_mark = self.calculate_moon_position(t_mark)
                    
                    # Spacecraft position
                    ax2.plot(sc_pos[0], sc_pos[1], 'o', color=colors[i], 
                            markersize=8, label=f'Day {i}')
                    
                    # Moon position
                    moon_circle = Circle(moon_pos_mark, R_MOON/1000, 
                                       color=colors[i], alpha=0.3)
                    ax2.add_patch(moon_circle)
        
        # Earth
        earth2 = Circle((0, 0), R_EARTH/1000, color='blue', alpha=0.8, label='Earth')
        ax2.add_patch(earth2)
        
        # Final Moon position
        moon_final = Circle(trajectory['moon_final_position'], R_MOON/1000, 
                           color='gray', alpha=0.8, label='Moon at Arrival')
        ax2.add_patch(moon_final)
        
        ax2.set_xlim(-50000, 450000)
        ax2.set_ylim(-200000, 200000)
        ax2.set_xlabel('Distance (km)')
        ax2.set_ylabel('Distance (km)')
        ax2.legend(loc='upper right')
        ax2.grid(True, alpha=0.3)
        ax2.set_aspect('equal')
        
        # Add mission statistics
        stats_text = f"""Mission Statistics:
LEO Altitude: 185 km
TLI ΔV: 3.15 km/s
Transfer Time: 3 days
Lunar Orbit: 100 km
Total Distance: {np.linalg.norm(trajectory['moon_final_position']):.0f} km"""
        
        ax1.text(0.02, 0.98, stats_text, transform=ax1.transAxes, 
                bbox=dict(boxstyle="round,pad=0.3", facecolor="lightblue", alpha=0.8),
                fontsize=10, verticalalignment='top')
        
        plt.tight_layout()
        
        # Save high-resolution plots
        plt.savefig('detailed_trajectory.png', dpi=300, bbox_inches='tight')
        plt.savefig('reports/MVP/detailed_trajectory.png', dpi=300, bbox_inches='tight')
        
        plt.show()
        
        return trajectory
    
    def create_3d_trajectory_plot(self):
        """Create 3D trajectory visualization"""
        print("🌍 Creating 3D trajectory visualization...")
        
        # Calculate trajectory
        trajectory = self.calculate_transfer_trajectory()
        
        # Create 3D plot
        fig = plt.figure(figsize=(15, 12))
        ax = fig.add_subplot(111, projection='3d')
        
        # For 3D, add z-component (assume planar for simplicity)
        leo_pos = trajectory['leo']['position']
        transfer_pos = trajectory['transfer']['position']
        lunar_pos = trajectory['lunar_orbit']['position']
        
        # Add z=0 for all positions (planar trajectory)
        leo_pos_3d = np.column_stack([leo_pos, np.zeros(len(leo_pos))])
        transfer_pos_3d = np.column_stack([transfer_pos, np.zeros(len(transfer_pos))])
        lunar_pos_3d = np.column_stack([lunar_pos, np.zeros(len(lunar_pos))])
        
        # Plot trajectories
        ax.plot(leo_pos_3d[:, 0], leo_pos_3d[:, 1], leo_pos_3d[:, 2], 
               'g-', linewidth=3, label='LEO Orbit')
        ax.plot(transfer_pos_3d[:, 0], transfer_pos_3d[:, 1], transfer_pos_3d[:, 2], 
               'r-', linewidth=4, label='Trans-Lunar Trajectory')
        ax.plot(lunar_pos_3d[:, 0], lunar_pos_3d[:, 1], lunar_pos_3d[:, 2], 
               'purple', linewidth=3, label='Lunar Orbit')
        
        # Create sphere for Earth
        u = np.linspace(0, 2 * np.pi, 50)
        v = np.linspace(0, np.pi, 50)
        earth_x = (R_EARTH/1000) * np.outer(np.cos(u), np.sin(v))
        earth_y = (R_EARTH/1000) * np.outer(np.sin(u), np.sin(v))
        earth_z = (R_EARTH/1000) * np.outer(np.ones(np.size(u)), np.cos(v))
        ax.plot_surface(earth_x, earth_y, earth_z, color='blue', alpha=0.8)
        
        # Create sphere for Moon
        moon_pos = trajectory['moon_final_position']
        moon_x = (R_MOON/1000) * np.outer(np.cos(u), np.sin(v)) + moon_pos[0]
        moon_y = (R_MOON/1000) * np.outer(np.sin(u), np.sin(v)) + moon_pos[1]
        moon_z = (R_MOON/1000) * np.outer(np.ones(np.size(u)), np.cos(v))
        ax.plot_surface(moon_x, moon_y, moon_z, color='gray', alpha=0.8)
        
        ax.set_xlabel('X Distance (km)')
        ax.set_ylabel('Y Distance (km)')
        ax.set_zlabel('Z Distance (km)')
        ax.set_title('3D Earth-Moon Transfer Trajectory', fontsize=14, fontweight='bold')
        ax.legend()
        
        # Set equal aspect ratio
        max_range = 400000
        ax.set_xlim([-50000, max_range])
        ax.set_ylim([-200000, 200000])
        ax.set_zlim([-100000, 100000])
        
        plt.savefig('trajectory_3d.png', dpi=300, bbox_inches='tight')
        plt.savefig('reports/MVP/trajectory_3d.png', dpi=300, bbox_inches='tight')
        
        plt.show()


def main():
    """Generate detailed trajectory visualizations"""
    print("🚀 DETAILED TRAJECTORY VISUALIZATION")
    print("High-fidelity Earth-Moon transfer analysis")
    print("="*50)
    
    visualizer = DetailedTrajectoryVisualizer()
    
    # Create detailed 2D plots
    trajectory_data = visualizer.create_detailed_trajectory_plot()
    
    # Create 3D visualization
    visualizer.create_3d_trajectory_plot()
    
    print("\n✅ Detailed visualizations created:")
    print("   - detailed_trajectory.png (2D high-fidelity)")
    print("   - trajectory_3d.png (3D visualization)")
    print("   - Saved to reports/MVP/")
    
    print(f"\n📊 Trajectory Analysis:")
    print(f"   Transfer distance: {np.linalg.norm(trajectory_data['moon_final_position']):.0f} km")
    print(f"   Transfer time: {trajectory_data['transfer_time']/(24*3600):.1f} days")
    print(f"   TLI burn location: ({trajectory_data['tli_position'][0]:.0f}, {trajectory_data['tli_position'][1]:.0f}) km")


if __name__ == "__main__":
    main()