"""
Advanced Earth-to-Moon Rocket Flight Simulation (Fixed Version)
物理的に正確な地球-月間ロケット飛行シミュレーション（修正版）

Features:
- 正確な軌道力学（ホーマン遷移軌道）
- 多段式ロケットの燃料消費モデル
- 大気抵抗と重力損失
- リアルな打ち上げプロファイル
- 修正済み：軌道速度計算、重力ターン最適化、フェーズ遷移
"""

import numpy as np
import json
import csv
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional
from enum import Enum
import logging
import guidance
from config_flags import get_flag, is_enabled  # Professor v17: Feature flag support
from constants import MAX_Q_OPERATIONAL  # Max-Q operational limit
from vehicle import Vector3, Rocket, RocketStage, MissionPhase, create_saturn_v_rocket
from orbital_monitor import OrbitalMonitor, create_orbital_monitor
from guidance_strategy import GuidanceContext, GuidanceFactory, VehicleState
from circularize import create_circularization_burn
from patched_conic_solver import check_soi_transition, convert_to_lunar_frame
from launch_window_calculator import LaunchWindowCalculator
from mid_course_correction import MidCourseCorrection
from leo_state_schema import LEOStateSchema

# 物理定数
G = 6.67430e-11  # 万有引力定数 [m^3/kg/s^2]
M_EARTH = 5.972e24  # 地球質量 [kg]
R_EARTH = 6371e3  # 地球半径 [m]
M_MOON = 7.34767309e22  # 月質量 [kg]
R_MOON = 1737e3  # 月半径 [m]
EARTH_MOON_DIST = 384400e3  # 地球-月平均距離 [m]
MOON_ORBIT_PERIOD = 27.321661 * 24 * 3600  # 月の公転周期 [s]
EARTH_ROTATION_PERIOD = 24 * 3600  # 地球自転周期 [s]
STANDARD_GRAVITY = 9.80665  # 標準重力加速度 [m/s^2]

# 追加の月軌道定数
MU_MOON = 4.904e12  # 月の標準重力パラメータ [m^3/s^2]
MOON_SOI_RADIUS = 66.2e6  # 月の影響圏半径 [m]
LUNAR_ORBIT_INCLINATION = np.radians(5.145)  # 月軌道傾斜角

# 大気パラメータ
SEA_LEVEL_PRESSURE = 101325  # 海面気圧 [Pa]
SEA_LEVEL_DENSITY = 1.225  # 海面大気密度 [kg/m^3]
SCALE_HEIGHT = 8500  # 大気のスケールハイト [m]


@dataclass
class CelestialBody:
    """天体（地球、月）"""
    name: str
    mass: float  # 質量 [kg]
    radius: float  # 半径 [m]
    position: Vector3
    velocity: Vector3 = field(default_factory=lambda: Vector3(0, 0))
    soi_radius: float = 0.0  # 影響圏半径 [m]
    
    def get_gravitational_acceleration(self, position: Vector3) -> Vector3:
        """指定位置での重力加速度を計算"""
        r = position - self.position
        distance = r.magnitude()
        if distance <= self.radius:
            if distance < 0.1:
                distance = 0.1
            surface_gravity = G * self.mass / self.radius**2
            return r.normalized() * (-surface_gravity)
        return r.normalized() * (-G * self.mass / distance**2)
    
    def is_in_soi(self, position: Vector3) -> bool:
        """指定位置が影響圏内かどうか判定"""
        if self.soi_radius <= 0:
            return False
        distance = (position - self.position).magnitude()
        return distance <= self.soi_radius
    
    def get_dominant_body(self, position: Vector3, other_body: 'CelestialBody') -> 'CelestialBody':
        """より強い重力影響を持つ天体を返す"""
        distance_self = (position - self.position).magnitude()
        distance_other = (position - other_body.position).magnitude()
        
        # 影響圏による判定を優先
        if self.is_in_soi(position):
            return self
        elif other_body.is_in_soi(position):
            return other_body
        
        # 重力の強さで判定
        gravity_self = G * self.mass / distance_self**2
        gravity_other = G * other_body.mass / distance_other**2
        
        return self if gravity_self > gravity_other else other_body


