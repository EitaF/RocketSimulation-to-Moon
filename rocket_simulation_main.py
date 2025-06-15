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

# 大気パラメータ
SEA_LEVEL_PRESSURE = 101325  # 海面気圧 [Pa]
SEA_LEVEL_DENSITY = 1.225  # 海面大気密度 [kg/m^3]
SCALE_HEIGHT = 8500  # 大気のスケールハイト [m]


class MissionPhase(Enum):
    """ミッションフェーズ"""
    PRE_LAUNCH = "pre_launch"
    LAUNCH = "launch"
    GRAVITY_TURN = "gravity_turn"
    STAGE_SEPARATION = "stage_separation"
    APOAPSIS_RAISE = "apoapsis_raise"  # 遠地点上昇燃焼
    COAST_TO_APOAPSIS = "coast_to_apoapsis"  # 遠地点まで慣性飛行
    CIRCULARIZATION = "circularization"  # 軌道円化燃焼
    TRANS_LUNAR_INJECTION = "trans_lunar_injection"
    COAST = "coast"
    LUNAR_ORBIT_INSERTION = "lunar_orbit_insertion"
    LUNAR_LANDING = "lunar_landing"
    LANDED = "landed"
    FAILED = "failed"


class Vector3:
    """3次元ベクトルクラス（計算は2次元で行うが、拡張性のため）"""
    
    def __init__(self, x: float, y: float, z: float = 0.0):
        self.data = np.array([x, y, z])
    
    @property
    def x(self) -> float:
        return self.data[0]
    
    @property
    def y(self) -> float:
        return self.data[1]
    
    @property
    def z(self) -> float:
        return self.data[2]
    
    def magnitude(self) -> float:
        return np.linalg.norm(self.data)
    
    def normalized(self) -> 'Vector3':
        mag = self.magnitude()
        if mag == 0:
            return Vector3(0, 0, 0)
        return Vector3(*(self.data / mag))
    
    def __add__(self, other: 'Vector3') -> 'Vector3':
        return Vector3(*(self.data + other.data))
    
    def __sub__(self, other: 'Vector3') -> 'Vector3':
        return Vector3(*(self.data - other.data))
    
    def __mul__(self, scalar: float) -> 'Vector3':
        return Vector3(*(self.data * scalar))
    
    def __repr__(self) -> str:
        return f"Vector3({self.x:.2e}, {self.y:.2e}, {self.z:.2e})"


@dataclass
class RocketStage:
    """ロケットステージのデータ"""
    name: str
    dry_mass: float  # 乾燥質量 [kg]
    propellant_mass: float  # 推進剤質量 [kg]
    thrust_sea_level: float  # 海面推力 [N]
    thrust_vacuum: float  # 真空推力 [N]
    specific_impulse_sea_level: float  # 海面比推力 [s]
    specific_impulse_vacuum: float  # 真空比推力 [s]
    burn_time: float  # 燃焼時間 [s]
    
    @property
    def total_mass(self) -> float:
        return self.dry_mass + self.propellant_mass
    
    def get_thrust(self, altitude: float) -> float:
        """高度に応じた推力を取得"""
        if altitude < 0:
            return self.thrust_sea_level
        elif altitude > 100e3:  # 100km以上は真空
            return self.thrust_vacuum
        else:
            # 0-100kmで線形補間
            factor = altitude / 100e3
            return self.thrust_sea_level * (1 - factor) + self.thrust_vacuum * factor
    
    def get_specific_impulse(self, altitude: float) -> float:
        """高度に応じた比推力を取得"""
        if altitude < 0:
            return self.specific_impulse_sea_level
        elif altitude > 100e3:  # 100km以上は真空
            return self.specific_impulse_vacuum
        else:
            # 0-100kmで線形補間
            factor = altitude / 100e3
            return self.specific_impulse_sea_level * (1 - factor) + self.specific_impulse_vacuum * factor
    
    def get_mass_flow_rate(self, altitude: float) -> float:
        """高度に応じた質量流量 [kg/s]"""
        thrust = self.get_thrust(altitude)
        isp = self.get_specific_impulse(altitude)
        return thrust / (isp * STANDARD_GRAVITY)
    
    def get_mass_at_time(self, burn_duration: float, altitude: float = 0) -> float:
        """指定時間後の質量を取得（高度考慮）"""
        if burn_duration >= self.burn_time:
            return self.dry_mass
        mass_flow = self.get_mass_flow_rate(altitude)
        return self.total_mass - mass_flow * burn_duration


