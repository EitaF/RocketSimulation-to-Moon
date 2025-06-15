"""
Rocket Trajectory Visualizer
ロケット軌道の可視化スクリプト

インタラクティブな2D軌道表示とリアルタイムアニメーション機能を提供
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.patches import Circle, FancyBboxPatch, Rectangle
from matplotlib.collections import LineCollection
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
import json
import sys
import os
from typing import Dict, List, Tuple, Optional
import argparse
from matplotlib.image import imread


class TrajectoryVisualizer:
    """軌道可視化クラス"""
    
    def __init__(self, results_file: str = "mission_results.json", 
                 config_file: str = "mission_config.json"):
        # データ読み込み
        try:
            with open(results_file, "r") as f:
                self.results = json.load(f)
        except FileNotFoundError:
            print(f"Error: {results_file} not found!")
            print("Please run 'python3 rocket_simulation.py' first to generate simulation data.")
            sys.exit(1)
        
        try:
            with open(config_file, "r") as f:
                self.config = json.load(f)
        except FileNotFoundError:
            self.config = {}
        
        # 必要なデータの存在確認
        required_keys = ["position_history", "time_history", "altitude_history", 
                        "velocity_history", "mass_history", "phase_history"]
        missing_keys = [key for key in required_keys if key not in self.results]
        
        if missing_keys:
            print(f"Error: Missing required data in {results_file}: {missing_keys}")
            print("Please run 'python3 rocket_simulation.py' again to generate complete data.")
            sys.exit(1)
        
        # 座標データを numpy 配列に変換
        self.positions = np.array(self.results["position_history"])
        self.times = np.array(self.results["time_history"])
        self.altitudes = np.array(self.results["altitude_history"])
        self.velocities = np.array(self.results["velocity_history"])
        self.masses = np.array(self.results["mass_history"])
        self.phases = self.results["phase_history"]
        
        # 定数
        self.R_EARTH = 6371e3
        self.R_MOON = 1737e3
        self.EARTH_MOON_DIST = 384400e3
        self.MOON_ORBIT_PERIOD = 27.321661 * 24 * 3600
        
        # カラーマップ（フェーズごと）- より濃い色で視認性向上
        self.phase_colors = {
            "pre_launch": "#606060",
            "launch": "#CC0000",
            "gravity_turn": "#FF6600",
            "stage_separation": "#CCCC00",
            "orbit_insertion": "#009900",
            "trans_lunar_injection": "#0099CC",
            "coast": "#0066CC",
            "lunar_orbit_insertion": "#CC00CC",
            "landed": "#009900",
            "failed": "#CC0000"
        }
        
        # 画像アセットを読み込み
        self.images = self._load_images()
    
    def _load_images(self) -> Dict:
        """画像ファイルを読み込み"""
        images = {}
        
        # 画像ファイルのパス
        image_files = {
            'earth': 'Earth_Image.png',
            'moon': 'Moon_Image.png', 
            'rocket': 'Rocket_Image.png'
        }
        
        for key, filename in image_files.items():
            try:
                if os.path.exists(filename):
                    images[key] = imread(filename)
                    print(f"Loaded {key} image: {filename}")
                else:
                    images[key] = None
                    print(f"Warning: {filename} not found")
            except Exception as e:
                images[key] = None
                print(f"Error loading {filename}: {e}")
        
        return images
    
    def create_figure(self) -> Tuple[plt.Figure, Dict]:
        """メイン図を作成"""
        fig = plt.figure(figsize=(16, 10), facecolor='#f8f8f8')
        
        # サブプロットレイアウト
        gs = fig.add_gridspec(3, 3, height_ratios=[2, 1, 1], width_ratios=[2, 1, 1],
                             hspace=0.3, wspace=0.3)
        
        axes = {
            'trajectory': fig.add_subplot(gs[0, :]),  # メイン軌道図
            'altitude': fig.add_subplot(gs[1, 0]),    # 高度プロファイル
            'velocity': fig.add_subplot(gs[1, 1]),    # 速度プロファイル
            'mass': fig.add_subplot(gs[1, 2]),        # 質量変化
            'phase': fig.add_subplot(gs[2, 0]),       # フェーズタイムライン
            'info': fig.add_subplot(gs[2, 1:])        # 情報パネル
        }
        
        # 背景色設定 - 明るい背景に変更
        for ax in axes.values():
            ax.set_facecolor('#f8f8f8')
        
        return fig, axes
    
    def setup_trajectory_plot(self, ax):
        """軌道プロットの設定"""
        ax.set_aspect('equal')
        ax.set_xlim(-self.EARTH_MOON_DIST * 1.2, self.EARTH_MOON_DIST * 1.2)
        ax.set_ylim(-self.EARTH_MOON_DIST * 0.6, self.EARTH_MOON_DIST * 0.6)
        ax.set_xlabel('Distance [km]', color='black', fontsize=12, fontweight='bold')
        ax.set_ylabel('Distance [km]', color='black', fontsize=12, fontweight='bold')
        ax.set_title('Earth-Moon Trajectory', color='black', fontsize=16, pad=20, fontweight='bold')
        ax.grid(True, alpha=0.5, color='gray')
        ax.tick_params(colors='black')
        
        # 地球を描画 (画像の代わりに円を使用)
        earth = Circle((0, 0), self.R_EARTH*2, color='#4169E1', zorder=10, alpha=0.8)
        ax.add_patch(earth)
        ax.text(0, 0, 'Earth', color='white', ha='center', va='center', fontsize=12, fontweight='bold')
        
        # スケール表示用の目盛り調整
        ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1000:.0f}'))
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1000:.0f}'))
    
    def setup_altitude_plot(self, ax):
        """高度プロファイルの設定"""
        ax.set_xlabel('Time [hours]', color='black', fontweight='bold')
        ax.set_ylabel('Altitude [km]', color='black', fontweight='bold')
        ax.set_title('Altitude Profile', color='black', fontweight='bold')
        ax.grid(True, alpha=0.5, color='gray')
        ax.tick_params(colors='black')
        ax.set_xlim(0, self.times[-1] / 3600)
        ax.set_ylim(0, max(self.altitudes) / 1000 * 1.1)
    
    def setup_velocity_plot(self, ax):
        """速度プロファイルの設定"""
        ax.set_xlabel('Time [hours]', color='black', fontweight='bold')
        ax.set_ylabel('Velocity [km/s]', color='black', fontweight='bold')
        ax.set_title('Velocity Profile', color='black', fontweight='bold')
        ax.grid(True, alpha=0.5, color='gray')
        ax.tick_params(colors='black')
        ax.set_xlim(0, self.times[-1] / 3600)
        
        # 速度の大きさを計算
        self.velocity_magnitudes = np.sqrt(np.sum(np.array(self.velocities)**2, axis=1))
        ax.set_ylim(0, max(self.velocity_magnitudes) / 1000 * 1.1)
    
    def setup_mass_plot(self, ax):
        """質量変化の設定"""
        ax.set_xlabel('Time [hours]', color='black', fontweight='bold')
        ax.set_ylabel('Mass [tons]', color='black', fontweight='bold')
        ax.set_title('Mass Profile', color='black', fontweight='bold')
        ax.grid(True, alpha=0.5, color='gray')
        ax.tick_params(colors='black')
        ax.set_xlim(0, self.times[-1] / 3600)
        ax.set_ylim(0, max(self.masses) / 1000 * 1.1)
    
    def setup_phase_plot(self, ax):
        """フェーズタイムラインの設定"""
        ax.set_xlabel('Time [hours]', color='black', fontweight='bold')
        ax.set_title('Mission Phases', color='black', fontweight='bold')
        ax.set_xlim(0, self.times[-1] / 3600)
        ax.set_ylim(-0.5, 1.5)
        ax.set_yticks([])
        ax.tick_params(colors='black')
    
    def setup_info_panel(self, ax):
        """情報パネルの設定"""
        ax.axis('off')
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        
        # ミッション情報のテキスト
        info_text = f"""Mission Status: {self.results['final_phase']}