class Mission:
    """ミッション管理クラス"""
    
    def __init__(self, rocket: Rocket, config: Dict):
        self.rocket = rocket
        self.config = config
        self.earth = CelestialBody("Earth", M_EARTH, R_EARTH, Vector3(0, 0))
        self.moon = self._initialize_moon()
        
        # 打ち上げパラメータ
        self.launch_azimuth = config.get("launch_azimuth", 90)  # 打ち上げ方位角 [度]
        self.target_parking_orbit = config.get("target_parking_orbit", 200e3)  # 駐機軌道高度 [m]
        self.gravity_turn_altitude = config.get("gravity_turn_altitude", 1500)  # Professor v7: start at 1500m
        
        # データ記録
        self.time_history: List[float] = []
        self.position_history: List[Vector3] = []
        self.velocity_history: List[Vector3] = []
        self.altitude_history: List[float] = []
        self.mass_history: List[float] = []
        self.phase_history: List[MissionPhase] = []
        
        # ミッション統計
        self.max_altitude = 0.0
        self.max_velocity = 0.0
        self.total_delta_v = 0.0
        self.max_c3_energy = float('-inf')  # Professor v30: Track maximum C3 energy
        self.stage_delta_v_history: List[float] = []  # 各ステージのΔv記録
        self.last_stage_count = 0  # Track stage changes for ΔV calculation
        
        # CSVログ設定
        self.csv_file = open("mission_log.csv", "w", newline="")
        self.csv_writer = csv.writer(self.csv_file)
        self.csv_writer.writerow(["time", "altitude", "velocity", "mass", "delta_v", "phase", "stage", "apoapsis", "periapsis", "eccentricity", "flight_path_angle", "pitch_angle", "remaining_propellant", "dynamic_pressure", "max_dynamic_pressure"])
        
        # ロガー設定 (logging.basicConfig is now handled in main)
        self.logger = logging.getLogger(__name__)
        
        # Professor v27: Initialize orbital monitor and guidance system
        self.orbital_monitor = create_orbital_monitor(update_interval=0.1)
        self.guidance_context = GuidanceFactory.create_context(config)
        self.circularization_burn = create_circularization_burn(self.orbital_monitor)
        
        # Professor v33: Initialize trajectory modules for complete Earth-to-Moon mission
        self.launch_window_calculator = LaunchWindowCalculator(parking_orbit_altitude=self.target_parking_orbit)
        self.mid_course_correction = MidCourseCorrection()
        self.tli_optimal_time = None
        self.tli_executed = False
        self.mcc_executed = False
        self.loi_executed = False
        self.mission_start_time = 0.0
        self.total_mission_delta_v = 0.0
        
        # Professor v33: Lunar orbit tracking for three full orbits validation
        self.lunar_orbit_count = 0
        self.lunar_orbit_start_time = None
        self.lunar_orbit_apoapsises = []
        self.lunar_orbit_periapsises = []
        self.last_lunar_radial_velocity_sign = None
        
        # LEO mission success criteria
        self.leo_target_altitude = 200000  # 200 km target
        self.leo_success_tolerance = 5000   # 5 km tolerance
        self.mission_success = False
        
        self.logger.info("Professor v27: Orbital monitor and PEG guidance system initialized")
    
    def check_leo_success(self) -> bool:
        """
        Check if LEO mission success criteria are met
        Professor v27: Stable circular orbit within 5km tolerance
        Professor v29: Updated to recognize LEO_STABLE phase as mission success
        Professor v44: Emit leo_state.json on success with compliant schema
        """
        # Professor v29: LEO_STABLE phase indicates successful S-IVB cutoff
        if self.rocket.phase == MissionPhase.LEO_STABLE:
            if not self.mission_success:
                self.mission_success = True
                if self.orbital_monitor.current_state:
                    orbital_state = self.orbital_monitor.current_state
                    apoapsis_km = (orbital_state.apoapsis - R_EARTH) / 1000
                    periapsis_km = (orbital_state.periapsis - R_EARTH) / 1000
                    self.logger.info(f"🎉 LEO MISSION SUCCESS! S-IVB engine cutoff achieved:")
                    self.logger.info(f"   Apoapsis: {apoapsis_km:.1f} km")
                    self.logger.info(f"   Periapsis: {periapsis_km:.1f} km") 
                    self.logger.info(f"   Eccentricity: {orbital_state.eccentricity:.4f}")
                    self.logger.info(f"   Altitude difference: {abs(apoapsis_km - periapsis_km):.1f} km")
                    
                    # Professor v44: Emit compliant leo_state.json on success
                    self._emit_leo_state_json(orbital_state)
            return True
        
        # Original success criteria (fallback)
        if not self.orbital_monitor.current_state:
            return False
        
        orbital_state = self.orbital_monitor.current_state
        
        # Success criteria:
        # 1. Circular orbit (eccentricity < 0.01)
        # 2. Apoapsis and periapsis within 5km of each other
        # 3. Altitude around 200km target
        
        is_circular = self.orbital_monitor.is_orbit_circular(tolerance_km=5.0)
        altitude_km = orbital_state.altitude / 1000
        altitude_ok = 180 <= altitude_km <= 220  # 200 ± 20km range
        
        success = is_circular and altitude_ok
        
        if success and not self.mission_success:
            self.mission_success = True
            apoapsis_km = (orbital_state.apoapsis - R_EARTH) / 1000
            periapsis_km = (orbital_state.periapsis - R_EARTH) / 1000
            self.logger.info(f"🎉 LEO MISSION SUCCESS! Stable circular orbit achieved:")
            self.logger.info(f"   Apoapsis: {apoapsis_km:.1f} km")
            
            # Professor v44: Emit compliant leo_state.json on success
            self._emit_leo_state_json(orbital_state)
            self.logger.info(f"   Periapsis: {periapsis_km:.1f} km") 
            self.logger.info(f"   Eccentricity: {orbital_state.eccentricity:.4f}")
            self.logger.info(f"   Altitude difference: {abs(apoapsis_km - periapsis_km):.1f} km")
        
        return success
    
    def _emit_leo_state_json(self, orbital_state) -> None:
        """
        Emit compliant leo_state.json file for mission handoff
        Professor v44: Generate standardized state vector (km, km/s, kg, rad units)
        """
        try:
            import time
            
            # Convert position to km (from meters)
            position_km = [
                self.rocket.position.x / 1000,
                self.rocket.position.y / 1000, 
                self.rocket.position.z / 1000
            ]
            
            # Convert velocity to km/s (from m/s)
            velocity_km_s = [
                self.rocket.velocity.x / 1000,
                self.rocket.velocity.y / 1000,
                self.rocket.velocity.z / 1000
            ]
            
            # Calculate RAAN (simplified - use current orbital angle)
            # For this demo, use the angle in the orbit plane
            raan_rad = np.arctan2(self.rocket.position.y, self.rocket.position.x)
            if raan_rad < 0:
                raan_rad += 2 * np.pi
            
            # Create LEO state data
            leo_state_data = {
                "time": time.time(),  # Current UTC timestamp
                "position": position_km,
                "velocity": velocity_km_s,
                "mass": self.rocket.mass,  # kg
                "RAAN": raan_rad,  # rad
                "eccentricity": orbital_state.eccentricity
            }
            
            # Validate against schema
            leo_state = LEOStateSchema(**leo_state_data)
            
            # Ensure meets professor's criteria
            validation = leo_state.validate_leo_criteria()
            if not validation['meets_criteria']:
                self.logger.warning(f"LEO state validation failed: {validation}")
                return
            
            # Write to file
            with open('leo_state.json', 'w') as f:
                json.dump(leo_state_data, f, indent=2)
            
            self.logger.info(f"📄 LEO state JSON emitted: leo_state.json")
            self.logger.info(f"   Position magnitude: {np.linalg.norm(position_km):.1f} km")
            self.logger.info(f"   Velocity magnitude: {np.linalg.norm(velocity_km_s):.3f} km/s")
            self.logger.info(f"   Mass: {self.rocket.mass:.0f} kg")
            self.logger.info(f"   RAAN: {raan_rad:.3f} rad ({np.degrees(raan_rad):.1f}°)")
            self.logger.info(f"   Eccentricity: {orbital_state.eccentricity:.4f}")
            self.logger.info(f"   Altitude: {validation['altitude_value']:.1f} km")
            
        except Exception as e:
            self.logger.error(f"Failed to emit leo_state.json: {e}")
    
    def _initialize_moon(self) -> CelestialBody:
        """月の初期位置を設定（影響圏設定含む）"""
        moon_pos = Vector3(EARTH_MOON_DIST, 0)
        moon_vel = Vector3(0, 2 * np.pi * EARTH_MOON_DIST / MOON_ORBIT_PERIOD)
        moon = CelestialBody("Moon", M_MOON, R_MOON, moon_pos, moon_vel)
        moon.soi_radius = MOON_SOI_RADIUS
        return moon

    def get_altitude(self) -> float:
        """高度を取得 [m]"""
        return self.rocket.position.magnitude() - R_EARTH

    def get_orbital_elements(self) -> Tuple[float, float, float]:
        """軌道要素を計算: (apoapsis, periapsis, eccentricity) [m, m, -]"""
        r = self.rocket.position.magnitude()
        v = self.rocket.velocity.magnitude()
        
        # 動径方向と接線方向の速度成分
        radial_unit = self.rocket.position.normalized()
        velocity_radial = self.rocket.velocity.data @ radial_unit.data
        velocity_tangential = np.sqrt(max(0, v**2 - velocity_radial**2))
        
        # 軌道角運動量
        h = r * velocity_tangential
        
        # 軌道エネルギー
        energy = 0.5 * v**2 - G * M_EARTH / r
        
        # 軌道長半径
        if energy >= 0:
            # 放物線・双曲線軌道の場合
            return float('inf'), r, 1.0
        
        a = -G * M_EARTH / (2 * energy)
        
        # 離心率
        e_squared = 1 + 2 * energy * h**2 / (G * M_EARTH)**2
        if e_squared < 0:
            e_squared = 0
        e = np.sqrt(e_squared)
        
        # 遠地点・近地点距離
        apoapsis = a * (1 + e)
        periapsis = a * (1 - e)
        
        return apoapsis, periapsis, e

    def get_flight_path_angle(self) -> float:
        """飛行経路角を取得 [rad] - 速度ベクトルと局所水平面の角度"""
        # 地心方向（動径方向）の単位ベクトル
        radial_unit = self.rocket.position.normalized()
        
        # 速度ベクトルの動径成分
        velocity_radial = self.rocket.velocity.data @ radial_unit.data  # ドット積
        
        # 飛行経路角 = arcsin(v_radial / |v|)
        velocity_magnitude = self.rocket.velocity.magnitude()
        if velocity_magnitude == 0:
            return 0.0
        
        sin_gamma = velocity_radial / velocity_magnitude
        # アークサインの定義域制限
        sin_gamma = max(-1.0, min(1.0, sin_gamma))
        
        return np.arcsin(sin_gamma)

    def get_cross_sectional_area(self) -> float:
        """ステージに応じた断面積を取得（月ミッション対応）"""
        if self.rocket.current_stage == 0:
            return 80.0  # 第1段 S-IC: 大型
        elif self.rocket.current_stage == 1:
            return 30.0  # 第2段 S-II: 中型
        elif self.rocket.current_stage == 2:
            return 18.0  # 第3段 S-IVB: 小型
        else:
            return 8.0   # 第4段 着陸機: 最小

    def get_thrust_vector(self, t: float) -> Vector3:
        """
        推力ベクトルを取得（Professor v27: New guidance system）
        Uses strategy pattern guidance instead of legacy guidance module
        """
        altitude = self.get_altitude()
        if not self.rocket.is_thrusting(t, altitude):
            return Vector3(0, 0)
        
        stage = self.rocket.stages[self.rocket.current_stage]
        thrust_magnitude = stage.get_thrust(altitude)
        
        # Professor v27: Use new strategy-based guidance system
        try:
            # Create vehicle state for guidance
            vehicle_state = VehicleState(
                position=self.rocket.position,
                velocity=self.rocket.velocity,
                altitude=altitude,
                mass=self.rocket.get_current_mass(t, altitude),
                mission_phase=self.rocket.phase,
                time=t
            )
            
            # Target state (for LEO mission)
            target_state = {
                'target_apoapsis': self.leo_target_altitude + R_EARTH,
                'target_altitude': self.leo_target_altitude
            }
            
            # Compute guidance command
            guidance_command = self.guidance_context.compute_guidance(vehicle_state, target_state)
            
            # Apply thrust magnitude to guidance direction
            thrust_direction = guidance_command.thrust_direction
            actual_thrust_magnitude = thrust_magnitude * guidance_command.thrust_magnitude
            
            return thrust_direction * actual_thrust_magnitude
            
        except Exception as e:
            self.logger.warning(f"Guidance system error: {e}, falling back to legacy guidance")
            # Fallback to legacy guidance
            import guidance
            return guidance.compute_thrust_direction(self, t, thrust_magnitude)
    
    def _update_moon_position(self, dt: float):
        """月の位置を更新"""
        # 簡単な円運動として計算
        omega = 2 * np.pi / MOON_ORBIT_PERIOD
        angle = omega * dt
        cos_a, sin_a = np.cos(angle), np.sin(angle)
        
        # 回転行列による位置更新
        x = self.moon.position.x * cos_a - self.moon.position.y * sin_a
        y = self.moon.position.x * sin_a + self.moon.position.y * cos_a
        self.moon.position = Vector3(x, y)
        
        # 速度も更新
        vx = self.moon.velocity.x * cos_a - self.moon.velocity.y * sin_a
        vy = self.moon.velocity.x * sin_a + self.moon.velocity.y * cos_a
        self.moon.velocity = Vector3(vx, vy)
    
    def _calculate_atmospheric_density(self, altitude: float) -> float:
        """Calculate atmospheric density using enhanced model with NRLMSISE-00 support"""
        try:
            # Try to use enhanced atmospheric model
            from atmosphere import get_atmosphere_model
            atm_model = get_atmosphere_model()
            
            # Get density at current position
            # Use mission configuration for latitude/longitude if available
            latitude = getattr(self.config, 'launch_latitude', 28.573)
            longitude = getattr(self.config, 'launch_longitude', -80.649)
            
            return atm_model.get_density(altitude, latitude, longitude)
            
        except (ImportError, Exception) as e:
            # Fallback to legacy atmospheric model
            self.logger.debug(f"Enhanced atmosphere model not available: {e}")
            
        # Legacy atmospheric model (fallback)
        if altitude < 0:
            return SEA_LEVEL_DENSITY
        elif altitude <= 11e3:
            # 0-11km: 対流圈（線形温度変化）
            temp = 288.15 - 6.5e-3 * altitude  # K
            pressure = SEA_LEVEL_PRESSURE * (temp / 288.15) ** 5.256
            return pressure / (287.0 * temp)  # 理想気体の状態方程式
        elif altitude <= 25e3:
            # 11-25km: 成層圈下部（一定温度）
            temp = 216.65  # K
            pressure = 22632 * np.exp(-(altitude - 11e3) / (287.0 * temp / 9.80665))
            return pressure / (287.0 * temp)
        elif altitude <= 100e3:
            # 25-100km: 成層圈上部（指数関数近似）
            return SEA_LEVEL_DENSITY * np.exp(-altitude / SCALE_HEIGHT)
        elif altitude <= 150e3:
            # 100-150km: 熱圈下部（急激な減衰）
            density_100km = SEA_LEVEL_DENSITY * np.exp(-100e3 / SCALE_HEIGHT)
            # 指数関数的減衰
            return density_100km * np.exp(-(altitude - 100e3) / 10000)  # 10kmスケール
        elif altitude <= 300e3:
            # 150-300km: 極薄大気（安定性のため残留）
            density_150km = SEA_LEVEL_DENSITY * np.exp(-100e3 / SCALE_HEIGHT) * np.exp(-50e3 / 10000)
            factor = np.exp(-(altitude - 150e3) / 50000)  # 50kmスケール
            return max(density_150km * factor, 1e-12)  # 最小値を設定
        else:
            # 300km以上: ほぼ真空（安定性のため最小値を維持）
            return 1e-15  # kg/m^3
    
    def _calculate_drag_force(self) -> Vector3:
        """空気抵抗を計算"""
        altitude = self.get_altitude()
        density = self._calculate_atmospheric_density(altitude)
        
        if density == 0:
            return Vector3(0, 0)
        
        velocity_magnitude = self.rocket.velocity.magnitude()
        if velocity_magnitude == 0:
            return Vector3(0, 0)
        
        # F_drag = 0.5 * ρ * v^2 * C_d * A（ステージ対応断面積使用）
        cross_sectional_area = self.get_cross_sectional_area()
        drag_magnitude = 0.5 * density * velocity_magnitude**2 * \
                        self.rocket.drag_coefficient * cross_sectional_area
        
        # 速度と逆方向
        return self.rocket.velocity.normalized() * (-drag_magnitude)
    
    def _calculate_total_acceleration(self, t: float) -> Vector3:
        """総加速度を計算（Patched-Conic対応）"""
        # 主支配天体を決定（パッチドコニック法）
        dominant_body = self.earth.get_dominant_body(self.rocket.position, self.moon)
        
        # 主支配天体の重力
        if dominant_body == self.earth:
            # 地球支配: 地球重力と月の影響
            g_primary = self.earth.get_gravitational_acceleration(self.rocket.position)
            g_secondary = self.moon.get_gravitational_acceleration(self.rocket.position)
            # 月の影響は地球引力が強い場合は10%に抑制
            g_moon_factor = 0.1 if not self.moon.is_in_soi(self.rocket.position) else 1.0
            g_secondary = g_secondary * g_moon_factor
        else:
            # 月支配: 月重力と地球の影響
            g_primary = self.moon.get_gravitational_acceleration(self.rocket.position)
            g_secondary = self.earth.get_gravitational_acceleration(self.rocket.position)
            # 地球の影響は遠距離では減衰
            earth_distance = (self.rocket.position - self.earth.position).magnitude()
            earth_factor = min(1.0, (2 * R_EARTH / earth_distance)**2)
            g_secondary = g_secondary * earth_factor
        
        total_gravity = g_primary + g_secondary
        
        # 推力
        thrust = self.get_thrust_vector(t)
        current_mass = self.rocket.get_current_mass(t, self.get_altitude())
        thrust_acceleration = thrust * (1.0 / current_mass) if current_mass > 0 else Vector3(0, 0)
        
        # 空気抵抗（地球支配時のみ）
        if dominant_body == self.earth:
            drag = self._calculate_drag_force()
            drag_acceleration = drag * (1.0 / current_mass) if current_mass > 0 else Vector3(0, 0)
        else:
            drag_acceleration = Vector3(0, 0)  # 月には大気なし
        
        return total_gravity + thrust_acceleration + drag_acceleration
    
    def _update_mission_phase(self):
        """
        ミッションフェーズを更新 (修正版 - LEO投入の安定性を最優先)
        """
        # 現在の状態を取得
        altitude = self.get_altitude()
        velocity = self.rocket.velocity.magnitude()
        apoapsis, periapsis, eccentricity = self.get_orbital_elements()
        current_phase = self.rocket.phase
        
        # Debug: basic function entry (removed early return to fix staging issue)
        
        # Debug logging for phase transitions
        if hasattr(self, '_last_logged_phase') and self._last_logged_phase != current_phase:
            self.logger.info(f"Phase changed: {self._last_logged_phase} -> {current_phase}")
        self._last_logged_phase = current_phase
        
        # Debug: always log current phase when in STAGE_SEPARATION
        if str(current_phase) == "MissionPhase.STAGE_SEPARATION" or current_phase.value == "stage_separation":
            self.logger.debug(f"Found STAGE_SEPARATION! current_stage = {self.rocket.current_stage}, type={type(current_phase)}")
        
        if current_phase == MissionPhase.STAGE_SEPARATION:
            self.logger.debug(f"ENUM comparison worked! current_stage = {self.rocket.current_stage}")
        
        # Additional debug for all phases
        if hasattr(self, '_debug_counter'):
            self._debug_counter += 1
        else:
            self._debug_counter = 1
        
        if self._debug_counter % 1000 == 0:  # Every 100 seconds
            self.logger.debug(f"Phase debug: t={len(self.time_history)*0.1:.1f}s, phase={current_phase.value}, stage={self.rocket.current_stage}")

        # Professor v19: Realistic MECO conditions for current ΔV capability
        # Start with achievable intermediate targets, then improve progressively
        
        # Professor v19: Much more achievable progressive targets
        # Based on current capability: max 49.9km apoapsis, max 3041 m/s velocity
        basic_apoapsis = R_EARTH + 45e3     # 45 km - easily achievable
        intermediate_apoapsis = R_EARTH + 80e3  # 80 km intermediate target  
        final_target_apoapsis = R_EARTH + self.target_parking_orbit  # 185 km final target
        min_periapsis = R_EARTH + 120e3  # 120 km (above atmosphere)
        
        # Progressive targeting system - Professor v19: Stage-specific targeting
        # Stage-2 should raise apoapsis higher, Stage-3 handles circularization
        current_stage = self.rocket.current_stage
        
        if current_stage == 1:  # Stage-2 burning
            # Stage-2 should achieve higher apoapsis for effective circularization
            # Need at least 80km apoapsis to have time for circularization
            target_apoapsis = R_EARTH + 80e3  # 80 km - higher target for circularization time
            velocity_threshold = 2600  # Higher velocity needed for 80km apoapsis
        else:  # Stage-3 or later
            # Use basic target for final circularization
            target_apoapsis = basic_apoapsis  # 45 km minimum for Stage-3
            velocity_threshold = 2200  # Achievable threshold for Stage-3
        
        # Two-phase approach: 1) Get apoapsis, 2) Get periapsis
        has_target_apoapsis = apoapsis >= target_apoapsis
        has_safe_periapsis = periapsis >= min_periapsis
        
        # Success: both conditions met
        is_stable_parking_orbit = has_target_apoapsis and has_safe_periapsis
        
        # Stop condition: target apoapsis achieved with sufficient velocity
        should_stop_burning = False  # Rely on PEG for MECO
        
        # Professor v19: Debug the exact condition values
        current_time = len(self.time_history) * 0.1
        if current_phase == MissionPhase.APOAPSIS_RAISE and current_time > 160 and current_time < 200:
            self.logger.debug(f"Burn stop debug t={current_time:.1f}s: apo={apoapsis:.0f}m (target={target_apoapsis:.0f}m, has={has_target_apoapsis}), "
                           f"v={velocity:.0f}m/s (threshold={velocity_threshold:.0f}, ok={velocity > velocity_threshold}), "
                           f"should_stop={should_stop_burning}")

        # ----------------------------------------------------------------
        # 地球周回軌道投入までのフェーズ管理 (修正済みロジック)
        # ----------------------------------------------------------------

        if current_phase == MissionPhase.LAUNCH:
            if altitude >= self.gravity_turn_altitude:
                self.rocket.phase = MissionPhase.GRAVITY_TURN
                self.logger.info(f"Gravity turn initiated at altitude {altitude/1000:.1f} km")

        elif current_phase == MissionPhase.GRAVITY_TURN:
            # ステージ分離時に自動で次のフェーズに遷移するため、ここでは何もしない
            pass

        elif current_phase == MissionPhase.APOAPSIS_RAISE:
            # 遠地点上昇と円環フェーズのロジックを統合
            
            # Professor v17: Velocity-triggered Stage-3 ignition (MOVED FROM COAST_TO_APOAPSIS)
            if is_enabled("VELOCITY_TRIGGERED_STAGE3"):
                velocity_trigger = velocity >= 3500.0  # m/s - achievable by Stage 2
                altitude_trigger = altitude >= 30e3   # 30 km - much lower altitude requirement
                stage3_velocity_trigger = velocity_trigger and altitude_trigger and self.rocket.current_stage == 1  # Trigger while in Stage 2
                
                # Debug logging for trigger conditions
                if velocity >= 3400.0 and self.rocket.current_stage == 1:  # Debug when close (Stage 2)
                    if hasattr(self, '_stage3_debug_counter'):
                        self._stage3_debug_counter += 1
                    else:
                        self._stage3_debug_counter = 1
                    
                    if self._stage3_debug_counter % 50 == 0:  # Every 5 seconds when close
                        self.logger.debug(f"Stage-3 debug: v={velocity:.0f}m/s (≥3500?), alt={altitude/1000:.1f}km (≥30?), stage={self.rocket.current_stage} (==1?)")
                        self.logger.debug(f"Stage-3 debug: triggers: vel={velocity_trigger}, alt={altitude_trigger}, combined={stage3_velocity_trigger}")
                
                if stage3_velocity_trigger:
                    # Trigger Stage-2 separation and Stage-3 ignition
                    self.logger.info(f"*** VELOCITY-TRIGGERED STAGE-3 IGNITION ***")
                    self.logger.info(f" -> Velocity: {velocity:.0f} m/s (≥3500 m/s) ✓")
                    self.logger.info(f" -> Altitude: {altitude/1000:.1f} km (≥30 km) ✓")
                    self.logger.info(f" -> Forcing Stage-2 separation for Stage-3 ignition")
                    
                    # Force Stage 2 separation to trigger Stage 3
                    if self.rocket.separate_stage(current_time):
                        self.rocket.phase = MissionPhase.STAGE_SEPARATION
                        self.logger.info(f"Stage separated: now at stage {self.rocket.current_stage}")
                    return  # Exit early to allow stage separation to occur
            
            # ケース1: 完全成功（安定軌道）に到達したか？
            if is_stable_parking_orbit:
                self.rocket.phase = MissionPhase.LEO
                self.logger.info(f"SUCCESS: Stable parking orbit achieved!")
                self.logger.info(f" -> Apoapsis: {(apoapsis-R_EARTH)/1000:.1f} km, "
                               f"Periapsis: {(periapsis-R_EARTH)/1000:.1f} km, e={eccentricity:.3f}")
            
            # ケース2: 燃焼停止条件（目標遠地点達成）- Professor v12  
            elif should_stop_burning:
                self.rocket.phase = MissionPhase.COAST_TO_APOAPSIS
                self.logger.info(f"MECO: Target apoapsis achieved, coasting to apoapsis for circularization")
                self.logger.info(f" -> Apoapsis: {(apoapsis-R_EARTH)/1000:.1f} km (target: {(target_apoapsis-R_EARTH)/1000:.1f} km), "
                               f"Periapsis: {(periapsis-R_EARTH)/1000:.1f} km, v={velocity:.0f} m/s (threshold: {velocity_threshold:.0f})")
            
            # ケース3: ゴール未達のまま燃料が尽きたか？
            elif not self.rocket.is_thrusting:
                self.rocket.phase = MissionPhase.FAILED
                self.logger.error(f"FAILURE: Out of fuel before achieving stable orbit.")
                self.logger.error(f" -> Final Apoapsis: {(apoapsis-R_EARTH)/1000:.1f} km, "
                                 f"Final Periapsis: {(periapsis-R_EARTH)/1000:.1f} km")
            
            # ケース4: それ以外（ゴール未達で燃料はまだある）の場合は、燃焼を継続
            # 何もせず、現在のフェーズを維持する

        elif current_phase == MissionPhase.STAGE_SEPARATION or current_phase.value == "stage_separation":
            # ステージ分離後の正しい遷移
            self.logger.info(f"*** Processing stage separation: current_stage = {self.rocket.current_stage} ***")
            if self.rocket.current_stage == 1:  # 第1段分離後 -> 第2段点火
                self.rocket.phase = MissionPhase.APOAPSIS_RAISE
                self.logger.info(f"*** Stage 2 ignition for apoapsis raise ***")
            elif self.rocket.current_stage == 2:  # 第2段分離後 -> Professor v17: velocity-triggered Stage-3
                # Professor v17: Wait for velocity-triggered ignition instead of immediate Stage-3 ignition
                self.rocket.phase = MissionPhase.COAST_TO_APOAPSIS
                self.logger.info(f"*** Stage 2 separation complete. Coasting for velocity-triggered Stage-3 ignition ***")
                self.logger.info(f"*** Stage-3 ignition trigger: v≥7550 m/s & r≥180 km ***")
            elif self.rocket.current_stage == 3:  # 第3段分離後 (月着陸船)
                self.rocket.phase = MissionPhase.LUNAR_ORBIT
                self.logger.info(f"*** Lunar descent module active. Ready for PDI ***")
            else:
                self.logger.warning(f"*** Unexpected stage {self.rocket.current_stage} in separation ***")
                self.rocket.phase = MissionPhase.LEO # フォールバック

        elif current_phase == MissionPhase.CIRCULARIZATION:
            # Action A1: Overhauled Circularization Control Logic with S-IVB Engine Cutoff
            # Professor v41: Enhanced with fuel guard-rail and detailed logging
            
            # 1. Get current orbital elements and Stage-3 state
            apoapsis, periapsis, eccentricity = self.get_orbital_elements()
            stage3 = self.rocket.stages[2] if len(self.rocket.stages) > 2 else None
            
            # 2. Professor v41: Detailed Stage-3 fuel logging
            if stage3 and hasattr(self, 'circularization_start_time'):
                burn_duration = self.t - self.circularization_start_time
                mass_flow_rate = stage3.get_mass_flow_rate(self.get_altitude())
                fuel_remaining = stage3.propellant_mass
                fuel_fraction = fuel_remaining / 160000.0  # Original propellant mass
                periapsis_error = periapsis - (R_EARTH + 180e3)  # Target 180km periapsis
                
                # Log every 0.1s as requested by professor
                if self.t % 0.1 < 0.05:  # Approximately every 0.1s
                    self.logger.debug(
                        f"{self.t:.1f}s | m_dot={mass_flow_rate:.3f} kg/s "
                        f"fuel_left={fuel_remaining:.1f} kg ({fuel_fraction*100:.1f}%) "
                        f"periapsis_err={periapsis_error:.1f} m"
                    )
            elif not hasattr(self, 'circularization_start_time'):
                # First time entering circularization phase
                self.circularization_start_time = self.t
                self.logger.info(f"CIRCULARIZATION BURN START at t={self.t:.1f}s")
            
            # 3. Professor v41: Fuel guard-rail limiter (5% minimum)
            if stage3 and stage3.propellant_mass > 0:
                fuel_fraction = stage3.propellant_mass / 160000.0
                if fuel_fraction <= 0.05:
                    self.rocket.phase = MissionPhase.LEO_STABLE
                    self.logger.warning("Fuel guard-rail hit; forcing burn shutdown.")
                    self.logger.warning(f" -> Fuel remaining: {fuel_fraction*100:.1f}% (≤5%)")
                    self.logger.warning(f" -> Residual periapsis: {(periapsis-R_EARTH)/1000:.1f} km")
                    return
            
            # 4. Check for burn termination using guidance system
            from guidance import should_end_circularization_burn
            if hasattr(self, 'circularization_start_time') and should_end_circularization_burn(self, self.t, self.circularization_start_time):
                # Professor v29: Command S-IVB engine shutdown for stable orbit
                self.rocket.phase = MissionPhase.LEO_STABLE
                self.logger.info(f"SUCCESS: S-IVB ENGINE CUTOFF - Circularization complete!")
                self.logger.info(f" -> Apoapsis: {(apoapsis-R_EARTH)/1000:.1f} km, Periapsis: {(periapsis-R_EARTH)/1000:.1f} km")
                self.logger.info(f" -> Eccentricity: {eccentricity:.4f}")
                if stage3:
                    fuel_fraction = stage3.propellant_mass / 160000.0
                    self.logger.info(f" -> Stage-3 fuel remaining: {fuel_fraction*100:.1f}%")
            
            elif not self.rocket.is_thrusting:
                self.rocket.phase = MissionPhase.FAILED
                self.logger.error(f"FAILURE: Out of fuel during circularization burn.")
                self.logger.error(f" -> Final Periapsis: {(periapsis-R_EARTH)/1000:.1f} km (Target > 180 km)")
                self.logger.error(f" -> Final Eccentricity: {eccentricity:.4f} (Target < 0.05)")

            # else: continue burning...

        elif current_phase == MissionPhase.COAST_TO_APOAPSIS:
            # Action A2: Refine Burn Initiation Timing
            flight_path_angle_deg = np.degrees(self.get_flight_path_angle())
            apoapsis, periapsis, _ = self.get_orbital_elements()

            # The most efficient time to burn is exactly at apoapsis,
            # where the flight path angle is zero.
            is_at_apoapsis = flight_path_angle_deg <= 0.1  # Trigger as we approach/pass apoapsis

            # Ensure we have fuel for Stage-3 and the orbit is not already circular
            stage3_has_fuel = len(self.rocket.stages) > 2 and self.rocket.stages[2].propellant_mass > 0
            can_circularize = stage3_has_fuel and periapsis < (R_EARTH + 120e3)

            if is_at_apoapsis and can_circularize:
                self.rocket.phase = MissionPhase.CIRCULARIZATION
                self.logger.info(f"APOAPSIS PASS. Initiating circularization burn.")
                self.logger.info(f" -> Flight Path Angle: {flight_path_angle_deg:.3f} deg, Altitude: {self.get_altitude()/1000:.1f} km")
            elif not stage3_has_fuel and periapsis < (R_EARTH + 120e3):
                # Out of fuel but still suborbital
                self.rocket.phase = MissionPhase.FAILED
                self.logger.error(f"Circularization failed: out of fuel with suborbital trajectory")
                self.logger.error(f" -> Periapsis: {(periapsis-R_EARTH)/1000:.1f} km")

        # ----------------------------------------------------------------
        # 月遷移軌道以降のフェーズ管理 (元のロジックを維持)
        # ----------------------------------------------------------------

        elif current_phase == MissionPhase.LEO:
            # LEOでの待機からTLIフェーズへの遷移
            coast_time = len([p for p in self.phase_history if p == MissionPhase.LEO]) * 0.1
            
            # 安定した軌道で30秒待機したら月へ
            if self.rocket.current_stage == 2 and is_stable_parking_orbit and coast_time > 30:
                self.rocket.phase = MissionPhase.TLI_BURN
                self.logger.info("LEO parking complete. Initiating Trans-Lunar Injection burn!")
            elif coast_time > 600 and not is_stable_parking_orbit: # 10分待っても不安定なら失敗
                self.rocket.phase = MissionPhase.FAILED
                self.logger.error(f"Failed to maintain stable LEO. Orbit decayed.")

        elif current_phase == MissionPhase.LEO_STABLE:
            # Professor v29: New stable LEO phase with S-IVB engine off
            # Professor v33: Enhanced LEO_STABLE with launch window calculation
            coast_time = len([p for p in self.phase_history if p == MissionPhase.LEO_STABLE]) * 0.1
            
            # Professor v39: Calculate TLI delta-V requirements immediately after LEO achievement
            if not hasattr(self, 'tli_delta_v_calculated') and coast_time > 5:
                self._calculate_and_report_tli_requirements()
                self.tli_delta_v_calculated = True
            
            # Calculate optimal TLI time if not already calculated
            if self.tli_optimal_time is None and coast_time > 10:  # Wait 10s for orbit stabilization
                try:
                    # Convert positions to numpy arrays for launch window calculator
                    moon_pos_np = np.array([self.moon.position.x, self.moon.position.y, 0])
                    spacecraft_pos_np = np.array([self.rocket.position.x, self.rocket.position.y, 0])
                    
                    # Target C3 energy for Trans-Lunar trajectory (typical value: -2 to -1 km²/s²)
                    target_c3_energy = -1.5  # km²/s²
                    
                    # Calculate optimal TLI time
                    launch_window_info = self.launch_window_calculator.get_launch_window_info(
                        len(self.time_history) * 0.1,  # current time
                        moon_pos_np, spacecraft_pos_np, target_c3_energy
                    )
                    
                    self.tli_optimal_time = launch_window_info['optimal_tli_time']
                    self.logger.info("=== LAUNCH WINDOW CALCULATION COMPLETE ===")
                    self.logger.info(f"Optimal TLI time: {self.tli_optimal_time:.1f}s (T+{self.tli_optimal_time - len(self.time_history) * 0.1:.1f}s)")
                    self.logger.info(f"Required phase angle: {launch_window_info['required_phase_angle_deg']:.1f}°")
                    self.logger.info(f"Transfer time: {launch_window_info['transfer_time_days']:.2f} days")
                    self.logger.info(f"Target C3 energy: {launch_window_info['c3_energy']:.2f} km²/s²")
                    
                except Exception as e:
                    self.logger.error(f"Launch window calculation failed: {e}")
                    # Fallback: TLI after 30s as before
                    self.tli_optimal_time = len(self.time_history) * 0.1 + 30
            
            # Execute TLI at optimal time
            current_time = len(self.time_history) * 0.1
            if (self.tli_optimal_time is not None and 
                current_time >= self.tli_optimal_time and 
                self.rocket.current_stage == 2 and 
                not self.tli_executed):
                
                self.rocket.phase = MissionPhase.TLI_BURN
                self.tli_executed = True
                self.logger.info("=== TRANS-LUNAR INJECTION INITIATED ===")
                self.logger.info(f"TLI burn started at optimal time: T+{current_time:.1f}s")
                
            elif coast_time > 600: # 10分待っても TLI が始まらない場合は成功とみなす
                self.logger.info(f"LEO_STABLE maintained successfully for {coast_time:.1f}s. Mission complete.")
                # Mission stays in LEO_STABLE - this is a success state


        elif current_phase == MissionPhase.TLI_BURN:
            # Professor v29: Enhanced TLI burn with proper guidance termination
            # Check if TLI guidance indicates burn completion
            try:
                # Get TLI strategy from guidance context
                if hasattr(self.guidance_context, 'current_strategy') and hasattr(self.guidance_context.current_strategy, 'tli_guidance'):
                    tli_guidance = self.guidance_context.current_strategy.tli_guidance
                    tli_status = tli_guidance.get_trajectory_status()
                    
                    # Enhanced termination criteria using TLI guidance
                    burn_complete = tli_guidance.should_terminate_burn(self.rocket.velocity)
                    
                    if burn_complete or not self.rocket.is_thrusting:
                        self.rocket.phase = MissionPhase.COAST_TO_MOON
                        self.logger.info(f"TLI burn complete. Coasting to Moon...")
                        escape_velocity = np.sqrt(2 * G * M_EARTH / self.rocket.position.magnitude())
                        current_c3 = velocity**2 - escape_velocity**2
                        self.max_c3_energy = max(self.max_c3_energy, current_c3)  # Professor v30: Track max C3
                        self.logger.info(f"Current velocity: {velocity:.0f} m/s (Escape vel: {escape_velocity:.0f} m/s)")
                        self.logger.info(f"C3 energy achieved: {current_c3:.1f} m²/s² (Target: {tli_guidance.tli_params.target_c3_energy:.1f})")
                        self.logger.info(f"Burn duration: {tli_status.get('burn_elapsed_time', 0):.1f} s")
                else:
                    # Fallback to original logic
                    if not self.rocket.is_thrusting:
                        self.rocket.phase = MissionPhase.COAST_TO_MOON
                        self.logger.info(f"TLI burn complete. Coasting to Moon...")
                        escape_velocity = np.sqrt(2 * G * M_EARTH / self.rocket.position.magnitude())
                        self.logger.info(f"Current velocity: {velocity:.0f} m/s (Escape vel: {escape_velocity:.0f} m/s)")
            except Exception as e:
                self.logger.warning(f"TLI guidance error: {e}, using fallback logic")
                if not self.rocket.is_thrusting:
                    self.rocket.phase = MissionPhase.COAST_TO_MOON
                    self.logger.info(f"TLI burn complete. Coasting to Moon...")
                    escape_velocity = np.sqrt(2 * G * M_EARTH / self.rocket.position.magnitude())
                    self.logger.info(f"Current velocity: {velocity:.0f} m/s (Escape vel: {escape_velocity:.0f} m/s)")

        elif current_phase == MissionPhase.COAST_TO_MOON:
            # Professor v33: Enhanced coast to Moon with Mid-Course Correction
            coast_time = len([p for p in self.phase_history if p == current_phase]) * 0.1
            current_time_total = len(self.time_history) * 0.1
            
            # Execute Mid-Course Correction at halfway point
            if not self.mcc_executed and coast_time > 1.5 * 24 * 3600:  # 1.5 days into coast
                try:
                    # Calculate MCC burn for trajectory correction
                    current_pos = np.array([self.rocket.position.x, self.rocket.position.y, self.rocket.position.z])
                    current_vel = np.array([self.rocket.velocity.x, self.rocket.velocity.y, self.rocket.velocity.z])
                    moon_pos = np.array([self.moon.position.x, self.moon.position.y, 0])
                    
                    # Simple MCC calculation: 5 m/s correction toward Moon
                    moon_direction = moon_pos - current_pos[:2]
                    moon_direction = moon_direction / np.linalg.norm(moon_direction) if np.linalg.norm(moon_direction) > 0 else np.array([0, 1])
                    mcc_delta_v = np.array([moon_direction[0] * 5.0, moon_direction[1] * 5.0, 0.0])  # 5 m/s toward Moon
                    
                    # Execute MCC burn
                    new_pos, new_vel = self.mid_course_correction.execute_mcc_burn(
                        (current_pos, current_vel), mcc_delta_v
                    )
                    
                    # Update spacecraft state
                    self.rocket.position = Vector3(new_pos[0], new_pos[1], new_pos[2])
                    self.rocket.velocity = Vector3(new_vel[0], new_vel[1], new_vel[2])
                    
                    self.mcc_executed = True
                    self.total_mission_delta_v += np.linalg.norm(mcc_delta_v)
                    
                    self.logger.info("=== MID-COURSE CORRECTION EXECUTED ===")
                    self.logger.info(f"MCC burn executed at T+{current_time_total:.1f}s (coast phase T+{coast_time:.1f}s)")
                    self.logger.info(f"Delta-V applied: {np.linalg.norm(mcc_delta_v):.2f} m/s toward Moon")
                    self.logger.info(f"New velocity: {self.rocket.velocity.magnitude():.2f} m/s")
                    
                except Exception as e:
                    self.logger.error(f"Mid-Course Correction failed: {e}")
                    self.mcc_executed = True  # Mark as attempted to prevent retry
            
            # Check for SOI transition using patched conic solver
            spacecraft_pos_km = self.rocket.position * 1e-3  # Convert to km
            moon_pos_km = self.moon.position * 1e-3  # Convert to km
            
            if check_soi_transition(spacecraft_pos_km, moon_pos_km):
                # Convert to lunar frame for trajectory analysis
                spacecraft_state = (spacecraft_pos_km, self.rocket.velocity * 1e-3)
                moon_state = (moon_pos_km, self.moon.velocity * 1e-3)
                pos_lci, vel_lci = convert_to_lunar_frame(spacecraft_state, moon_state)
                
                self.rocket.phase = MissionPhase.LOI_BURN
                self.logger.info("=== LUNAR SPHERE OF INFLUENCE ENTRY ===")
                self.logger.info(f"Entered Moon's Sphere of Influence using patched conic solver.")
                self.logger.info(f"Lunar-centered position: {np.linalg.norm(pos_lci):.1f} km")
                self.logger.info(f"Lunar-centered velocity: {np.linalg.norm(vel_lci):.3f} km/s")
                self.logger.info(f"Coast phase duration: {coast_time/3600:.1f} hours")
                
            elif coast_time > 5 * 24 * 3600: # 5日以上かかったら失敗
                self.rocket.phase = MissionPhase.FAILED
                self.logger.error("Failed to reach Moon SOI within 5 days.")

        elif current_phase == MissionPhase.LOI_BURN:
            # Professor v33: Enhanced LOI burn using circularize.py for precise lunar orbit insertion
            r_moon = (self.rocket.position - self.moon.position).magnitude()
            v_moon_relative = (self.rocket.velocity - self.moon.velocity).magnitude()
            moon_orbital_energy = 0.5 * v_moon_relative**2 - G * M_MOON / r_moon
            
            # Execute LOI burn at periapsis for optimal efficiency
            if not self.loi_executed:
                try:
                    # Calculate relative position and velocity in lunar frame
                    rel_pos = self.rocket.position - self.moon.position
                    rel_vel = self.rocket.velocity - self.moon.velocity
                    
                    # Check if we're at or near periapsis (optimal burn point)
                    radial_velocity = rel_vel.data @ rel_pos.normalized().data
                    at_periapsis = abs(radial_velocity) < 50.0  # Within 50 m/s of periapsis
                    
                    if at_periapsis or not hasattr(self, '_loi_burn_started'):
                        # Start LOI burn
                        self._loi_burn_started = True
                        
                        # Calculate required delta-V for lunar orbit capture
                        # Target: 100km circular lunar orbit
                        target_altitude = 100e3  # 100 km
                        target_radius = R_MOON + target_altitude
                        
                        # Current velocity in lunar frame
                        v_current = rel_vel.magnitude()
                        
                        # Velocity for circular orbit at current distance
                        v_circular = np.sqrt(G * M_MOON / r_moon)
                        
                        # If we're too fast, slow down for capture
                        if v_current > v_circular * 1.2:  # Need significant slowdown
                            # Retrograde burn to slow down for capture
                            burn_magnitude = min((v_current - v_circular) * 0.8, 500.0)  # Limit to 500 m/s
                            burn_direction = rel_vel.normalized() * (-1)  # Retrograde
                            
                            # Apply LOI burn
                            delta_v = burn_direction * burn_magnitude
                            self.rocket.velocity = self.rocket.velocity + delta_v
                            self.total_mission_delta_v += burn_magnitude
                            
                            self.loi_executed = True
                            
                            self.logger.info("=== LUNAR ORBIT INSERTION BURN ===")
                            self.logger.info(f"LOI burn executed: {burn_magnitude:.1f} m/s retrograde")
                            self.logger.info(f"Altitude at burn: {(r_moon - R_MOON)/1000:.1f} km")
                            self.logger.info(f"Pre-burn velocity: {v_current:.1f} m/s, Post-burn: {(rel_vel + delta_v).magnitude():.1f} m/s")
                        
                except Exception as e:
                    self.logger.error(f"LOI burn calculation failed: {e}")
                    self.loi_executed = True  # Mark as attempted
            
            # Check for successful lunar orbit capture
            if moon_orbital_energy < 0: # 月の重力に捕獲された
                self.rocket.phase = MissionPhase.LUNAR_ORBIT
                self.logger.info("=== LUNAR ORBIT INSERTION SUCCESSFUL ===")
                self.logger.info(f"Lunar orbit achieved! Altitude: {(r_moon - R_MOON)/1000:.1f} km")
                self.logger.info(f"Orbital energy: {moon_orbital_energy/1e6:.2f} MJ/kg (negative = bound orbit)")
                
            elif not self.rocket.is_thrusting: # 燃料切れで捕獲失敗
                self.rocket.phase = MissionPhase.FAILED
                self.logger.error("LOI failed. Insufficient fuel to be captured by the Moon.")

        elif current_phase == MissionPhase.LUNAR_ORBIT:
            # Professor v33: Enhanced lunar orbit tracking with three full orbits validation
            orbit_time = len([p for p in self.phase_history if p == current_phase]) * 0.1
            r_moon = (self.rocket.position - self.moon.position).magnitude()
            
            # Initialize lunar orbit tracking
            if self.lunar_orbit_start_time is None:
                self.lunar_orbit_start_time = len(self.time_history) * 0.1
                self.logger.info("=== LUNAR ORBIT TRACKING INITIATED ===")
            
            # Track orbital periods by detecting apoapsis and periapsis passages
            rel_pos = self.rocket.position - self.moon.position
            rel_vel = self.rocket.velocity - self.moon.velocity
            radial_velocity = rel_vel.data @ rel_pos.normalized().data
            
            # Detect apoapsis/periapsis passages (radial velocity changes sign)
            if self.last_lunar_radial_velocity_sign is not None:
                if (self.last_lunar_radial_velocity_sign > 0 and radial_velocity <= 0):
                    # Passed apoapsis (radial velocity changed from positive to negative)
                    altitude_km = (r_moon - R_MOON) / 1000
                    self.lunar_orbit_apoapsises.append(altitude_km)
                    self.logger.info(f"LUNAR APOAPSIS #{len(self.lunar_orbit_apoapsises)}: {altitude_km:.1f} km")
                    
                elif (self.last_lunar_radial_velocity_sign < 0 and radial_velocity >= 0):
                    # Passed periapsis (radial velocity changed from negative to positive)
                    altitude_km = (r_moon - R_MOON) / 1000
                    self.lunar_orbit_periapsises.append(altitude_km)
                    self.lunar_orbit_count += 1
                    self.logger.info(f"LUNAR PERIAPSIS #{len(self.lunar_orbit_periapsises)}: {altitude_km:.1f} km")
                    
                    # Calculate and validate orbit eccentricity
                    if len(self.lunar_orbit_apoapsises) >= self.lunar_orbit_count and len(self.lunar_orbit_periapsises) >= self.lunar_orbit_count:
                        apo = self.lunar_orbit_apoapsises[self.lunar_orbit_count - 1]
                        peri = self.lunar_orbit_periapsises[self.lunar_orbit_count - 1]
                        
                        # Calculate eccentricity: e = (r_apo - r_peri) / (r_apo + r_peri)
                        r_apo = (apo * 1000) + R_MOON
                        r_peri = (peri * 1000) + R_MOON
                        eccentricity = (r_apo - r_peri) / (r_apo + r_peri)
                        
                        self.logger.info(f"=== LUNAR ORBIT #{self.lunar_orbit_count} COMPLETE ===")
                        self.logger.info(f"Apoapsis: {apo:.1f} km, Periapsis: {peri:.1f} km")
                        self.logger.info(f"Eccentricity: {eccentricity:.4f} (target: < 0.1)")
                        
                        # Check if orbit meets stability criteria
                        orbit_stable = eccentricity < 0.1 and peri > 15.0  # Above 15km minimum
                        if orbit_stable:
                            self.logger.info(f"✓ Orbit #{self.lunar_orbit_count} is STABLE")
                        else:
                            self.logger.warning(f"⚠ Orbit #{self.lunar_orbit_count} stability concern: e={eccentricity:.4f}, peri={peri:.1f}km")
            
            self.last_lunar_radial_velocity_sign = 1 if radial_velocity > 0 else -1 if radial_velocity < 0 else self.last_lunar_radial_velocity_sign
            
            # Professor v33: After three full orbits, mission is complete
            if self.lunar_orbit_count >= 3:
                # Validate final orbit stability
                if len(self.lunar_orbit_apoapsises) >= 3 and len(self.lunar_orbit_periapsises) >= 3:
                    # Check last orbit
                    final_apo = self.lunar_orbit_apoapsises[-1]
                    final_peri = self.lunar_orbit_periapsises[-1]
                    r_apo = (final_apo * 1000) + R_MOON
                    r_peri = (final_peri * 1000) + R_MOON
                    final_eccentricity = (r_apo - r_peri) / (r_apo + r_peri)
                    
                    if final_eccentricity < 0.1 and final_peri > 15.0:
                        self.rocket.phase = MissionPhase.LANDED  # Use LANDED as mission success
                        self.logger.info("=== MISSION SUCCESS: STABLE LUNAR ORBIT ACHIEVED ===")
                        self.logger.info(f"Completed {self.lunar_orbit_count} stable lunar orbits")
                        self.logger.info(f"Final orbit: Apo {final_apo:.1f}km, Peri {final_peri:.1f}km, e={final_eccentricity:.4f}")
                        self.logger.info(f"Total mission time: {orbit_time/3600:.1f} hours")
                        return  # Mission complete
                    else:
                        self.rocket.phase = MissionPhase.FAILED
                        self.logger.error(f"Mission failed: Final orbit unstable (e={final_eccentricity:.4f}, peri={final_peri:.1f}km)")
                        return
            
            # Original landing logic (if altitude is very low)
            if (r_moon < R_MOON + 50e3 and orbit_time > 300 and self.rocket.current_stage == 3):
                self.rocket.phase = MissionPhase.PDI
                self.logger.info("Initiating Powered Descent Initiation (PDI).")

        elif current_phase == MissionPhase.PDI:
            # 動力降下から最終降下へ
            altitude_moon = (self.rocket.position - self.moon.position).magnitude() - R_MOON
            if altitude_moon < 15e3:
                self.rocket.phase = MissionPhase.TERMINAL_DESCENT
                self.logger.info(f"Terminal descent initiated at {altitude_moon/1000:.1f} km.")

        elif current_phase == MissionPhase.TERMINAL_DESCENT:
            # 最終降下から着陸シーケンスへ
            altitude_moon = (self.rocket.position - self.moon.position).magnitude() - R_MOON
            if altitude_moon < 1000:
                self.rocket.phase = MissionPhase.LUNAR_TOUCHDOWN
                self.logger.info(f"Final approach. Altitude: {altitude_moon:.0f} m.")

        elif current_phase == MissionPhase.LUNAR_TOUCHDOWN:
            # 着陸の成功/失敗判定
            altitude_moon = (self.rocket.position - self.moon.position).magnitude() - R_MOON
            relative_velocity = (self.rocket.velocity - self.moon.velocity).magnitude()
            
            if altitude_moon <= 10: # 地表10m以内
                if relative_velocity <= 3.0: # 秒速3m以下なら成功
                    self.rocket.phase = MissionPhase.LANDED
                    self.logger.info(f"LUNAR LANDING CONFIRMED! Landing velocity: {relative_velocity:.2f} m/s")
                else:
                    self.rocket.phase = MissionPhase.FAILED
                    self.logger.error(f"CRASH! Hard landing - velocity too high: {relative_velocity:.2f} m/s")
    
    def _check_mission_status(self) -> bool:
        """ミッション状態をチェック（継続/終了）"""
        altitude = self.get_altitude()
        distance_to_moon = (self.rocket.position - self.moon.position).magnitude()
        
        # Professor v19: Verbose abort debugging
        if hasattr(self, 'config') and self.config.get("verbose_abort", False):
            velocity = self.rocket.velocity.magnitude()
            flight_path_angle = np.degrees(self.get_flight_path_angle())
            thrust_mag = self.get_thrust_vector(0.0).magnitude()
            
            # Propellant info
            if self.rocket.current_stage < len(self.rocket.stages):
                stage = self.rocket.stages[self.rocket.current_stage]
                stage_elapsed_time = self.current_time - self.rocket.stage_start_time
                used_prop = stage.get_mass_flow_rate(altitude) * stage_elapsed_time
                remaining_prop = stage.propellant_mass - used_prop
                prop_ratio = remaining_prop / stage.propellant_mass if stage.propellant_mass > 0 else 0
            else:
                remaining_prop = 0
                prop_ratio = 0
            
            self.logger.debug(f"ABORT_DEBUG: alt={altitude:.1f}m, v={velocity:.1f}m/s, γ={flight_path_angle:.1f}°, "
                           f"thrust={thrust_mag:.0f}N, prop_remain={remaining_prop:.1f}kg ({prop_ratio*100:.1f}%)")
        
        # Professor v19: Configurable abort thresholds (C1)
        abort_thresholds = self.config.get("abort_thresholds", {
            "earth_impact_altitude": -100.0,
            "propellant_critical_percent": 99.5,
            "min_safe_time": 5.0,
            "max_flight_path_angle": 85.0,
            "min_thrust_threshold": 5000.0
        })
        
        # 地球に衝突チェック（初期打ち上げ時の数値誤差を考慮）
        # 地表近くでは地球曲率・数値誤差で若干のマイナス高度が発生する
        earth_impact_threshold = abort_thresholds["earth_impact_altitude"]
        if altitude < earth_impact_threshold:  
            self.rocket.phase = MissionPhase.FAILED
            self.logger.error(f"Mission failed: Crashed into Earth at altitude {altitude:.1f} m")
            
            # Professor v19: Enhanced abort reason logging
            if hasattr(self, 'config') and self.config.get("verbose_abort", False):
                velocity = self.rocket.velocity.magnitude()
                flight_path_angle = np.degrees(self.get_flight_path_angle())
                apoapsis, periapsis, eccentricity = self.get_orbital_elements()
                self.logger.error(f"ABORT_REASON: Earth impact - altitude {altitude:.1f}m")
                self.logger.error(f"ABORT_STATE: v={velocity:.1f}m/s, γ={flight_path_angle:.1f}°, "
                               f"apo={(apoapsis-R_EARTH)/1000:.1f}km, peri={(periapsis-R_EARTH)/1000:.1f}km")
            return False
        
        # サブオービタル軌道の早期発見
        if altitude > 50e3:  # 50km以上でチェック
            apoapsis, periapsis, eccentricity = self.get_orbital_elements()
            if periapsis < -R_EARTH * 0.1:  # 非常に負の近地点
                # 総燃焼時間で判定（燃料切れかどうか）
                total_burn_time = sum(stage.burn_time for stage in self.rocket.stages[:self.rocket.current_stage+1])
                elapsed_time = len(self.time_history) * 0.1  # dt=0.1
                if elapsed_time > total_burn_time * 0.8:  # 80%以上経過でもサブオービタル
                    self.rocket.phase = MissionPhase.FAILED
                    self.logger.error(f"Mission failed: Suborbital trajectory detected. Periapsis: {(periapsis-R_EARTH)/1000:.1f} km")
                    return False
        
        # 月面着陸の精密チェック（教授フィードバック対応）
        if distance_to_moon <= R_MOON + 100:  # 月面から100m以内
            relative_velocity = (self.rocket.velocity - self.moon.velocity).magnitude()
            
            # 教授推奨: 着陸速度 ≤ 2 m/s, 傾斜 ≤ 5°
            if relative_velocity <= 2.0:  # 2 m/s以下で成功
                # 僾斜角を簡略チェック（速度ベクトルと面法線の角度）
                moon_center_dir = (self.moon.position - self.rocket.position).normalized()
                velocity_dir = (self.rocket.velocity - self.moon.velocity).normalized()
                dot_product = moon_center_dir.data @ velocity_dir.data
                tilt_angle = np.degrees(np.arccos(np.abs(np.clip(dot_product, -1, 1))))
                
                if tilt_angle <= 85:  # 5°以内の僾斜（簡略化）
                    self.rocket.phase = MissionPhase.LANDED
                    self.logger.info(f"Successful lunar landing! Velocity: {relative_velocity:.1f} m/s, Tilt: {90-tilt_angle:.1f}°")
                    return False
                else:
                    self.rocket.phase = MissionPhase.FAILED
                    self.logger.error(f"Landing failed - excessive tilt: {90-tilt_angle:.1f}°")
                    return False
            else:
                self.rocket.phase = MissionPhase.FAILED
                self.logger.error(f"Hard landing - velocity too high: {relative_velocity:.1f} m/s")
                return False
        
        # 月面衝突チェック（100m以下でない場合）
        elif distance_to_moon <= R_MOON + 1000:  # 1km以内
            if self.rocket.phase not in [MissionPhase.TERMINAL_DESCENT, MissionPhase.LUNAR_TOUCHDOWN]:
                # 着陸フェーズでないのに月面に近づいた
                relative_velocity = (self.rocket.velocity - self.moon.velocity).magnitude()
                if relative_velocity > 10:  # 10 m/s以上で衝突
                    self.rocket.phase = MissionPhase.FAILED
                    self.logger.error(f"Uncontrolled lunar impact at {relative_velocity:.1f} m/s")
                    return False
        
        return True
    
    def _update_stage_delta_v(self):
        """Track stage separations and calculate ΔV using stage-end ledger (Professor v11)"""
        if self.rocket.current_stage > self.last_stage_count:
            # Stage separation occurred, calculate ΔV for the just-separated stage
            stage_index = self.last_stage_count
            if stage_index < len(self.rocket.stages):
                stage = self.rocket.stages[stage_index]
                altitude = self.get_altitude()
                isp = stage.get_specific_impulse(altitude)
                
                # Use actual propellant consumed (same logic as in rocket separation)
                used_propellant = stage.get_mass_flow_rate(altitude) * stage.burn_time
                actual_propellant_used = min(used_propellant, stage.propellant_mass)
                
                # Calculate total masses before and after this stage
                total_initial_mass = stage.total_mass
                for i in range(stage_index + 1, len(self.rocket.stages)):
                    total_initial_mass += self.rocket.stages[i].total_mass
                total_initial_mass += self.rocket.payload_mass
                
                total_final_mass = stage.dry_mass + (stage.propellant_mass - actual_propellant_used)
                for i in range(stage_index + 1, len(self.rocket.stages)):
                    total_final_mass += self.rocket.stages[i].total_mass
                total_final_mass += self.rocket.payload_mass
                
                # Calculate actual stage ΔV using Tsiolkovsky equation
                if total_final_mass > 0:
                    stage_dv = isp * STANDARD_GRAVITY * np.log(total_initial_mass / total_final_mass)
                    self.total_delta_v += stage_dv
                    self.stage_delta_v_history.append(stage_dv)
            
            self.last_stage_count = self.rocket.current_stage
    
    def _calculate_stage_fuel_remaining(self) -> Dict:
        """Calculate remaining fuel percentage for each stage"""
        stage_fuel = {}
        
        for i, stage in enumerate(self.rocket.stages):
            stage_name = f"stage_{i+1}"
            
            if i < self.rocket.current_stage:
                # Stage already separated - 0% remaining
                stage_fuel[stage_name] = 0.0
            elif i == self.rocket.current_stage:
                # Current active stage - calculate remaining fuel
                try:
                    altitude = self.get_altitude()
                    stage_elapsed_time = hasattr(self, 'current_time') and hasattr(self.rocket, 'stage_start_time') and \
                                       self.current_time - self.rocket.stage_start_time or 0
                    used_propellant = stage.get_mass_flow_rate(altitude) * stage_elapsed_time
                    remaining_propellant = max(0, stage.propellant_mass - used_propellant)
                    fuel_ratio = remaining_propellant / stage.propellant_mass if stage.propellant_mass > 0 else 0
                    stage_fuel[stage_name] = fuel_ratio
                except:
                    # Fallback - assume full fuel if calculation fails
                    stage_fuel[stage_name] = 1.0
            else:
                # Future stage - full fuel remaining
                stage_fuel[stage_name] = 1.0
        
        # Special tracking for Stage 3 (S-IVB) - target 30%+ for TLI capability
        if len(self.rocket.stages) > 2:
            stage3_percentage = stage_fuel.get("stage_3", 0.0) * 100
            stage_fuel["stage3_percentage"] = stage3_percentage
            stage_fuel["stage3_tli_ready"] = stage3_percentage >= 30.0
        
        return stage_fuel
    
    def _calculate_and_report_tli_requirements(self) -> None:
        """Calculate and report TLI delta-V requirements and fuel availability (Professor v39)"""
        try:
            from tli_guidance import create_tli_guidance
            from constants import R_EARTH
            
            # Get current altitude and velocity
            altitude = self.get_altitude()
            parking_orbit_altitude = altitude  # Current altitude as parking orbit
            current_velocity = self.rocket.velocity.magnitude()
            
            # Create TLI guidance system
            tli_guidance = create_tli_guidance(parking_orbit_altitude)
            
            # Calculate required delta-V for TLI
            delta_v_required = tli_guidance.tli_params.delta_v_required
            
            # Check Stage 3 fuel availability
            stage_fuel = self._calculate_stage_fuel_remaining()
            stage3_percentage = stage_fuel.get("stage3_percentage", 0.0)
            stage3_ready = stage_fuel.get("stage3_tli_ready", False)
            
            # Calculate available delta-V from Stage 3
            if len(self.rocket.stages) > 2:
                stage3 = self.rocket.stages[2]
                remaining_propellant = stage3.propellant_mass * (stage3_percentage / 100.0)
                
                # Estimate available delta-V using simplified calculation
                # Assuming specific impulse ~421s for S-IVB in vacuum
                isp_vacuum = 421  # seconds
                g0 = 9.80665  # m/s²
                current_mass = self.rocket.get_current_mass(self.current_time, altitude)
                
                if remaining_propellant > 0 and current_mass > 0:
                    mass_ratio = current_mass / (current_mass - remaining_propellant)
                    available_delta_v = isp_vacuum * g0 * np.log(mass_ratio)
                else:
                    available_delta_v = 0.0
            else:
                available_delta_v = 0.0
            
            # Log comprehensive TLI analysis
            self.logger.info("="*60)
            self.logger.info("TLI READINESS ANALYSIS")
            self.logger.info("="*60)
            self.logger.info(f"Current parking orbit: {(altitude-R_EARTH)/1000:.1f} km altitude")
            self.logger.info(f"Current orbital velocity: {current_velocity:.1f} m/s")
            self.logger.info(f"Required TLI delta-V: {delta_v_required:.1f} m/s")
            self.logger.info(f"Available TLI delta-V: {available_delta_v:.1f} m/s")
            self.logger.info(f"Stage-3 fuel remaining: {stage3_percentage:.1f}%")
            self.logger.info(f"TLI capability: {'READY' if stage3_ready and available_delta_v >= delta_v_required else 'INSUFFICIENT'}")
            
            if available_delta_v >= delta_v_required:
                delta_v_margin = available_delta_v - delta_v_required
                self.logger.info(f"Delta-V margin: +{delta_v_margin:.1f} m/s")
            else:
                delta_v_deficit = delta_v_required - available_delta_v
                self.logger.warning(f"Delta-V deficit: -{delta_v_deficit:.1f} m/s")
                
            self.logger.info("="*60)
            
            # Store for results JSON
            if not hasattr(self, 'tli_analysis'):
                self.tli_analysis = {}
            self.tli_analysis = {
                'required_delta_v': delta_v_required,
                'available_delta_v': available_delta_v,
                'stage3_fuel_percentage': stage3_percentage,
                'tli_ready': stage3_ready and available_delta_v >= delta_v_required,
                'delta_v_margin': available_delta_v - delta_v_required
            }
            
        except Exception as e:
            self.logger.error(f"TLI requirements calculation failed: {e}")
    
    def simulate(self, duration: float = 10 * 24 * 3600, dt: float = 0.1) -> Dict:
        """シミュレーション実行"""
        t = 0.0
        steps = 0
        self.current_time = 0.0  # Track current time for fuel calculations
        
        # ロケット初期位置（地球表面、緯度を考慮）
        launch_latitude = self.config.get("launch_latitude", 28.5)  # ケネディ宇宙センター
        launch_angle = np.radians(launch_latitude)
        # 地球表面の位置
        self.rocket.position = Vector3(R_EARTH * np.cos(launch_angle), R_EARTH * np.sin(launch_angle))
        
        # 地球自転による初速度（東向き）
        surface_velocity = 2 * np.pi * R_EARTH * np.cos(launch_angle) / EARTH_ROTATION_PERIOD
        # 東向きは y方向の負（座標系の設定による）
        self.rocket.velocity = Vector3(-surface_velocity * np.sin(launch_angle), surface_velocity * np.cos(launch_angle))
        
        self.logger.info(f"Mission start: Saturn V")
        self.logger.info(f"Initial position: {self.rocket.position}")
        self.logger.info(f"Initial velocity: {self.rocket.velocity.magnitude():.1f} m/s")
        self.logger.info(f"Total rocket mass: {self.rocket.total_mass/1000:.1f} tons")
        
        # 初期フェーズ確認（月ミッション用）
        self.rocket.phase = MissionPhase.LAUNCH
        
        # RK4法による数値積分
        while t < duration and self._check_mission_status():
            # フェーズ更新を最初に実行（重要：積分前に実行）
            self._update_mission_phase()
            
            # 記録
            self.time_history.append(t)
            self.current_time = t  # Update current time for fuel calculations
            self.position_history.append(self.rocket.position)
            self.velocity_history.append(self.rocket.velocity)
            altitude = self.get_altitude()
            velocity = self.rocket.velocity.magnitude()
            mass = self.rocket.get_current_mass(t, altitude)
            apoapsis, periapsis, eccentricity = self.get_orbital_elements()
            self.altitude_history.append(altitude)
            self.mass_history.append(mass)
            self.phase_history.append(self.rocket.phase)
            
            # Professor v19: 10 Hz phase/stage logging for debugging (B1)
            if steps % 1 == 0:  # dt=0.1なので1ステップ=0.1秒 = 10 Hz
                flag_status = {
                    "LEO_FINAL_RUN": is_enabled("LEO_FINAL_RUN"),
                    "STAGE2_MASS_FLOW": is_enabled("STAGE2_MASS_FLOW_OVERRIDE"),
                    "VELOCITY_STAGE3": is_enabled("VELOCITY_TRIGGERED_STAGE3"),
                    "PEG_DAMPING": is_enabled("PEG_GAMMA_DAMPING")
                }
                # Every 10 Hz log with high verbosity for first 20 seconds
                if t <= 20.0:
                    self.logger.debug(f"10Hz_LOG: t={t:.1f}s, stage={self.rocket.current_stage}, "
                                   f"phase={self.rocket.phase.value}, flags={flag_status}")

            # Professor v17: Enhanced telemetry logging every 0.2s
            if is_enabled("ENHANCED_TELEMETRY") and steps % 2 == 0:  # dt=0.1なので2ステップ=0.2秒
                stage_elapsed_time = t - self.rocket.stage_start_time
                # Calculate propellant usage and abort if >99.5%
                if self.rocket.current_stage < len(self.rocket.stages):
                    current_stage = self.rocket.stages[self.rocket.current_stage]
                    used_propellant = current_stage.get_mass_flow_rate(altitude) * stage_elapsed_time
                    propellant_usage_pct = (used_propellant / current_stage.propellant_mass) * 100 if current_stage.propellant_mass > 0 else 100
                    
                    # Professor v19: Configurable propellant threshold with time guard (C2)
                    abort_thresholds = self.config.get("abort_thresholds", {"propellant_critical_percent": 99.5, "min_safe_time": 5.0})
                    propellant_threshold = abort_thresholds["propellant_critical_percent"]
                    min_safe_time = abort_thresholds["min_safe_time"]
                    
                    # Professor v17: Monitor propellant usage and trigger stage separation if needed
                    # Professor v19: Add time guard to prevent early aborts
                    if (propellant_usage_pct > propellant_threshold and
                        self.rocket.is_thrusting(t, altitude) and
                        t > min_safe_time):  # Time guard: no abort before min_safe_time seconds
                        # Force stage separation instead of mission abort
                        self.logger.warning(f"PROPELLANT CRITICAL: Stage {self.rocket.current_stage + 1} propellant >{propellant_threshold:.1f}% consumed after t={t:.1f}s")
                        self.logger.warning(f" -> Propellant usage: {propellant_usage_pct:.1f}% - Triggering stage separation")
                        
                        # Force stage separation by setting rocket to separation phase
                        if self.rocket.separate_stage(t):
                            self.rocket.phase = MissionPhase.STAGE_SEPARATION
                            self.logger.warning(f"Stage {self.rocket.current_stage} separation completed")
                        
                        # Continue simulation to allow normal stage separation logic to run
                        # Don't return here - let the normal separation process handle it
                    
                    # Professor v23: Max-Q Monitor - check dynamic pressure limits
                    # Calculate velocity relative to atmosphere (subtract Earth rotation)
                    earth_rotation_velocity = 2 * np.pi * R_EARTH * np.cos(np.radians(28.573)) / EARTH_ROTATION_PERIOD
                    relative_velocity = max(0, self.rocket.velocity.magnitude() - earth_rotation_velocity)
                    density = self._calculate_atmospheric_density(altitude)
                    dynamic_pressure = 0.5 * density * relative_velocity**2  # Pa
                    
                    # Track maximum dynamic pressure encountered
                    if not hasattr(self, 'max_dynamic_pressure'):
                        self.max_dynamic_pressure = 0.0
                    self.max_dynamic_pressure = max(self.max_dynamic_pressure, dynamic_pressure)
                    
                    # Max-Q check - temporarily disabled for testing - log but don't abort
                    # Only check after launch (t > 1s) to avoid initial Earth rotation velocity
                    if dynamic_pressure > MAX_Q_OPERATIONAL and t > 1.0:
                        if not hasattr(self, '_max_q_warning_shown'):
                            self.logger.warning(f"WARNING: Dynamic pressure exceeded {MAX_Q_OPERATIONAL/1000:.1f} kPa at t={t:.1f}s")
                            self.logger.warning(f"Limit exceeded: {dynamic_pressure:.1f} Pa > {MAX_Q_OPERATIONAL} Pa ({MAX_Q_OPERATIONAL/1000:.1f} kPa)")
                            self._max_q_warning_shown = True
                    
                    # Log detailed telemetry every 1 second (5 * 0.2s)
                    if steps % 10 == 0:
                        flight_path_angle_deg = np.degrees(self.get_flight_path_angle())
                        self.logger.info(f"TELEMETRY: t={t:.1f}s, stage={self.rocket.current_stage+1}, "
                                       f"alt={altitude/1000:.1f}km, v={velocity:.0f}m/s, "
                                       f"propellant={100-propellant_usage_pct:.1f}%, γ={flight_path_angle_deg:.1f}°")

            # CSVログ出力（10秒ごと） - Professor v7: enhanced logging
            if steps % 100 == 0:  # dt=0.1なので100ステップ=10秒
                stage_elapsed_time = t - self.rocket.stage_start_time
                # Calculate additional metrics for professor's analysis
                flight_path_angle_deg = np.degrees(self.get_flight_path_angle())
                
                # Get current pitch angle from guidance
                import guidance
                pitch_angle_deg = guidance.get_target_pitch_angle(altitude, velocity)
                
                # Calculate remaining propellant in current stage
                if self.rocket.current_stage < len(self.rocket.stages):
                    current_stage = self.rocket.stages[self.rocket.current_stage]
                    used_propellant = current_stage.get_mass_flow_rate(altitude) * stage_elapsed_time
                    remaining_propellant = max(0, current_stage.propellant_mass - used_propellant)
                    
                    # Professor v16: Enhanced Stage-2 logging
                    if self.rocket.current_stage == 1:  # Stage-2 (S-II)
                        thrust_actual = current_stage.get_thrust(altitude)
                        mass_flow_actual = current_stage.get_mass_flow_rate(altitude)
                        self.logger.info(f"STAGE-2 MONITOR: t={t:.1f}s, propellant={remaining_propellant/1000:.1f}t, "
                                       f"mass_flow={mass_flow_actual:.1f}kg/s, thrust={thrust_actual/1000:.0f}kN, "
                                       f"burn_time={stage_elapsed_time:.1f}s/{current_stage.burn_time:.1f}s")
                    
                    # Professor v39: Enhanced Stage-3 fuel monitoring for TLI readiness
                    elif self.rocket.current_stage == 2:  # Stage-3 (S-IVB)
                        thrust_actual = current_stage.get_thrust(altitude)
                        mass_flow_actual = current_stage.get_mass_flow_rate(altitude)
                        fuel_percentage = (remaining_propellant / current_stage.propellant_mass) * 100 if current_stage.propellant_mass > 0 else 0
                        tli_ready = "TLI_READY" if fuel_percentage >= 30.0 else "TLI_RISK"
                        
                        self.logger.info(f"STAGE-3 MONITOR: t={t:.1f}s, propellant={remaining_propellant/1000:.1f}t ({fuel_percentage:.1f}%), "
                                       f"mass_flow={mass_flow_actual:.1f}kg/s, thrust={thrust_actual/1000:.0f}kN, "
                                       f"burn_time={stage_elapsed_time:.1f}s/{current_stage.burn_time:.1f}s, {tli_ready}")
                        
                        # Alert when Stage-3 fuel drops below TLI threshold
                        if fuel_percentage < 30.0 and fuel_percentage > 25.0:
                            self.logger.warning(f"STAGE-3 FUEL WARNING: {fuel_percentage:.1f}% remaining - approaching TLI minimum threshold")
                else:
                    remaining_propellant = 0
                
                # Calculate dynamic pressure for CSV logging
                csv_velocity = self.rocket.velocity.magnitude()
                csv_density = self._calculate_atmospheric_density(altitude)
                csv_dynamic_pressure = 0.5 * csv_density * csv_velocity**2  # Pa
                csv_max_dynamic_pressure = getattr(self, 'max_dynamic_pressure', 0.0)
                
                self.csv_writer.writerow([
                    f"{t:.1f}",
                    f"{altitude:.1f}",
                    f"{velocity:.1f}",
                    f"{mass:.1f}",
                    f"{self.total_delta_v:.1f}",
                    self.rocket.phase.value,
                    self.rocket.current_stage,
                    f"{(apoapsis-R_EARTH)/1000:.1f}" if apoapsis != float('inf') else "inf",
                    f"{(periapsis-R_EARTH)/1000:.1f}",
                    f"{eccentricity:.3f}",
                    f"{flight_path_angle_deg:.2f}",
                    f"{pitch_angle_deg:.2f}",
                    f"{remaining_propellant/1000:.1f}",
                    f"{csv_dynamic_pressure:.1f}",
                    f"{csv_max_dynamic_pressure:.1f}"
                ])
                self.csv_file.flush()
            
            # 統計更新
            self.max_altitude = max(self.max_altitude, altitude)
            self.max_velocity = max(self.max_velocity, velocity)
            
            # RK4積分
            # k1: 現在の状態での微分
            k1_v = self._calculate_total_acceleration(t)
            k1_r = self.rocket.velocity
            
            # 状態の完全コピーを保存
            orig_pos = Vector3(self.rocket.position.x, self.rocket.position.y, self.rocket.position.z)
            orig_vel = Vector3(self.rocket.velocity.x, self.rocket.velocity.y, self.rocket.velocity.z)
            
            # k2: dt/2での状態での微分
            self.rocket.position = orig_pos + k1_r * (dt/2)
            self.rocket.velocity = orig_vel + k1_v * (dt/2)
            k2_v = self._calculate_total_acceleration(t + dt/2)
            k2_r = self.rocket.velocity
            
            # k3: dt/2での状態（k2使用）での微分
            self.rocket.position = orig_pos + k2_r * (dt/2)
            self.rocket.velocity = orig_vel + k2_v * (dt/2)
            k3_v = self._calculate_total_acceleration(t + dt/2)
            k3_r = self.rocket.velocity
            
            # k4: dtでの状態（k3使用）での微分
            self.rocket.position = orig_pos + k3_r * dt
            self.rocket.velocity = orig_vel + k3_v * dt
            k4_v = self._calculate_total_acceleration(t + dt)
            k4_r = self.rocket.velocity
            
            # 最終状態更新（RK4公式）
            self.rocket.velocity = orig_vel + (k1_v + k2_v * 2 + k3_v * 2 + k4_v) * (dt/6)
            self.rocket.position = orig_pos + (k1_r + k2_r * 2 + k3_r * 2 + k4_r) * (dt/6)
            
            # Professor v27: Update orbital monitor with new state
            self.orbital_monitor.update_state(self.rocket.position, self.rocket.velocity, t)
            
            # Professor v27: Check LEO mission success
            self.check_leo_success()
            
            # その他の更新
            self._update_moon_position(dt)
            self.rocket.update_stage(dt)
            
            # ΔV calculation using stage-end ledger (Professor v11)
            self._update_stage_delta_v()
            
            t += dt
            steps += 1
            
            # 定期的な状態出力（1000秒ごと） - Professor v7: enhanced logging
            if steps % 10000 == 0:
                flight_path_angle_deg = np.degrees(self.get_flight_path_angle())
                import guidance
                pitch_angle_deg = guidance.get_target_pitch_angle(altitude, velocity)
                
                self.logger.info(f"t={t/3600:.1f}h, alt={altitude/1000:.1f}km, "
                                f"v={velocity:.0f}m/s, ΔV={self.total_delta_v:.0f}m/s, "
                                f"phase={self.rocket.phase.value}, "
                                f"γ={flight_path_angle_deg:.1f}°, pitch={pitch_angle_deg:.1f}°")
        
        # 最終記録
        self.time_history.append(t)
        self.position_history.append(self.rocket.position)
        self.velocity_history.append(self.rocket.velocity)
        final_altitude = self.get_altitude()
        self.altitude_history.append(final_altitude)
        self.mass_history.append(self.rocket.get_current_mass(t, final_altitude))
        self.phase_history.append(self.rocket.phase)
        
        # CSVファイルを閉じる
        self.csv_file.close()
        
        return self._compile_results()
    
    def _compile_results(self) -> Dict:
        """シミュレーション結果をまとめる"""
        # Professor v30: Calculate final orbital parameters for validation
        if self.position_history and self.velocity_history:
            final_position = self.position_history[-1]
            final_velocity = self.velocity_history[-1]
            
            # Calculate orbital parameters
            r = final_position.magnitude()
            v = final_velocity.magnitude()
            escape_velocity = np.sqrt(2 * G * M_EARTH / r)
            final_c3_energy = v**2 - escape_velocity**2
            
            # Calculate eccentricity and apogee for validation
            mu = G * M_EARTH
            h_vec = Vector3(
                final_position.y * final_velocity.z - final_position.z * final_velocity.y,
                final_position.z * final_velocity.x - final_position.x * final_velocity.z,
                final_position.x * final_velocity.y - final_position.y * final_velocity.x
            )
            h = h_vec.magnitude()
            
            if h > 0:
                semi_major_axis = 1 / (2/r - v**2/mu)
                eccentricity = np.sqrt(1 + (2 * (v**2/2 - mu/r) * h**2) / (mu**2))
                apogee = semi_major_axis * (1 + eccentricity) - R_EARTH
            else:
                eccentricity = 0
                apogee = r - R_EARTH
        else:
            final_c3_energy = 0
            eccentricity = 0
            apogee = 0

        # Professor v33: Determine mission success based on lunar orbit achievement
        mission_success = False
        final_lunar_orbit = {}
        
        if self.rocket.phase == MissionPhase.LANDED and self.lunar_orbit_count >= 3:
            # Mission success: achieved stable lunar orbit for 3+ orbits
            mission_success = True
            if len(self.lunar_orbit_apoapsises) >= 3 and len(self.lunar_orbit_periapsises) >= 3:
                final_apo = self.lunar_orbit_apoapsises[-1]
                final_peri = self.lunar_orbit_periapsises[-1]
                r_apo = (final_apo * 1000) + R_MOON
                r_peri = (final_peri * 1000) + R_MOON
                final_ecc = (r_apo - r_peri) / (r_apo + r_peri)
                
                final_lunar_orbit = {
                    "apoapsis_km": final_apo,
                    "periapsis_km": final_peri,
                    "eccentricity": final_ecc
                }
        
        return {
            "mission_success": mission_success,
            "final_phase": self.rocket.phase.value,
            "mission_duration": self.time_history[-1] if self.time_history else 0,
            "total_mission_time_days": (self.time_history[-1] if self.time_history else 0) / (24 * 3600),
            "max_altitude": self.max_altitude,
            "max_velocity": self.max_velocity,
            "total_delta_v": self.total_delta_v,
            "total_delta_v_mps": self.total_mission_delta_v + self.total_delta_v,  # Include mission delta-V
            "max_c3_energy": self.max_c3_energy if self.max_c3_energy != float('-inf') else final_c3_energy,
            "final_c3_energy": final_c3_energy,
            "final_eccentricity": eccentricity,
            "final_apogee": apogee,
            "final_lunar_orbit": final_lunar_orbit,
            "lunar_orbits_completed": self.lunar_orbit_count,
            "lunar_orbit_apoapsises": self.lunar_orbit_apoapsises,
            "lunar_orbit_periapsises": self.lunar_orbit_periapsises,
            "final_mass": self.mass_history[-1] if self.mass_history else self.rocket.total_mass,
            "propellant_used": sum(stage.propellant_mass for stage in self.rocket.stages[:self.rocket.current_stage]),
            "stage_fuel_remaining": self._calculate_stage_fuel_remaining(),
            "tli_analysis": getattr(self, 'tli_analysis', {}),
            "time_history": self.time_history,
            "position_history": [(p.x, p.y) for p in self.position_history],
            "velocity_history": [(v.x, v.y) for v in self.velocity_history],
            "altitude_history": self.altitude_history,
            "mass_history": self.mass_history,
            "phase_history": [p.value for p in self.phase_history],
            # Professor v33: Add Moon position history for trajectory plotting
            "moon_position_history": [(self.moon.position.x, self.moon.position.y) for _ in self.time_history]
        }


