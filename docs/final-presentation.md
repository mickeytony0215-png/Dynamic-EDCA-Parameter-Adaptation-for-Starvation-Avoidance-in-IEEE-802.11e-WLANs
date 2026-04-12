# Final Project Presentation
# Dynamic EDCA Parameter Adaptation for Starvation Avoidance in IEEE 802.11 WLANs

> Duration: ~15 minutes presentation + 5 minutes Q&A
> Status: 🟢 Complete / 🟡 Pending simulation data / 🔴 Pending implementation

---

## 1. Introduction (~2 min) 🟢

### Slide 1-1: Title Page
- Title: Dynamic EDCA Parameter Adaptation for Starvation Avoidance in IEEE 802.11 WLANs
- Team members / Student IDs
- Course name / Date

### Slide 1-2: Motivation
- Modern WLANs simultaneously carry voice, video, web browsing, and background sync traffic
- EDCA uses static parameters for QoS differentiation, but causes low-priority traffic starvation under heavy load
- Wi-Fi 6/7 introduced new features (MU-EDCA, MLO), yet EDCA fairness issues persist
- Existing DRL approaches perform well but incur high computational cost; lightweight alternatives are needed

### Slide 1-3: Research Objectives
- Propose QAD-EDCA (Queue-Aware Dynamic EDCA) algorithm
- Real-time queue state monitoring at the AP with dynamic EDCA parameter adjustment
- Goals: mitigate starvation, improve fairness, preserve high-priority QoS, low computational cost

---

## 2. Background + Problem Definition (~3 min) 🟢

### Slide 2-1: EDCA Mechanism Overview
- Four Access Categories: AC_VO > AC_VI > AC_BE > AC_BK
- Channel access parameters: AIFSN, CWmin/CWmax, TXOP limit
- Parameter table:

| AC | CWmin | CWmax | AIFSN | TXOP |
|----|-------|-------|-------|------|
| AC_BK | 15 | 1023 | 7 | 2.528 ms |
| AC_BE | 15 | 1023 | 3 | 2.528 ms |
| AC_VI | 7 | 15 | 2 | 4.096 ms |
| AC_VO | 3 | 7 | 2 | 2.080 ms |

### Slide 2-2: The Starvation Problem
- Figure: high-priority STA proportion vs. AC_BE/AC_BK throughput collapse
- Ugwu et al. [2]: AIFSN has significantly more influence on QoS than CW
- Mammeri et al. [3]: severe starvation of low-priority traffic in 802.11ac

### Slide 2-3: Formal Problem Statement
- Starvation condition definition:

$$
\text{Starvation}(AC_i) \iff \left( \frac{Q_i}{Q_{cap}} > Q_{th} \right) \lor \left( P_{loss,i} > P_{th} \right)
$$

### Slide 2-4: Limitations of Existing Approaches

| Approach | Limitation |
|----------|-----------|
| SDMA [3] | Relies on multichannel; inapplicable to single-channel scenarios |
| OBSS QoS [4] | Only addresses inter-BSS interference, not intra-BSS starvation |
| PDCF-DRL [6] | High computational complexity; requires training convergence |
| ReinWiFi [8] | Application-layer, not MAC-layer |

- **Research Gap**: Lack of a lightweight, MAC-layer, real-time queue-aware starvation avoidance mechanism

---

## 3. Solution (~4 min) 🟢

### Slide 3-1: QAD-EDCA Architecture

```
┌─────────────────────────────────┐
│       QAD-EDCA Manager (AP)     │
│                                 │
│  Monitor ──→ Detect ──→ Adjust  │
│     │           │          │    │
│  Queue/Loss  Starvation?  AIFSN │
│  per AC       Y/N        CWmin  │
│                          TXOP   │
└────────────┬────────────────────┘
             │ Beacon Frame
    ┌────────┴────────┐
    ▼        ▼        ▼
  STA_1    STA_2    STA_N
```

### Slide 3-2: Three-Stage Adjustment Strategy
1. **Reduce AIFSN** (BE/BK) → shorten pre-contention wait time
2. **Increase CWmin** (VO/VI) → moderate channel access aggressiveness
3. **Reduce TXOP** (VO/VI) → decrease channel occupation duration

- Recovery mechanism: exponential decay $P(t+1) = P(t) + \gamma \cdot (P_{default} - P(t))$

### Slide 3-3: Algorithm Pseudo-code

```
Every T_mon seconds at AP:
  1. Measure Q_i, P_loss_i for AC_BE, AC_BK

  2. If Starvation detected:
       AIFSN_BE/BK  ← max(AIFSN - Δ, 2)
       CWmin_VO/VI  ← min(CWmin × α, CWmin_BE_default)
       TXOP_VO/VI   ← max(TXOP × β, TXOP_min)

  3. Else:
       Exponential recovery toward defaults

  4. Broadcast via beacon

  5. If VO delay > 150ms or VI delay > 300ms:
       Partial revert (50%)
```

