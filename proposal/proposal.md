# Dynamic EDCA Parameter Adaptation for Starvation Avoidance in IEEE 802.11 WLANs

## Team Members

| Name | Student ID | Responsibilities |
|------|-----------|-----------------|
| (To be filled) | | |
| (To be filled) | | |

---

## 1. Background

### 1.1 EDCA Mechanism and QoS Differentiation

The Enhanced Distributed Channel Access (EDCA) mechanism in IEEE 802.11 provides Quality of Service (QoS) differentiation for WLANs. EDCA classifies traffic into four Access Categories (ACs) — Voice (AC_VO), Video (AC_VI), Best Effort (AC_BE), and Background (AC_BK) — each configured with distinct channel access parameters: Arbitration Inter-Frame Space Number (AIFSN), Contention Window (CWmin/CWmax), and Transmission Opportunity limit (TXOP limit) [1].

However, recent research continues to expose fundamental flaws in EDCA's static parameter configuration. Ugwu et al. [2] systematically analyzed the effect of service differentiation on QoS in EDCA through MATLAB simulation, confirming that high-priority traffic severely starves low-priority traffic under saturation, and that AIFSN has significantly more influence on QoS than CW. Mammeri et al. [3] observed that the priority mechanism in IEEE 802.11ac EDCA causes severe starvation for low-priority traffic, proposing a Starvation-avoidance Dynamic Multichannel Access (SDMA) method.

### 1.2 EDCA Evolution from Wi-Fi 6 to Wi-Fi 7

With the introduction of IEEE 802.11ax (Wi-Fi 6), EDCA was extended to multi-user scenarios (MU-EDCA), introducing Trigger Frames and Target Wake Time (TWT) [10]. Tuan et al. [4] addressed the Overlapping BSS (OBSS) problem in 802.11ax environments by reducing interfering AP transmission power and extending TXOP limits for low-QoS stations, achieving a 21.4% reduction in average downlink transmission delay for interfered stations.

IEEE 802.11be (Wi-Fi 7) further introduces Multi-Link Operation (MLO), bringing new challenges for cross-link traffic management with EDCA. Recent research [5] shows that static EDCA parameters in MLO environments cannot guarantee strict delay bounds, proposing a Genetic Algorithm-based MLO EDCA QoS optimization scheme.

### 1.3 Machine Learning-Driven EDCA Optimization

Deep Reinforcement Learning (DRL) has been extensively applied to dynamic EDCA parameter adjustment in recent years. Zuo et al. [6] proposed PDCF-DRL, integrating DRL into the EDCA contention window backoff mechanism, achieving normalized throughput above 76% and collision rates below 18% across 20–120 station scenarios. In single AC_VO traffic scenarios, traditional EDCA exhibits collision rates of 64%–85% and throughput of only 13%–32% with 20–120 stations, whereas PDCF-DRL maintains collision rates of 7%–16% and throughput of 77%–85%. Du et al. [7] combined Federated Learning (FL) with Deep Deterministic Policy Gradient (DDPG) for intelligent channel access in dense Wi-Fi deployments, outperforming conventional DRL by up to 45.9% in MAC delay reduction in dynamic scenarios. Li et al. [8] proposed ReinWiFi, a reinforcement learning-based framework that significantly outperforms EDCA in commercial environments with unknown interference.

Despite their impressive performance, DRL methods are limited by high computational complexity and training convergence time, restricting real-time deployment on resource-constrained devices. This project explores a lightweight, rule-based adaptive scheme that achieves effective starvation avoidance at lower computational cost.

---

## 2. Problem Definition

### 2.1 Formal Definition of Starvation Condition

Prior studies have described EDCA starvation in qualitative terms: Ugwu et al. [2] observed that low-priority traffic suffers from "traffic congestion and frame loss rate are high" under saturation, while Mammeri et al. [3] noted that BE/BK "throughputs are almost zero" when high-priority traffic dominates. However, no formal, quantifiable detection criterion has been established in the literature. We propose the following starvation condition for a low-priority Access Category $AC_i$ (where $i \in \{BE, BK\}$):