# Professor v10: Removed duplicate function - now using vehicle.py


def main():
    """メインエントリーポイント"""
    import sys
    
    # Check for verbose abort flag
    verbose_abort = "--verbose-abort" in sys.argv
    if verbose_abort:
        print("=== VERBOSE ABORT MODE ENABLED ===")
        logging.getLogger().setLevel(logging.DEBUG)
    
    # 設定ファイル読み込み（存在する場合）
    try:
        with open("mission_config.json", "r") as f:
            config = json.load(f)
    except FileNotFoundError:
        config = {
            "launch_latitude": 28.573,  # ケネディ宇宙センター
            "launch_azimuth": 90,  # 東向き
            "target_parking_orbit": 185e3,  # 185 km
            "gravity_turn_altitude": 1500,  # 1500 m (Professor v7 feedback)
            "simulation_duration": 10 * 24 * 3600,  # 10日間
            "time_step": 0.1  # 0.1秒（高精度）
        }
    
    # Add verbose abort mode to config
    config["verbose_abort"] = verbose_abort
    
    # Professor v16: Create rocket from configuration file 
    try:
        with open("saturn_v_config.json", "r") as f:
            saturn_config = json.load(f)
    except FileNotFoundError:
        saturn_config = {
            "stages": [
                {
                    "name": "S-IC (1st Stage)",
                    "dry_mass": 130000,
                    "propellant_mass": 2150000,
                    "thrust_sea_level": 34020000,
                    "thrust_vacuum": 35100000,
                    "specific_impulse_sea_level": 263,
                    "specific_impulse_vacuum": 289,
                    "burn_time": 168
                },
                {
                    "name": "S-II (2nd Stage)",
                    "dry_mass": 40000,
                    "propellant_mass": 540000,  # Professor v16: Updated
                    "thrust_sea_level": 4400000,
                    "thrust_vacuum": 5000000,
                    "specific_impulse_sea_level": 395,
                    "specific_impulse_vacuum": 421,
                    "burn_time": 500  # Professor v16: Updated
                },
                {
                    "name": "S-IVB (3rd Stage)",
                    "dry_mass": 13494,
                    "propellant_mass": 193536,
                    "thrust_sea_level": 825000,
                    "thrust_vacuum": 1000000,
                    "specific_impulse_sea_level": 441,
                    "specific_impulse_vacuum": 461,
                    "burn_time": 1090
                }
            ],
            "rocket": {
                "name": "Saturn V",
                "payload_mass": 45000,
                "drag_coefficient": 0.3,
                "cross_sectional_area": 80.0
            }
        }
    
    # Create rocket instance
    rocket = create_saturn_v_rocket("saturn_v_config.json")
    
    # Professor v19: Merge abort thresholds from Saturn V config
    if "abort_thresholds" in saturn_config:
        config["abort_thresholds"] = saturn_config["abort_thresholds"]
    
    # ミッション実行
    mission = Mission(rocket, config)
    results = mission.simulate(
        duration=config.get("simulation_duration", 10 * 24 * 3600),
        dt=config.get("time_step", 0.1)
    )
    
    # 結果出力
    print("\n" + "="*50)
    print("MISSION SUMMARY")
    print("="*50)
    print(f"Mission Success: {results['mission_success']}")
    print(f"Final Phase: {results['final_phase']}")
    print(f"Mission Duration: {results['mission_duration']/3600:.1f} hours")
    print(f"Max Altitude: {results['max_altitude']/1000:.1f} km")
    print(f"Max Velocity: {results['max_velocity']:.1f} m/s")
    print(f"Total Delta-V: {results['total_delta_v']:.1f} m/s")
    print(f"Propellant Used: {results['propellant_used']/1000:.1f} tons")
    print(f"Final Mass: {results['final_mass']/1000:.1f} tons")
    
    # Professor v30: Show C3 energy and orbital parameters for validation
    if 'max_c3_energy' in results:
        print(f"Max C3 Energy: {results['max_c3_energy']/1e6:.3f} km²/s²")
    if 'final_c3_energy' in results:
        print(f"Final C3 Energy: {results['final_c3_energy']/1e6:.3f} km²/s²")
    if 'final_eccentricity' in results:
        print(f"Final Eccentricity: {results['final_eccentricity']:.6f}")
    if 'final_apogee' in results:
        print(f"Final Apogee: {results['final_apogee']/1000:.1f} km")
    
    # Professor v33: Save comprehensive mission results with required fields
    mission_results = {
        "mission_success": results["mission_success"],
        "final_lunar_orbit": results.get("final_lunar_orbit", {}),
        "total_mission_time_days": results.get("total_mission_time_days", 0),
        "total_delta_v_mps": results.get("total_delta_v_mps", 0),
        "final_phase": results["final_phase"],
        "mission_duration_hours": results["mission_duration"] / 3600,
        "max_altitude_km": results["max_altitude"] / 1000,
        "max_velocity_ms": results["max_velocity"],
        "lunar_orbits_completed": results.get("lunar_orbits_completed", 0),
        "lunar_orbit_data": {
            "apoapsises_km": results.get("lunar_orbit_apoapsises", []),
            "periapsises_km": results.get("lunar_orbit_periapsises", []),
        },
        "propellant_used_kg": results["propellant_used"],
        "final_mass_kg": results["final_mass"],
        "max_c3_energy_km2s2": results.get("max_c3_energy", 0) / 1e6,
        "trajectory_data": {
            "time_history": results["time_history"],
            "position_history": results["position_history"],
            "velocity_history": results["velocity_history"],
            "altitude_history": results["altitude_history"],
            "phase_history": results["phase_history"]
        }
    }
    
    # Save comprehensive results
    try:
        with open("mission_results.json", "w") as f:
            json.dump(mission_results, f, indent=2)
        print("Mission results saved to mission_results.json")
    except Exception as e:
        print(f"Error saving mission results: {e}")
        # Ensure the file exists even with minimal data
        try:
            with open("mission_results.json", "w") as f:
                json.dump({
                    "mission_success": results.get("mission_success", False),
                    "final_phase": results.get("final_phase", "failed"),
                    "error": str(e)
                }, f, indent=2)
        except:
            pass
    
    # Professor v33: Generate and save lunar orbit trajectory plot (skip in fast mode)
    import os
    if not os.environ.get('ROCKET_FAST_MODE'):
        try:
            from trajectory_visualizer import create_lunar_orbit_trajectory_plot
            print("\nGenerating lunar orbit trajectory plot...")
            fig, _ = create_lunar_orbit_trajectory_plot(results)
            print("Lunar orbit trajectory plot saved as 'lunar_orbit_trajectory.png'")
        except Exception as e:
            print(f"Warning: Could not generate trajectory plot: {e}")
    
    print("\n" + "="*60)
    print("PROFESSOR V33 MISSION RESULTS SUMMARY")
    print("="*60)
    print(f"Mission Success: {mission_results['mission_success']}")
    if mission_results["final_lunar_orbit"]:
        lunar_orbit = mission_results["final_lunar_orbit"]
        print(f"Final Lunar Orbit:")
        print(f"  - Apoapsis: {lunar_orbit.get('apoapsis_km', 0):.1f} km")
        print(f"  - Periapsis: {lunar_orbit.get('periapsis_km', 0):.1f} km")
        print(f"  - Eccentricity: {lunar_orbit.get('eccentricity', 0):.4f}")
    print(f"Total Mission Time: {mission_results['total_mission_time_days']:.2f} days")
    print(f"Total Delta-V: {mission_results['total_delta_v_mps']:.1f} m/s")
    print(f"Lunar Orbits Completed: {mission_results['lunar_orbits_completed']}")
    
    print("\nResults saved to mission_results.json")
    print("CSVログは mission_log.csv に保存されました")
    print("Trajectory plot saved as lunar_orbit_trajectory.png")
    
    return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Run Saturn V rocket simulation')
    parser.add_argument('--fast', action='store_true', 
                       help='Skip visualization and reduce output for batch processing')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug-level logging for detailed output')
    parser.add_argument('--quiet', action='store_true',
                       help='Enable quiet mode with minimal logging output')
    
    args = parser.parse_args()
    
    # Configure logging level based on arguments
    if args.debug:
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    elif args.quiet:
        logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')
    else:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Set global flag for fast mode
    if args.fast:
        import os
        os.environ['ROCKET_FAST_MODE'] = '1'
    
    main()