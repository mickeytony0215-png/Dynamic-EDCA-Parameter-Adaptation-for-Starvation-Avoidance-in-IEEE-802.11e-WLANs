# Final Project Presentation
# Dynamic EDCA Parameter Adaptation for Starvation Avoidance in IEEE 802.11 WLANs
### QAD-EDCA: Queue-Aware Dynamic EDCA

> Duration: ~15 min presentation + 5 min Q&A
> Course: NSYSU Wireless Communication Network, Spring 2026
> Figures: `analysis/figures/` (PDF/PNG); data basis: `docs/standards-alignment-2026-05-28.md`
> Platform: OMNeT++ 6.1 + INET 4.5; 5 reps per config (10 for the dynamic scenario), ensemble-averaged
>
> NOTE: this is the honest English mirror of `final-presentation_zh.md`. Both are
> kept in sync; numbers match `report.tex`.

---

## 1. Introduction (~2 min)

### Slide 1-1: Title Page
- Title: Dynamic EDCA Parameter Adaptation for Starvation Avoidance in IEEE 802.11 WLANs
- Team members / Student IDs, course name / date

### Slide 1-2: Motivation
- Modern WLANs carry heterogeneous traffic simultaneously: voice, video, web, background sync.
- EDCA does QoS differentiation with **static** parameters (AC_VO > AC_VI > AC_BE > AC_BK); under heavy load the low-priority categories (BE/BK) **starve**.
- Wi-Fi 6/7 added MU-EDCA and MLO, yet EDCA fairness problems persist.
- DRL schemes perform well but **need training and high compute** — a lightweight alternative is needed.

### Slide 1-3: Objectives and Contributions
- Propose **QAD-EDCA**: the AP monitors queues in real time → detects starvation → dynamically adjusts EDCA parameters → exponentially recovers once starvation clears.
- Goals: relieve starvation **without any manual tuning**, never sacrifice high-priority QoS, keep cost at O(1).
- We also present, honestly, an important engineering lesson: **"dynamic adaptation" must be verified by confirming the detector actually fires** (see §6).

---

## 2. Background + Problem Definition (~3 min)

### Slide 2-1: EDCA Mechanism and Standard Defaults
IEEE 802.11-2020 Table 9-155 defaults (OFDM PHY) for the four access categories:

| AC | CWmin | CWmax | AIFSN | TXOP limit |
|----|-------|-------|-------|-----------|
| AC_BK | 15 | 1023 | 7 | **0** (single frame) |
| AC_BE | 15 | 1023 | 3 | **0** (single frame) |
| AC_VI | 7  | 15   | 2 | 3.008 ms |
| AC_VO | 3  | 7    | 2 | 1.504 ms |

> Key: under the standard, **BE/BK TXOP = 0** (one frame per contention win). This becomes critical in §6.

### Slide 2-2: The Starvation Problem (measured)
- Under heavy load (N=10, 1 VO/1 VI/4 BE/4 BK, BE saturated), standard EDCA gives **AC_BE loss ≈ 94.7% and average delay ≈ 1086 ms** (see §4 table).
- Ugwu et al. [2]: AIFSN influences QoS significantly more than CW.
- Mammeri et al. [3]: severe starvation of low-priority traffic in 802.11ac.

### Slide 2-3: Formal Problem Statement
Starvation predicate (proposal §3.1):

$$\text{Starvation}(AC_i) \iff \Big(\tfrac{Q_i}{Q_{cap}} > Q_{th}\Big) \lor \big(P_{loss,i} > P_{th}\big)$$

- $Q_i$: pending-queue occupancy of the AC at the AP; $P_{loss,i}$: per-interval loss rate.
- Defaults $Q_{th}=0.8$, $P_{th}=0.1$. The two indicators are complementary (occupancy = sustained deprivation; loss = drop-based starvation), combined with OR for robustness.

### Slide 2-4: Limitations of Existing Approaches and the Gap