$$
\text{Starvation}(AC_i) \iff \left( \frac{Q_i}{Q_{cap}} > Q_{th} \right) \lor \left( P_{loss,i} > P_{th} \right)
$$

where:
- $Q_i$: current queue length of $AC_i$
- $Q_{cap}$: queue capacity
- $Q_{th}$: queue occupancy threshold (default 80%)
- $P_{loss,i}$: packet loss rate of $AC_i$ during the monitoring interval
- $P_{th}$: packet loss rate threshold (default 10%)

The two indicators are combined with a logical OR because they capture complementary starvation symptoms. Queue occupancy ($Q_i/Q_{cap}$) detects the case where packets accumulate in the buffer faster than they can be transmitted, indicating sustained channel access deprivation. Packet loss rate ($P_{loss,i}$) captures scenarios where starvation manifests through packet drops rather than queue buildup — for instance, when the queue is full and incoming packets are dropped at the entry point, or when packets are discarded after exceeding the MAC-layer retry limit due to repeated collisions with high-priority traffic. Using either indicator alone would miss certain starvation patterns; their combination ensures robust detection across all failure modes.

### 2.2 Limitations of Static EDCA

Standard EDCA assigns fixed parameters per IEEE 802.11-2020 Table 9-155 [1]. The contention window values are derived from the PHY-layer constants $aCWmin$ and $aCWmax$ using the following encoding:

$$CWmin = 2^{ECWmin} - 1, \quad CWmax = 2^{ECWmax} - 1$$

The default EDCA parameter set for non-AP STAs (OFDM PHY, Clause 17–21) is:

| AC | CWmin | CWmax | AIFSN | TXOP limit |
|----|-------|-------|-------|------------|
| AC_BK | $aCWmin$ | $aCWmax$ | 7 | 2.528 ms |
| AC_BE | $aCWmin$ | $aCWmax$ | 3 | 2.528 ms |
| AC_VI | $(aCWmin+1)/2 - 1$ | $aCWmin$ | 2 | 4.096 ms |
| AC_VO | $(aCWmin+1)/4 - 1$ | $(aCWmin+1)/2 - 1$ | 2 | 2.080 ms |

For OFDM PHY ($aCWmin = 15$, $aCWmax = 1023$), the concrete values are:

| AC | CWmin | CWmax | AIFSN | TXOP limit |
|----|-------|-------|-------|------------|
| AC_BK | 15 | 1023 | 7 | 2.528 ms |
| AC_BE | 15 | 1023 | 3 | 2.528 ms |
| AC_VI | 7 | 15 | 2 | 4.096 ms |
| AC_VO | 3 | 7 | 2 | 2.080 ms |

These parameters are determined at association time and remain constant throughout the session. The protocol lacks any feedback mechanism to detect or alleviate starvation. As verified by Ugwu et al. [2], these static parameters cause drastic increases in packet loss for low-priority traffic under saturation load.

### 2.3 Limitations of Existing Approaches

| Approach | Representative Work | Key Limitations |
|----------|-------------------|-----------------|
| Dynamic multichannel access | Mammeri et al. [3] | Relies on 802.11ac channel bonding; not directly applicable to single-channel BSS scenarios |
| OBSS QoS improvement | Tuan et al. [4] | Focuses on inter-BSS interference; does not address intra-BSS AC starvation |
| DRL-based schemes | Zuo et al. [6], Du et al. [7] | High computational complexity; slow training convergence |
| Application-layer optimization | Li et al. [8] | Operates at application layer; does not directly adjust MAC-layer EDCA parameters |

**Research Gap**: There is a lack of lightweight, MAC-layer mechanisms that can sense queue states in real-time and dynamically adjust EDCA parameters for starvation avoidance.

---

## 3. Proposed Solution: QAD-EDCA

### 3.1 Design Objectives

QAD-EDCA aims to address the starvation problem while respecting the following prioritized objectives:

| Priority | Objective | Target Metric |
|----------|-----------|---------------|
| 1 | Mitigate starvation of low-priority ACs | AC_BE/AC_BK packet loss rate < 15% (down from > 40%) |
| 2 | Preserve high-priority QoS guarantees | AC_VO delay < 150 ms, AC_VI delay < 300 ms |
| 3 | Improve overall fairness | Jain's Fairness Index > 0.8 (up from ~0.4) |

The goal is not to equalize all ACs, but to ensure low-priority traffic can maintain a minimum viable throughput without degrading real-time services.

### 3.2 Architecture

QAD-EDCA operates at the Access Point (AP) as a centralized monitor and controller. The AP is chosen as the control point because:

- It has visibility into all per-AC queues within the BSS.
- It can disseminate updated EDCA parameters to all associated stations via the EDCA Parameter Set element in beacon frames, requiring no modification to STA implementations.
- The monitoring interval ($T_{mon} = 100$ ms) is synchronized with the standard beacon interval, introducing no additional overhead.

Unlike DRL-based approaches [6][7] that require training phases and significant computational resources, QAD-EDCA is a lightweight rule-based engine with O(1) computational complexity per monitoring cycle — it only reads 4 queue lengths and 4 loss rates, evaluates threshold conditions, and applies deterministic adjustments.

### 3.3 Three-Stage Adjustment Strategy

Upon detecting starvation, QAD-EDCA simultaneously applies three complementary strategies that target different phases of the EDCA channel access process:

#### Strategy 1: AIFSN Reduction for Low-Priority ACs

$$AIFSN_i = \max(AIFSN_i - \Delta_{AIFS},\ 2), \quad i \in \{BE, BK\}$$

AIFSN determines how many time slots a STA must wait after a SIFS before entering contention. Reducing AIFSN for BE/BK shortens their pre-contention wait, giving them earlier access to the channel. The floor value of 2 matches AC_VO/AC_VI defaults, ensuring low-priority ACs never become more aggressive than high-priority ones. This is the most effective single lever, as confirmed by Ugwu et al. [2]: "AIFS has more influence on the QoS of EDCA protocol" than CW.

#### Strategy 2: CWmin Increase for High-Priority ACs

$$CWmin_i = \min(CWmin_i \times \alpha_{CW},\ CWmin_{default,BE}), \quad i \in \{VO, VI\}$$

CWmin determines the backoff window size. Increasing CWmin for VO/VI widens their backoff range, moderating their channel access aggressiveness. The ceiling is set to $CWmin_{default,BE} = 15$, ensuring high-priority ACs always retain a structural advantage over low-priority ones. The effect on channel access probability is:

$$\tau_i = \frac{2}{CWmin_i + 1}$$

As CWmin increases from 3 to 15, the per-slot transmission probability drops from 50% to 12.5%, significantly reducing high-priority dominance.

#### Strategy 3: TXOP Limit Reduction for High-Priority ACs

$$TXOP_i = \max(TXOP_i \times \beta_{TXOP},\ TXOP_{min}), \quad i \in \{VO, VI\}$$

TXOP limit determines how long a STA can occupy the channel after winning contention. Reducing TXOP forces high-priority STAs to release the channel sooner, creating more access opportunities for low-priority traffic. The floor value $TXOP_{min}$ ensures at least one frame can be transmitted per access.

#### Why All Three Simultaneously

The three strategies are applied concurrently rather than sequentially because they operate on different phases of channel access: AIFSN affects *when contention begins*, CWmin affects *how long the backoff lasts*, and TXOP affects *how long the channel is occupied after winning*. Simultaneous adjustment across all three dimensions provides the fastest response to starvation conditions.

### 3.4 Recovery Mechanism

When the starvation condition is no longer satisfied, parameters recover toward their default values via exponential decay:

$$P(t+1) = P(t) + \gamma \cdot \left(P_{default} - P(t)\right), \quad 0 < \gamma < 1$$