### Slide 3-4: Mathematical Model
- Channel access probability: $\tau_i = \frac{2}{CWmin_i + 1}$
- Fairness metric (Jain Index): $J(\mathbf{x}) = \frac{(\sum x_i)^2}{n \sum x_i^2}$
- Key parameters:

| Parameter | Default | Description |
|-----------|---------|-------------|
| $T_{mon}$ | 100 ms | Monitoring interval |
| $Q_{th}$ | 80% | Queue occupancy threshold |
| $P_{th}$ | 10% | Packet loss rate threshold |
| $\Delta_{AIFS}$ | 1 | AIFSN adjustment step |
| $\alpha_{CW}$ | 2.0 | CWmin scaling factor |
| $\beta_{TXOP}$ | 0.75 | TXOP scaling factor |
| $\gamma$ | 0.3 | Recovery factor |

---

## 4. Analysis and Discussion (~3 min) 🟡

### Slide 4-1: Simulation Environment
- OMNeT++ 6.1 + INET Framework 4.5
- Network topology: 1 AP + N STAs (N = 5, 10, 15, 20)
- Traffic model: VO (G.711 64kbps), VI (1.024 Mbps), BE (saturated), BK (40.96 kbps)

### Slide 4-2: Starvation Demonstration (Baseline)
<!-- 🟡 Pending simulation data -->
- Figure: per-AC throughput vs. high-priority STA proportion under standard EDCA
- Expected: AC_BE/AC_BK throughput approaches zero when high-priority ratio >60%

### Slide 4-3: QAD-EDCA Effectiveness
<!-- 🟡 Pending simulation data -->
- Figure: QAD-EDCA vs. standard EDCA per-AC throughput comparison
- Figure: Jain's Fairness Index vs. high-priority STA proportion
- Expected: fairness improves from ~0.4 to >0.8

### Slide 4-4: Parameter Sensitivity Analysis
<!-- 🟡 Pending simulation data -->
- Figure: performance under different $Q_{th}$ and $P_{th}$ combinations
- Figure: $T_{mon}$ impact on responsiveness vs. stability
- Figure: $\gamma$ effect on oscillation behavior

### Slide 4-5: QoS Preservation Verification
<!-- 🟡 Pending simulation data -->
- Figure: AC_VO delay remains <150 ms during adjustments
- Figure: AC_VI delay remains <300 ms during adjustments

---

## 5. Comparison / Demo (~3 min) 🟡

### Slide 5-1: Comparison Summary Table
<!-- 🟡 Pending simulation data -->

| Metric | Standard EDCA | SDMA [3] | PDCF-DRL [6] | QAD-EDCA |
|--------|--------------|----------|-------------|----------|
| BE/BK throughput | — | — | — | — |
| Jain Index | — | — | — | — |
| VO delay | — | — | — | — |
| Complexity | O(1) | O(1) | O(DRL training) | O(1) |
| Training required | No | No | Yes | No |

### Slide 5-2: Key Findings
<!-- 🟡 Pending simulation data -->
- QAD-EDCA vs. Standard EDCA: starvation mitigation effectiveness
- QAD-EDCA vs. PDCF-DRL: performance vs. computational cost trade-off
- QAD-EDCA applicability and limitations

### Slide 5-3: Live Demo
<!-- 🔴 Pending implementation -->
- Using OMNeT++ Qtenv GUI:
  1. Baseline scenario: observe starvation occurring
  2. QAD-EDCA scenario: observe dynamic parameter adjustment in action
  3. Real-time queue occupancy and throughput visualization

### Slide 5-4: Conclusion
- QAD-EDCA successfully mitigates EDCA starvation with lightweight rules
- Significantly improves fairness while preserving VO/VI QoS guarantees
- No training phase required; suitable for real-time deployment on resource-constrained APs
- Future work: extend to Wi-Fi 7 MLO environments; hybrid approach with DRL schemes

---

## Q&A Preparation (~5 min)

### Anticipated Questions and Talking Points

**Q1: Why not just use DRL?**
- DRL achieves better performance but requires training time and computational resources
- QAD-EDCA is positioned as a lightweight alternative suitable for immediate deployment
- The two are complementary: QAD-EDCA can serve as a transitional mechanism before DRL converges

**Q2: Is the 100ms monitoring interval too slow?**
- Beacon frame interval is typically 100ms; monitoring is synchronized with it
- Faster monitoring increases computational overhead and may cause oscillation
- Sensitivity analysis will demonstrate the impact of different T_mon values

**Q3: How do you ensure adjustments don't degrade VO/VI QoS?**
- Step 5 QoS constraint verification mechanism
- Adjustments are bounded (CWmin capped at BE default; AIFSN floor at 2)
- Partial revert mechanism (50%) serves as a safety valve

**Q4: How does this differ from real-world deployment?**
- Simulation uses ideal channel model; real environments have fading and interference
- Beacon frame propagation delay is instantaneous in simulation but not in practice
- Future work can integrate with 802.11ax TWT for further improvement

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
