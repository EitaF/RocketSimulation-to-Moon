#!/usr/bin/env python3
"""
Stage-3 ΔV Audit Script
Action Item #1 from Professor v23 Feedback
Validates Stage-3 mass and Isp numbers, computes ideal and finite-loss ΔV
"""

import json
import math
from vehicle import STANDARD_GRAVITY

def calculate_ideal_delta_v(propellant_mass, dry_mass, isp_vacuum):
    """
    Calculate ideal ΔV using Tsiolkovsky rocket equation
    ΔV = Isp * g * ln(m_initial / m_final)
    """
    m_initial = propellant_mass + dry_mass
    m_final = dry_mass
    
    if m_final <= 0 or m_initial <= m_final:
        return 0.0
    
    mass_ratio = m_initial / m_final
    delta_v = isp_vacuum * STANDARD_GRAVITY * math.log(mass_ratio)
    return delta_v

def calculate_finite_loss_delta_v(ideal_delta_v, gravity_losses=0.15, drag_losses=0.02, steering_losses=0.03):
    """
    Apply realistic losses to ideal ΔV
    Typical losses for upper stages:
    - Gravity losses: ~15% (less than lower stages due to higher altitude)
    - Drag losses: ~2% (minimal at high altitude)
    - Steering losses: ~3% (attitude control, guidance corrections)
    """
    total_loss_factor = gravity_losses + drag_losses + steering_losses
    finite_delta_v = ideal_delta_v * (1 - total_loss_factor)
    return finite_delta_v

def audit_stage3_config():
    """Main audit function"""
    print("=== Stage-3 (S-IVB) ΔV Audit ===\n")
    
    # Load configuration
    try:
        with open("saturn_v_config.json", 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        print("ERROR: saturn_v_config.json not found!")
        return False
    
    # Extract Stage-3 data
    stage3 = config["stages"][2]  # S-IVB is the 3rd stage (index 2)
    
    print(f"Stage: {stage3['name']}")
    print(f"Dry Mass: {stage3['dry_mass']:,.0f} kg")
    print(f"Propellant Mass: {stage3['propellant_mass']:,.0f} kg")
    print(f"Total Mass: {stage3['dry_mass'] + stage3['propellant_mass']:,.0f} kg")
    print(f"Isp (vacuum): {stage3['specific_impulse_vacuum']} s")
    print(f"Thrust (vacuum): {stage3['thrust_vacuum']:,.0f} N")
    print(f"Burn Time: {stage3['burn_time']} s")
    print()
    
    # Calculate mass ratio
    total_mass = stage3['dry_mass'] + stage3['propellant_mass']
    mass_ratio = total_mass / stage3['dry_mass']
    
    print(f"Mass Ratio: {mass_ratio:.2f}")
    print()
    
    # Calculate ideal ΔV
    ideal_dv = calculate_ideal_delta_v(
        stage3['propellant_mass'],
        stage3['dry_mass'],
        stage3['specific_impulse_vacuum']
    )
    
    print(f"Ideal ΔV (Tsiolkovsky): {ideal_dv/1000:.2f} km/s")
    
    # Calculate finite-loss ΔV with different loss models
    print("\nFinite-loss ΔV estimates:")
    
    # Conservative losses (upper stage typical)
    conservative_dv = calculate_finite_loss_delta_v(ideal_dv, 0.15, 0.02, 0.03)
    print(f"Conservative losses (20%): {conservative_dv/1000:.2f} km/s")
    
    # Moderate losses
    moderate_dv = calculate_finite_loss_delta_v(ideal_dv, 0.20, 0.03, 0.05)
    print(f"Moderate losses (28%): {moderate_dv/1000:.2f} km/s")
    
    # Aggressive losses
    aggressive_dv = calculate_finite_loss_delta_v(ideal_dv, 0.25, 0.05, 0.07)
    print(f"Aggressive losses (37%): {aggressive_dv/1000:.2f} km/s")
    
    # Check if current configuration is physically reasonable
    print(f"\n=== ANALYSIS ===")
    print(f"Professor's feedback mentions 'actual' contribution of 2.8-3.2 km/s")
    print(f"This would represent losses of: {((ideal_dv - 3000)/ideal_dv)*100:.1f}% to {((ideal_dv - 2800)/ideal_dv)*100:.1f}%")
    
    if ideal_dv/1000 > 10:
        print(f"⚠️  WARNING: Ideal ΔV of {ideal_dv/1000:.1f} km/s seems very high!")
        print(f"   Mass ratio of {mass_ratio:.1f} with Isp {stage3['specific_impulse_vacuum']}s gives unrealistic performance")
        print(f"   Typical S-IVB mass ratio is ~6-8, not {mass_ratio:.1f}")
        
        # Calculate realistic propellant mass for target ΔV
        target_dv = 4000  # 4 km/s target
        target_mass_ratio = math.exp(target_dv / (stage3['specific_impulse_vacuum'] * STANDARD_GRAVITY))
        realistic_prop_mass = stage3['dry_mass'] * (target_mass_ratio - 1)
        
        print(f"\n💡 RECOMMENDATION:")
        print(f"   For a realistic 4 km/s ΔV capability:")
        print(f"   - Mass ratio should be: {target_mass_ratio:.1f}")
        print(f"   - Propellant mass should be: {realistic_prop_mass:,.0f} kg")
        print(f"   - Current propellant mass is: {stage3['propellant_mass']:,.0f} kg")
        print(f"   - Difference: {stage3['propellant_mass'] - realistic_prop_mass:+,.0f} kg")
        
        return False
    else:
        print(f"✅ Configuration appears physically reasonable")
        return True

def verify_burn_time_consistency():
    """Verify that burn time is consistent with propellant mass and thrust"""
    print(f"\n=== BURN TIME VERIFICATION ===")
    
    with open("saturn_v_config.json", 'r') as f:
        config = json.load(f)
    
    stage3 = config["stages"][2]
    
    # Calculate mass flow rate
    mass_flow_rate = stage3['thrust_vacuum'] / (stage3['specific_impulse_vacuum'] * STANDARD_GRAVITY)
    calculated_burn_time = stage3['propellant_mass'] / mass_flow_rate
    
    print(f"Mass flow rate: {mass_flow_rate:.1f} kg/s")
    print(f"Calculated burn time: {calculated_burn_time:.1f} s")
    print(f"Config burn time: {stage3['burn_time']} s")
    print(f"Difference: {calculated_burn_time - stage3['burn_time']:+.1f} s")
    
    if abs(calculated_burn_time - stage3['burn_time']) > 10:
        print("⚠️  WARNING: Burn time inconsistency > 10 seconds!")
        return False
    else:
        print("✅ Burn time is consistent")
        return True

if __name__ == "__main__":
    config_ok = audit_stage3_config()
    burn_time_ok = verify_burn_time_consistency()
    
    if not (config_ok and burn_time_ok):
        print(f"\n❌ AUDIT FAILED - Configuration needs correction")
        exit(1)
    else:
        print(f"\n✅ AUDIT PASSED - Configuration is valid")
        exit(0)