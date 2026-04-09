# Dynamic EDCA Parameter Adaptation for Starvation Avoidance in IEEE 802.11e WLANs

## Team Members

| Name | Student ID | Responsibilities |
|------|-----------|-----------------|
| (To be filled) | | |
| (To be filled) | | |

---

## 1. Introduction

The IEEE 802.11e amendment introduces the Enhanced Distributed Channel Access (EDCA) mechanism to provide Quality of Service (QoS) differentiation in Wireless Local Area Networks (WLANs). EDCA defines four Access Categories (ACs)---Voice (AC_VO), Video (AC_VI), Best Effort (AC_BE), and Background (AC_BK)---each configured with distinct channel access parameters: Arbitration Inter-Frame Space Number (AIFSN), Contention Window minimum and maximum (CWmin, CWmax), and Transmission Opportunity limit (TXOP limit). Higher-priority ACs are assigned more aggressive parameters (smaller CWmin, shorter AIFS, longer TXOP), enabling them to gain channel access more frequently and for longer durations.

While this differentiation successfully prioritizes delay-sensitive traffic such as voice and video, it introduces a fundamental fairness problem. Under heavy network load, high-priority traffic monopolizes channel access, leaving lower-priority traffic (BE and BK) with severely degraded throughput---or in extreme cases, complete starvation. The standard EDCA mechanism employs static, pre-configured parameters that remain fixed regardless of actual network conditions. This rigidity means that once a starvation condition develops, the standard protocol provides no adaptive mechanism to alleviate it.

The starvation problem is not merely a theoretical concern. In real-world deployments, WLANs simultaneously carry a mix of traffic types: video conferencing, web browsing, email, and background synchronization. When voice and video traffic consume a disproportionate share of channel resources, even basic web browsing (AC_BE) can become unusable. This degradation violates user expectations and undermines the utility of the network for non-real-time applications.

In this project, we propose **Queue-Aware Dynamic EDCA (QAD-EDCA)**, an adaptive algorithm that monitors per-AC queue occupancy and packet loss at the Access Point (AP) and dynamically adjusts EDCA parameters to provide minimum bandwidth guarantees for low-priority traffic while preserving the QoS requirements of high-priority flows. We evaluate our approach through extensive simulations using OMNeT++ with the INET Framework, comparing against standard EDCA and existing dynamic adaptation schemes from the literature.

---

## 2. Problem Definition

### 2.1 Starvation Condition

We formally define the starvation condition for a low-priority Access Category $AC_i$ (where $i \in \{BE, BK\}$) as follows:

$$
\text{Starvation}(AC_i) \iff \left( Q_i > Q_{th} \right) \lor \left( P_{loss,i} > P_{th} \right)
$$

where $Q_i$ denotes the current queue length of $AC_i$, $Q_{th}$ is the queue length threshold, $P_{loss,i}$ is the packet loss rate of $AC_i$, and $P_{th}$ is the packet loss rate threshold.

Starvation occurs when high-priority ACs (AC_VO, AC_VI) dominate channel access to the extent that low-priority ACs cannot successfully transmit frames within acceptable time bounds. The queues of low-priority ACs overflow, leading to packet drops and unbounded delays.

### 2.2 Limitations of Static EDCA

The standard EDCA assigns fixed parameters based on the 802.11e specification:

| AC | CWmin | CWmax | AIFSN | TXOP limit |
|----|-------|-------|-------|------------|
| AC_VO | $(aCWmin+1)/4 - 1$ | $(aCWmin+1)/2 - 1$ | 2 | 1.504 ms |
| AC_VI | $(aCWmin+1)/2 - 1$ | $aCWmin$ | 2 | 3.008 ms |
| AC_BE | $aCWmin$ | $aCWmax$ | 3 | 0 |
| AC_BK | $aCWmin$ | $aCWmax$ | 7 | 0 |

These parameters are determined at association time and remain constant throughout the session. The protocol lacks any feedback mechanism to detect when low-priority traffic is being starved or to adaptively reallocate channel access opportunities. As the proportion of high-priority stations increases, the fixed parameter gap between ACs leads to increasingly severe unfairness.

---

## 3. Proposed Solution: QAD-EDCA

### 3.1 Overview

Queue-Aware Dynamic EDCA (QAD-EDCA) operates at the Access Point (AP) as a centralized monitor and controller. The algorithm periodically samples the queue state and loss metrics of each AC and, upon detecting a starvation condition, applies graduated parameter adjustments to rebalance channel access opportunities. The adjustments are disseminated to all associated stations (STAs) via beacon frames.

### 3.2 Algorithm Design

The QAD-EDCA algorithm employs three complementary adjustment strategies, applied in escalating order of aggressiveness:

1. **AIFS Reduction for Low-Priority ACs**: Decrease the AIFSN of AC_BE and AC_BK by $\Delta_{AIFS}$, reducing their waiting time before contention.
2. **CWmin Increase for High-Priority ACs**: Increase the CWmin of AC_VO and AC_VI by a factor $\alpha_{CW}$, moderating their channel access aggressiveness.
3. **TXOP Limit Reduction for High-Priority ACs**: Decrease the TXOP limit of AC_VO and AC_VI by a factor $\beta_{TXOP}$, reducing the duration of each channel occupation.

