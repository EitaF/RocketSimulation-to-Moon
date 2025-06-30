"""
Physical Constants - Single Source of Truth
Task 5-6: Centralize constants to eliminate magic numbers and ensure consistency
"""

import math


# === FUNDAMENTAL PHYSICAL CONSTANTS ===

# Universal gravitational constant [m³/(kg·s²)]
G = 6.67430e-11

# Standard gravity acceleration [m/s²]
STANDARD_GRAVITY = 9.80665

# Speed of light in vacuum [m/s]
SPEED_OF_LIGHT = 299792458

# Boltzmann constant [J/K]
BOLTZMANN_CONSTANT = 1.380649e-23

# Gas constant [J/(mol·K)]
GAS_CONSTANT = 8.314462618


# === EARTH CONSTANTS ===

# Earth physical properties
EARTH_MASS = 5.972e24              # kg
EARTH_RADIUS = 6371e3              # m (mean radius)
EARTH_EQUATORIAL_RADIUS = 6378137   # m (WGS84)
EARTH_POLAR_RADIUS = 6356752.314245 # m (WGS84)
EARTH_FLATTENING = 1/298.257223563  # WGS84 flattening

# Earth rotation
EARTH_ROTATION_PERIOD = 24 * 3600   # s (sidereal day: 23h 56m 4s)
EARTH_SIDEREAL_DAY = 86164.0905     # s (exact sidereal day)
EARTH_ANGULAR_VELOCITY = 2 * math.pi / EARTH_SIDEREAL_DAY  # rad/s

# Earth orbital mechanics
EARTH_ORBITAL_VELOCITY = 29780      # m/s (around Sun)
EARTH_ESCAPE_VELOCITY = 11180       # m/s (from surface)
EARTH_MU = G * EARTH_MASS           # m³/s² (gravitational parameter)

# Earth atmosphere
SEA_LEVEL_PRESSURE = 101325         # Pa
SEA_LEVEL_DENSITY = 1.225           # kg/m³
SEA_LEVEL_TEMPERATURE = 288.15      # K
ATMOSPHERIC_SCALE_HEIGHT = 8500     # m
DRY_AIR_GAS_CONSTANT = 287.0        # J/(kg·K)


# === MOON CONSTANTS ===

# Moon physical properties
MOON_MASS = 7.34767309e22           # kg
MOON_RADIUS = 1737e3                # m (mean radius)
MOON_DENSITY = 3344                 # kg/m³

# Moon orbital mechanics
MOON_ORBIT_RADIUS = 384400e3        # m (semi-major axis)
MOON_ORBIT_PERIOD = 27.321661 * 24 * 3600  # s (sidereal month)
MOON_ESCAPE_VELOCITY = 2380         # m/s (from surface)
MOON_MU = G * MOON_MASS             # m³/s² (gravitational parameter)

# Moon's sphere of influence
MOON_SOI_RADIUS = 66.2e6            # m (sphere of influence)

# Moon orbit characteristics
LUNAR_ORBIT_INCLINATION = math.radians(5.145)  # rad (to ecliptic)
LUNAR_ORBIT_ECCENTRICITY = 0.0549


# === SUN CONSTANTS ===

# Sun physical properties
SUN_MASS = 1.98847e30               # kg
SUN_RADIUS = 696340e3               # m
SUN_LUMINOSITY = 3.828e26           # W

# Sun-Earth system
AU = 149597870700                   # m (astronomical unit)
SOLAR_CONSTANT = 1361               # W/m² (at Earth distance)


# === LAUNCH SITE CONSTANTS ===

# Kennedy Space Center (KSC)
KSC_LATITUDE = 28.573               # degrees
KSC_LONGITUDE = -80.649             # degrees
KSC_ALTITUDE = 0                    # m (sea level)

# Surface velocity due to Earth rotation at KSC
KSC_SURFACE_VELOCITY = 2 * math.pi * EARTH_RADIUS * math.cos(math.radians(KSC_LATITUDE)) / EARTH_SIDEREAL_DAY


# === ROCKET PERFORMANCE CONSTANTS ===

# Typical specific impulse values [s]
ISP_SOLID_BOOSTER = 250             # Solid rocket booster
ISP_KEROSENE_LOX = 300              # RP-1/LOX (sea level)
ISP_HYDROGEN_LOX = 450              # LH2/LOX (vacuum)
ISP_HYPERGOLIC = 300                # Hypergolic propellants