Max Altitude: {self.results['max_altitude']/1000:.1f} km
Max Velocity: {self.results['max_velocity']:.1f} m/s
Total ΔV: {self.results['total_delta_v']:.1f} m/s
Propellant Used: {self.results['propellant_used']/1000:.1f} tons"""
        
        ax.text(0.05, 0.95, info_text, color='black', fontsize=12, 
                va='top', ha='left', family='monospace', fontweight='bold',
                bbox=dict(boxstyle="round,pad=0.5", facecolor='#e0e0e0', alpha=0.9, edgecolor='black'))
    
    def animate_trajectory(self, save_animation: bool = False):
        """軌道アニメーションを作成"""
        fig, axes = self.create_figure()
        
        # 各プロットの初期設定
        self.setup_trajectory_plot(axes['trajectory'])
        self.setup_altitude_plot(axes['altitude'])
        self.setup_velocity_plot(axes['velocity'])
        self.setup_mass_plot(axes['mass'])
        self.setup_phase_plot(axes['phase'])
        self.setup_info_panel(axes['info'])
        
        # アニメーション用要素
        # 軌道の軌跡
        self.trail_line, = axes['trajectory'].plot([], [], 'red', alpha=0.8, linewidth=3)
        
        # ロケット位置 (アニメーション用)
        if self.images['rocket'] is not None:
            # ロケット画像をアニメーション用に準備
            rocket_size = self.R_EARTH * 0.8
            self.rocket_imagebox = OffsetImage(self.images['rocket'], zoom=rocket_size/max(self.images['rocket'].shape))
            self.rocket_ab = AnnotationBbox(self.rocket_imagebox, (0, self.R_EARTH), frameon=False, zorder=20)
            axes['trajectory'].add_artist(self.rocket_ab)
            self.rocket_marker = None  # 画像使用時はマーカーを使わない
        else:
            # フォールバック: 赤い点
            self.rocket_marker, = axes['trajectory'].plot([], [], 'ro', markersize=8, zorder=20)
            self.rocket_ab = None
        
        # 月 (アニメーション用)
        if self.images['moon'] is not None:
            # 月画像をアニメーション用に準備
            moon_size = self.R_MOON * 30
            self.moon_imagebox = OffsetImage(self.images['moon'], zoom=moon_size/max(self.images['moon'].shape))
            self.moon_ab = AnnotationBbox(self.moon_imagebox, (self.EARTH_MOON_DIST, 0), frameon=False, zorder=9)
            axes['trajectory'].add_artist(self.moon_ab)
            self.moon_circle = None  # 画像使用時は円を使わない
        else:
            # フォールバック: 円
            self.moon_circle = Circle((0, 0), self.R_MOON * 10, color='#C0C0C0', zorder=9)
            axes['trajectory'].add_patch(self.moon_circle)
            self.moon_ab = None
        
        # プロファイルライン
        self.altitude_line, = axes['altitude'].plot([], [], 'green', linewidth=3)
        self.velocity_line, = axes['velocity'].plot([], [], 'blue', linewidth=3)
        self.mass_line, = axes['mass'].plot([], [], 'red', linewidth=3)
        
        # フェーズバー
        self.phase_bars = []
        
        # 現在時刻表示
        self.time_text = axes['trajectory'].text(0.02, 0.98, '', transform=axes['trajectory'].transAxes,
                                                color='black', fontsize=14, va='top', fontweight='bold',
                                                bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.9, edgecolor='black'))
        
        def init():
            """アニメーション初期化"""
            self.trail_line.set_data([], [])
            if self.rocket_marker is not None:
                self.rocket_marker.set_data([], [])
            self.altitude_line.set_data([], [])
            self.velocity_line.set_data([], [])
            self.mass_line.set_data([], [])
            
            return_list = [self.trail_line, self.altitude_line, self.velocity_line, self.mass_line, self.time_text]
            if self.rocket_marker is not None:
                return_list.append(self.rocket_marker)
            if self.moon_circle is not None:
                return_list.append(self.moon_circle)
            return return_list
        
        def update(frame):
            """アニメーション更新"""
            # スキップ設定（高速化のため）
            skip = max(1, len(self.times) // 1000)
            idx = frame * skip
            
            if idx >= len(self.times):
                idx = len(self.times) - 1
            
            # 現在時刻
            current_time = self.times[idx]
            
            # 月の位置更新
            moon_angle = 2 * np.pi * current_time / self.MOON_ORBIT_PERIOD
            moon_x = self.EARTH_MOON_DIST * np.cos(moon_angle)
            moon_y = self.EARTH_MOON_DIST * np.sin(moon_angle)
            
            if self.moon_circle is not None:
                self.moon_circle.center = (moon_x, moon_y)
            elif self.moon_ab is not None:
                self.moon_ab.xybox = (moon_x, moon_y)
            
            # ロケット軌跡
            trail_start = max(0, idx - 500)  # 最近500点のみ表示
            self.trail_line.set_data(self.positions[trail_start:idx+1, 0], 
                                   self.positions[trail_start:idx+1, 1])
            
            # ロケット位置
            if self.rocket_marker is not None:
                self.rocket_marker.set_data([self.positions[idx, 0]], [self.positions[idx, 1]])
            elif self.rocket_ab is not None:
                self.rocket_ab.xybox = (self.positions[idx, 0], self.positions[idx, 1])
            
            # プロファイル更新
            time_hours = self.times[:idx+1] / 3600
            self.altitude_line.set_data(time_hours, self.altitudes[:idx+1] / 1000)
            self.velocity_line.set_data(time_hours, self.velocity_magnitudes[:idx+1] / 1000)
            self.mass_line.set_data(time_hours, self.masses[:idx+1] / 1000)
            
            # フェーズバー更新
            if idx > 0 and self.phases[idx] != self.phases[idx-1]:
                # 新しいフェーズの開始
                phase_color = self.phase_colors.get(self.phases[idx], '#FFFFFF')
                bar_start = self.times[idx] / 3600
                bar_width = 0.5
                bar = Rectangle((bar_start, 0), bar_width, 1, 
                              facecolor=phase_color, alpha=0.7)
                axes['phase'].add_patch(bar)
                self.phase_bars.append(bar)
                
                # フェーズ名表示
                axes['phase'].text(bar_start + bar_width/2, 0.5, self.phases[idx], 
                                 rotation=90, ha='center', va='center', 
                                 fontsize=8, color='black', fontweight='bold')
            
            # 時刻表示更新
            self.time_text.set_text(f'T+{current_time/3600:.1f} hours\n'
                                  f'Alt: {self.altitudes[idx]/1000:.1f} km\n'
                                  f'Vel: {self.velocity_magnitudes[idx]:.1f} m/s\n'
                                  f'Phase: {self.phases[idx]}')
            
            return_list = [self.trail_line, self.altitude_line, self.velocity_line, self.mass_line, self.time_text]
            if self.rocket_marker is not None:
                return_list.append(self.rocket_marker)
            if self.moon_circle is not None:
                return_list.append(self.moon_circle)
            return return_list
        
        # アニメーション作成
        total_frames = min(len(self.times) // max(1, len(self.times) // 1000), 1000)
        anim = animation.FuncAnimation(fig, update, init_func=init, 
                                     frames=total_frames, interval=50, 
                                     blit=True, repeat=True)
        
        if save_animation:
            print("Saving animation... (this may take a while)")
            anim.save('rocket_trajectory.mp4', writer='ffmpeg', fps=30, 
                     bitrate=2000, dpi=100)
            print("Animation saved as rocket_trajectory.mp4")
        
        plt.show()
    
    def create_static_plots(self):
        """静的なプロットを作成"""
        fig, axes = self.create_figure()
        
        # 各プロットの設定
        self.setup_trajectory_plot(axes['trajectory'])
        self.setup_altitude_plot(axes['altitude'])
        self.setup_velocity_plot(axes['velocity'])
        self.setup_mass_plot(axes['mass'])
        self.setup_phase_plot(axes['phase'])
        self.setup_info_panel(axes['info'])
        
        # 軌道全体を描画
        # フェーズごとに色分け
        for i in range(len(self.phases)):
            if i == 0 or self.phases[i] != self.phases[i-1]:
                # 新しいフェーズの開始点を探す
                start_idx = i
                phase = self.phases[i]
                color = self.phase_colors.get(phase, '#FFFFFF')
                
                # 終了点を探す
                end_idx = start_idx
                while end_idx < len(self.phases) - 1 and self.phases[end_idx] == phase:
                    end_idx += 1
                
                # フェーズの軌道を描画
                axes['trajectory'].plot(self.positions[start_idx:end_idx+1, 0], 
                                      self.positions[start_idx:end_idx+1, 1], 
                                      color=color, linewidth=3, alpha=0.9, 
                                      label=phase.replace('_', ' ').title())
        
        # 月の軌道
        moon_orbit_angles = np.linspace(0, 2*np.pi, 100)
        moon_orbit_x = self.EARTH_MOON_DIST * np.cos(moon_orbit_angles)
        moon_orbit_y = self.EARTH_MOON_DIST * np.sin(moon_orbit_angles)
        axes['trajectory'].plot(moon_orbit_x, moon_orbit_y, '#666666', 
                              linestyle='--', alpha=0.7, linewidth=2, label='Moon Orbit')
        
        # 最終的な月の位置
        final_time = self.times[-1]
        moon_angle = 2 * np.pi * final_time / self.MOON_ORBIT_PERIOD
        moon_x = self.EARTH_MOON_DIST * np.cos(moon_angle)
        moon_y = self.EARTH_MOON_DIST * np.sin(moon_angle)
        
        # 月を描画 (画像の代わりに円を使用)
        moon = Circle((moon_x, moon_y), self.R_MOON * 20, color='#C0C0C0', zorder=9, alpha=0.8)
        axes['trajectory'].add_patch(moon)
        axes['trajectory'].text(moon_x, moon_y, 'Moon', color='black', 
                              ha='center', va='center', fontsize=12, fontweight='bold')
        
        # 最終ロケット位置
        if len(self.positions) > 0:
            final_rocket_x = self.positions[-1, 0]
            final_rocket_y = self.positions[-1, 1]
            
            # ロケット位置をマーカーで表示
            axes['trajectory'].plot(final_rocket_x, final_rocket_y, 'ro', markersize=12, zorder=20, markeredgecolor='black', markeredgewidth=2)
            axes['trajectory'].text(final_rocket_x, final_rocket_y + self.R_EARTH*3, 'Rocket', color='black', 
                                  ha='center', va='bottom', fontsize=10, fontweight='bold')
        
        # 凡例
        axes['trajectory'].legend(loc='upper right', facecolor='white', 
                                edgecolor='black', labelcolor='black')
        
        # プロファイルプロット
        time_hours = self.times / 3600
        axes['altitude'].plot(time_hours, self.altitudes / 1000, 'green', linewidth=3)
        axes['velocity'].plot(time_hours, self.velocity_magnitudes / 1000, 'blue', linewidth=3)
        axes['mass'].plot(time_hours, self.masses / 1000, 'red', linewidth=3)
        
        # フェーズタイムライン
        current_phase = None
        phase_start = 0
        for i, (t, phase) in enumerate(zip(self.times, self.phases)):
            if phase != current_phase:
                if current_phase is not None:
                    # 前のフェーズを描画
                    color = self.phase_colors.get(current_phase, '#FFFFFF')
                    bar_width = (t - phase_start) / 3600
                    bar = Rectangle((phase_start / 3600, 0), bar_width, 1,
                                  facecolor=color, alpha=0.7, edgecolor='white')
                    axes['phase'].add_patch(bar)
                    
                    # フェーズ名
                    if bar_width > 1:  # 幅が十分な場合のみ表示
                        axes['phase'].text(phase_start / 3600 + bar_width / 2, 0.5,
                                         current_phase.replace('_', ' ').title(),
                                         rotation=90, ha='center', va='center',
                                         fontsize=8, color='black', fontweight='bold')
                
                current_phase = phase
                phase_start = t
        
        # 最後のフェーズ
        if current_phase is not None:
            color = self.phase_colors.get(current_phase, '#FFFFFF')
            bar_width = (self.times[-1] - phase_start) / 3600
            bar = Rectangle((phase_start / 3600, 0), bar_width, 1,
                          facecolor=color, alpha=0.7, edgecolor='white')
            axes['phase'].add_patch(bar)
        
        plt.tight_layout()
        plt.savefig('rocket_trajectory_static.png', dpi=300, facecolor='#f8f8f8', bbox_inches='tight')
        plt.show()
    
    def create_analysis_plots(self):
        """詳細分析プロットを作成"""
        fig, axes = plt.subplots(2, 2, figsize=(14, 10), facecolor='white')
        fig.suptitle('Mission Analysis', color='black', fontsize=16, fontweight='bold')
        
        # フラット化
        axes = axes.flatten()
        
        # 背景色設定
        for ax in axes:
            ax.set_facecolor('white')
            ax.tick_params(colors='black')
            ax.xaxis.label.set_color('black')
            ax.yaxis.label.set_color('black')
            ax.title.set_color('black')
            ax.xaxis.label.set_fontweight('bold')
            ax.yaxis.label.set_fontweight('bold')
            ax.title.set_fontweight('bold')
        
        # 1. 加速度プロファイル
        if len(self.velocities) > 1:
            dt = np.diff(self.times)
            dv = np.diff(self.velocities, axis=0)
            accelerations = np.sqrt(np.sum(dv**2, axis=1)) / dt
            
            axes[0].plot(self.times[1:] / 3600, accelerations, 'y-', linewidth=1)
            axes[0].set_xlabel('Time [hours]')
            axes[0].set_ylabel('Acceleration [m/s²]')
            axes[0].set_title('Acceleration Profile')
            axes[0].grid(True, alpha=0.3)
            axes[0].set_yscale('log')
        
        # 2. 軌道エネルギー
        # 比力学的エネルギー = 運動エネルギー - ポテンシャルエネルギー
        distances = np.sqrt(np.sum(self.positions**2, axis=1))
        velocity_magnitudes = np.sqrt(np.sum(np.array(self.velocities)**2, axis=1))
        kinetic_energy = 0.5 * velocity_magnitudes**2
        potential_energy = -G * M_EARTH / distances  # 地球のみ（簡略化）
        specific_energy = kinetic_energy + potential_energy
        
        axes[1].plot(self.times / 3600, specific_energy / 1e6, 'c-', linewidth=2)
        axes[1].axhline(y=0, color='black', linestyle='--', alpha=0.7)
        axes[1].set_xlabel('Time [hours]')
        axes[1].set_ylabel('Specific Energy [MJ/kg]')
        axes[1].set_title('Orbital Energy')
        axes[1].grid(True, alpha=0.3)
        
        # 3. 燃料効率
        if len(self.masses) > 1:
            fuel_consumption_rate = -np.diff(self.masses) / np.diff(self.times)
            axes[2].plot(self.times[1:] / 3600, fuel_consumption_rate, 'r-', linewidth=1)
            axes[2].set_xlabel('Time [hours]')
            axes[2].set_ylabel('Fuel Consumption Rate [kg/s]')
            axes[2].set_title('Fuel Consumption')
            axes[2].grid(True, alpha=0.3)
        
        # 4. 地球からの距離 vs 月からの距離
        # 月の位置を計算
        moon_positions = []
        for t in self.times:
            angle = 2 * np.pi * t / self.MOON_ORBIT_PERIOD
            moon_positions.append([self.EARTH_MOON_DIST * np.cos(angle),
                                 self.EARTH_MOON_DIST * np.sin(angle)])
        moon_positions = np.array(moon_positions)
        
        earth_distances = distances / 1000  # km
        moon_distances = np.sqrt(np.sum((self.positions - moon_positions)**2, axis=1)) / 1000
        
        axes[3].plot(self.times / 3600, earth_distances, 'b-', label='Earth', linewidth=2)
        axes[3].plot(self.times / 3600, moon_distances, 'gray', label='Moon', linewidth=2)
        axes[3].set_xlabel('Time [hours]')
        axes[3].set_ylabel('Distance [km]')
        axes[3].set_title('Distance from Earth and Moon')
        axes[3].grid(True, alpha=0.3)
        axes[3].legend(facecolor='white', edgecolor='black', labelcolor='black')
        axes[3].set_yscale('log')
        
        plt.tight_layout()
        plt.savefig('mission_analysis.png', dpi=300, facecolor='white')
        plt.show()


def main():
    """メインエントリーポイント"""
    parser = argparse.ArgumentParser(description='Rocket Trajectory Visualizer')
    parser.add_argument('--results', default='mission_results.json',
                      help='Path to mission results file')
    parser.add_argument('--config', default='mission_config.json',
                      help='Path to mission config file')
    parser.add_argument('--mode', choices=['static', 'animate', 'analysis', 'all'],
                      default='all', help='Visualization mode')
    parser.add_argument('--save-animation', action='store_true',
                      help='Save animation as MP4')
    
    args = parser.parse_args()
    
    # ビジュアライザー作成
    visualizer = TrajectoryVisualizer(args.results, args.config)
    
    # モードに応じて実行
    if args.mode == 'static' or args.mode == 'all':
        print("Creating static trajectory plot...")
        visualizer.create_static_plots()
    
    if args.mode == 'animate' or args.mode == 'all':
        print("Creating animated trajectory...")
        visualizer.animate_trajectory(save_animation=args.save_animation)
    
    if args.mode == 'analysis' or args.mode == 'all':
        print("Creating analysis plots...")
        visualizer.create_analysis_plots()


if __name__ == "__main__":
    # 定数定義（インポートエラー回避）
    G = 6.67430e-11
    M_EARTH = 5.972e24
    
    main()