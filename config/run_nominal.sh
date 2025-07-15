#!/bin/bash
#
# Nominal Mission Execution Script
# Professor v43 Feedback: Run complete lunar simulation
# 
# This script executes the lunar simulation and validates results
# Exit code 0 = success, non-zero = failure
#

set -e  # Exit on any error

echo "🚀 LUNAR MISSION - NOMINAL RUN"
echo "Professor v43 MVP Implementation"
echo "================================"

# Check Python availability
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 not found"
    exit 1
fi

# Check required files
REQUIRED_FILES=(
    "lunar_sim_main.py"
    "unified_trajectory_system.py"
    "trajectory_planner.py"
    "finite_burn_executor.py"
    "residual_projector.py"
    "launch_window_preprocessor.py"
    "engine.py"
)

echo "📋 Checking required files..."
for file in "${REQUIRED_FILES[@]}"; do
    if [[ ! -f "$file" ]]; then
        echo "❌ Error: Required file missing: $file"
        exit 1
    fi
    echo "   ✅ $file"
done

# Create reports directory
mkdir -p reports/MVP
echo "📁 Created reports directory: reports/MVP/"

# Run the simulation
echo ""
echo "🔥 Starting lunar simulation..."
echo "Target: Touchdown velocity ≤ 2 m/s, tilt ≤ 5°"
echo ""

# Execute main simulation
if python3 lunar_sim_main.py; then
    SIMULATION_SUCCESS=true
    echo ""
    echo "✅ Simulation completed successfully"
else
    SIMULATION_SUCCESS=false
    echo ""
    echo "❌ Simulation failed"
fi

# Check if results file exists
if [[ -f "lunar_mission_results.json" ]]; then
    echo "📊 Results saved to: lunar_mission_results.json"
    
    # Extract key metrics using Python
    TOUCHDOWN_VELOCITY=$(python3 -c "
import json
with open('lunar_mission_results.json', 'r') as f:
    data = json.load(f)
    if data['success']:
        print(f\"{data['touchdown']['velocity']:.2f}\")
    else:
        print('FAILED')
")
    
    TOUCHDOWN_TILT=$(python3 -c "
import json
with open('lunar_mission_results.json', 'r') as f:
    data = json.load(f)
    if data['success']:
        print(f\"{data['touchdown']['tilt_angle']:.2f}\")
    else:
        print('FAILED')
")
    
    MEETS_CRITERIA=$(python3 -c "
import json
with open('lunar_mission_results.json', 'r') as f:
    data = json.load(f)
    print(data['performance_metrics']['meets_professor_criteria'])
")
    
    echo ""
    echo "📈 MISSION METRICS:"
    echo "   Touchdown velocity: $TOUCHDOWN_VELOCITY m/s (target: ≤ 2.0)"
    echo "   Touchdown tilt: $TOUCHDOWN_TILT° (target: ≤ 5.0°)"
    echo "   Meets professor criteria: $MEETS_CRITERIA"
    
    # Copy results to reports directory
    cp lunar_mission_results.json reports/MVP/
    if [[ -f "lunar_mission.log" ]]; then
        cp lunar_mission.log reports/MVP/
    fi
    
    # Validate success criteria
    if [[ "$MEETS_CRITERIA" == "True" && "$SIMULATION_SUCCESS" == "true" ]]; then
        echo ""
        echo "🎉 NOMINAL RUN SUCCESS!"
        echo "✅ All professor criteria met"
        echo "✅ No runtime errors"
        echo "✅ Full state logs generated"
        
        # Create success marker
        echo "SUCCESS: $(date)" > reports/MVP/nominal_run_status.txt
        echo "Touchdown velocity: $TOUCHDOWN_VELOCITY m/s" >> reports/MVP/nominal_run_status.txt
        echo "Touchdown tilt: $TOUCHDOWN_TILT°" >> reports/MVP/nominal_run_status.txt
        
        exit 0
    else
        echo ""
        echo "❌ NOMINAL RUN FAILED"
        echo "Professor criteria not met or simulation error"
        
        # Create failure marker
        echo "FAILED: $(date)" > reports/MVP/nominal_run_status.txt
        echo "Reason: Criteria not met or simulation error" >> reports/MVP/nominal_run_status.txt
        
        exit 1
    fi
else
    echo "❌ Error: Results file not generated"
    exit 1
fi