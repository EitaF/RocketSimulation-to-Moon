#!/usr/bin/env python3
"""
Debug script to understand the stage separation bug
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from vehicle import create_saturn_v_rocket, MissionPhase
import logging

# Set up detailed logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def analyze_stage_separation_logic():
    """Analyze the stage separation logic and indexing"""
    
    print("="*60)
    print("STAGE SEPARATION BUG ANALYSIS")
    print("="*60)
    
    # Create Saturn V rocket
    rocket = create_saturn_v_rocket()
    
    print(f"\n1. INITIAL ROCKET CONFIGURATION:")
    print(f"   Total stages: {len(rocket.stages)}")
    print(f"   Current stage index: {rocket.current_stage}")
    print(f"   Current phase: {rocket.phase}")
    
    print(f"\n2. STAGE INDEXING:")
    for i, stage in enumerate(rocket.stages):
        print(f"   Stage {i}: {stage.name}")
    
    print(f"\n3. STAGE SEPARATION LOGIC ANALYSIS:")
    print(f"   Initial current_stage: {rocket.current_stage}")
    
    # Simulate stage separations
    print(f"\n4. SIMULATING STAGE SEPARATIONS:")
    
    # Test Stage 1 separation
    print(f"\n   Before Stage 1 separation:")
    print(f"     current_stage = {rocket.current_stage}")
    print(f"     Stage name = {rocket.stages[rocket.current_stage].name}")
    
    success = rocket.separate_stage(168.0)  # After S-IC burn time
    print(f"\n   After Stage 1 separation:")
    print(f"     Separation success: {success}")
    print(f"     current_stage = {rocket.current_stage}")
    if rocket.current_stage < len(rocket.stages):
        print(f"     Stage name = {rocket.stages[rocket.current_stage].name}")
    else:
        print(f"     ERROR: current_stage {rocket.current_stage} >= len(stages) {len(rocket.stages)}")
    
    # Test Stage 2 separation
    print(f"\n   Before Stage 2 separation:")
    print(f"     current_stage = {rocket.current_stage}")
    if rocket.current_stage < len(rocket.stages):
        print(f"     Stage name = {rocket.stages[rocket.current_stage].name}")
    
    success = rocket.separate_stage(968.0)  # After S-II burn time
    print(f"\n   After Stage 2 separation:")
    print(f"     Separation success: {success}")
    print(f"     current_stage = {rocket.current_stage}")
    if rocket.current_stage < len(rocket.stages):
        print(f"     Stage name = {rocket.stages[rocket.current_stage].name}")
    else:
        print(f"     ERROR: current_stage {rocket.current_stage} >= len(stages) {len(rocket.stages)}")
    
    # Test Stage 3 separation
    print(f"\n   Before Stage 3 separation:")
    print(f"     current_stage = {rocket.current_stage}")
    if rocket.current_stage < len(rocket.stages):
        print(f"     Stage name = {rocket.stages[rocket.current_stage].name}")
    
    success = rocket.separate_stage(1447.0)  # After S-IVB burn time
    print(f"\n   After Stage 3 separation:")
    print(f"     Separation success: {success}")
    print(f"     current_stage = {rocket.current_stage}")
    if rocket.current_stage < len(rocket.stages):
        print(f"     Stage name = {rocket.stages[rocket.current_stage].name}")
    else:
        print(f"     No more stages (current_stage {rocket.current_stage} >= len(stages) {len(rocket.stages)})")
    
    print(f"\n5. MISSION PHASE TRANSITIONS:")
    print(f"   Analyzing phase transition logic in rocket_simulation_main.py...")
    
    # Analyze the problematic code section
    print(f"\n6. BUG LOCATION ANALYSIS:")
    print(f"   The error 'Unexpected stage 0 in separation' occurs at line 579:")
    print(f"   self.logger.warning(f'*** Unexpected stage {{self.rocket.current_stage}} in separation ***')")
    print(f"   ")
    print(f"   This happens in the STAGE_SEPARATION phase handler (lines 564-581)")
    print(f"   ")
    print(f"   The problem is likely:")
    print(f"   1. current_stage is 0 when it should be 1, 2, or 3")
    print(f"   2. The phase gets stuck in STAGE_SEPARATION")
    print(f"   3. Infinite loop because phase never changes from STAGE_SEPARATION")
    
    print(f"\n7. STAGE INDEXING EXPECTATIONS:")
    print(f"   Based on the code logic:")
    print(f"   - Stage 0 = S-IC (1st stage) - should separate to become stage 1")
    print(f"   - Stage 1 = S-II (2nd stage) - should separate to become stage 2") 
    print(f"   - Stage 2 = S-IVB (3rd stage) - should separate to become stage 3")
    print(f"   - Stage 3+ = Payload/Lunar module")
    print(f"   ")
    print(f"   The error suggests current_stage=0 during separation, which means:")
    print(f"   - Either separation logic is wrong")
    print(f"   - Or the stage index got reset somehow")
    print(f"   - Or the phase transition logic has a bug")

if __name__ == "__main__":
    analyze_stage_separation_logic()