@dataclass
class Rocket:
    """多段式ロケット"""
    name: str
    stages: List[RocketStage]
    payload_mass: float  # ペイロード質量 [kg]
    drag_coefficient: float = 0.3  # 抗力係数
    cross_sectional_area: float = 10.0  # 断面積 [m^2]
    
    def get_cross_sectional_area(self) -> float:
        """ステージに応じた断面積を取得"""
        if self.current_stage == 0:
            return 80.0  # 第1段: 大型
        elif self.current_stage == 1:
            return 30.0  # 第2段: 中型
        else:
            return 18.0  # 第3段: 小型
    
    # 状態変数
    position: Vector3 = field(default_factory=lambda: Vector3(0, 0))
    velocity: Vector3 = field(default_factory=lambda: Vector3(0, 0))
    current_stage: int = 0
    stage_burn_time: float = 0.0
    stage_total_burn_time: float = 0.0  # Total burn time for multi-burn stages
    phase: MissionPhase = MissionPhase.LAUNCH  # 直接LAUNCHから開始
    
    @property
    def current_mass(self) -> float:
        """現在の総質量"""
        altitude = self.get_altitude()
        mass = self.payload_mass
        for i in range(self.current_stage, len(self.stages)):
            if i == self.current_stage:
                # 第3段の場合は総燃焼時間を使用（多回燃焼対応）
                if i == 2:
                    mass += self.stages[i].get_mass_at_time(self.stage_total_burn_time, altitude)
                else:
                    mass += self.stages[i].get_mass_at_time(self.stage_burn_time, altitude)
            else:
                mass += self.stages[i].total_mass
        return mass
    
    @property
    def is_thrusting(self) -> bool:
        """推進中かどうか"""
        # 推進しないフェーズ
        non_thrusting_phases = [
            MissionPhase.PRE_LAUNCH, 
            MissionPhase.COAST, 
            MissionPhase.COAST_TO_APOAPSIS,
            MissionPhase.LANDED, 
            MissionPhase.FAILED
        ]
        if self.phase in non_thrusting_phases:
            return False
            
        # 第3段の多回燃焼対応: TLIとLOIで別々に燃焼
        if (self.current_stage == 2 and 
            self.phase in [MissionPhase.TRANS_LUNAR_INJECTION, MissionPhase.LUNAR_ORBIT_INSERTION]):
            # TLI: 最初の400秒, LOI: 残りの燃料
            if self.phase == MissionPhase.TRANS_LUNAR_INJECTION:
                return self.stage_burn_time < 450  # TLI用燃焼時間（延長）
            elif self.phase == MissionPhase.LUNAR_ORBIT_INSERTION:
                return self.stage_total_burn_time < self.stages[self.current_stage].burn_time
        
        # 一般的な推進条件
        return (self.current_stage < len(self.stages) and 
                self.stage_burn_time < self.stages[self.current_stage].burn_time)
    
    def get_thrust_vector(self) -> Vector3:
        """推力ベクトルを取得（ガイダンスモジュール使用）"""
        if not self.is_thrusting:
            return Vector3(0, 0)
        
        stage = self.stages[self.current_stage]
        altitude = self.get_altitude()
        thrust_magnitude = stage.get_thrust(altitude)
        
        # ガイダンスモジュールに委託
        return guidance.compute_thrust_direction(self, thrust_magnitude)
    
    def update_stage(self, dt: float):
        """ステージの更新"""
        if self.current_stage >= len(self.stages):
            return
        
        # 推進中の場合のみ燃焼時間を更新
        if self.is_thrusting:
            self.stage_burn_time += dt
            self.stage_total_burn_time += dt
        
        # 第3段の特別処理（TLI完了時にコーストに移行）
        if (self.current_stage == 2 and 
            self.phase == MissionPhase.TRANS_LUNAR_INJECTION and 
            self.stage_burn_time >= 450):  # TLI完了（時間延長）
            self.phase = MissionPhase.COAST
            self.stage_burn_time = 0.0  # LOI用にリセット
            logging.info(f"TLI burn complete. Coasting to Moon...")
            return
        
        # 通常のステージ分離（第3段はより柔軟に処理）
        if self.stage_total_burn_time >= self.stages[self.current_stage].burn_time:
            # ステージのΔvを計算（ロケット方程式 - 修正版）
            stage = self.stages[self.current_stage]
            altitude = self.get_altitude()
            isp = stage.get_specific_impulse(altitude)
            
            # より正確な質量計算（他のステージ含む）
            total_initial_mass = stage.total_mass
            for i in range(self.current_stage + 1, len(self.stages)):
                total_initial_mass += self.stages[i].total_mass
            total_initial_mass += self.payload_mass
            
            total_final_mass = stage.dry_mass
            for i in range(self.current_stage + 1, len(self.stages)):
                total_final_mass += self.stages[i].total_mass
            total_final_mass += self.payload_mass
            
            stage_delta_v = isp * STANDARD_GRAVITY * np.log(total_initial_mass / total_final_mass)
            
            logging.info(f"Stage {self.current_stage + 1} separation at altitude {self.get_altitude()/1000:.1f} km")
            logging.info(f"Stage {self.current_stage + 1} theoretical delta-V: {stage_delta_v:.1f} m/s")
            logging.info(f"Velocity: {self.velocity.magnitude():.0f} m/s, Apoapsis: {(self.get_orbital_elements()[0]-R_EARTH)/1000:.1f} km")
            
            self.current_stage += 1
            self.stage_burn_time = 0.0
            self.stage_total_burn_time = 0.0
            
            if self.current_stage < len(self.stages):
                self.phase = MissionPhase.STAGE_SEPARATION
    
    def get_altitude(self) -> float:
        """高度を取得 [m]"""
        return self.position.magnitude() - R_EARTH
    
    def get_flight_path_angle(self) -> float:
        """飛行経路角を取得 [rad] - 速度ベクトルと局所水平面の角度"""
        # 地心方向（動径方向）の単位ベクトル
        radial_unit = self.position.normalized()
        
        # 速度ベクトルの動径成分
        velocity_radial = self.velocity.data @ radial_unit.data  # ドット積
        
        # 飛行経路角 = arcsin(v_radial / |v|)
        velocity_magnitude = self.velocity.magnitude()
        if velocity_magnitude == 0:
            return 0.0
        
        sin_gamma = velocity_radial / velocity_magnitude
        # アークサインの定義域制限
        sin_gamma = max(-1.0, min(1.0, sin_gamma))
        
        return np.arcsin(sin_gamma)
    
    def get_orbital_elements(self) -> Tuple[float, float, float]:
        """軌道要素を計算: (apoapsis, periapsis, eccentricity) [m, m, -]"""
        r = self.position.magnitude()
        v = self.velocity.magnitude()
        
        # 動径方向と接線方向の速度成分
        radial_unit = self.position.normalized()
        velocity_radial = self.velocity.data @ radial_unit.data
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


