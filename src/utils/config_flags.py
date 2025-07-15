"""
Configuration Flags for Mission Control
Professor v17: LEO_FINAL_RUN flag for safe rollback capability
"""

import os
import json
from typing import Dict, Any

class ConfigFlags:
    """
    Feature flag management for mission control
    Allows safe rollback of features via configuration
    """
    
    def __init__(self, config_file: str = "mission_flags.json"):
        self.config_file = config_file
        self.flags = self._load_flags()
    
    def _load_flags(self) -> Dict[str, Any]:
        """Load feature flags from configuration file"""
        default_flags = {
            "LEO_FINAL_RUN": True,           # Professor v17: Enable final LEO run optimizations
            "STAGE2_MASS_FLOW_OVERRIDE": True,  # T01: Stage-2 mass flow hotfix
            "PEG_GAMMA_DAMPING": True,       # T02: PEG convergence improvements  
            "VELOCITY_TRIGGERED_STAGE3": True,  # T04: Velocity-triggered Stage-3
            "ENHANCED_TELEMETRY": True,      # T05: 0.2s telemetry logging
            "PITCH_OPTIMIZATION": False,    # T03: Use optimized pitch schedule (set to True after sweep)
            "MONTE_CARLO_MODE": False,      # For Monte Carlo analysis
            "DEBUG_MODE": False,            # Extra debug logging
            "SAFE_MODE": False              # Conservative fallback settings
        }
        
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    loaded_flags = json.load(f)
                # Merge with defaults to ensure all flags exist
                default_flags.update(loaded_flags)
            
            # Save current flags back to file
            with open(self.config_file, 'w') as f:
                json.dump(default_flags, f, indent=2)
                
        except Exception as e:
            print(f"Warning: Could not load flags from {self.config_file}: {e}")
            print("Using default flags")
        
        return default_flags
    
    def get(self, flag_name: str, default: Any = False) -> Any:
        """Get flag value with optional default"""
        return self.flags.get(flag_name, default)
    
    def set(self, flag_name: str, value: Any) -> None:
        """Set flag value and save to file"""
        self.flags[flag_name] = value
        self._save_flags()
    
    def _save_flags(self) -> None:
        """Save current flags to configuration file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.flags, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save flags to {self.config_file}: {e}")
    
    def enable_leo_final_run(self) -> None:
        """Enable all LEO final run optimizations"""
        self.flags.update({
            "LEO_FINAL_RUN": True,
            "STAGE2_MASS_FLOW_OVERRIDE": True,
            "PEG_GAMMA_DAMPING": True,
            "VELOCITY_TRIGGERED_STAGE3": True,
            "ENHANCED_TELEMETRY": True
        })
        self._save_flags()
        print("LEO_FINAL_RUN mode enabled - all optimizations active")
    
    def enable_safe_mode(self) -> None:
        """Enable safe mode with conservative settings"""
        self.flags.update({
            "LEO_FINAL_RUN": False,
            "STAGE2_MASS_FLOW_OVERRIDE": False,
            "PEG_GAMMA_DAMPING": False,
            "VELOCITY_TRIGGERED_STAGE3": False,
            "ENHANCED_TELEMETRY": False,
            "PITCH_OPTIMIZATION": False,
            "SAFE_MODE": True
        })
        self._save_flags()
        print("SAFE_MODE enabled - all optimizations disabled")
    
    def rollback(self) -> None:
        """Quick rollback to safe configuration"""
        self.enable_safe_mode()
        print("ROLLBACK COMPLETE: All features disabled for safety")
    
    def status(self) -> str:
        """Get current flag status summary"""
        status_lines = ["=== MISSION CONFIGURATION FLAGS ==="]
        
        # Critical flags first
        critical_flags = ["LEO_FINAL_RUN", "SAFE_MODE"]
        for flag in critical_flags:
            value = self.flags.get(flag, False)
            status = "ENABLED" if value else "DISABLED"
            status_lines.append(f"{flag:25s}: {status}")
        
        status_lines.append("")
        status_lines.append("Feature Flags:")
        
        # Feature flags
        feature_flags = [
            "STAGE2_MASS_FLOW_OVERRIDE",
            "PEG_GAMMA_DAMPING", 
            "VELOCITY_TRIGGERED_STAGE3",
            "ENHANCED_TELEMETRY",
            "PITCH_OPTIMIZATION"
        ]
        
        for flag in feature_flags:
            value = self.flags.get(flag, False)
            status = "ON" if value else "OFF"
            status_lines.append(f"  {flag:23s}: {status}")
        
        status_lines.append("")
        status_lines.append("Quick Commands:")
        status_lines.append("  config.enable_leo_final_run()  # Enable all optimizations")
        status_lines.append("  config.rollback()              # Emergency rollback")
        
        return "\n".join(status_lines)

# Global configuration instance
config = ConfigFlags()

def get_flag(flag_name: str, default: Any = False) -> Any:
    """Quick access to flag values"""
    return config.get(flag_name, default)

def is_enabled(flag_name: str) -> bool:
    """Check if a flag is enabled (True)"""
    return bool(config.get(flag_name, False))

def enable_feature(flag_name: str) -> None:
    """Enable a specific feature"""
    config.set(flag_name, True)
    print(f"Feature {flag_name} enabled")

def disable_feature(flag_name: str) -> None:
    """Disable a specific feature"""
    config.set(flag_name, False)
    print(f"Feature {flag_name} disabled")

if __name__ == "__main__":
    # Command line interface for flag management
    import sys
    
    if len(sys.argv) == 1:
        print(config.status())
    elif sys.argv[1] == "status":
        print(config.status())
    elif sys.argv[1] == "enable-final-run":
        config.enable_leo_final_run()
    elif sys.argv[1] == "rollback":
        config.rollback()
    elif sys.argv[1] == "safe-mode":
        config.enable_safe_mode()
    else:
        print("Usage: python config_flags.py [status|enable-final-run|rollback|safe-mode]")