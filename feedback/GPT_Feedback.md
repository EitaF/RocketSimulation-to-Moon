ほなコードを覗いてみて、物理的に「そら月まで行かれへんわ！」いうポイントと、どう直したらええかを整理するで。
（以下、ソースは全部 rocket\_simulation\_main.py から引用）

---

## 1. 打ち上げ方向が地球半径とズレとる

```python
if self.phase == MissionPhase.LAUNCH:
    return Vector3(0, 1) * stage.thrust
```

上向き（+Y）固定やけど、ロケットの初期位置は地球中心から見て

$$
\mathbf r_0=(R_\oplus\sin\phi,\;R_\oplus\cos\phi)
$$

（ここで $\phi$ は発射緯度）やから、本来の「真上」は単位ベクトル

$$
\hat{\mathbf r}=\frac{\mathbf r_0}{\lVert\mathbf r_0\rVert}
$$

に沿わなアカン。始めから斜めに力入れてるせいで、無駄に横方向 Δv を食い潰してまう。

**修正案**

```python
if self.phase == MissionPhase.LAUNCH:
    up = self.position.normalized()          # 地球中心→機体方向
    return up * stage.thrust
```

---

## 2. ピッチオーバー（重力ターン）が急過ぎる

高度 1 km でいきなり 45° は速攻で水平に向き過ぎ。
・高度 10 km で 5–10°
・高度 100 km で 45–60°
くらいのゆる～いカーブにしたら、重力損失 $Δv_g$ を 500–700 m/s 節約できる。

**イメージ式**

$$
\theta(h)=\theta_{\text{min}}+\left(\theta_{\text{max}}-\theta_{\text{min}}\right)\frac{h-h_0}{h_1-h_0}
$$

（線形補間、ただしクランプ）

---

## 3. Δv が月着陸までギリ足らん

理想 Δv（空気抵抗・重力損失抜き）

| 区間         | 必要 Δv \[km/s] | 説明                     |
| ---------- | ------------- | ---------------------- |
| 打ち上げ + LEO | ≈ 9.4         | 含む重力・空気損失で実際は \~9.7–10 |
| TLI        | ≈ 3.2         |                        |
| LOI        | ≈ 0.9         |                        |
| 降下・着陸      | ≈ 1.6         |                        |
| **合計**     | **15.1**      |                        |

現在のサターン V 定義では理想値

$$
Δv_\text{ideal}=12.7\;\text{km/s}
$$

しかない（計算済）。空気・重力損失を引くと LEO + TLI で燃料が底を突いて LOI が出来へん。

**修正案**

* ペイロードを月着陸段（LM）と上昇段に分け、

  * S-IVB は TLI まで（残燃料ゼロ）
  * LM 降下段を別ステージ（Isp ≈ 311 s、推進剤 ≈ 8200 kg）で追加
* もしくは S-IVB の推進剤を +40 t 増やし、burn\_time も 900 s に変更

---

## 4. TLI タイミングが 200 s 待ちやと早過ぎる

```python
if coast_time > 200:
    self.rocket.phase = MissionPhase.TRANS_LUNAR_INJECTION
```

低軌道で 3 分ちょっと回っただけで月方向に火を焚くと、月まで約 60° 位置ズレが出る。最低でも **半周 (\~45 min)** は待って、月進行方向に合わせてから焚くこと。

*目安*

$$
t_\text{coast}\approx\frac{\pi r_\text{LEO}}{v_\text{circ}} \;\approx\; 45\ \text{min}
$$

---

## 5. LOI 用の推力が残っていない

LOI フェーズは

```python
if self.rocket.phase == MissionPhase.LUNAR_ORBIT_INSERTION:
    return self.velocity.normalized() * (-stage.thrust)
```

とするのは OK やけど、既に `stage_burn_time >= burn_time` で推薬ゼロ。
**対策**

* Stage 3 を 2 回点火に対応（TLI → シャットダウン → LOI で再点火）させ、
  `stage_burn_time` をリセットする関数を作る
* あるいは LOI 用に LM 降下段を使う

---

## 6. 空気抵抗モデルを 100 km でスパッと切っている

実際は $120\text{–}150 km$ でも稀薄大気の抵抗が効く。

$$
\rho(h)=\rho_0 e^{-h/H}
$$

で $h>120\text{ km}$ まで延長しとくと、低軌道加速で数十 m/s 余分に必要＝予備燃料設計に効く。

---

## まとめ – 最低限この 4 点を直すと月へ行ける確率アップ！

1. **打ち上げ推力ベクトルを「位置の外向き」に変更**
2. **ピッチオーバーをゆるやかに（10 km＝5°、100 km＝60°程度）**
3. **TLI までに十分な Δv を持つようステージ質量／Isp を再設計**
4. **低軌道を 40–45 分コーストして適切な TLI 窓を選択**

これだけでも LUNAR\_ORBIT\_INSERTION までは到達できるはずやで。
さらに着陸したいなら LM 用降下・上昇ステージをモデリングして、LOI 後に分離＆降下エンジンを使う流れに変えてみてや。応援しとるで！