With $\gamma = 0.3$, a parameter at its adjustment limit returns to approximately 83% of its default value within 5 monitoring cycles (~500 ms). Gradual recovery is essential to prevent oscillation: if parameters were instantly restored, starvation would likely reoccur immediately, triggering another adjustment cycle — a ping-pong effect that degrades both fairness and QoS stability.

### 3.5 QoS Constraint Verification (Safety Valve)

After applying adjustments, the algorithm verifies that high-priority QoS guarantees remain intact:

$$\text{If } d_{VO} > 150\text{ ms} \lor d_{VI} > 300\text{ ms}: \quad P_{adjusted} \leftarrow \frac{P_{adjusted} + P_{default}}{2}$$

This partial revert (midpoint between current adjustment and default) serves as a safety valve, ensuring that **Objective 2 (QoS preservation) always takes precedence over Objective 1 (starvation mitigation)**. The bounded adjustment ranges (AIFSN floor at 2, CWmin ceiling at $CWmin_{default,BE}$, TXOP floor at $TXOP_{min}$) provide additional structural safeguards.

### 3.6 Fairness Quantification

Overall fairness across ACs is measured using Jain's Fairness Index [9]:

$$J(\mathbf{x}) = \frac{\left(\sum_{i=1}^{n} x_i\right)^2}{n \sum_{i=1}^{n} x_i^2}, \quad J \in \left[\frac{1}{n}, 1\right]$$

where $x_i$ is the normalized throughput of the $i$-th AC. $J = 1$ indicates perfect fairness. Under standard EDCA with high-priority dominance, $J$ drops to ~0.4; QAD-EDCA targets $J > 0.8$.

### 3.7 Pseudo-code

```
Algorithm: QAD-EDCA Dynamic Parameter Adjustment
Input: Monitoring interval T_mon, thresholds Q_th, P_th
       Adjustment factors: delta_AIFS, alpha_CW, beta_TXOP
       Recovery factor: gamma (0 < gamma < 1)

Every T_mon seconds at the AP:
  1. Monitor: For each AC in {BE, BK}:
       Read Q_i = queue occupancy ratio of AC_i
       Read P_loss_i = packet loss rate of AC_i

  2. Detect: If Starvation(AC_BE) OR Starvation(AC_BK):
       // Starvation detected -- apply three-stage adjustment
       a. AIFSN_BE = max(AIFSN_BE - delta_AIFS, 2)
          AIFSN_BK = max(AIFSN_BK - delta_AIFS, 2)
       b. CWmin_VO = min(CWmin_VO * alpha_CW, CWmin_default_BE)
          CWmin_VI = min(CWmin_VI * alpha_CW, CWmin_default_BE)
       c. TXOP_VO = max(TXOP_VO * beta_TXOP, TXOP_min)
          TXOP_VI = max(TXOP_VI * beta_TXOP, TXOP_min)

  3. Recover: Else (no starvation):
       For each parameter P in {AIFSN, CWmin, TXOP}:
         P(t+1) = P(t) + gamma * (P_default - P(t))

  4. Broadcast: Disseminate updated parameters via beacon frame

  5. Verify: If delay_VO > 150 ms OR delay_VI > 300 ms:
       Partially revert: P = (P_adjusted + P_default) / 2
```

### 3.8 Key Parameters

| Parameter | Symbol | Default | Description |
|-----------|--------|---------|-------------|
| Monitoring interval | $T_{mon}$ | 100 ms | Synchronized with beacon interval |
| Queue threshold | $Q_{th}$ | 80% | Queue occupancy ratio triggering detection |
| Loss rate threshold | $P_{th}$ | 10% | Packet loss rate triggering detection |
| AIFS adjustment step | $\Delta_{AIFS}$ | 1 | AIFSN reduction per cycle; floor = 2 |
| CW scaling factor | $\alpha_{CW}$ | 2.0 | CWmin multiplier; ceiling = $CWmin_{default,BE}$ |
| TXOP scaling factor | $\beta_{TXOP}$ | 0.75 | TXOP multiplier; floor = $TXOP_{min}$ |
| Recovery factor | $\gamma$ | 0.3 | Exponential decay rate; ~83% recovery in 5 cycles |