@dataclass
class CelestialBody:
    """天体（地球、月）"""
    name: str
    mass: float  # 質量 [kg]
    radius: float  # 半径 [m]
    position: Vector3
    velocity: Vector3 = field(default_factory=lambda: Vector3(0, 0))
    
    def get_gravitational_acceleration(self, position: Vector3) -> Vector3:
        """指定位置での重力加速度を計算"""
        r = position - self.position
        distance = r.magnitude()
        if distance <= self.radius:
            # 表面またはそれより内側では表面重力を使用
            if distance < 0.1:  # 極小値回避
                distance = 0.1
            surface_gravity = G * self.mass / self.radius**2
            return r.normalized() * (-surface_gravity)
        return r.normalized() * (-G * self.mass / distance**2)


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
        self.gravity_turn_altitude = config.get("gravity_turn_altitude", 1e3)  # 重力ターン開始高度を早める
        
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
        self.stage_delta_v_history: List[float] = []  # 各ステージのΔv記録
        
        # CSVログ設定
        self.csv_file = open("mission_log.csv", "w", newline="")
        self.csv_writer = csv.writer(self.csv_file)
        self.csv_writer.writerow(["time", "altitude", "velocity", "mass", "delta_v", "phase", "stage", "apoapsis", "periapsis", "eccentricity"])
        
        # ロガー設定
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
    
    def _initialize_moon(self) -> CelestialBody:
        """月の初期位置を設定"""
        # 簡略化: 月は円軌道上を公転
        moon_pos = Vector3(EARTH_MOON_DIST, 0)
        moon_vel = Vector3(0, 2 * np.pi * EARTH_MOON_DIST / MOON_ORBIT_PERIOD)
        return CelestialBody("Moon", M_MOON, R_MOON, moon_pos, moon_vel)
    
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
        """高度に応じた大気密度を計算（改良版 - より現実的なモデル）"""
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
        altitude = self.rocket.get_altitude()
        density = self._calculate_atmospheric_density(altitude)
        
        if density == 0:
            return Vector3(0, 0)
        
        velocity_magnitude = self.rocket.velocity.magnitude()
        if velocity_magnitude == 0:
            return Vector3(0, 0)
        
        # F_drag = 0.5 * ρ * v^2 * C_d * A（ステージ対応断面積使用）
        cross_sectional_area = self.rocket.get_cross_sectional_area()
        drag_magnitude = 0.5 * density * velocity_magnitude**2 * \
                        self.rocket.drag_coefficient * cross_sectional_area
        
        # 速度と逆方向
        return self.rocket.velocity.normalized() * (-drag_magnitude)
    
    def _calculate_total_acceleration(self) -> Vector3:
        """総加速度を計算"""
        # 重力
        g_earth = self.earth.get_gravitational_acceleration(self.rocket.position)
        g_moon = self.moon.get_gravitational_acceleration(self.rocket.position)
        
        # 推力
        thrust = self.rocket.get_thrust_vector()
        thrust_acceleration = thrust * (1.0 / self.rocket.current_mass) if self.rocket.current_mass > 0 else Vector3(0, 0)
        
        # 空気抵抗
        drag = self._calculate_drag_force()
        drag_acceleration = drag * (1.0 / self.rocket.current_mass) if self.rocket.current_mass > 0 else Vector3(0, 0)
        
        total_accel = g_earth + g_moon + thrust_acceleration + drag_acceleration
        
        return total_accel
    
    def _update_mission_phase(self):
        """ミッションフェーズを更新（改良版 - 正しい軌道力学に基づく）"""
        altitude = self.rocket.get_altitude()
        velocity = self.rocket.velocity.magnitude()
        apoapsis, periapsis, eccentricity = self.rocket.get_orbital_elements()
        
        # 目標軌道速度を計算
        target_radius = R_EARTH + self.target_parking_orbit
        target_orbital_velocity = np.sqrt(G * M_EARTH / target_radius)
        
        if self.rocket.phase == MissionPhase.LAUNCH:
            # 重力ターン開始を早める
            if altitude >= self.gravity_turn_altitude:
                self.rocket.phase = MissionPhase.GRAVITY_TURN
                self.logger.info(f"Gravity turn initiated at altitude {altitude/1000:.1f} km")
                
        elif self.rocket.phase == MissionPhase.GRAVITY_TURN:
            # 重力ターンは第1段燃焼終了まで継続
            pass
                
        elif self.rocket.phase == MissionPhase.APOAPSIS_RAISE:
            # 修正：軌道達成まで継続（より積極的）
            current_radius = self.rocket.position.magnitude()
            current_orbital_velocity = np.sqrt(G * M_EARTH / current_radius)
            
            # 軌道達成条件をより厳格に（安定軌道のため）
            orbital_achieved = (velocity >= target_orbital_velocity * 0.90 and 
                              apoapsis >= target_radius * 0.9 and
                              periapsis >= R_EARTH)  # 負の近地点を防ぐ
            
            # 燃料切れ、または軌道達成時に次のフェーズへ
            if not self.rocket.is_thrusting or orbital_achieved:
                if orbital_achieved:
                    self.rocket.phase = MissionPhase.COAST_TO_APOAPSIS
                    self.logger.info(f"Orbital trajectory achieved: v={velocity:.0f} m/s (target: {target_orbital_velocity:.0f} m/s)")
                    self.logger.info(f"Apoapsis: {(apoapsis-R_EARTH)/1000:.1f} km, Periapsis: {(periapsis-R_EARTH)/1000:.1f} km")
                else:
                    # 燃料切れで軌道未達成の場合
                    if periapsis > R_EARTH:
                        self.rocket.phase = MissionPhase.COAST
                        self.logger.warning(f"Fuel depleted but stable orbit achieved. e={eccentricity:.3f}")
                    else:
                        self.rocket.phase = MissionPhase.FAILED
                        self.logger.error(f"Fuel depleted, suborbital trajectory. Mission failed.")
                
        elif self.rocket.phase == MissionPhase.COAST_TO_APOAPSIS:
            # 遠地点付近に到達したら円化燃焼開始
            radial_velocity = self.rocket.velocity.data @ self.rocket.position.normalized().data
            current_radius = self.rocket.position.magnitude()
            
            # 遠地点に近づいた判定
            if abs(radial_velocity) < 50 and current_radius >= (apoapsis - R_EARTH) * 0.95 + R_EARTH:
                if self.rocket.current_stage <= 2 and self.rocket.stages[self.rocket.current_stage].propellant_mass > 0:
                    self.rocket.phase = MissionPhase.CIRCULARIZATION
                    self.logger.info(f"Starting circularization burn at apoapsis {altitude/1000:.1f} km")
                else:
                    self.rocket.phase = MissionPhase.COAST
                    self.logger.info(f"Elliptical orbit achieved. e={eccentricity:.3f}")
                
        elif self.rocket.phase == MissionPhase.CIRCULARIZATION:
            # 軌道円化完了の判定
            target_periapsis = R_EARTH + self.target_parking_orbit * 0.85
            if periapsis >= target_periapsis or not self.rocket.is_thrusting:
                self.rocket.phase = MissionPhase.COAST
                self.logger.info(f"Parking orbit achieved! Apoapsis: {(apoapsis-R_EARTH)/1000:.1f} km, "
                               f"Periapsis: {(periapsis-R_EARTH)/1000:.1f} km, e={eccentricity:.3f}")
                
        elif self.rocket.phase == MissionPhase.COAST:
            # TLIタイミングの判定（改良版 - 軌道確認後に実行）
            coast_time = len([p for p in self.phase_history if p == MissionPhase.COAST]) * 0.1  # dt=0.1
            
            # 駐機軌道の確認
            parking_orbit_ok = (periapsis >= (R_EARTH + 150e3) and 
                              apoapsis >= (R_EARTH + 150e3) and 
                              eccentricity < 0.1)
            
            # 第3段が利用可能で、駐機軌道が達成されている場合のみTLI
            if (self.rocket.current_stage == 2 and 
                parking_orbit_ok and 
                coast_time > 300 and  # 5分後（短縮）
                self.rocket.stages[2].propellant_mass > 50000):  # 十分な燃料
                
                # TLI必要速度の概算
                current_velocity = self.rocket.velocity.magnitude()
                earth_escape_velocity = np.sqrt(2 * G * M_EARTH / self.rocket.position.magnitude())
                tli_delta_v_required = earth_escape_velocity - current_velocity + 3200  # 月まで3.2km/s追加
                
                # 第3段の残Δv概算
                stage3 = self.rocket.stages[2]
                current_mass = self.rocket.current_mass
                final_mass = current_mass - stage3.propellant_mass
                available_delta_v = stage3.specific_impulse_vacuum * STANDARD_GRAVITY * np.log(current_mass / final_mass)
                
                self.logger.info(f"TLI Check: Required {tli_delta_v_required:.0f} m/s, Available {available_delta_v:.0f} m/s")
                
                if available_delta_v >= tli_delta_v_required * 0.9:  # 90%のマージン
                    # 月方向への最適なタイミングを簡略計算
                    to_moon = self.moon.position - self.rocket.position
                    velocity_dir = self.rocket.velocity.normalized()
                    angle = np.arccos(np.clip(velocity_dir.data @ to_moon.normalized().data, -1, 1))
                    if angle < np.pi/3:  # 60度以内
                        self.rocket.phase = MissionPhase.TRANS_LUNAR_INJECTION
                        self.logger.info("Initiating Trans-Lunar Injection burn!")
                elif coast_time > 3600:  # 1時間経過したら強制実行
                    self.rocket.phase = MissionPhase.TRANS_LUNAR_INJECTION
                    self.logger.warning(f"Forcing TLI despite insufficient delta-V")
                
        elif self.rocket.phase == MissionPhase.STAGE_SEPARATION:
            # ステージ分離後の正しい遷移（修正版）
            if self.rocket.current_stage == 0:  # 第1段分離後
                self.rocket.phase = MissionPhase.APOAPSIS_RAISE
                self.logger.info(f"Stage 2 ignition for apoapsis raise")
            elif self.rocket.current_stage == 1:  # 第2段分離後
                # 第3段は常にAPOAPSIS_RAISEに遷移（燃料切れまで推進）
                self.rocket.phase = MissionPhase.APOAPSIS_RAISE
                self.logger.info(f"Stage 3 continuing apoapsis raise")
            elif self.rocket.current_stage == 2:  # 第3段分離後
                # 軌道状態を確認してCOASTまたはTLIへ
                self.rocket.phase = MissionPhase.COAST
                self.logger.info(f"All stages separated. Final orbit check pending.")
            else:
                self.rocket.phase = MissionPhase.COAST
    
    def _check_mission_status(self) -> bool:
        """ミッション状態をチェック（継続/終了）"""
        altitude = self.rocket.get_altitude()
        distance_to_moon = (self.rocket.position - self.moon.position).magnitude()
        
        # 地球に衝突
        if altitude < -10e3:  # 10km以下（地下）なら確実に衝突
            self.rocket.phase = MissionPhase.FAILED
            self.logger.error("Mission failed: Crashed into Earth")
            return False
        
        # 月の影響圏チェック
        moon_soi_radius = 66e3  # 月の影響圏半径 [km]
        if distance_to_moon < moon_soi_radius * 1000 and self.rocket.phase == MissionPhase.COAST:
            if self.rocket.current_stage == 2:  # 第3段が残っている
                self.rocket.phase = MissionPhase.LUNAR_ORBIT_INSERTION
                self.logger.info(f"Entering Moon's sphere of influence at {distance_to_moon/1000:.0f} km")
        
        # 月面着陸
        if distance_to_moon <= R_MOON + 1000:  # 月面から1km以内
            # 速度チェック（軟着陸判定）
            relative_velocity = (self.rocket.velocity - self.moon.velocity).magnitude()
            if relative_velocity < 100:  # 100 m/s以下なら成功
                self.rocket.phase = MissionPhase.LANDED
                self.logger.info(f"Successfully landed on the Moon! Landing velocity: {relative_velocity:.1f} m/s")
                return False
            else:
                self.rocket.phase = MissionPhase.FAILED
                self.logger.error(f"Crashed into Moon at {relative_velocity:.0f} m/s")
                return False
        
        return True
    
    def simulate(self, duration: float = 10 * 24 * 3600, dt: float = 0.1) -> Dict:
        """シミュレーション実行"""
        t = 0.0
        steps = 0
        
        # ロケット初期位置（地球表面、緯度を考慮）
        launch_latitude = self.config.get("launch_latitude", 28.5)  # ケネディ宇宙センター
        launch_angle = np.radians(launch_latitude)
        # 地球表面の位置
        self.rocket.position = Vector3(R_EARTH * np.cos(launch_angle), R_EARTH * np.sin(launch_angle))
        
        # 地球自転による初速度（東向き）
        surface_velocity = 2 * np.pi * R_EARTH * np.cos(launch_angle) / EARTH_ROTATION_PERIOD
        # 東向きは y方向の負（座標系の設定による）
        self.rocket.velocity = Vector3(-surface_velocity * np.sin(launch_angle), surface_velocity * np.cos(launch_angle))
        
        self.logger.info(f"Mission start: {self.rocket.name}")
        self.logger.info(f"Initial position: {self.rocket.position}")
        self.logger.info(f"Initial velocity: {self.rocket.velocity.magnitude():.1f} m/s")
        self.logger.info(f"Total rocket mass: {self.rocket.current_mass/1000:.1f} tons")
        
        # 初期フェーズ確認
        self.rocket.phase = MissionPhase.LAUNCH
        
        # RK4法による数値積分
        while t < duration and self._check_mission_status():
            # フェーズ更新を最初に実行（重要：積分前に実行）
            self._update_mission_phase()
            
            # 記録
            self.time_history.append(t)
            self.position_history.append(self.rocket.position)
            self.velocity_history.append(self.rocket.velocity)
            altitude = self.rocket.get_altitude()
            velocity = self.rocket.velocity.magnitude()
            mass = self.rocket.current_mass
            apoapsis, periapsis, eccentricity = self.rocket.get_orbital_elements()
            self.altitude_history.append(altitude)
            self.mass_history.append(mass)
            self.phase_history.append(self.rocket.phase)
            
            # CSVログ出力（10秒ごと）
            if steps % 100 == 0:  # dt=0.1なので100ステップ=10秒
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
                    f"{eccentricity:.3f}"
                ])
                self.csv_file.flush()
            
            # 統計更新
            self.max_altitude = max(self.max_altitude, altitude)
            self.max_velocity = max(self.max_velocity, velocity)
            
            # RK4積分
            # k1: 現在の状態での微分
            k1_v = self._calculate_total_acceleration()
            k1_r = self.rocket.velocity
            
            # 状態の完全コピーを保存
            orig_pos = Vector3(self.rocket.position.x, self.rocket.position.y, self.rocket.position.z)
            orig_vel = Vector3(self.rocket.velocity.x, self.rocket.velocity.y, self.rocket.velocity.z)
            
            # k2: dt/2での状態での微分
            self.rocket.position = orig_pos + k1_r * (dt/2)
            self.rocket.velocity = orig_vel + k1_v * (dt/2)
            k2_v = self._calculate_total_acceleration()
            k2_r = self.rocket.velocity
            
            # k3: dt/2での状態（k2使用）での微分
            self.rocket.position = orig_pos + k2_r * (dt/2)
            self.rocket.velocity = orig_vel + k2_v * (dt/2)
            k3_v = self._calculate_total_acceleration()
            k3_r = self.rocket.velocity
            
            # k4: dtでの状態（k3使用）での微分
            self.rocket.position = orig_pos + k3_r * dt
            self.rocket.velocity = orig_vel + k3_v * dt
            k4_v = self._calculate_total_acceleration()
            k4_r = self.rocket.velocity
            
            # 最終状態更新（RK4公式）
            self.rocket.velocity = orig_vel + (k1_v + k2_v * 2 + k3_v * 2 + k4_v) * (dt/6)
            self.rocket.position = orig_pos + (k1_r + k2_r * 2 + k3_r * 2 + k4_r) * (dt/6)
            
            # その他の更新
            self._update_moon_position(dt)
            self.rocket.update_stage(dt)
            
            # デルタV計算（推進時のみ - より正確な計算）
            if self.rocket.is_thrusting:
                thrust_magnitude = self.rocket.get_thrust_vector().magnitude()
                if thrust_magnitude > 0 and self.rocket.current_mass > 0:
                    accel = thrust_magnitude / self.rocket.current_mass
                    delta_v_increment = accel * dt
                    self.total_delta_v += delta_v_increment
            
            t += dt
            steps += 1
            
            # 定期的な状態出力（1000秒ごと）
            if steps % 10000 == 0:
                self.logger.info(f"t={t/3600:.1f}h, alt={altitude/1000:.1f}km, "
                                f"v={velocity:.0f}m/s, ΔV={self.total_delta_v:.0f}m/s, "
                                f"phase={self.rocket.phase.value}")
        
        # 最終記録
        self.time_history.append(t)
        self.position_history.append(self.rocket.position)
        self.velocity_history.append(self.rocket.velocity)
        self.altitude_history.append(self.rocket.get_altitude())
        self.mass_history.append(self.rocket.current_mass)
        self.phase_history.append(self.rocket.phase)
        
        # CSVファイルを閉じる
        self.csv_file.close()
        
        return self._compile_results()
    
    def _compile_results(self) -> Dict:
        """シミュレーション結果をまとめる"""
        return {
            "mission_success": self.rocket.phase == MissionPhase.LANDED,
            "final_phase": self.rocket.phase.value,
            "mission_duration": self.time_history[-1] if self.time_history else 0,
            "max_altitude": self.max_altitude,
            "max_velocity": self.max_velocity,
            "total_delta_v": self.total_delta_v,
            "final_mass": self.rocket.current_mass,
            "propellant_used": sum(stage.propellant_mass for stage in self.rocket.stages),
            "time_history": self.time_history,
            "position_history": [(p.x, p.y) for p in self.position_history],
            "velocity_history": [(v.x, v.y) for v in self.velocity_history],
            "altitude_history": self.altitude_history,
            "mass_history": self.mass_history,
            "phase_history": [p.value for p in self.phase_history]
        }