# Propellant densities [kg/m³]
DENSITY_RP1 = 810                   # RP-1 kerosene
DENSITY_LOX = 1141                  # Liquid oxygen
DENSITY_LH2 = 71                    # Liquid hydrogen
DENSITY_N2O4 = 1450                 # Nitrogen tetroxide
DENSITY_MMH = 874                   # Monomethylhydrazine

# Typical thrust-to-weight ratios
TWR_FIRST_STAGE = 1.2               # First stage at liftoff
TWR_UPPER_STAGE = 0.8               # Upper stage
TWR_LANDING = 3.0                   # Landing burn


# === ORBITAL MECHANICS CONSTANTS ===

# Standard orbital elements
LEO_ALTITUDE_MIN = 160e3            # m (minimum stable LEO)
LEO_ALTITUDE_MAX = 2000e3           # m (maximum LEO)
GEO_ALTITUDE = 35786e3              # m (geostationary orbit)

# Orbital velocities at Earth surface level
ORBITAL_VELOCITY_LEO = 7800         # m/s (200 km circular orbit)
ORBITAL_VELOCITY_GTO = 10000        # m/s (GTO insertion)

# Lunar mission constants
LUNAR_TRANSFER_VELOCITY = 11100     # m/s (trans-lunar injection)
LUNAR_ORBITAL_VELOCITY = 1600       # m/s (100 km lunar orbit)


# === ATMOSPHERIC FLIGHT CONSTANTS ===

# Mach number and speed of sound
SPEED_OF_SOUND_SEA_LEVEL = 343      # m/s (at 15°C)
MACH_1 = SPEED_OF_SOUND_SEA_LEVEL

# Dynamic pressure limits
MAX_Q_STRUCTURAL = 35000            # Pa (typical structural limit)
MAX_Q_APOLLO = 33000                # Pa (Apollo program limit)

# Flight envelope
KARMAN_LINE = 100e3                 # m (space boundary)
ATMOSPHERE_TOP = 600e3              # m (practical atmosphere boundary)


# === MISSION TIMELINE CONSTANTS ===

# Typical mission durations
LAUNCH_TO_LEO = 600                 # s (10 minutes)
LEO_TO_TLI = 5400                   # s (1.5 hours)
EARTH_TO_MOON = 3 * 24 * 3600       # s (3 days)
LUNAR_MISSION_DURATION = 14 * 24 * 3600  # s (14 days)

# Mission phases
GRAVITY_TURN_START = 1500           # m (altitude to start gravity turn)
MECO_TARGET_VELOCITY = 7800         # m/s (main engine cutoff velocity)


# === MATHEMATICAL CONSTANTS ===

# Already available in math module, but included for completeness
PI = math.pi
E = math.e
SQRT_2 = math.sqrt(2)

# Conversion factors
DEG_TO_RAD = math.pi / 180
RAD_TO_DEG = 180 / math.pi
KM_TO_M = 1000
M_TO_KM = 1e-3
HOURS_TO_SECONDS = 3600
SECONDS_TO_HOURS = 1/3600


# === SIMULATION CONSTANTS ===

# Numerical integration
DEFAULT_TIME_STEP = 0.1             # s
MAX_TIME_STEP = 1.0                 # s
MIN_TIME_STEP = 0.01                # s

# Convergence tolerances
POSITION_TOLERANCE = 1.0            # m
VELOCITY_TOLERANCE = 0.1            # m/s
ANGULAR_TOLERANCE = 0.01            # rad

# Safety factors
STRUCTURAL_SAFETY_FACTOR = 1.4      # 40% margin
PROPELLANT_SAFETY_MARGIN = 0.05     # 5% reserve


# === UNIT CONVERSION UTILITIES ===

def m_to_km(meters: float) -> float:
    """Convert meters to kilometers"""
    return meters * M_TO_KM


def km_to_m(kilometers: float) -> float:
    """Convert kilometers to meters"""
    return kilometers * KM_TO_M


def deg_to_rad(degrees: float) -> float:
    """Convert degrees to radians"""
    return degrees * DEG_TO_RAD


def rad_to_deg(radians: float) -> float:
    """Convert radians to degrees"""
    return radians * RAD_TO_DEG


def hours_to_seconds(hours: float) -> float:
    """Convert hours to seconds"""
    return hours * HOURS_TO_SECONDS