---

## 4. Simulation Design

### 4.1 Simulation Environment

We use **OMNeT++ 6.1** with **INET Framework 4.5** as our simulation platform.

### 4.2 Network Topology

The simulated network consists of a single AP operating in infrastructure BSS mode with $N$ associated wireless stations. We evaluate four network sizes: $N \in \{5, 10, 15, 20\}$.

### 4.3 Traffic Model

| AC | Application | Packet Size | Send Interval | Data Rate |
|----|-------------|-------------|---------------|-----------|
| AC_VO | VoIP (G.711) | 160 bytes | 20 ms | 64 kbps |
| AC_VI | Video stream | 1280 bytes | 10 ms | 1.024 Mbps |
| AC_BE | Bulk transfer (saturated UDP) | 1500 bytes | Variable | Saturated |
| AC_BK | Background sync | 512 bytes | 100 ms | 40.96 kbps |

### 4.4 Experimental Variables

1. **High-priority STA proportion**: 20%, 40%, 60%, 80% of STAs generate VO/VI traffic.
2. **Overall network load**: Light (<30%), Medium (30–60%), Heavy (60–90%), Saturated (>90%).
3. **QAD-EDCA threshold parameters**: Sweep $Q_{th} \in \{50\%, 70\%, 80\%, 90\%\}$ and $P_{th} \in \{5\%, 10\%, 15\%, 20\%\}$.

### 4.5 Performance Metrics

- **Per-AC throughput** (Mbps)
- **Per-AC average delay and delay jitter** (ms)
- **Per-AC packet loss rate** (%)
- **Jain's Fairness Index** across all ACs
- **QoS satisfaction**: AC_VO delay < 150 ms and AC_VI delay < 300 ms

### 4.6 Comparison Schemes

1. **Standard EDCA** (Baseline): Fixed default parameters per IEEE 802.11 [1].
2. **Tuned Static EDCA**: Optimized static AIFSN/CW configuration based on findings of [2], representing the best achievable performance without dynamic adaptation.
3. **PDCF-DRL (Zuo 2025)**: DRL-based contention window backoff [6].
4. **QAD-EDCA** (Proposed): Queue-aware dynamic adaptation scheme.

---

## 5. Expected Analysis and Discussion

### 5.1 Expected Results

Based on findings in the literature:
- **Starvation mitigation**: QAD-EDCA should reduce AC_BE/AC_BK packet loss from >40% (standard EDCA) to <15% when high-priority STA proportion reaches 60%–80%.
- **Fairness improvement**: Jain's Fairness Index from ~0.4 (standard EDCA) to >0.8.
- **QoS preservation**: AC_VO delay <150 ms and AC_VI delay <300 ms maintained during adjustments.
- **Computational efficiency**: No training phase required, unlike DRL schemes [6][7].

### 5.2 Discussion Topics

- Sensitivity analysis of threshold parameters ($Q_{th}$, $P_{th}$)
- Trade-off between monitoring interval $T_{mon}$ and responsiveness vs. stability
- Effect of recovery factor $\gamma$ on oscillation behavior
- Performance comparison with DRL schemes at different network scales

---

## 6. Project Plan and Timeline

### 6.1 Schedule

| Week | Period | Tasks | Deliverables |
|------|--------|-------|-------------|
| 1–2 | Apr 15 – Apr 28 | Environment setup; Implement and validate baseline EDCA simulation; Reproduce starvation under high load | Baseline results; Starvation demonstration plots |
| 3–4 | Apr 29 – May 12 | Implement QAD-EDCA algorithm in OMNeT++/INET; Integrate with Edcaf module; Unit testing | Working QAD-EDCA module; Preliminary comparison |
| 5–6 | May 13 – May 26 | Run full experimental matrix; Collect throughput, delay, loss, fairness data; Implement comparison schemes | Complete simulation data; Analysis scripts |
| 7–8 | May 27 – Jun 10 | Analyze results and generate figures; Write final report; Prepare presentation slides | Final report (PDF); Presentation slides |