When the starvation condition is resolved (queue length and loss rate return below thresholds), parameters are gradually restored toward their default values using an exponential decay function to avoid oscillation.

### 3.3 Pseudo-code

```
Algorithm: QAD-EDCA Dynamic Parameter Adjustment
Input: Monitoring interval T_mon, thresholds Q_th, P_th
       Adjustment factors: delta_AIFS, alpha_CW, beta_TXOP
       Recovery factor: gamma (0 < gamma < 1)

Every T_mon seconds at the AP:
  1. For each AC in {BE, BK}:
       Measure Q_i = queue length of AC_i
       Measure P_loss_i = packet loss rate of AC_i

  2. If (Q_BE > Q_th) OR (P_loss_BE > P_th)
        OR (Q_BK > Q_th) OR (P_loss_BK > P_th):
       // Starvation detected -- apply adjustments
       a. AIFSN_BE = max(AIFSN_BE - delta_AIFS, 2)
          AIFSN_BK = max(AIFSN_BK - delta_AIFS, 2)
       b. CWmin_VO = min(CWmin_VO * alpha_CW, CWmin_default_BE)
          CWmin_VI = min(CWmin_VI * alpha_CW, CWmin_default_BE)
       c. TXOP_VO = max(TXOP_VO * beta_TXOP, TXOP_min)
          TXOP_VI = max(TXOP_VI * beta_TXOP, TXOP_min)

  3. Else:
       // No starvation -- recover toward defaults
       a. AIFSN_BE = AIFSN_BE + gamma * (AIFSN_default_BE - AIFSN_BE)
          AIFSN_BK = AIFSN_BK + gamma * (AIFSN_default_BK - AIFSN_BK)
       b. CWmin_VO = CWmin_VO + gamma * (CWmin_default_VO - CWmin_VO)
          CWmin_VI = CWmin_VI + gamma * (CWmin_default_VI - CWmin_VI)
       c. TXOP_VO = TXOP_VO + gamma * (TXOP_default_VO - TXOP_VO)
          TXOP_VI = TXOP_VI + gamma * (TXOP_default_VI - TXOP_VI)

  4. Broadcast updated parameters to all STAs via beacon frame

  5. Verify QoS constraints:
       If delay_VO > 150 ms OR delay_VI > 300 ms:
         Partially revert adjustments (reduce delta by 50%)
```

### 3.4 Key Parameters

| Parameter | Symbol | Default Value | Description |
|-----------|--------|---------------|-------------|
| Monitoring interval | $T_{mon}$ | 100 ms | How often the AP checks queue states |
| Queue threshold | $Q_{th}$ | 80% of buffer size | Triggers starvation detection |
| Loss rate threshold | $P_{th}$ | 10% | Triggers starvation detection |
| AIFS adjustment step | $\Delta_{AIFS}$ | 1 | AIFSN reduction per adjustment cycle |
| CW scaling factor | $\alpha_{CW}$ | 2.0 | Multiplier for CWmin increase |
| TXOP scaling factor | $\beta_{TXOP}$ | 0.75 | Multiplier for TXOP reduction |
| Recovery factor | $\gamma$ | 0.3 | Exponential decay toward defaults |

---

## 4. Simulation Design

### 4.1 Simulation Environment

We use **OMNeT++ 6.1** with **INET Framework 4.5** as our simulation platform. INET provides a complete implementation of the IEEE 802.11e EDCA mechanism through the `Ieee80211Mac` module with QoS support enabled via the `qosStation` parameter.

### 4.2 Network Topology

The simulated network consists of a single Access Point (AP) operating in infrastructure Basic Service Set (BSS) mode, with $N$ associated wireless stations (STAs). We evaluate four network sizes: $N \in \{5, 10, 15, 20\}$.

### 4.3 Traffic Model

| AC | Application | Packet Size | Send Interval | Data Rate |
|----|-------------|-------------|---------------|-----------|
| AC_VO | VoIP (G.711) | 160 bytes | 20 ms | 64 kbps |
| AC_VI | Video stream | 1280 bytes | 10 ms | 1.024 Mbps |
| AC_BE | Bulk transfer (FTP/TCP or saturated UDP) | 1500 bytes | Variable | Saturated |
| AC_BK | Background sync | 512 bytes | 100 ms | 40.96 kbps |

### 4.4 Experimental Variables

1. **High-priority STA proportion**: 20%, 40%, 60%, 80% of STAs generate VO/VI traffic.
2. **Overall network load**: Light ($<30\%$ capacity), Medium ($30\text{--}60\%$), Heavy ($60\text{--}90\%$), Saturated ($>90\%$).
3. **QAD-EDCA threshold parameters**: We sweep $Q_{th} \in \{50\%, 70\%, 80\%, 90\%\}$ and $P_{th} \in \{5\%, 10\%, 15\%, 20\%\}$ to evaluate sensitivity.

