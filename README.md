# Earth-to-Moon Rocket Flight Simulation

A physics-accurate rocket flight simulation implementing multi-stage rocket dynamics, orbital mechanics, and guidance systems for Earth-to-Moon missions.

## Features

- **Multi-stage rocket simulation** with realistic propellant consumption
- **Orbital mechanics** with accurate gravitational modeling
- **Atmospheric effects** including drag and density variation
- **Advanced guidance systems** including gravity turn and circularization
- **Real-time telemetry** and mission phase tracking
- **LEO insertion optimization** with precise apoapsis timing and prograde thrust vectoring

## Core Components

### Main Simulation Engine
- `rocket_simulation_main.py` - Primary simulation engine with mission phases
- `vehicle.py` - Rocket and stage definitions
- `guidance.py` - Guidance and control systems

### Advanced Systems
- `circularize.py` - Circularization burn optimization
- `peg.py` - Powered Explicit Guidance (PEG) implementation
- `config_flags.py` - Feature flag system for testing configurations

### Configuration
- `saturn_v_config.json` - Saturn V rocket configuration
- `mission_config.json` - Mission parameters and settings
- `mission_flags.json` - Runtime feature flags

### Visualization
- `rocket_visualizer.py` - Real-time mission visualization
- `trajectory_visualizer.py` - Trajectory plotting and analysis

## Quick Start

1. **Basic simulation run:**
   ```bash
   python3 rocket_simulation_main.py
   ```

2. **With verbose abort debugging:**
   ```bash
   python3 rocket_simulation_main.py --verbose-abort
   ```

3. **View trajectory:**
   ```bash
   python3 trajectory_visualizer.py
   ```

## Mission Phases

The simulation models the complete mission profile:

1. **LAUNCH** - Initial ascent from launch pad
2. **GRAVITY_TURN** - Gradual pitch-over maneuver
3. **STAGE_SEPARATION** - Multi-stage separation events
4. **APOAPSIS_RAISE** - Raising apoapsis altitude
5. **COAST_TO_APOAPSIS** - Coasting to optimal burn point
6. **CIRCULARIZATION** - Circularization burn at apoapsis
7. **LEO** - Low Earth Orbit achieved
8. **TLI_BURN** - Trans-Lunar Injection (future)

## Key Improvements (Actions A1, A2, A3)

Recent enhancements based on professor feedback:

- **A1: Enhanced Circularization Control** - Proper periapsis monitoring and success conditions
- **A2: Precise Burn Timing** - Circularization burns triggered at exact apoapsis (γ ≈ 0°)
- **A3: Optimal Thrust Vectoring** - Prograde thrust alignment for maximum efficiency

## Output Files

The simulation generates:
- `mission_results.json` - Complete mission data
- `mission_log.csv` - Timestamped telemetry data
- Trajectory plots (PNG format)

## Configuration

### Vehicle Configuration (`saturn_v_config.json`)
Modify rocket stages, propellant masses, and performance parameters.

### Mission Settings (`mission_config.json`)
Adjust launch parameters, target orbits, and simulation settings.

### Feature Flags (`mission_flags.json`)
Enable/disable experimental features and guidance modes.

## Dependencies

- Python 3.x
- NumPy
- Matplotlib (for visualization)
- JSON (standard library)

## Documentation

- `usage_example.md` - Detailed usage examples
- `Implementation_Report_A1_A2_A3.md` - Latest implementation report
- `Feedback/` - Professor feedback and requirements

## Development Notes

The simulation uses:
- **RK4 integration** for numerical accuracy
- **Patched-conic approximation** for Earth-Moon gravity
- **Realistic atmospheric models** with exponential density decay
- **Feature flag system** for testing new capabilities

## Status

**Current Status**: LEO insertion logic complete and tested
**Next Phase**: Vehicle performance optimization for stable orbit achievement

---

**Note**: This simulation is designed for educational and research purposes, implementing realistic aerospace engineering principles for rocket flight dynamics and orbital mechanics.