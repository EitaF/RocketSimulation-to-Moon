import numpy as np

# Constants
R_SOI_MOON_KM = 66100  # Sphere of Influence of the Moon in km

def check_soi_transition(spacecraft_pos_eci, moon_pos_eci):
    """
    Checks if the spacecraft has entered the Moon's Sphere of Influence (SOI).

    Args:
        spacecraft_pos_eci (np.ndarray): Spacecraft position vector in ECI frame (km).
        moon_pos_eci (np.ndarray): Moon position vector in ECI frame (km).

    Returns:
        bool: True if the spacecraft is within the Moon's SOI, False otherwise.
    """
    relative_pos = spacecraft_pos_eci - moon_pos_eci
    distance = np.linalg.norm(relative_pos)
    return distance <= R_SOI_MOON_KM

def convert_to_lunar_frame(spacecraft_state_eci, moon_state_eci):
    """
    Converts the spacecraft's state vector from Earth-centered Inertial (ECI)
    to a Moon-centered Inertial frame.

    Args:
        spacecraft_state_eci (tuple): A tuple (pos_vec, vel_vec) for the spacecraft in ECI.
        moon_state_eci (tuple): A tuple (pos_vec, vel_vec) for the Moon in ECI.

    Returns:
        tuple: A tuple (pos_vec_lci, vel_vec_lci) for the spacecraft in the lunar frame.
    """
    sc_pos_eci, sc_vel_eci = spacecraft_state_eci
    moon_pos_eci, moon_vel_eci = moon_state_eci

    # Position in lunar frame is the relative position vector
    pos_lci = sc_pos_eci - moon_pos_eci

    # Velocity in lunar frame is the relative velocity vector
    vel_lci = sc_vel_eci - moon_vel_eci

    return (pos_lci, vel_lci)