def create_saturn_v_rocket() -> Rocket:
    """サターンVロケット（修正版）- 軌道達成のための最適化パラメータ"""
    stages = [
        RocketStage(
            name="S-IC (1st Stage)",
            dry_mass=131000,  # kg
            propellant_mass=2150000,  # kg
            thrust_sea_level=37.4e6,  # N (海面推力 +10%)
            thrust_vacuum=38.6e6,  # N (真空推力 +10%)
            specific_impulse_sea_level=263,  # s (海面Isp)
            specific_impulse_vacuum=289,  # s (真空Isp)
            burn_time=162  # s (実際の燃焼時間)
        ),
        RocketStage(
            name="S-II (2nd Stage)",
            dry_mass=39000,  # kg
            propellant_mass=480000,  # kg (燃料さらに増量)
            thrust_sea_level=4.4e6,  # N (海面推力)
            thrust_vacuum=5.2e6,  # N (真空推力 - 強化)
            specific_impulse_sea_level=395,  # s (海面Isp)
            specific_impulse_vacuum=421,  # s (真空Isp)
            burn_time=410  # s (燃焼時間さらに延長)
        ),
        RocketStage(
            name="S-IVB (3rd Stage)",
            dry_mass=15610,  # kg (で2%の燃料をドライマスに移動)
            propellant_mass=112700,  # kg (プロフェッサー推奨2%減)
            thrust_sea_level=825000,  # N (海面推力)
            thrust_vacuum=1033000,  # N (真空推力)
            specific_impulse_sea_level=430,  # s (海面Isp)
            specific_impulse_vacuum=460,  # s (真空Isp プロフェッサー推奨460s)
            burn_time=750  # s (TLI + LOI用の総燃焼時間)
        )
    ]
    
    return Rocket(
        name="Saturn V",
        stages=stages,
        payload_mass=43000,  # Apollo CSM + LM (少し軽量化)
        drag_coefficient=0.3,
        cross_sectional_area=80.0  # m^2
    )


def main():
    """メインエントリーポイント"""
    # 設定ファイル読み込み（存在する場合）
    try:
        with open("mission_config.json", "r") as f:
            config = json.load(f)
    except FileNotFoundError:
        config = {
            "launch_latitude": 28.573,  # ケネディ宇宙センター
            "launch_azimuth": 90,  # 東向き
            "target_parking_orbit": 185e3,  # 185 km
            "gravity_turn_altitude": 1e3,  # 1 km (早期開始)
            "simulation_duration": 10 * 24 * 3600,  # 10日間
            "time_step": 0.1  # 0.1秒（高精度）
        }
    
    # ロケット作成
    rocket = create_saturn_v_rocket()
    
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
    
    # 結果を保存
    with open("mission_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print("\nResults saved to mission_results.json")
    print("CSVログは mission_log.csv に保存されました")
    print("Run visualizer.py to see the trajectory visualization")


if __name__ == "__main__":
    main()