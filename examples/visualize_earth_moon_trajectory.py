#!/usr/bin/env python3
"""
Complete Earth-to-Moon Trajectory Visualization
Professor v45 Implementation - Full Mission Visualization

This script creates comprehensive visualizations of the complete Earth-to-Moon trajectory:
1. Launch phase from Earth surface to LEO
2. Trans-Lunar Injection (TLI)
3. Coast to Moon SOI
4. Lunar Orbit Insertion (LOI)
5. Powered descent to lunar surface
"""

import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.patches as patches
from matplotlib.patches import Circle, FancyBboxPatch
import matplotlib.animation as animation
from datetime import datetime, timedelta
import json

# Physical constants
G = 6.67430e-11
M_EARTH = 5.972e24
M_MOON = 7.34767309e22
R_EARTH = 6371e3
R_MOON = 1737e3
EARTH_MOON_DIST = 384400e3
MOON_SOI_RADIUS = 66100e3
LEO_ALTITUDE = 200e3

# Launch constants
KSC_LATITUDE = 28.573
KSC_LONGITUDE = -80.649


class EarthMoonTrajectoryVisualizer:
    """Complete Earth-to-Moon trajectory visualization"""
    
    def __init__(self):
        """Initialize the visualizer"""
        self.fig = None
        self.trajectory_data = self._generate_trajectory_data()
        
    def _generate_trajectory_data(self):
        """Generate realistic trajectory data for all mission phases"""
        
        # Phase 1: Launch to LEO (0-600 seconds)
        launch_times = np.linspace(0, 600, 600)
        launch_positions = []
        launch_velocities = []
        
        for t in launch_times:
            # Simplified launch trajectory
            if t < 46:  # Vertical ascent
                altitude = 0.5 * 4.0 * t**2  # 4 m/s² acceleration
                r = R_EARTH + altitude
                pos = [r * np.cos(np.radians(KSC_LATITUDE)), 
                       r * np.sin(np.radians(KSC_LATITUDE)), 0]
                vel = [0, 4.0 * t, 0]  # Vertical velocity
            else:  # Gravity turn
                # Simplified gravity turn trajectory
                altitude = 1500 + (t - 46) * 150  # ~150 m/s climb rate
                r = R_EARTH + altitude
                # Gradual eastward turn
                angle_offset = (t - 46) * 0.001  # Gradual turn
                pos = [r * np.cos(np.radians(KSC_LATITUDE) + angle_offset), 
                       r * np.sin(np.radians(KSC_LATITUDE) + angle_offset), 0]
                vel = [100 + (t - 46) * 10, 50 + (t - 46) * 5, 0]  # Building horizontal velocity
            
            launch_positions.append(pos)
            launch_velocities.append(vel)
        
        # Phase 2: TLI burn (LEO to departure)
        tli_time = 600
        leo_position = [R_EARTH + LEO_ALTITUDE, 0, 0]
        leo_velocity = [0, np.sqrt(G * M_EARTH / (R_EARTH + LEO_ALTITUDE)), 0]
        
        # Phase 3: Coast to Moon (3 days)
        coast_times = np.linspace(0, 3 * 24 * 3600, 1000)
        coast_positions = []
        
        for t in coast_times:
            # Simplified transfer orbit (straight line approximation)
            progress = t / (3 * 24 * 3600)
            x = (R_EARTH + LEO_ALTITUDE) + progress * (EARTH_MOON_DIST - R_EARTH - LEO_ALTITUDE)
            y = 0
            z = 0
            coast_positions.append([x, y, z])
        
        # Phase 4: Lunar orbit and descent
        lunar_orbit_radius = R_MOON + 100e3
        descent_positions = []
        
        # Orbital positions around Moon
        orbital_angles = np.linspace(0, 2 * np.pi, 100)
        for angle in orbital_angles:
            x = EARTH_MOON_DIST + lunar_orbit_radius * np.cos(angle)
            y = lunar_orbit_radius * np.sin(angle)
            z = 0
            descent_positions.append([x, y, z])
        
        # Descent trajectory
        descent_altitudes = np.linspace(100e3, 0, 50)
        for alt in descent_altitudes:
            x = EARTH_MOON_DIST
            y = 0
            z = alt
            descent_positions.append([x, y, z])
        
        return {
            'launch': {
                'times': launch_times,
                'positions': np.array(launch_positions),
                'velocities': np.array(launch_velocities)
            },
            'tli': {
                'position': leo_position,
                'velocity': leo_velocity,
                'time': tli_time
            },
            'coast': {
                'times': coast_times,
                'positions': np.array(coast_positions)
            },
            'lunar': {
                'positions': np.array(descent_positions)
            }
        }
    
    def create_complete_trajectory_plot(self):
        """Create the complete Earth-to-Moon trajectory visualization"""
        
        # Create figure with subplots
        fig = plt.figure(figsize=(20, 16))
        fig.suptitle('Complete Earth-to-Moon Trajectory\nProfessor v45 Implementation', 
                    fontsize=16, fontweight='bold')
        
        # 1. Launch phase detail
        ax1 = plt.subplot(2, 3, 1)
        self._plot_launch_phase(ax1)
        
        # 2. LEO insertion and TLI
        ax2 = plt.subplot(2, 3, 2)
        self._plot_leo_and_tli(ax2)
        
        # 3. Complete trajectory overview
        ax3 = plt.subplot(2, 3, 3)
        self._plot_complete_trajectory(ax3)
        
        # 4. Lunar approach and orbit
        ax4 = plt.subplot(2, 3, 4)
        self._plot_lunar_approach(ax4)
        
        # 5. Powered descent
        ax5 = plt.subplot(2, 3, 5)
        self._plot_powered_descent(ax5)
        
        # 6. Mission timeline
        ax6 = plt.subplot(2, 3, 6)
        self._plot_mission_timeline(ax6)
        
        plt.tight_layout()
        return fig
    
    def _plot_launch_phase(self, ax):
        """Plot detailed launch phase from Earth surface to LEO"""
        
        # Earth surface
        earth_circle = Circle((0, 0), R_EARTH/1000, color='lightblue', alpha=0.7)
        ax.add_patch(earth_circle)
        
        # Launch trajectory
        launch_pos = self.trajectory_data['launch']['positions']
        launch_x = launch_pos[:, 0] / 1000  # Convert to km
        launch_y = launch_pos[:, 1] / 1000
        
        # Plot trajectory with color coding by time
        times = self.trajectory_data['launch']['times']
        colors = plt.cm.plasma(times / times[-1])
        
        for i in range(len(launch_x) - 1):
            ax.plot(launch_x[i:i+2], launch_y[i:i+2], 
                   color=colors[i], linewidth=2, alpha=0.8)
        
        # Mark key events
        ax.plot(launch_x[0], launch_y[0], 'ro', markersize=8, label='Launch (LC-39A)')
        ax.plot(launch_x[46], launch_y[46], 'go', markersize=6, label='Gravity Turn Start')
        ax.plot(launch_x[-1], launch_y[-1], 'bo', markersize=8, label='LEO Insertion')
        
        # Add atmosphere boundary
        atmosphere_circle = Circle((0, 0), (R_EARTH + 100e3)/1000, 
                                 fill=False, color='gray', linestyle='--', alpha=0.5)
        ax.add_patch(atmosphere_circle)
        
        ax.set_xlim(-7000, 7500)
        ax.set_ylim(-7000, 7500)
        ax.set_aspect('equal')
        ax.set_title('Launch Phase: Earth Surface to LEO\n(0-600 seconds)')
        ax.legend(loc='upper left', fontsize=8)
        ax.grid(True, alpha=0.3)
        ax.set_xlabel('X (km)')
        ax.set_ylabel('Y (km)')
        
        # Add annotations
        ax.annotate('Vertical Ascent\n(0-46s)', xy=(launch_x[20], launch_y[20]), 
                   xytext=(6000, 3000), fontsize=8,
                   arrowprops=dict(arrowstyle='->', color='red', alpha=0.7))
        ax.annotate('Gravity Turn\n(46-600s)', xy=(launch_x[300], launch_y[300]), 
                   xytext=(2000, 6000), fontsize=8,
                   arrowprops=dict(arrowstyle='->', color='green', alpha=0.7))
    
    def _plot_leo_and_tli(self, ax):
        """Plot LEO parking orbit and TLI burn"""
        
        # Earth
        earth_circle = Circle((0, 0), R_EARTH/1000, color='lightblue', alpha=0.7)
        ax.add_patch(earth_circle)
        
        # LEO orbit
        leo_radius = (R_EARTH + LEO_ALTITUDE) / 1000
        leo_circle = Circle((0, 0), leo_radius, fill=False, color='blue', linewidth=2)
        ax.add_patch(leo_circle)
        
        # TLI departure trajectory
        angles = np.linspace(0, np.pi, 50)
        tli_x = leo_radius * np.cos(angles)
        tli_y = leo_radius * np.sin(angles)
        
        # Hyperbolic departure
        for i in range(len(angles)):
            scale = 1 + i * 0.05  # Expanding spiral
            ax.plot(tli_x[i] * scale, tli_y[i] * scale, 
                   color='red', alpha=0.8, linewidth=2)
        
        # Mark key points
        ax.plot(leo_radius, 0, 'bo', markersize=8, label='LEO Parking Orbit')
        ax.plot(leo_radius * 1.2, 0, 'ro', markersize=8, label='TLI Burn')
        
        # Add labels
        ax.set_xlim(-10000, 15000)
        ax.set_ylim(-8000, 8000)
        ax.set_aspect('equal')
        ax.set_title('LEO Parking Orbit & TLI Burn\n(Trans-Lunar Injection)')
        ax.legend(loc='upper left', fontsize=8)
        ax.grid(True, alpha=0.3)
        ax.set_xlabel('X (km)')
        ax.set_ylabel('Y (km)')
        
        # Add annotations
        ax.annotate('185 km Parking Orbit', xy=(leo_radius, 0), 
                   xytext=(8000, -4000), fontsize=8,
                   arrowprops=dict(arrowstyle='->', color='blue', alpha=0.7))
        ax.annotate('ΔV = 3,150 m/s', xy=(leo_radius * 1.2, 0), 
                   xytext=(12000, 2000), fontsize=8,
                   arrowprops=dict(arrowstyle='->', color='red', alpha=0.7))
    
    def _plot_complete_trajectory(self, ax):
        """Plot the complete Earth-to-Moon trajectory overview"""
        
        # Earth
        earth_circle = Circle((0, 0), R_EARTH/1000, color='lightblue', alpha=0.8, label='Earth')
        ax.add_patch(earth_circle)
        
        # Moon
        moon_x = EARTH_MOON_DIST / 1000
        moon_circle = Circle((moon_x, 0), R_MOON/1000, color='gray', alpha=0.8, label='Moon')
        ax.add_patch(moon_circle)
        
        # Moon SOI
        moon_soi = Circle((moon_x, 0), MOON_SOI_RADIUS/1000, 
                         fill=False, color='gray', linestyle='--', alpha=0.5, label='Moon SOI')
        ax.add_patch(moon_soi)
        
        # LEO
        leo_circle = Circle((0, 0), (R_EARTH + LEO_ALTITUDE)/1000, 
                           fill=False, color='blue', linewidth=2, alpha=0.7)
        ax.add_patch(leo_circle)
        
        # Transfer trajectory
        coast_pos = self.trajectory_data['coast']['positions']
        coast_x = coast_pos[:, 0] / 1000
        coast_y = coast_pos[:, 1] / 1000
        
        # Plot transfer orbit
        ax.plot(coast_x, coast_y, 'r-', linewidth=3, alpha=0.8, label='Transfer Trajectory')
        
        # Mark key points
        ax.plot(0, 0, 'bo', markersize=8, label='Earth')
        ax.plot(moon_x, 0, 'go', markersize=8, label='Moon')
        ax.plot(coast_x[0], coast_y[0], 'ro', markersize=6, label='TLI Departure')
        ax.plot(coast_x[-1], coast_y[-1], 'mo', markersize=6, label='Moon SOI Entry')
        
        # Add distance scale
        ax.plot([0, 50000], [-300000, -300000], 'k-', linewidth=2)
        ax.text(25000, -320000, '50,000 km', ha='center', fontsize=8)
        
        ax.set_xlim(-50000, 450000)
        ax.set_ylim(-350000, 350000)
        ax.set_aspect('equal')
        ax.set_title('Complete Earth-to-Moon Trajectory\n(384,400 km journey)')
        ax.legend(loc='upper left', fontsize=8)
        ax.grid(True, alpha=0.3)
        ax.set_xlabel('X (km)')
        ax.set_ylabel('Y (km)')
        
        # Add mission phases
        ax.text(50000, 200000, 'Phase 1: Launch to LEO\n(0-10 min)', 
               fontsize=9, bbox=dict(boxstyle="round,pad=0.3", facecolor='lightblue'))
        ax.text(150000, 100000, 'Phase 2: TLI Burn\n(ΔV = 3,150 m/s)', 
               fontsize=9, bbox=dict(boxstyle="round,pad=0.3", facecolor='lightcoral'))
        ax.text(250000, 50000, 'Phase 3: Coast to Moon\n(3 days)', 
               fontsize=9, bbox=dict(boxstyle="round,pad=0.3", facecolor='lightyellow'))
        ax.text(350000, -100000, 'Phase 4: LOI & Descent\n(ΔV = 2,550 m/s)', 
               fontsize=9, bbox=dict(boxstyle="round,pad=0.3", facecolor='lightgreen'))
    
    def _plot_lunar_approach(self, ax):
        """Plot lunar approach, orbit insertion, and orbital mechanics"""
        
        # Moon
        moon_circle = Circle((0, 0), R_MOON/1000, color='gray', alpha=0.8)
        ax.add_patch(moon_circle)
        
        # Lunar orbit (100 km)
        orbit_radius = (R_MOON + 100e3) / 1000
        orbit_circle = Circle((0, 0), orbit_radius, fill=False, color='blue', linewidth=2)
        ax.add_patch(orbit_circle)
        
        # Approach trajectory (hyperbolic)
        approach_x = np.linspace(-5000, -orbit_radius, 100)
        approach_y = np.sqrt(np.maximum(0, (approach_x + 2000)**2 - 2000**2)) * 0.3
        
        ax.plot(approach_x, approach_y, 'r-', linewidth=3, alpha=0.8, label='Approach Trajectory')
        ax.plot(approach_x, -approach_y, 'r-', linewidth=3, alpha=0.8)
        
        # LOI burn point
        loi_x, loi_y = -orbit_radius, 0
        ax.plot(loi_x, loi_y, 'ro', markersize=8, label='LOI Burn')
        
        # Orbital motion
        orbital_angles = np.linspace(0, 2*np.pi, 100)
        orbital_x = orbit_radius * np.cos(orbital_angles)
        orbital_y = orbit_radius * np.sin(orbital_angles)
        ax.plot(orbital_x, orbital_y, 'b-', linewidth=2, alpha=0.8, label='100 km Orbit')
        
        # Mark key points
        ax.plot(0, 0, 'go', markersize=10, label='Moon')
        ax.plot(orbit_radius, 0, 'bo', markersize=6, label='Orbital Position')
        
        ax.set_xlim(-6000, 3000)
        ax.set_ylim(-3000, 3000)
        ax.set_aspect('equal')
        ax.set_title('Lunar Approach & Orbit Insertion\n(LOI ΔV = 850 m/s)')
        ax.legend(loc='upper left', fontsize=8)
        ax.grid(True, alpha=0.3)
        ax.set_xlabel('X (km)')
        ax.set_ylabel('Y (km)')
        
        # Add annotations
        ax.annotate('SOI Entry\n(2.5 km/s)', xy=(-4000, 1000), 
                   xytext=(-3000, 2000), fontsize=8,
                   arrowprops=dict(arrowstyle='->', color='red', alpha=0.7))
        ax.annotate('Circular Orbit\n(1.6 km/s)', xy=(orbit_radius, 0), 
                   xytext=(2000, 1500), fontsize=8,
                   arrowprops=dict(arrowstyle='->', color='blue', alpha=0.7))
    
    def _plot_powered_descent(self, ax):
        """Plot powered descent trajectory"""
        
        # Moon surface
        moon_surface = Circle((0, 0), R_MOON/1000, color='gray', alpha=0.8)
        ax.add_patch(moon_surface)
        
        # Descent trajectory phases
        altitudes = np.array([100e3, 15e3, 500, 0]) / 1000  # Convert to km
        descent_x = np.array([0, 0, 0, 0])
        descent_y = R_MOON/1000 + altitudes
        
        # Plot descent phases
        colors = ['blue', 'orange', 'red', 'green']
        labels = ['Deorbit (50 m/s)', 'Braking (1500 m/s)', 'Final Approach', 'Touchdown']
        
        for i in range(len(descent_y)-1):
            ax.plot([descent_x[i], descent_x[i+1]], [descent_y[i], descent_y[i+1]], 
                   color=colors[i], linewidth=4, alpha=0.8, label=labels[i])
            ax.plot(descent_x[i], descent_y[i], 'o', color=colors[i], markersize=8)
        
        # Final touchdown
        ax.plot(descent_x[-1], descent_y[-1], 'o', color=colors[-1], markersize=10, label=labels[-1])
        
        # Add altitude markers
        for i, alt in enumerate(altitudes):
            if alt > 0:
                ax.text(200, R_MOON/1000 + alt, f'{alt:.0f} km', 
                       fontsize=8, ha='left', va='center')
        
        # Add velocity annotations
        velocities = ['0 m/s', '50 m/s', '~100 m/s', '≤2 m/s']
        for i, vel in enumerate(velocities):
            ax.text(-500, descent_y[i], vel, fontsize=8, ha='right', va='center',
                   bbox=dict(boxstyle="round,pad=0.2", facecolor='lightgray', alpha=0.7))
        
        ax.set_xlim(-1000, 1000)
        ax.set_ylim(1600, 2000)
        ax.set_aspect('equal')
        ax.set_title('Powered Descent to Lunar Surface\n(Total ΔV = 1,700 m/s)')
        ax.legend(loc='upper left', fontsize=8)
        ax.grid(True, alpha=0.3)
        ax.set_xlabel('X (km)')
        ax.set_ylabel('Y (km)')
        
        # Add success criteria
        ax.text(600, 1650, 'Success Criteria:\n• Velocity ≤ 2 m/s\n• Tilt ≤ 5°\n• Soft Landing', 
               fontsize=8, bbox=dict(boxstyle="round,pad=0.3", facecolor='lightgreen', alpha=0.7))
    
    def _plot_mission_timeline(self, ax):
        """Plot mission timeline and ΔV budget"""
        
        # Mission phases
        phases = ['Launch', 'TLI', 'Coast', 'LOI', 'Descent']
        delta_v_values = [9300, 3150, 0, 850, 1700]  # m/s
        durations = [10, 0.5, 4320, 1, 11]  # minutes
        colors = ['blue', 'red', 'yellow', 'green', 'purple']
        
        # Create timeline
        ax.barh(phases, delta_v_values, color=colors, alpha=0.7)
        
        # Add values on bars
        for i, (phase, dv) in enumerate(zip(phases, delta_v_values)):
            if dv > 0:
                ax.text(dv/2, i, f'{dv} m/s', ha='center', va='center', 
                       fontweight='bold', color='white')
        
        # Add total budget line
        total_budget = 15000
        ax.axvline(x=total_budget, color='red', linestyle='--', linewidth=2, 
                  label=f'Total Budget: {total_budget} m/s')
        
        # Add actual total
        actual_total = sum(delta_v_values)
        ax.axvline(x=actual_total, color='green', linestyle='-', linewidth=2, 
                  label=f'Actual Total: {actual_total} m/s')
        
        ax.set_xlabel('ΔV (m/s)')
        ax.set_title('Mission ΔV Budget & Timeline\n(Professor v45 Specifications)')
        ax.legend(loc='lower right', fontsize=8)
        ax.grid(True, alpha=0.3)
        
        # Add duration annotations
        for i, (phase, duration) in enumerate(zip(phases, durations)):
            if duration > 0:
                if duration >= 60:
                    duration_str = f'{duration/60:.1f} hours'
                else:
                    duration_str = f'{duration:.1f} min'
                ax.text(max(delta_v_values) * 0.7, i + 0.3, duration_str, 
                       fontsize=8, style='italic', color='gray')
        
        # Add success indicator
        success_text = "✅ Within Budget" if actual_total <= total_budget else "❌ Over Budget"
        ax.text(max(delta_v_values) * 0.5, len(phases) - 0.5, success_text, 
               fontsize=12, fontweight='bold', 
               bbox=dict(boxstyle="round,pad=0.3", facecolor='lightgreen', alpha=0.8))
    
    def create_3d_trajectory_plot(self):
        """Create 3D visualization of the complete trajectory"""
        
        fig = plt.figure(figsize=(15, 10))
        ax = fig.add_subplot(111, projection='3d')
        
        # Earth
        u = np.linspace(0, 2 * np.pi, 50)
        v = np.linspace(0, np.pi, 50)
        x_earth = R_EARTH/1000 * np.outer(np.cos(u), np.sin(v))
        y_earth = R_EARTH/1000 * np.outer(np.sin(u), np.sin(v))
        z_earth = R_EARTH/1000 * np.outer(np.ones(np.size(u)), np.cos(v))
        ax.plot_surface(x_earth, y_earth, z_earth, alpha=0.6, color='lightblue')
        
        # Moon
        moon_x = EARTH_MOON_DIST / 1000
        x_moon = R_MOON/1000 * np.outer(np.cos(u), np.sin(v)) + moon_x
        y_moon = R_MOON/1000 * np.outer(np.sin(u), np.sin(v))
        z_moon = R_MOON/1000 * np.outer(np.ones(np.size(u)), np.cos(v))
        ax.plot_surface(x_moon, y_moon, z_moon, alpha=0.6, color='gray')
        
        # Transfer trajectory
        coast_pos = self.trajectory_data['coast']['positions']
        ax.plot(coast_pos[:, 0]/1000, coast_pos[:, 1]/1000, coast_pos[:, 2]/1000, 
               'r-', linewidth=3, alpha=0.8, label='Transfer Trajectory')
        
        # Launch trajectory
        launch_pos = self.trajectory_data['launch']['positions']
        ax.plot(launch_pos[:, 0]/1000, launch_pos[:, 1]/1000, launch_pos[:, 2]/1000, 
               'b-', linewidth=2, alpha=0.8, label='Launch Trajectory')
        
        # Lunar orbit
        lunar_pos = self.trajectory_data['lunar']['positions']
        ax.plot(lunar_pos[:, 0]/1000, lunar_pos[:, 1]/1000, lunar_pos[:, 2]/1000, 
               'g-', linewidth=2, alpha=0.8, label='Lunar Orbit & Descent')
        
        ax.set_xlabel('X (km)')
        ax.set_ylabel('Y (km)')
        ax.set_zlabel('Z (km)')
        ax.set_title('3D Earth-to-Moon Trajectory\nComplete Mission Overview')
        ax.legend()
        
        return fig
    
    def save_all_plots(self):
        """Generate and save all trajectory visualizations"""
        
        print("🚀 Generating Earth-to-Moon Trajectory Visualizations...")
        
        # Main trajectory plot
        fig1 = self.create_complete_trajectory_plot()
        fig1.savefig('earth_moon_trajectory_complete.png', dpi=300, bbox_inches='tight')
        print("✅ Saved: earth_moon_trajectory_complete.png")
        
        # 3D trajectory plot
        fig2 = self.create_3d_trajectory_plot()
        fig2.savefig('earth_moon_trajectory_3d.png', dpi=300, bbox_inches='tight')
        print("✅ Saved: earth_moon_trajectory_3d.png")
        
        # Show plots
        plt.show()
        
        return fig1, fig2


def main():
    """Main execution function"""
    
    print("🌍🚀🌙 Earth-to-Moon Trajectory Visualization")
    print("=" * 50)
    print("Professor v45 Implementation")
    print("Complete Mission Visualization")
    print()
    
    # Create visualizer
    visualizer = EarthMoonTrajectoryVisualizer()
    
    # Generate and save all plots
    fig1, fig2 = visualizer.save_all_plots()
    
    print()
    print("✅ Visualization Complete!")
    print("📊 Generated comprehensive Earth-to-Moon trajectory plots")
    print("📁 Files saved in current directory")
    print()
    print("Mission Phases Visualized:")
    print("• Launch: Earth surface to 200 km LEO")
    print("• TLI: Trans-Lunar Injection burn (3,150 m/s ΔV)")
    print("• Coast: 3-day journey to Moon (384,400 km)")
    print("• LOI: Lunar Orbit Insertion (850 m/s ΔV)")
    print("• Descent: Powered descent to surface (1,700 m/s ΔV)")
    print("• Total: 15,000 m/s ΔV budget (within specification)")


if __name__ == "__main__":
    main()