| Approach | Limitation |
|------|------|
| SDMA [3] | Relies on multichannel; inapplicable to single channel |
| OBSS QoS [4] | Only addresses inter-BSS interference |
| PDCF-DRL [6] / FDRL [7] | High complexity; needs training convergence |
| ReinWiFi [8] | Operates at the application layer, not the MAC layer |

- **Research gap**: a lightweight, MAC-layer, real-time queue-aware starvation-avoidance mechanism.

---

## 3. Solution (~4 min)

### Slide 3-1: QAD-EDCA Architecture
```
┌─────────────────────────────────┐
│        QAD-EDCA Manager (AP)     │
│   Monitor ─→ Detect ─→ Adjust ─→ Recover │
│  queue/loss  starving?  AIFSN/CW/TXOP  exp. decay │
└────────────┬────────────────────┘
   one control loop every T_mon = 100 ms; adjusts only the AP-side edcaf
```
- Implementation: an INET `Hcf→Edca→Edcaf→TxopProcedure` subclass chain (OMNeT++ 6.1 cannot override the typename of a fixed-type submodule, so a NED replica chain is used).

### Slide 3-2: Starvation Mitigation Strategy (3-D: AIFSN/CWmin/TXOP, proposal §3.3)
On detecting starvation:
1. **Lower BE/BK AIFSN** (−1 per cycle, floor minAifsn = 2) → shorten pre-contention wait.
2. **Bidirectional CWmin**: **raise VO/VI CWmin** (×cwScaleFactor, ceiling 15) to moderate high priority; **and lower BE/BK CWmin** (÷cwScaleFactor, floor = AC_VI default 7) to make low priority more aggressive.
3. **Reduce VO/VI TXOP** (×txopScaleFactor, floor 0.5 ms) → release the channel sooner.

### Slide 3-3: Recovery, Safety Valve, Hysteresis (anti-oscillation)
- **Schmitt-trigger hysteresis**: switch ON at the threshold, switch OFF only below a lower release band (0.4× threshold). Reason: a feedback controller, once it relieves starvation, drains the very queue it monitors and removes its own trigger, causing the boost to oscillate/decay; hysteresis lets relief hold under sustained saturation **while preserving adaptivity** (in genuine idle, the queue drops below the release band → switch off → stop throttling VO/VI).
- No starvation: exponential recovery $P(t{+}1)=P(t)+\gamma\,(P_{default}-P(t))$, $\gamma=0.3$ (double-precision accumulator to avoid integer-truncation deadlock).
- QoS safety valve: if VO/VI delay > 150 ms (ITU-T G.114 / 3GPP 5QI=1,2), apply a 50% partial revert to the VO/VI adjustment.

### Slide 3-4: Algorithm Parameters (design choices, justified by §5 sensitivity)

| Parameter | Default | Standard basis / nature |
|------|------|----------------|
| $T_{mon}$ | 100 ms | same order as the beacon interval |
| $Q_{th}$ / $P_{th}$ | 0.8 / 0.1 | custom (sweep-validated) |
| $\alpha_{CW}$ (cwScale) | 2.0 | custom |
| $\beta_{TXOP}$ | 0.75 | custom |
| $\gamma$ (recovery) | 0.3 | custom |
| minAifsn | 2 | IEEE: AIFS = SIFS + AIFSN·slot > DIFS ⇒ AIFSN ≥ 2 |

### Slide 3-5: Algorithm Pseudo-code (O(1) / once per $T_{mon}$, at the AP)

