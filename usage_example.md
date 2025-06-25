# ロケット軌道シミュレーション - 使用ガイド

## 概要

このシミュレーションは、地球から月への実際のロケットミッションを物理的に正確にモデル化したものです。サターンVロケットを基にした多段式ロケットの打ち上げから月到達までの全過程をシミュレートします。

## 主な機能

### 1. 物理的精度
- **正確な軌道力学**: 地球と月の重力を考慮した2体問題
- **多段式ロケット**: 実際のサターンVに基づいた3段式構成
- **燃料消費モデル**: ツィオルコフスキーの公式に基づく質量変化
- **大気抵抗**: 高度に応じた指数関数的な大気密度モデル
- **リアルな打ち上げプロファイル**: 垂直打ち上げ→重力ターン→軌道投入

### 2. ミッションフェーズ
1. **打ち上げ** (Launch): 垂直上昇
2. **重力ターン** (Gravity Turn): 効率的な軌道投入のための旋回
3. **ステージ分離** (Stage Separation): 燃料を使い切った段の分離
4. **軌道投入** (Orbit Insertion): 地球周回軌道への投入
5. **月遷移軌道投入** (Trans-Lunar Injection): 月へ向かう軌道への投入
6. **巡航** (Coast): エンジン停止状態での飛行
7. **月軌道投入** (Lunar Orbit Insertion): 月周回軌道への投入
8. **着陸** (Landed): 月面到達

### 3. 可視化機能
- **リアルタイム軌道アニメーション**: ロケットの動きを追跡
- **複数のデータプロット**: 高度、速度、質量、加速度の時間変化
- **フェーズ別色分け**: ミッションの各段階を視覚的に区別
- **詳細分析グラフ**: エネルギー、燃料効率などの高度な分析

## 使用方法

### 基本的な実行

```bash
# シミュレーション実行
python rocket_simulation.py

# 可視化（すべてのモード）
python visualizer.py

# 静的プロットのみ
python visualizer.py --mode static

# アニメーションのみ
python visualizer.py --mode animate

# 分析プロットのみ
python visualizer.py --mode analysis

# アニメーションをMP4として保存
python visualizer.py --mode animate --save-animation
```

### カスタム設定

`mission_config.json`を編集することで、様々なパラメータを調整できます：

```json
{
  "launch_latitude": 28.573,      # 打ち上げ地点の緯度
  "launch_azimuth": 72,           # 打ち上げ方位角（度）
  "target_parking_orbit": 185000, # 駐機軌道高度（m）
  "gravity_turn_altitude": 10000, # 重力ターン開始高度（m）
  "simulation_duration": 432000,  # シミュレーション時間（秒）
  "time_step": 1.0               # 時間ステップ（秒）
}
```

## 必要なライブラリ

```bash
pip install numpy matplotlib
```

アニメーション保存には追加で必要：
```bash
pip install ffmpeg-python
# またはシステムにffmpegをインストール
```

## 出力ファイル

### シミュレーション結果
- `mission_results.json`: 全シミュレーションデータ
  - 時刻履歴
  - 位置・速度・高度・質量の時系列データ
  - ミッション統計（最大高度、最大速度、総ΔVなど）

### 可視化結果
- `rocket_trajectory_static.png`: 静的な軌道図
- `mission_analysis.png`: 詳細分析グラフ
- `rocket_trajectory.mp4`: 軌道アニメーション（オプション）

## カスタマイズ例

### 1. 異なるロケットの作成

```python
def create_custom_rocket():
    stages = [
        RocketStage(
            name="First Stage",
            dry_mass=50000,      # kg
            propellant_mass=500000,
            thrust=7.5e6,        # N
            specific_impulse=300, # s
            burn_time=150        # s
        ),
        # 追加のステージ...
    ]
    
    return Rocket(
        name="Custom Rocket",
        stages=stages,
        payload_mass=10000,
        drag_coefficient=0.25,
        cross_sectional_area=20.0
    )
```

### 2. 新しいミッションプロファイル

月周回ミッションや異なる軌道への投入など、`Mission`クラスの`_update_mission_phase`メソッドを修正することで実現できます。

### 3. 追加の物理効果

- 太陽重力の追加
- 大気の詳細モデル（温度勾配など）
- 地球の扁平率の考慮
- 推力ベクトル制御

## 教育的価値

このシミュレーションは以下の概念を学ぶのに役立ちます：

1. **軌道力学**
   - ケプラーの法則
   - ホーマン遷移軌道
   - 脱出速度

2. **ロケット工学**
   - ツィオルコフスキーの公式
   - 多段式ロケットの利点
   - 比推力の重要性

3. **数値計算**
   - ルンゲ・クッタ法（RK4）
   - 数値積分の精度
   - 計算の安定性

4. **プログラミング**
   - オブジェクト指向設計
   - データ可視化
   - リアルタイムアニメーション

## トラブルシューティング

### よくある問題

1. **シミュレーションが終了しない**
   - `simulation_duration`を短くする
   - `time_step`を大きくする（精度は下がります）

2. **メモリ不足**
   - データ記録の頻度を下げる
   - アニメーションのフレーム数を減らす

3. **アニメーションが遅い**
   - `skip`パラメータを調整
   - 軌跡の表示点数を減らす

## 物理定数と単位

- 距離: メートル [m]
- 時間: 秒 [s]
- 質量: キログラム [kg]
- 速度: メートル毎秒 [m/s]
- 加速度: メートル毎秒毎秒 [m/s²]
- 力: ニュートン [N]

## 参考文献

1. Bate, Mueller, and White (1971). *Fundamentals of Astrodynamics*
2. Sutton and Biblarz (2016). *Rocket Propulsion Elements*
3. NASA Technical Reports Server - Apollo Mission Reports

## ライセンス

このコードは教育目的で自由に使用できます。商用利用の場合は適切なクレジットを表示してください。