def seconds_to_hours(seconds: float) -> float:
    """Convert seconds to hours"""
    return seconds * SECONDS_TO_HOURS


def calculate_escape_velocity(mass: float, radius: float) -> float:
    """Calculate escape velocity for a celestial body"""
    return math.sqrt(2 * G * mass / radius)


def calculate_orbital_velocity(mass: float, radius: float) -> float:
    """Calculate circular orbital velocity at given radius"""
    return math.sqrt(G * mass / radius)


def calculate_sphere_of_influence(primary_mass: float, secondary_mass: float, 
                                 orbital_distance: float) -> float:
    """Calculate sphere of influence radius for two-body system"""
    return orbital_distance * (secondary_mass / primary_mass) ** (2/5)


# === VALIDATION FUNCTIONS ===

def validate_constants():
    """Validate physical constants for consistency"""
    errors = []
    
    # Check Earth escape velocity
    calculated_escape = calculate_escape_velocity(EARTH_MASS, EARTH_RADIUS)
    if abs(calculated_escape - EARTH_ESCAPE_VELOCITY) > 100:
        errors.append(f"Earth escape velocity mismatch: {calculated_escape:.0f} vs {EARTH_ESCAPE_VELOCITY}")
    
    # Check Moon escape velocity
    calculated_moon_escape = calculate_escape_velocity(MOON_MASS, MOON_RADIUS)
    if abs(calculated_moon_escape - MOON_ESCAPE_VELOCITY) > 50:
        errors.append(f"Moon escape velocity mismatch: {calculated_moon_escape:.0f} vs {MOON_ESCAPE_VELOCITY}")
    
    # Check orbital velocity at LEO
    calculated_leo_vel = calculate_orbital_velocity(EARTH_MASS, EARTH_RADIUS + 200e3)
    if abs(calculated_leo_vel - ORBITAL_VELOCITY_LEO) > 100:
        errors.append(f"LEO velocity mismatch: {calculated_leo_vel:.0f} vs {ORBITAL_VELOCITY_LEO}")
    
    # Check Moon SOI
    calculated_soi = calculate_sphere_of_influence(EARTH_MASS, MOON_MASS, MOON_ORBIT_RADIUS)
    if abs(calculated_soi - MOON_SOI_RADIUS) / MOON_SOI_RADIUS > 0.1:  # 10% tolerance
        errors.append(f"Moon SOI mismatch: {calculated_soi/1e6:.1f}e6 vs {MOON_SOI_RADIUS/1e6:.1f}e6 m")
    
    return errors


def main():
    """Test and validate constants module"""
    print("Physical Constants Module")
    print("=" * 30)
    
    print(f"Earth mass: {EARTH_MASS:.2e} kg")
    print(f"Earth radius: {EARTH_RADIUS/1000:.0f} km")
    print(f"Earth escape velocity: {EARTH_ESCAPE_VELOCITY:.0f} m/s")
    print(f"Moon mass: {MOON_MASS:.2e} kg")
    print(f"Moon radius: {MOON_RADIUS/1000:.0f} km")
    print(f"Earth-Moon distance: {MOON_ORBIT_RADIUS/1000:.0f} km")
    
    print(f"\nCalculated values:")
    print(f"Earth escape velocity: {calculate_escape_velocity(EARTH_MASS, EARTH_RADIUS):.0f} m/s")
    print(f"Moon escape velocity: {calculate_escape_velocity(MOON_MASS, MOON_RADIUS):.0f} m/s")
    print(f"LEO orbital velocity: {calculate_orbital_velocity(EARTH_MASS, EARTH_RADIUS + 200e3):.0f} m/s")
    print(f"Moon SOI radius: {calculate_sphere_of_influence(EARTH_MASS, MOON_MASS, MOON_ORBIT_RADIUS)/1e6:.1f} million km")
    
    print(f"\nUnit conversions:")
    print(f"100 km = {km_to_m(100):.0f} m")
    print(f"45 degrees = {deg_to_rad(45):.3f} radians")
    print(f"2 hours = {hours_to_seconds(2):.0f} seconds")
    
    print(f"\nValidation:")
    errors = validate_constants()
    if errors:
        for error in errors:
            print(f"⚠️  {error}")
    else:
        print("✅ All constants validated successfully")


if __name__ == "__main__":
    main()