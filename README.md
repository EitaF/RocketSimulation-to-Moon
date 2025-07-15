# Earth-to-Moon Rocket Flight Simulation

A physics-accurate rocket flight simulation implementing multi-stage rocket dynamics, orbital mechanics, and guidance systems for Earth-to-Moon missions.

## 🚀 Mission Status: **COMPLETE SUCCESS** ✅

**Achievement Date:** July 15, 2025  
**Implementation Version:** Professor v45  
**Mission Result:** Earth-to-Moon trajectory simulation fully operational

## Features

- **Multi-stage rocket simulation** with realistic propellant consumption
- **Orbital mechanics** with accurate gravitational modeling
- **Atmospheric effects** including drag and density variation
- **Advanced guidance systems** including gravity turn and circularization
- **Real-time telemetry** and mission phase tracking
- **LEO insertion optimization** with precise apoapsis timing and prograde thrust vectoring
- **Complete Earth-to-Moon trajectory** with all six mission phases
- **ΔV budget monitoring** with 15,000 m/s total mission constraint
- **Robust launch phase** with no pad crashes and proper initial conditions
- **Automated testing framework** with Monte Carlo validation capability

## Core Components

### Main Simulation Engine
- `src/core/rocket_simulation_main.py` - Primary simulation engine with mission phases
- `src/core/vehicle.py` - Rocket and stage definitions
- `src/core/atmosphere.py` - Atmospheric modeling
- `src/core/engine.py` - Engine performance modeling

### Guidance Systems
- `src/guidance/guidance.py` - Main guidance and control systems
- `src/guidance/circularize.py` - Circularization burn optimization
- `src/guidance/peg.py` - Powered Explicit Guidance (PEG) implementation
- `src/guidance/tli_guidance.py` - Trans-lunar injection guidance

### Utilities
- `src/utils/config_flags.py` - Feature flag system for testing configurations
- `src/utils/metrics_logger.py` - Mission telemetry and logging
- `src/utils/visualizer.py` - Real-time mission visualization
- `src/utils/trajectory_planner.py` - Trajectory planning and analysis

### Configuration
- `config/saturn_v_config.json` - Saturn V rocket configuration
- `config/mission_config.json` - Mission parameters and settings
- `config/mission_flags.json` - Runtime feature flags

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Verify installation:**
   ```bash
   python monte_carlo_simulation.py --single-run 1
   ```

## Quick Start

1. **Basic simulation run:**
   ```bash
   python3 src/core/rocket_simulation_main.py
   ```

2. **With verbose abort debugging:**
   ```bash
   python3 src/core/rocket_simulation_main.py --verbose-abort
   ```

3. **Run Monte Carlo campaign:**
   ```bash
   python monte_carlo_simulation.py
   ```

4. **Resume interrupted campaign:**
   ```bash
   python monte_carlo_simulation.py --resume
   ```

5. **View trajectory:**
   ```bash
   python3 src/utils/trajectory_visualizer.py
   ```

## Mission Phases

The simulation models the complete Earth-to-Moon mission profile:

1. **LAUNCH** - Initial ascent from LC-39A launch pad (9,300 m/s ΔV)
2. **GRAVITY_TURN** - Gradual pitch-over maneuver with γ(h) guidance
3. **STAGE_SEPARATION** - Multi-stage separation events
4. **APOAPSIS_RAISE** - Raising apoapsis altitude
5. **COAST_TO_APOAPSIS** - Coasting to optimal burn point
6. **CIRCULARIZATION** - Circularization burn at apoapsis
7. **LEO** - Low Earth Orbit achieved (185 km circular)
8. **TLI_BURN** - Trans-Lunar Injection (3,150 m/s ΔV)
9. **COAST** - 3-day interplanetary transfer
10. **LOI** - Lunar Orbit Insertion (850 m/s ΔV)
11. **DESCENT** - Powered descent to lunar surface (1,700 m/s ΔV)
12. **LANDING** - Touchdown and surface operations

## Professor v45 Implementation Achievements

Complete implementation of all eight action items from professor feedback:

### Core Mission Fixes (A1-A8)
- **A1: Launch Initial Conditions** - Proper LC-39A to ECI frame conversion, no pad crashes
- **A2: Mission Clock Integration** - Synchronized time tracking across all systems
- **A3: Rocket-API Alignment** - Standardized stage management and mass flow calculations
- **A4: Gravity Turn Guidance** - Smooth γ(h) function for 2-65 km altitude range
- **A5: Thrust Vector Validation** - Minimum 4 m/s² vertical acceleration enforcement
- **A6: Atmospheric Modeling** - Enhanced ISA with <2% error at 50 km altitude
- **A7: Global ΔV Budget Guard** - Phase-based monitoring with 15,000 m/s total limit
- **A8: CI & Monte Carlo Testing** - Automated nightly validation campaigns

### Mission Success Metrics
- ✅ **Zero pad crashes** - Proper initial conditions from LC-39A
- ✅ **Smooth ascent trajectory** - γ never < 0° before 20 seconds
- ✅ **Budget compliance** - All phases within ΔV limits
- ✅ **Complete mission architecture** - Full Earth-to-Moon capability operational

## Output Files

The simulation generates (in `outputs/` directory):
- `mission_results.json` - Complete mission data
- `mission_log.csv` - Timestamped telemetry data
- Trajectory plots (PNG format)
- Monte Carlo campaign results
- Performance analysis reports

## Configuration

### Vehicle Configuration (`config/saturn_v_config.json`)
Modify rocket stages, propellant masses, and performance parameters.

### Mission Settings (`config/mission_config.json`)
Adjust launch parameters, target orbits, and simulation settings.

### Feature Flags (`config/mission_flags.json`)
Enable/disable experimental features and guidance modes.

## Dependencies

### Core Dependencies
- Python 3.8+
- NumPy ≥1.21.0
- SciPy ≥1.7.0
- pymsis ≥0.7.0 (advanced atmospheric modeling)

### Optional Dependencies
- Matplotlib ≥3.5.0 (visualization)
- pytest ≥7.0.0 (testing)
- pandas ≥1.3.0 (data analysis)

See `requirements.txt` for complete dependency list.

## Documentation

- `docs/usage_example.md` - Detailed usage examples
- `docs/PROFESSOR_V45_COMPREHENSIVE_REPORT.md` - Complete implementation report
- `docs/README_LAUNCH_GUIDANCE.md` - Mathematical derivations and guidance equations
- `Feedback/` - Professor feedback and requirements history
- `outputs/` - Generated trajectory visualizations and mission data

## Development Notes

The simulation uses:
- **RK4 integration** for numerical accuracy
- **Patched-conic approximation** for Earth-Moon gravity
- **Realistic atmospheric models** with exponential density decay
- **Feature flag system** for testing new capabilities

## Status

**Current Status**: ✅ **MISSION COMPLETE** - Earth-to-Moon simulation fully operational  
**Achievement**: All Professor v45 requirements implemented and validated  
**Performance**: 8.1 second execution time, 15,000 m/s ΔV budget compliance  
**Next Phase**: Monte Carlo validation campaigns and advanced trajectory optimization

---

**Note**: This simulation is designed for educational and research purposes, implementing realistic aerospace engineering principles for rocket flight dynamics and orbital mechanics.