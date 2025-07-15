# Directory Structure

## Overview
This repository has been organized for clarity and ease of navigation. Here's the complete directory structure:

```
RocketSimulation-to-Moon/
├── README.md                      # Main project documentation
├── requirements.txt               # Python dependencies
├── .gitignore                    # Git ignore rules
├── 
├── src/                          # Source code
│   ├── core/                     # Core simulation engine
│   │   ├── rocket_simulation_main.py    # Main simulation engine
│   │   ├── vehicle.py                   # Rocket and stage definitions
│   │   ├── atmosphere.py                # Atmospheric modeling
│   │   ├── engine.py                    # Engine performance modeling
│   │   ├── constants.py                 # Physical constants
│   │   └── full_mission_driver.py       # Full mission orchestration
│   │
│   ├── guidance/                 # Guidance and control systems
│   │   ├── guidance.py                  # Main guidance system
│   │   ├── circularize.py               # Circularization burns
│   │   ├── peg.py                       # Powered Explicit Guidance
│   │   ├── tli_guidance.py              # Trans-lunar injection
│   │   └── guidance_strategy.py         # Guidance strategies
│   │
│   └── utils/                    # Utilities and tools
│       ├── config_flags.py              # Feature flags
│       ├── metrics_logger.py            # Telemetry logging
│       ├── trajectory_visualizer.py     # Trajectory plotting
│       ├── rocket_visualizer.py         # Real-time visualization
│       ├── monte_carlo_simulation.py    # Monte Carlo campaigns
│       ├── abort_manager.py             # Abort handling
│       ├── fault_detector.py            # Fault detection
│       └── orbital_monitor.py           # Orbital monitoring
│
├── config/                       # Configuration files
│   ├── saturn_v_config.json             # Rocket configuration
│   ├── mission_config.json              # Mission parameters
│   ├── mission_flags.json               # Runtime flags
│   ├── engine_curve.json                # Engine performance curves
│   └── *.yaml                           # Parameter sweep configs
│
├── tests/                        # Test suite
│   ├── test_professor_v45_fixes.py      # Professor v45 validation
│   ├── test_*.py                        # Unit tests
│   └── generate_test_report.py          # Test reporting
│
├── examples/                     # Example scripts and demos
│   ├── basic_mission_example.py         # Basic usage example
│   ├── advanced_production_demo.py      # Advanced demonstrations
│   ├── simple_accurate_trajectory.py    # Simple trajectory demo
│   └── demo_*.py                        # Various demos
│
├── docs/                         # Documentation
│   ├── PROFESSOR_V45_COMPREHENSIVE_REPORT.md  # Complete implementation report
│   ├── README_LAUNCH_GUIDANCE.md               # Mathematical derivations
│   ├── usage_example.md                        # Usage examples
│   └── *_Report.md                             # Historical reports
│
├── outputs/                      # Generated outputs (gitignored)
│   ├── *.png                            # Trajectory plots
│   ├── *.json                           # Mission results
│   ├── *.log                            # Simulation logs
│   ├── *.csv                            # Telemetry data
│   └── reports/                         # Analysis reports
│
├── assets/                       # Static assets
│   ├── Earth_Image.png                  # Earth visualization
│   ├── Moon_Image.png                   # Moon visualization
│   └── Rocket_Image.png                 # Rocket visualization
│
└── Feedback/                     # Professor feedback history
    └── Professor_feedback_v*.md         # Feedback iterations
```

## Key Files

### Quick Start
- `src/core/rocket_simulation_main.py` - Run the main simulation
- `src/utils/trajectory_visualizer.py` - Generate trajectory plots
- `examples/basic_mission_example.py` - Simple usage example

### Configuration
- `config/saturn_v_config.json` - Modify rocket specifications
- `config/mission_config.json` - Adjust mission parameters
- `config/mission_flags.json` - Enable/disable features

### Documentation
- `docs/PROFESSOR_V45_COMPREHENSIVE_REPORT.md` - Complete implementation details
- `docs/README_LAUNCH_GUIDANCE.md` - Mathematical background
- `docs/usage_example.md` - Detailed usage instructions

### Testing
- `tests/test_professor_v45_fixes.py` - Validation of all v45 fixes
- `src/utils/monte_carlo_simulation.py` - Statistical validation

## File Organization Principles

1. **Source Code (`src/`)**: All Python source code organized by functionality
2. **Configuration (`config/`)**: All configuration files in one place
3. **Documentation (`docs/`)**: All documentation and reports
4. **Tests (`tests/`)**: Complete test suite
5. **Examples (`examples/`)**: Demonstration scripts and tutorials
6. **Outputs (`outputs/`)**: Generated files (excluded from git)
7. **Assets (`assets/`)**: Static images and resources

This organization makes it easy to:
- Find specific functionality
- Understand the codebase structure
- Maintain and extend the code
- Run tests and validation
- Generate documentation