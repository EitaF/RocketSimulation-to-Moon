#!/usr/bin/env python3
"""
Corrected Trajectory Visualization for Earth-Moon Transfer
Uses proper Lambert's problem solution to ensure spacecraft actually reaches the Moon
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from scipy.optimize import fsolve
import json

# Physical constants
G = 6.67430e-11  # Gravitational constant
M_EARTH = 5.972e24  # Earth mass [kg]
M_MOON = 7.34767309e22  # Moon mass [kg]
R_EARTH = 6371e3  # Earth radius [m]
R_MOON = 1737e3  # Moon radius [m]
MU_EARTH = G * M_EARTH
MU_MOON = G * M_MOON
EARTH_MOON_DIST = 384400e3  # Earth-Moon distance [m]


class CorrectTrajectoryVisualizer:
    """Correct trajectory visualization using Lambert's problem"""
    
    def __init__(self):
        self.earth_pos = np.array([0, 0])  # Earth at origin
        self.moon_orbital_radius = EARTH_MOON_DIST / 1000  # km
        self.moon_angular_velocity = 2 * np.pi / (27.321661 * 24 * 3600)  # rad/s
        
    def solve_lambert_problem(self, r1, r2, tof, mu):
        """
        Solve Lambert's problem to find velocity vectors for transfer
        r1: initial position vector [km]
        r2: final position vector [km] 
        tof: time of flight [s]
        mu: gravitational parameter [km³/s²]
        """
        r1 = np.array(r1)
        r2 = np.array(r2)
        
        r1_mag = np.linalg.norm(r1)
        r2_mag = np.linalg.norm(r2)
        
        # Calculate transfer angle
        cos_dnu = np.dot(r1, r2) / (r1_mag * r2_mag)
        cos_dnu = np.clip(cos_dnu, -1.0, 1.0)
        
        # Determine transfer direction (assume prograde)
        cross_product = np.cross(r1, r2)
        if cross_product >= 0:
            dnu = np.arccos(cos_dnu)
        else:
            dnu = 2 * np.pi - np.arccos(cos_dnu)
        
        # Calculate chord and semi-perimeter
        c = np.linalg.norm(r2 - r1)
        s = (r1_mag + r2_mag + c) / 2
        
        # Use universal variable method
        def universal_kepler(x):
            """Universal Kepler equation to solve for x"""
            z = x**2
            
            if z > 0:
                C = (1 - np.cos(np.sqrt(z))) / z
                S = (np.sqrt(z) - np.sin(np.sqrt(z))) / np.sqrt(z**3)
            elif z < 0:
                sqrt_minus_z = np.sqrt(-z)
                C = (1 - np.cosh(sqrt_minus_z)) / z
                S = (np.sinh(sqrt_minus_z) - sqrt_minus_z) / np.sqrt((-z)**3)
            else:
                C = 1/2
                S = 1/6
            
            y = r1_mag + r2_mag + (x * (s - c)) / np.sqrt(C)
            if y <= 0:
                return float('inf')
            
            t_calc = (x**3 * S + x * np.sqrt(y)) / np.sqrt(mu)
            return t_calc - tof
        
        # Solve for universal variable x
        try:
            x_solution = fsolve(universal_kepler, 0.0)[0]
            
            # Calculate final values
            z = x_solution**2
            if z > 0:
                C = (1 - np.cos(np.sqrt(z))) / z
                S = (np.sqrt(z) - np.sin(np.sqrt(z))) / np.sqrt(z**3)
            elif z < 0:
                sqrt_minus_z = np.sqrt(-z)
                C = (1 - np.cosh(sqrt_minus_z)) / z
                S = (np.sinh(sqrt_minus_z) - sqrt_minus_z) / np.sqrt((-z)**3)
            else:
                C = 1/2
                S = 1/6
            
            y = r1_mag + r2_mag + (x_solution * (s - c)) / np.sqrt(C)
            
            # Lagrange coefficients
            f = 1 - y / r1_mag
            g = (r1_mag * r2_mag * np.sin(dnu)) / np.sqrt(mu * y)
            gdot = 1 - y / r2_mag
            
            # Calculate velocity vectors
            v1 = (r2 - f * r1) / g
            v2 = (gdot * r2 - r1) / g
            
            return v1, v2, True
            
        except:
            return np.zeros(2), np.zeros(2), False
    
    def propagate_orbit(self, r0, v0, mu, t_span, dt=60):
        """
        Propagate orbit using Runge-Kutta 4th order integration
        """
        times = np.arange(0, t_span, dt)
        positions = np.zeros((len(times), 2))
        velocities = np.zeros((len(times), 2))
        
        r = np.array(r0, dtype=float)
        v = np.array(v0, dtype=float)
        
        for i, t in enumerate(times):
            positions[i] = r
            velocities[i] = v
            
            # RK4 integration
            def derivatives(pos, vel):
                r_mag = np.linalg.norm(pos)
                acc = -mu * pos / (r_mag**3)
                return vel, acc
            
            # RK4 steps
            k1_r, k1_v = derivatives(r, v)
            k2_r, k2_v = derivatives(r + k1_r * dt/2, v + k1_v * dt/2)
            k3_r, k3_v = derivatives(r + k2_r * dt/2, v + k2_v * dt/2)
            k4_r, k4_v = derivatives(r + k3_r * dt, v + k3_v * dt)
            
            r = r + (k1_r + 2*k2_r + 2*k3_r + k4_r) * dt/6
            v = v + (k1_v + 2*k2_v + 2*k3_v + k4_v) * dt/6
        
        return times, positions, velocities
    
    def calculate_moon_position(self, t):
        """Calculate Moon position at time t [seconds]"""
        angle = self.moon_angular_velocity * t
        return np.array([
            self.moon_orbital_radius * np.cos(angle),
            self.moon_orbital_radius * np.sin(angle)
        ])
    
    def calculate_correct_transfer_trajectory(self):
        """Calculate Earth-Moon transfer that actually reaches the Moon"""
        print("🚀 Calculating CORRECT Earth-Moon transfer trajectory...")
        
        # Mission parameters
        leo_altitude = 185  # km
        leo_radius = (R_EARTH / 1000) + leo_altitude  # km
        transfer_time = 3 * 24 * 3600  # 3 days in seconds
        
        # Initial position in LEO
        r1 = np.array([leo_radius, 0])  # km
        
        # Moon position at arrival (3 days from now)
        moon_arrival_pos = self.calculate_moon_position(transfer_time)
        r2 = moon_arrival_pos  # km
        
        print(f"🌍 LEO position: ({r1[0]:.1f}, {r1[1]:.1f}) km")
        print(f"🌙 Moon arrival position: ({r2[0]:.1f}, {r2[1]:.1f}) km")
        print(f"📏 Transfer distance: {np.linalg.norm(r2 - r1):.1f} km")
        
        # Solve Lambert's problem for the transfer
        v1, v2, success = self.solve_lambert_problem(
            r1, r2, transfer_time, MU_EARTH / 1000**3
        )
        
        if not success:
            print("❌ Lambert solution failed!")
            return None
        
        # Calculate required delta-V
        leo_velocity = np.sqrt(MU_EARTH / 1000**3 / leo_radius)  # Circular velocity
        circular_v = np.array([0, leo_velocity])
        delta_v = np.linalg.norm(v1 - circular_v)
        
        print(f"🔥 Required TLI ΔV: {delta_v:.3f} km/s")
        print(f"🎯 Transfer velocity: ({v1[0]:.3f}, {v1[1]:.3f}) km/s")
        
        # Phase 1: LEO orbit (1 orbit before TLI)
        leo_period = 2 * np.pi * np.sqrt(leo_radius**3 / (MU_EARTH / 1000**3))
        t_leo, pos_leo, vel_leo = self.propagate_orbit(
            r0=r1,
            v0=circular_v,
            mu=MU_EARTH / 1000**3,
            t_span=leo_period,
            dt=60
        )
        
        # Phase 2: Transfer trajectory with Lambert solution
        t_transfer, pos_transfer, vel_transfer = self.propagate_orbit(
            r0=r1,
            v0=v1,  # Use Lambert solution velocity
            mu=MU_EARTH / 1000**3,
            t_span=transfer_time,
            dt=3600  # 1 hour steps
        )
        
        # Verify we reach the Moon
        final_pos = pos_transfer[-1]
        moon_final_pos = self.calculate_moon_position(transfer_time)
        arrival_error = np.linalg.norm(final_pos - moon_final_pos)
        
        print(f"🎯 Final spacecraft position: ({final_pos[0]:.1f}, {final_pos[1]:.1f}) km")
        print(f"🌙 Moon position at arrival: ({moon_final_pos[0]:.1f}, {moon_final_pos[1]:.1f}) km")
        print(f"📐 Arrival accuracy: {arrival_error:.1f} km")
        
        # Phase 3: Lunar orbit
        lunar_orbit_radius = (R_MOON / 1000) + 100  # 100 km altitude
        lunar_velocity = np.sqrt(MU_MOON / 1000**3 / lunar_orbit_radius)
        
        t_lunar, pos_lunar_rel, vel_lunar = self.propagate_orbit(
            r0=[lunar_orbit_radius, 0],
            v0=[0, lunar_velocity],
            mu=MU_MOON / 1000**3,
            t_span=6 * 3600,  # 6 hours
            dt=300
        )
        
        # Convert to absolute coordinates
        pos_lunar = pos_lunar_rel + moon_final_pos
        
        return {
            'leo': {'time': t_leo, 'position': pos_leo},
            'transfer': {'time': t_transfer, 'position': pos_transfer},
            'lunar_orbit': {'time': t_lunar, 'position': pos_lunar},
            'moon_positions': self.get_moon_trajectory(transfer_time),
            'lambert_solution': {'v1': v1, 'v2': v2, 'delta_v': delta_v},
            'arrival_error': arrival_error,
            'moon_final_position': moon_final_pos
        }
    
    def get_moon_trajectory(self, transfer_time):
        """Get Moon positions during transfer"""
        times = np.arange(0, transfer_time + 3600, 3600)  # Every hour
        positions = []
        for t in times:
            positions.append(self.calculate_moon_position(t))
        return np.array(positions)
    
    def create_corrected_trajectory_plot(self):
        """Create accurate trajectory plot that actually reaches the Moon"""
        print("📊 Creating CORRECTED trajectory visualization...")
        
        # Calculate correct trajectory
        trajectory = self.calculate_correct_transfer_trajectory()
        
        if trajectory is None:
            print("❌ Failed to calculate trajectory")
            return
        
        # Create figure
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 10))
        fig.suptitle('CORRECTED Earth-Moon Transfer Trajectory - Lambert Solution', 
                     fontsize=16, fontweight='bold')
        
        # Plot 1: Complete trajectory
        ax1.set_title('Complete Transfer (Lambert Solution)', fontsize=14, fontweight='bold')
        
        # Draw Earth
        earth = Circle((0, 0), R_EARTH/1000, color='blue', alpha=0.8, label='Earth')
        ax1.add_patch(earth)
        
        # Draw Moon's orbital path
        moon_orbit = Circle((0, 0), self.moon_orbital_radius, 
                           fill=False, color='lightgray', linestyle='--', alpha=0.5)
        ax1.add_patch(moon_orbit)
        
        # Plot Moon positions during transfer
        moon_positions = trajectory['moon_positions']
        ax1.plot(moon_positions[:, 0], moon_positions[:, 1], 'gray', 
                linewidth=2, alpha=0.6, label='Moon Path')
        
        # Draw Moon at start and end
        moon_start = Circle(moon_positions[0], R_MOON/1000, color='lightgray', alpha=0.5)
        moon_end = Circle(moon_positions[-1], R_MOON/1000, color='gray', alpha=0.8, label='Moon at Arrival')
        ax1.add_patch(moon_start)
        ax1.add_patch(moon_end)
        
        # Plot spacecraft trajectory
        leo_pos = trajectory['leo']['position']
        transfer_pos = trajectory['transfer']['position']
        lunar_pos = trajectory['lunar_orbit']['position']
        
        ax1.plot(leo_pos[:, 0], leo_pos[:, 1], 'g-', linewidth=2, label='LEO Orbit')
        ax1.plot(transfer_pos[:, 0], transfer_pos[:, 1], 'r-', linewidth=3, 
                label='Lambert Transfer', alpha=0.9)
        ax1.plot(lunar_pos[:, 0], lunar_pos[:, 1], 'purple', linewidth=2, 
                label='Lunar Orbit')
        
        # Mark key points
        ax1.plot(leo_pos[0, 0], leo_pos[0, 1], 'go', markersize=10, label='TLI Start')
        ax1.plot(transfer_pos[-1, 0], transfer_pos[-1, 1], 'ro', markersize=8, label='Moon Arrival')
        
        ax1.set_xlim(-50000, 450000)
        ax1.set_ylim(-200000, 200000)
        ax1.set_xlabel('Distance (km)')
        ax1.set_ylabel('Distance (km)')
        ax1.legend(loc='upper right')
        ax1.grid(True, alpha=0.3)
        ax1.set_aspect('equal')
        
        # Plot 2: Zoomed view of arrival
        ax2.set_title('Moon Arrival Detail', fontsize=14, fontweight='bold')
        
        moon_final = trajectory['moon_final_position']
        
        # Zoom around Moon
        zoom_size = 20000  # km
        ax2.set_xlim(moon_final[0] - zoom_size, moon_final[0] + zoom_size)
        ax2.set_ylim(moon_final[1] - zoom_size, moon_final[1] + zoom_size)
        
        # Draw Moon
        moon_zoom = Circle(moon_final, R_MOON/1000, color='gray', alpha=0.8, label='Moon')
        ax2.add_patch(moon_zoom)
        
        # Draw Moon's SOI
        soi_radius = 66100  # km
        soi_circle = Circle(moon_final, soi_radius, fill=False, color='orange', 
                           linestyle=':', alpha=0.7, label='Moon SOI')
        ax2.add_patch(soi_circle)
        
        # Plot final part of transfer
        n_final = min(50, len(transfer_pos))  # Last 50 points
        ax2.plot(transfer_pos[-n_final:, 0], transfer_pos[-n_final:, 1], 
                'r-', linewidth=3, label='Final Approach')
        
        # Plot lunar orbit
        ax2.plot(lunar_pos[:, 0], lunar_pos[:, 1], 'purple', linewidth=2, 
                label='Lunar Orbit')
        
        # Mark arrival point
        ax2.plot(transfer_pos[-1, 0], transfer_pos[-1, 1], 'ro', markersize=10, 
                label='Arrival Point')
        
        ax2.set_xlabel('Distance (km)')
        ax2.set_ylabel('Distance (km)')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        ax2.set_aspect('equal')
        
        # Add accuracy information
        lambert_info = trajectory['lambert_solution']
        accuracy_text = f"""Lambert Solution Results:
TLI ΔV: {lambert_info['delta_v']:.3f} km/s
Arrival Error: {trajectory['arrival_error']:.1f} km
Transfer Time: 3.0 days
Success: {'✅ YES' if trajectory['arrival_error'] < 10000 else '❌ NO'}"""
        
        ax1.text(0.02, 0.98, accuracy_text, transform=ax1.transAxes, 
                bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgreen", alpha=0.8),
                fontsize=10, verticalalignment='top')
        
        plt.tight_layout()
        
        # Save plots
        plt.savefig('corrected_trajectory.png', dpi=300, bbox_inches='tight')
        plt.savefig('reports/MVP/corrected_trajectory.png', dpi=300, bbox_inches='tight')
        
        plt.show()
        
        return trajectory


def main():
    """Generate corrected trajectory visualization"""
    print("🚀 CORRECTED TRAJECTORY VISUALIZATION")
    print("Using Lambert's Problem for Accurate Earth-Moon Transfer")
    print("="*60)
    
    visualizer = CorrectTrajectoryVisualizer()
    
    # Create corrected trajectory
    trajectory_data = visualizer.create_corrected_trajectory_plot()
    
    if trajectory_data:
        print(f"\n✅ Corrected trajectory created successfully!")
        print(f"   📏 Arrival accuracy: {trajectory_data['arrival_error']:.1f} km")
        print(f"   🔥 TLI ΔV: {trajectory_data['lambert_solution']['delta_v']:.3f} km/s")
        print(f"   🎯 Lambert solution: {'✅ SUCCESS' if trajectory_data['arrival_error'] < 10000 else '❌ FAILED'}")
        print("\n📁 Files generated:")
        print("   - corrected_trajectory.png")
        print("   - reports/MVP/corrected_trajectory.png")
    else:
        print("❌ Failed to generate corrected trajectory")


if __name__ == "__main__":
    main()