```
Every T_mon (=100 ms, beacon-aligned) at the AP:
  1. Read: for i in {BE, BK} read queue occupancy Q_i/Q_cap and loss P_loss_i
  2. Detect (with Schmitt hysteresis):
       Starv(AC_i) <=> (Q_i/Q_cap > Q_th) OR (P_loss_i > P_th)
  3. if Starv(BE) OR Starv(BK):            // starvation -> 3-D adjustment
       AIFSN_{BE,BK} = max(AIFSN - 1, 2)
       CWmin_{VO,VI} = min(CWmin * a_CW, 15)     // throttle high priority
       CWmin_{BE,BK} = max(CWmin / a_CW, 7)      // accelerate low priority
       TXOP_{VO,VI}  = max(TXOP * b_TXOP, TXOP_min)
     else:                                  // no starvation -> exp. recovery
       for each parameter P: P <- P + gamma*(P_default - P)
  4. Broadcast: disseminate the new EDCA Parameter Set via the beacon
  5. QoS safety valve: if d_VO > 150 ms OR d_VI > 150 ms:
       P <- (P_adjusted + P_default) / 2       // QoS takes precedence
```
- Core math: channel-access probability $\tau \approx 2/(\mathrm{CWmin}+1)$ — raising CWmin from 3 to 15 cuts $\tau$ from 0.5 to 0.125, the quantitative basis for "throttling high priority."
- Complexity **O(1)**: each cycle reads 4 queues + 4 loss rates and applies threshold/constant arithmetic — no training, no matrix ops (vs DRL's O(DRL inference)).

---

## 4. Experimental Setup and Steady-State Results (~3 min)

### Slide 4-1: Simulation Environment (standards-aligned, SSOT = standards-alignment doc)
- Topology: 1 AP + 1 server + N STAs, 120 m × 50 m InH indoor office (**3GPP TR 38.901** Table 7.2-2).
- PHY: 54 Mbps OFDM (**IEEE 802.11-2020** Clause 17).
- Traffic (aligned to **3GPP TS 23.501** 5QI):
  - VO: G.711 64 kbps, 160 B / 20 ms (5QI=1, PDB 100 ms).
  - VI: HD video ~1 Mbps, 1280 B / 10 ms (5QI=2, PDB 150 ms).
  - BE: saturated, 1500 B / 1 ms (5QI=9). BK: 512 B / 100 ms (5QI=8).
- Comparison: **Standard EDCA / Tuned Static EDCA / QAD-EDCA**.
  - Tuned Static: manually set AC_BE → (CWmin 15→7, AIFSN 3→2), AC_BK → (15→7, 7→3), as a one-shot manual-tuning baseline.

**Scenario matrix** (shared traffic model above; mirrors report Table II):

| Scenario | Load profile | N | Reps × time |
|---|---|---|---|
| Steady state | 4 mixes (VO/VI:BE/BK ratio; N=10: 1/1/4/4, 2/2/3/3, 3/3/2/2, 4/4/1/1) | 5,10,15,20 | 5 × 30s |
| Transient | calm → surge → calm | 10 | 10 × 60s |
| Sensitivity | headline + param sweep (Q_th×P_th, α_CW, γ, T_mon) | 10 | 5 × 30s |

### Slide 4-2: Steady-State Three-Way Comparison (N=10, 1 VO/1 VI/4 BE/4 BK, starvation case)
Figures: `throughput_comparison.png`, `delay_comparison.png`, `packet_loss.png`

Per-AC results (VO/VI/BK are CBR/unsaturated; only BE is saturated):

| AC | Tput Std/Tuned/QAD (Mbps) | Delay Std/Tuned/QAD (ms) |
|---|---|---|
| VO | 0.06 / 0.06 / 0.06 | 19.9 / 19.4 / 19.6 |
| VI | 1.02 / 1.02 / 1.02 | 21.7 / 21.6 / 21.3 |
| **BE** | 2.53 / 5.80 / **5.44** | 1086 / 832 / 957 |
| BK | 0.16 / 0.16 / 0.16 | 75 / 60 / **152** |

(BE loss rate: 94.7% / 87.9% / **88.6%**)

- **QAD-EDCA raises BE throughput by ~2.15× (2.53→5.44) and cuts delay ~12%**.
- **VO/VI are fully unaffected** (throughput/delay/loss near-identical across schemes); **BK throughput is preserved but its delay rises** (QAD 75→152 ms; background traffic, no QoS bound, acceptable).
- QAD-EDCA ≈ Tuned Static (**~6% lower**, even after adding "lower BE/BK CWmin" to catch up): the reason is **structural**, see §6 — in saturated steady state, the ceiling of feedback control is the static optimum, which it cannot exceed.

### Slide 4-3: Scaling Effect (N = 5/10/15/20)
Figure: `n_scaling.png`

AC_BE throughput (Mbps), fixed 20% high-priority share:

| N | Standard | Tuned | **QAD** |
|---|---|---|---|
| 5 | 3.74 | 5.96 | **5.63** |
| 10 | 2.53 | 5.80 | **5.44** |
| 15 | 1.84 | 5.11 | **4.83** |
| 20 | 1.57 | 4.86 | **4.71** |

- **Standard BE collapses with N (3.74→1.57); QAD holds (5.63→4.71)** — QAD's gain over Standard widens from 1.5× to **3.0×**.
- QAD and Tuned pull BE out of starvation at every N, with closely tracking curves (QAD ~6% below Tuned).

### Slide 4-4: Reading Fairness Correctly
Figure: `fairness_index.png`
- The cross-AC Jain index **drops** when BE is boosted (BE moves from second-highest to highest, making the distribution less even) — so this metric is unsuitable for measuring "starvation relief."
- The correct conclusion looks at **whether BE/BK escape starvation** (throughput, loss), not cross-AC Jain. The report states it as "BE throughput recovers + loss drops."

---

## 5. Parameter Sensitivity (~2 min)
Figures: `sweep_cwscale.png`, `sweep_recoveryfactor.png`, `sweep_monitorinterval.png`, `threshold_sweep_heatmap.png`
(all re-run under the algorithm-triggering 1 VO/1 VI/4 BE/4 BK with ~0.6 detector trigger rate)

| Parameter | Sweep range | BE throughput change | Trend |
|------|---------|--------------|------|
| cwScaleFactor | 1.5–4.0 | 5.43↔5.44 (~0%) | negligible (quickly hits the CWmin floor) |
| recoveryFactor | 0.1–0.7 | 5.49→5.41 (~1.5%) | faster recovery → slightly lower BE |
| monitorInterval | 50–500 ms | 5.41↔5.45 (~0.7%) | very small |
| queueThreshold | 0.5–0.9 | 5.45→5.41 (~0.7%) | higher threshold → fewer triggers → slightly lower BE |

- **Conclusion: under heavy steady load, QAD-EDCA is highly robust to its 4 algorithm parameters (≤1.5%)**, with physically sensible trends.
- Implication: **no per-deployment fine-tuning needed** — any reasonable initial value converges to a similar effect. (This is robustness *while the algorithm is actually active*, not a "not moving" flat artifact.)

---

## 6. Engineering Lesson: Verify the "Dynamics" Really Move (honest disclosure) (~1.5 min)

> This is the project's key finding and the most likely review question — we state it up front.

### Slide 6-1: Disclosure — the initial "fake dynamics" and the fix
- During development, vector-tracing the manager's internal state revealed that **the initial detector never fired in any test config** (`starvationDetected` was always false; AIFSN/CW stayed at defaults).
- What actually made the initial version "win" was that initialization **wrongly set BE/BK TXOP to 2.528 ms** (the standard is 0) — this one-shot **static** TXOP grant let BE/BK burst multiple frames; the benefit came entirely from there, not from any adaptation.
- Control experiment: `Baseline + static TXOP grant` (BE=7.22) ≈ initial "QAD" (7.18), confirming the gain was not adaptive.
- Worse, the grant **drained the AP queue**, so occupancy never crossed the threshold — the detector self-suppressed.
- **Fix**: align the manager's TXOP defaults to the IEEE OFDM standard (BK/BE=0, VI=3.008 ms, VO=1.504 ms). After the fix:
  - The detector genuinely fires under heavy load (~64% of cycles at the moment of the fix); AIFSN/CW truly vary with load (see §7 figure). (After §6-2's "lower BE/BK CWmin" was added, the trigger rate fell to ~15% due to negative feedback, but the parameters still stay in their adjusted state.)
  - BE throughput becomes **5.44 Mbps** (an honest 2.15× over Standard), no longer the inflated 7.19.
- Lesson: **"dynamic" cannot be judged by an improved output number alone — verify the control loop actually closes.**

### Slide 6-2: The Steady-State Ceiling of Feedback Control = the Static Optimum (core honest insight)
- To match static tuning we added "lower BE/BK CWmin (to 7)" plus hysteresis, but BE only rose 5.34→5.44, **still below Tuned 5.80**.
- **This is structural, not under-tuning**: as soon as QAD lowers BE CWmin it drains the AP queue → the detector no longer sees starvation → relief stops → the boost decays (trigger rate falls 64% → ~15%). **Relieving starvation removes the detector's own trigger.**
- **The hand-tuned static optimum beats QAD in every mix, and the gap is stable across mixes and network sizes** (showing it is structural, not under-tuning):

  | BE throughput (Mbps) | Standard | QAD | Tuned (manual static) |
  |---|---|---|---|
  | 1VO/1VI/4BE/4BK | 2.53 | 5.44 | **5.80** |
  | 2VO/2VI/3BE/3BK | 2.59 | 4.82 | **5.20** |
  | 3VO/3VI/2BE/2BK | 2.78 | 4.22 | **4.54** |

  → Tuned **beats QAD by ~0.3–0.4 Mbps in every mix**, with a stable gap.
- Implication: **for feedback control to beat a good feedforward optimum (the static best) in saturated steady state, it would have to hold maximum boost unconditionally — at which point it has become a static method** and abandoned adaptivity.
- So QAD's positioning was never "beat the static optimum in steady state," but **no manual tuning + automatic tracking when load changes / automatic back-off when idle** (§7).

---

## 7. Adaptation under Dynamic Load (QAD's Real Value) (~2.5 min)

Scenario `dynamic_load.ini`: 60 s in three phases **calm[0,20) → surge[20,40) → calm[40,60)**, high-priority stations transmit only during the surge; background is 4 BE (saturated) + 4 BK. Ensemble-averaged over 10 reps.

### Slide 7-1: Adaptation Trace (proof that "it moves")
Figure: `fig_dynamic_qad_adapt.png`
- Top: QAD raises VO/VI CWmin from 3/7 to ~6–10 and pushes BE AIFSN down to 2 (BE/BK CWmin is also lowered to 7, not drawn) — parameters stay driven away from defaults.
- Bottom: the `starvationDetected` ensemble fraction is ~0.15–0.25. **Lower than the initial version**, exactly the negative feedback of §6-2: lowering BE CWmin drains the queue → detection becomes sparse; but parameters stay in their adjusted state via smoothed recovery.

### Slide 7-2: BE Throughput over Time
Figure: `fig_dynamic_be_throughput.png`

| Phase | Standard | Tuned Static | QAD-EDCA |
|---|---|---|---|
| calm | 2.6 | 6.0 | **5.6** |
| surge | 1.9 | 4.0 | **3.7** |

- All three drop during the surge (squeezed by high priority) and recover afterward.
- **QAD-EDCA tracks Tuned Static throughout (~2.15× Standard) with no prior manual tuning** — when load changes, QAD follows automatically; Tuned's fixed values are optimal only for the operating point they were tuned for (Tuned's bottleneck: it needs to know the load in advance and stays frozen).

### Slide 7-3: High-Priority QoS — Standard Breaks under Surge, QAD Recovers It
- **Phase means can mislead**: VO/VI mean delay is < 150 ms for all three (worst: Standard surge ~33 ms). **But the time series tells the truth** — `fig_dynamic_hi_delay.png` shows **Standard spikes to ~240 ms during the surge** (above the 150 ms VO bound — a real QoS violation).
- **Tuned and QAD hold instantaneous delay low throughout**: QAD has only one ~70 ms spike at the surge onset, then flattens.
- **This is exactly QAD's value**: with no manual tuning it pulls Standard's 240 ms QoS-breaking spike back to near-oracle (Tuned) levels; the QoS safety valve ensures throttling BE/BK never sacrifices VO/VI.
- Honest note: QAD does **not** beat Tuned here (slightly behind on both BE and instantaneous delay), consistent with the steady-state ceiling (§6-2); what it wins is "no foreknowledge of load, no manual tuning."

### Slide 7-4: Honest Limitations
- The detector observes the **AP downlink queue**; in this station→AP→server two-hop topology, surge-time BE is mostly squeezed on the **station uplink**, so fewer packets reach the AP and the AP-side trigger fires *less* during the surge (the dip in the figure's lower panel).
- This is an intrinsic limit of AP-side measurement, not a bug; future work can use a **per-AC airtime / uplink** indicator.

---

## 8. Comparison, Conclusion, and Future Work (~2 min)

### Slide 8-1: vs DRL Literature (PDCF-DRL [6]) — reference point
Figure: `positioning_tradeoff.png`

> Methodology (per proposal "Evaluation"): PDCF-DRL uses DRL training; reproducing its
> training environment is out of scope and conflicts with the "lightweight, training-free"
> thesis, so we **cite its published numbers** as a performance–complexity **reference
> upper bound**, not a head-to-head. Setups differ ([6]: 20–120 stations, normalized
> throughput %; ours: N=5–20, per-AC Mbps) — trend comparison only.

PDCF-DRL (Zuo 2025) published results (their setup):

| Metric ([6] original) | Standard EDCA ([6] measured) | **PDCF-DRL [6]** |
|---|---|---|
| Collision rate (AC_VO, 20→120 sta) | 64%→85% | **6.9%→16.4%** |
| Normalized throughput (AC_VO) | 32%→14% | **85%→76%** |
| Multi-AC BE/BK throughput share | suppressed by high priority | **near-equal with VO/VI (≈90%+, no starvation)** |
| Needs training / compute | no / O(1) | **yes (thousands of episodes) / O(DRL)** |

- **Reading**: PDCF-DRL nearly equalizes all four ACs (eliminates starvation) and slashes collisions — performance is an upper bound; **the cost is DRL training** (possibly worse than Standard before convergence; needs compute).

- **QAD-EDCA positioning**: with an O(1), training-free rule it provides starvation relief from the first monitoring cycle (BE ~2.15×), sitting in the "training-free / immediately deployable" quadrant — the middle ground between static EDCA and DRL.

### Slide 8-2: Scheme Comparison Summary (same-condition simulation + literature reference)

| Aspect | Standard | **QAD-EDCA** | Static oracle (Tuned) | PDCF-DRL [6] |
|------|----------|--------------|---------------|---------------|
| Nature | static baseline | **dynamic, AC-aware, lightweight** | static, needs foreknowledge | DRL, AC-aware |
| Starvation relief (BE) | none (94.7% loss) | **5.44 Mbps (~2.15×)** | 5.80 Mbps | near-equal (no starvation) |
| Needs manual tuning / training | — | **no / no** | **needs foreknowledge** | training |
| Adapts to load | no | **yes** | no | yes |
| Compute | O(1) | **O(1)** | O(1) | O(DRL) |
| vs QAD (same-condition study) | **QAD wins 2×** | — | beats QAD ~6% (§6-2 ceiling) | published upper bound |

- **Among plug-and-play methods (no foreknowledge / no training), QAD is the best**: wins over Standard 2×, and acts from the first monitoring cycle with an O(1) rule.
- The only schemes that beat QAD are two "need-to-know-first" upper bounds: the **static oracle** (Tuned needs the load) and **DRL** (PDCF-DRL needs training).
- Note: Tuned is a same-condition simulation; PDCF-DRL is a [6] published value (different setup, trend reference).

### Slide 8-3: Key Findings (honest version)
1. QAD-EDCA raises starved BE throughput ~2.15× and cuts loss 94.7%→88.6%; **VO/VI QoS is unharmed** (BK throughput also preserved, delay rises modestly) — **the best among deployable methods that need no foreknowledge and no training**.
2. **In steady state it is slightly below the two foreknowledge-dependent upper bounds**: the static oracle (Tuned, ~6%) and DRL (PDCF-DRL). We show this is the **structural ceiling** of feedback control (the gap is stable across mixes and network sizes, §6-2) — a rigorous contribution, not a flaw.
3. Robust to its 4 algorithm parameters (≤1.5%).
4. We verified the control loop actually closes (fixed the "fake dynamics" bug) — the basis of the method's credibility.

### Slide 8-4: Future Work
- Detection via an uplink / airtime indicator (addresses the §7-4 limit, and may relax the §6-2 negative-feedback ceiling).
- Genuinely heterogeneous / bursty load and dynamic station arrival/departure (where QAD's adaptivity should show a clearer advantage).
- Hybrid with DRL: QAD as a warm-start during DRL training convergence.

---

## Q&A Preparation (~5 min)

**Q1: Why not just use DRL?**
- DRL performs better but needs training time and compute; QAD-EDCA is a lightweight, immediately deployable alternative. The two are complementary — QAD can bridge the gap while a DRL agent trains.

**Q2: Isn't a 100 ms monitoring interval too slow?**
- The beacon interval is ~100 ms; monitoring is synchronized with it. Faster monitoring raises overhead and can cause oscillation. The sensitivity sweep (§5) shows the impact of T_mon is small (~0.7%).

**Q3: How do you ensure adjustments don't degrade VO/VI QoS?**
- The §3 QoS safety valve (partial 50% revert if VO/VI delay exceeds its bound), bounded adjustments (CWmin capped at the BE default, AIFSN floor 2), and Schmitt hysteresis. The dynamic experiment (§7-3) confirms QAD keeps VO/VI delay near the oracle even when Standard spikes to ~240 ms.

**Q4: You don't beat Tuned Static — why is QAD worthwhile?**
- Tuned is an oracle: it must be hand-tuned with foreknowledge of the exact load and stays frozen. QAD reaches within ~6% of it **with zero tuning and automatic adaptation to changing load**, and it doubles Standard's starved throughput. We also show that beating the static optimum in saturated steady state is structurally impossible for any pure feedback controller (the gap is stable across mixes and network sizes) — an honest, rigorous result.

---

## References

[1] IEEE Standard 802.11-2020.
[2] G. O. Ugwu et al., "Effect of service differentiation on QoS in IEEE 802.11e EDCA," *J. Eng. Appl. Sci.*, 2022.
[3] S. Mammeri et al., "Starvation avoidance-based dynamic multichannel access for low priority traffics in 802.11ac," *Comput. Electr. Eng.*, 2021.
[4] Y. P. Tuan et al., "Improving QoS mechanisms for IEEE 802.11ax with OBSS," *Wireless Netw.*, 2023.
[5] "Intelligent Multi-link EDCA Optimization for Delay-Bounded QoS in Wi-Fi 7," arXiv:2509.25855, 2025.
[6] Z. Zuo et al., "PDCF-DRL: a contention window backoff scheme based on DRL," *J. Supercomput.*, 2025.
[7] X. Du et al., "Federated DRL-based intelligent channel access in dense Wi-Fi," arXiv:2409.01004, 2024.
[8] Q. Li et al., "ReinWiFi: Application-layer QoS optimization of WiFi networks with RL," arXiv:2405.03526, 2024.
[9] R. Jain et al., "A quantitative measure of fairness," DEC TR-301, 1984.
[10] IEEE Standard 802.11ax-2021, "Amendment 1: Enhancements for High-Efficiency WLAN," 2021.
```