### 6.2 Gantt Chart

```
Task                          W1   W2   W3   W4   W5   W6   W7   W8
                             4/15 4/22 4/29 5/06 5/13 5/20 5/27 6/03
Environment & Baseline       ████ ████
QAD-EDCA Implementation                ████ ████
Experiments & Data Collection                     ████ ████
Comparison Scheme Impl.                           ████ ████
Analysis & Figures                                          ████ ████
Report Writing                                         ████ ████ ████
Presentation Prep                                                ████
                                                          Deadline: 6/10
```

### 6.3 Team Responsibilities

| Role | Member | Tasks |
|------|--------|-------|
| Algorithm Design & Implementation | (To be filled) | QAD-EDCA algorithm design; C++ implementation in OMNeT++/INET |
| Simulation & Experimentation | (To be filled) | Network topology setup; Traffic configuration; Running experiments |
| Analysis & Visualization | (To be filled) | Result parsing; Statistical analysis; Figure generation |
| Report & Literature Review | (To be filled) | Literature survey; Proposal and final report writing |

*Note: Team members may share responsibilities across roles.*

---

## 7. References

[1] IEEE Standard 802.11-2020, "IEEE Standard for Information Technology — Wireless LAN Medium Access Control (MAC) and Physical Layer (PHY) Specifications," IEEE, 2020.

[2] G. O. Ugwu, U. N. Nwawelu, and M. A. Ahaneku, "Effect of service differentiation on QoS in IEEE 802.11e enhanced distributed channel access: a simulation approach," *Journal of Engineering and Applied Science*, vol. 69, no. 1, pp. 1–15, 2022. DOI: 10.1186/s44147-021-00055-3.

[3] S. Mammeri, M. Yazid, R. Kacimi, and L. Bouallouche-Medjkoune, "Starvation avoidance-based dynamic multichannel access for low priority traffics in 802.11ac communication systems," *Computers & Electrical Engineering*, vol. 90, art. 106942, 2021. DOI: 10.1016/j.compeleceng.2020.106942.

[4] Y. P. Tuan, L. A. Chen, T. Y. Lin, et al., "Improving QoS mechanisms for IEEE 802.11ax with overlapping basic service sets," *Wireless Networks*, vol. 29, pp. 387–401, 2023. DOI: 10.1007/s11276-022-03148-w.

[5] P. Yi, W. Cheng, J. Wang, J. Pan, Y. Ouyang, and W. Zhang, "Intelligent Multi-link EDCA Optimization for Delay-Bounded QoS in Wi-Fi 7," arXiv preprint arXiv:2509.25855, 2025.

[6] Z. Zuo, D. Wang, X. Nie, X. Pan, M. Deng, and M. Ma, "PDCF-DRL: a contention window backoff scheme based on deep reinforcement learning for differentiating access categories," *The Journal of Supercomputing*, vol. 81, art. 213, 2025. DOI: 10.1007/s11227-024-06634-4.

[7] X. Du, X. Fang, R. He, L. Yan, L. Lu, and C. Luo, "Federated deep reinforcement learning-based intelligent channel access in dense Wi-Fi deployments," arXiv preprint arXiv:2409.01004, 2024.

[8] Q. Li, B. Lv, Y. Hong, and R. Wang, "ReinWiFi: Application-layer QoS optimization of WiFi networks with reinforcement learning," arXiv preprint arXiv:2405.03526, 2024.

[9] R. Jain, D. Chiu, and W. Hawe, "A quantitative measure of fairness and discrimination for resource allocation in shared computer systems," *DEC Research Report TR-301*, 1984.

[10] IEEE Standard 802.11ax-2021, "IEEE Standard for Information Technology — Amendment 1: Enhancements for High-Efficiency WLAN," IEEE, 2021.