### 4.5 Performance Metrics

- **Per-AC throughput** (bits/s)
- **Per-AC average delay and delay jitter** (seconds)
- **Per-AC packet loss rate** (%)
- **Jain's Fairness Index** across all ACs: $J = \frac{(\sum_{i=1}^{n} x_i)^2}{n \sum_{i=1}^{n} x_i^2}$
- **QoS satisfaction**: Whether AC_VO delay $< 150$ ms and AC_VI delay $< 300$ ms

### 4.6 Comparison Schemes

1. **Standard EDCA** (Baseline): Fixed default parameters per IEEE 802.11e.
2. **Adaptive EDCA (Banchs 2010)**: Optimal EDCA parameter configuration based on analytical model [1].
3. **Starvation Prediction EDCA (Engelstad 2005)**: Delay and throughput analysis with starvation prediction [2].
4. **QAD-EDCA** (Proposed): Our queue-aware dynamic adaptation scheme.

---

## 5. Project Plan and Timeline

| Week | Period | Tasks | Deliverables |
|------|--------|-------|-------------|
| 1--2 | Apr 15 -- Apr 28 | Environment setup; Implement and validate baseline EDCA simulation; Reproduce standard EDCA starvation under high load | Baseline simulation results; Starvation demonstration plots |
| 3--4 | Apr 29 -- May 12 | Implement QAD-EDCA algorithm in OMNeT++/INET; Integrate with Edcaf module; Unit testing | Working QAD-EDCA module; Preliminary comparison results |
| 5--6 | May 13 -- May 26 | Run full experimental matrix (N, load, thresholds); Collect throughput, delay, loss, fairness data; Implement literature comparison schemes | Complete simulation data; Analysis scripts |
| 7--8 | May 27 -- Jun 10 | Analyze results and generate figures; Write final report; Prepare presentation slides | Final report (PDF); Presentation slides |

### Gantt Chart

```
Task                          W1   W2   W3   W4   W5   W6   W7   W8
                             4/15 4/22 4/29 5/06 5/13 5/20 5/27 6/03
Environment & Baseline       ████ ████
QAD-EDCA Implementation                ████ ████
Experiments & Data Collection                     ████ ████
Literature Comparison                             ████ ████
Analysis & Figures                                          ████ ████
Report Writing                                         ████ ████ ████
Presentation Prep                                                ████
                                                          Deadline: 6/10
```

---

## 6. Team Responsibilities

| Role | Member | Tasks |
|------|--------|-------|
| Algorithm Design & Implementation | (To be filled) | QAD-EDCA algorithm design; C++ implementation in OMNeT++/INET |
| Simulation & Experimentation | (To be filled) | Network topology setup; Traffic configuration; Running experiments |
| Analysis & Visualization | (To be filled) | Result parsing; Statistical analysis; Figure generation |
| Report & Literature Review | (To be filled) | Literature survey; Proposal and final report writing |

*Note: Team members may share responsibilities across roles.*

---

## 7. References

[1] A. Banchs and X. Perez-Costa, "Providing throughput guarantees in IEEE 802.11e wireless LANs," in *Proc. IEEE Wireless Communications and Networking Conference (WCNC)*, 2002; Extended analysis in A. Banchs, A. Azcorra, C. Garcia, and R. Cuevas, "Applications and challenges of the 802.11e EDCA mechanism: a survey," *IEEE Communications Surveys & Tutorials*, vol. 12, no. 1, 2010.

[2] P. E. Engelstad, O. N. Osterbo, "Delay and throughput analysis of IEEE 802.11e EDCA with starvation prediction," in *Proc. IEEE Conference on Local Computer Networks (LCN)*, 2005.

[3] I. Inan, F. Keceli, and E. Ayanoglu, "Fairness Provision in the IEEE 802.11e Infrastructure Basic Service Set," arXiv preprint arXiv:0704.1842, 2007.

[4] J. Lee, J. Choi, and S. Bahk, "Starvation avoidance-based dynamic multichannel access for low priority traffics in 802.11ac," *Computers & Electrical Engineering*, vol. 82, 2020.

[5] IEEE Standard 802.11e-2005, "IEEE Standard for Information technology--Local and metropolitan area networks--Specific requirements--Part 11: Wireless LAN Medium Access Control (MAC) and Physical Layer (PHY) Specifications, Amendment 8: Medium Access Control (MAC) Quality of Service Enhancements," IEEE, 2005.

[6] R. Jain, D. Chiu, and W. Hawe, "A quantitative measure of fairness and discrimination for resource allocation in shared computer systems," *DEC Research Report TR-301*, 1984.

[7] IEEE Standard 802.11-2020, "IEEE Standard for Information Technology--Telecommunications and Information Exchange between Systems--Local and Metropolitan Area Networks--Specific Requirements--Part 11: Wireless LAN Medium Access Control (MAC) and Physical Layer (PHY) Specifications," IEEE, 2020.
