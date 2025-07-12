#!/usr/bin/env python3
"""
Quick-look plot generation for MVP
Professor v43: orbit_track.png and altitude_vs_time.png
"""

import numpy as np
import matplotlib.pyplot as plt
import json
from lunar_sim_main import LunarSimulation

def generate_quick_look_plots():
    """Generate quick-look plots for the mission"""
    print("📊 Generating quick-look plots...")
    
    # Run a simulation to get trajectory data
    simulation = LunarSimulation()
    results = simulation.run_complete_mission()
    
    if not results['success']:
        print("❌ Cannot generate plots - simulation failed")
        return
    
    # Extract mission states
    states = results['mission_states']
    
    # Extract data for plotting
    times = [state['time'] for state in states]
    altitudes = [state['altitude']/1000 for state in states]  # Convert to km
    phases = [state['phase'] for state in states]
    
    # Create figure with subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
    
    # Plot 1: Orbit track (simplified trajectory)
    ax1.set_title('Lunar Mission Trajectory - Orbit Track', fontsize=14, fontweight='bold')
    
    # Create simplified orbital track
    earth_x, earth_y = 0, 0
    moon_x, moon_y = 384400, 0  # Moon position (km)
    
    # Plot Earth and Moon
    earth_circle = plt.Circle((earth_x, earth_y), 6371, color='blue', alpha=0.6, label='Earth')
    moon_circle = plt.Circle((moon_x, moon_y), 1737, color='gray', alpha=0.6, label='Moon')
    ax1.add_patch(earth_circle)
    ax1.add_patch(moon_circle)
    
    # Plot trajectory phases
    leo_orbit = plt.Circle((earth_x, earth_y), 6556, fill=False, color='green', linewidth=2, label='LEO (185 km)')
    lunar_orbit = plt.Circle((moon_x, moon_y), 1837, fill=False, color='red', linewidth=2, label='Lunar Orbit (100 km)')
    ax1.add_patch(leo_orbit)
    ax1.add_patch(lunar_orbit)
    
    # Draw transfer trajectory
    transfer_x = np.linspace(6556, moon_x - 1837, 100)
    transfer_y = 50000 * np.sin(np.pi * transfer_x / (moon_x - 6556))  # Simplified arc
    ax1.plot(transfer_x, transfer_y, 'orange', linewidth=3, label='Trans-Lunar Trajectory')
    
    # Add phase markers
    ax1.plot(6556, 0, 'go', markersize=10, label='TLI Burn')
    ax1.plot(moon_x - 66100, 0, 'ro', markersize=8, label='LOI Burn')
    ax1.plot(moon_x - 1737, 0, 'ko', markersize=8, label='Touchdown')
    
    ax1.set_xlim(-50000, 450000)
    ax1.set_ylim(-100000, 150000)
    ax1.set_xlabel('Distance (km)')
    ax1.set_ylabel('Distance (km)')
    ax1.legend(loc='upper right')
    ax1.grid(True, alpha=0.3)
    ax1.set_aspect('equal', adjustable='box')
    
    # Plot 2: Altitude vs Time
    ax2.set_title('Mission Altitude Profile', fontsize=14, fontweight='bold')
    
    # Convert time to hours
    time_hours = [t/3600 for t in times]
    
    # Plot altitude profile
    colors = {'LEO': 'green', 'TLI_COAST': 'orange', 'MOON_SOI': 'red', 
              'LUNAR_ORBIT': 'purple', 'SURFACE_HOVER': 'black'}
    
    for i, phase in enumerate(phases):
        color = colors.get(phase, 'blue')
        if i < len(time_hours) - 1:
            ax2.plot([time_hours[i], time_hours[i+1]], [altitudes[i], altitudes[i+1]], 
                    color=color, linewidth=3, label=phase if phase not in [p for j, p in enumerate(phases) if j < i] else "")
    
    # Add phase annotations
    phase_times = {
        'TLI Burn': 0.2,
        'Coast to Moon': 36,
        'LOI Burn': 72.1,
        'Powered Descent': 72.3,
        'Touchdown': 72.5
    }
    
    for phase, time_h in phase_times.items():
        if time_h <= max(time_hours):
            ax2.axvline(x=time_h, color='gray', linestyle='--', alpha=0.7)
            ax2.text(time_h, max(altitudes)*0.8, phase, rotation=90, alpha=0.7)
    
    ax2.set_xlabel('Mission Time (hours)')
    ax2.set_ylabel('Altitude (km)')
    ax2.legend(loc='upper right')
    ax2.grid(True, alpha=0.3)
    ax2.set_yscale('log')  # Log scale for better visualization
    
    # Add mission metrics text
    touchdown = results['touchdown']
    metrics_text = f"""Mission Success: {results['success']}
Touchdown Velocity: {touchdown['velocity']:.2f} m/s
Touchdown Tilt: {touchdown['tilt_angle']:.2f}°
Total ΔV: {results['total_delta_v']:.1f} m/s
Professor Criteria: {'✅ PASS' if results['performance_metrics']['meets_professor_criteria'] else '❌ FAIL'}"""
    
    ax2.text(0.02, 0.02, metrics_text, transform=ax2.transAxes, 
             bbox=dict(boxstyle="round,pad=0.3", facecolor="lightblue", alpha=0.8),
             fontsize=10, verticalalignment='bottom')
    
    plt.tight_layout()
    
    # Save plots
    plt.savefig('orbit_track.png', dpi=150, bbox_inches='tight')
    plt.savefig('altitude_vs_time.png', dpi=150, bbox_inches='tight')
    
    # Also save to reports directory
    import os
    os.makedirs('reports/MVP', exist_ok=True)
    plt.savefig('reports/MVP/orbit_track.png', dpi=150, bbox_inches='tight')
    plt.savefig('reports/MVP/altitude_vs_time.png', dpi=150, bbox_inches='tight')
    
    plt.close()
    
    print("✅ Quick-look plots generated:")
    print("   - orbit_track.png")
    print("   - altitude_vs_time.png")
    print("   - Saved to reports/MVP/")

if __name__ == "__main__":
    generate_quick_look_plots()