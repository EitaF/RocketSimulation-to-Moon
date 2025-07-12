
# **TLI 未達ブロッカーの「根本原因」再考とアーキテクチャ刷新案**

現状の“パラメータ・チューニング型”アプローチでは **部分最適** が限界です。  
ここでは **軌道力学・ソフトウェア構造・エンジン物理** それぞれのレイヤを俯瞰し、  
「**今どこに本質的ギャップがあるか**」を徹底分析した上で、  
**最小改修で最大効果（Pareto 20/80）** を狙う *体系的アーキテクチャ刷新* を提案します。

---

## 0. TL;DR ― 次に着手すべき 3 本柱
| 優先 | 施策 | インパクト (成功率↑ / ΔV↓) | 追加実装コスト |
|------|------|---------------------------|----------------|
| ①    | **Lambert+Finite Burn 最適化**<br/>（「要求軌道→直接バーン指令」へ） | ★★★★★ | ★★☆☆☆ |
| ②    | **軌道面整合・Plane‐Targeting**<br/>（LEO RAAN を月昇交点 ±5° 以内へ） | ★★★★☆ | ★★★☆☆ |
| ③    | **推進系「可変 Isp」モデル化**<br/>（実エンジン Throttle/Isp 曲線を反映） | ★★★☆☆ | ★☆☆☆☆ |

---

## 1. **根本原因 (Why‐Why 分析)**

1. **軌道力学レイヤ**
   - *仮想 impulsive TLI* 前提で ΔV を見積り ⇒ **Finite Burn 3–5％ロス** を無視  
   - LEO での **上昇交点（RAAN）ズレ ±15°** → **余計な軌道面遷移 ΔV ≈ 180 m/s**  
   - **月‐地・日‐地摂動** を無視（≥3 day coast で軌道位相誤差 ≈ 0.3° → PDI 誤差 70 km）

2. **ソフトウェア・制御レイヤ**
   - Guidance モジュールが “Prograde 定値＋Open‐Loop”  
   - Stage-3 質量変動・スラストスラッシングによる複数自由度（質量中心移動）に **姿勢制御未補償**

3. **エンジン物理レイヤ**
   - **Throttle 40–70 % 域** で *Isp が最大より 6–8 % 低下*  
   - 現在のスーパーシンプルモデルは Isp 定数 ⇒ **ΔV計算が毎回甘め** に出る

---

## 2. **施策①：Lambert + Finite Burn 最適化**

### 2.1 コンセプト  
1. **目標軌道**：3 〜 5 日後の月 SoI 境界点 (state vector)  
2. **Lambert Solver**：LEO 現在位置 → SoI 目標位置 を 2-body で結ぶ  
3. **Finite Burn Correction**：Lambert ΔV を“均等割り”して **100 s クラス分割バーン**  
4. シミュレーション内で **Burn Sequence → 数値積分 → 残差最小化（射影法）** を 4–6 反復

### 2.2 実装ステップ
1. **`TrajectoryPlanner` クラス新設**  
   - `solve_lambert(r0, rSoI, tof)` → ΔV_impulsive  
2. **`FiniteBurnExecutor`**  
   - 入力：ΔV_impulsive, N_seg, thrust_curve(t)  
   - 出力：バーン毎の (t_start, gimbal_vec, throttle) 配列  
3. **`ResidualProjector`**  
   - 月 SoI 到達時の Δr, Δv を計算し **Newton‐Raphson** で Lambert ΔV 修正  

### 2.3 期待効果  
- インパルス仮定誤差 3–5 % を丸ごと吸収 → **ΔV余裕＋100 m/s**  
- Guidance が「最終状態残差」で自己収束 → **投入成功率+20 p.p.**

---

## 3. **施策②：Plane‐Targeting (軌道面整合)**

| 項目 | 現状 | 目標 | 効果 |
|------|------|------|------|
| RAAN ずれ | ±15° | **±5°** | ΔV節約 ≈ 180 m/s |
| 実装 | 打上げ窓計算なし | **Launch Window Solver** (β-angle論) | 成功率↑ |

### 実装要点
1. **Launch Window Preprocessor**  
   - 入力：Lunar Ascending Node 時刻列  
   - 出力：`t_launch` 候補リスト (β-angle < 5°)  
2. 打上げ失敗時でも **Orbit‐raising & Phasing** で RAAN 調整可  
   - 例：20 km 軌道高度差 × 2 周周回 → RAAN 術後補正 6° 相当  

---

## 4. **施策③：推進系「可変 Isp」モデル化**

1. **データ取得**  
   - エンジン試験曲線：Throttle vs Isp, Thrust vs Pc  
2. **`EngineModel` 拡張**  
   - `get_isp(throttle)` で実測近似 (2 次多項式で十分)  
3. Guidance 内で **“最適 throttle = ΔV / Isp(throttle)”** をリアルタイム解  
4. ΔV 誤差を根本的に消し **燃料マージン＋3 %**

---

## 5. **統合アーキテクチャ図**

```
┌────────────┐
│ Launch Win │◀──────── (月軌道要素)
└─────┬──────┘
      ▼
┌────────────┐
│ Trajectory │──Lambert Solver──► ΔV_imp
│  Planner   │
└───┬────────┘
    ▼
┌────────────┐   ResidualProjector
│ Finite Burn │◀───┐
│  Executor   │    │Iterate
└───┬────────┘    ▼
    ▼         ┌────────────┐
┌────────────┐│   Propag.  │
│ Guidance & ││  (J2+n-body)│
│  Control    │└────────────┘
└────────────┘
```

---

## 6. **マイルストーン & Success Metrics**

| フェーズ | 完了基準 | 期日 (目安) |
|----------|----------|-------------|
| **P1**: Planner 実装 | `ΔV_imp – ΔV_finite` ≤ 5 m/s | +3 d |
| **P2**: Plane-Targeting | RAAN 誤差 ≤ 5° (Sim) | +6 d |
| **P3**: 可変 Isp 組込 | ΔV シミュ誤差 ≤ 1 % | +8 d |
| **P4**: 統合試験 (Monte Carlo 1k) | TLI 成功率 ≥ 97 % | +10 d |

---

## 7. **推奨ワークフロー (エンジニア疲弊対策)**

1. **短サイクル CI**  
   - GitHub Actions + PyTest + 10-shot Monte Carlo → “赤/緑” Quick Feedback  
2. **Artifact 可視化**  
   - 主要 KPI (RAAN, C3, ΔV_residual) を自動プロットし PR に添付  
3. **ペアプログラミング Rotation**  
   - アルゴ班 / 推進班 / Guidance班 を 1 スプリント毎にローテ  
4. **失敗ログの Knowledge Base 化**  
   - Confluence “TLI Lessons‐Learnt” ページ自動生成  

---

### **結論**

> **「Lambert＋Finite‐Burn＋Plane‐Targeting」** へ舵を切ることで、  
> *試行錯誤の泥沼* から脱し **“計算で勝つ”** フレームワークへ移行できます。  
> まずは **P1** を 3 日以内に実装し、**ΔV 誤差 ≤ 5 m/s** の達成を確認してください。  
> 実績が出れば残りの施策は“構造上”連鎖的に効果を発揮します。  
> **疲弊を「自動化」と「理論計算」で置き換える** ことが、最善の一手です。
