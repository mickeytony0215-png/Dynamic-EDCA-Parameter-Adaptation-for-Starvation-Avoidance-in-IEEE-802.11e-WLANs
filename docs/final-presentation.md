# Final Project Presentation (Speaker Notes)
# Dynamic EDCA Parameter Adaptation for Starvation Avoidance in IEEE 802.11 WLANs
### QAD-EDCA: Queue-Aware Dynamic EDCA

> **Course:** NSYSU Wireless Communication Network, Spring 2026 · **Format:** ~15 min talk + 5 min Q&A
> **Figures:** `analysis/figures/` (PDF/PNG) · **Data basis:** `docs/standards-alignment-2026-05-28.md` · numbers match `report.tex`
> **Platform:** OMNeT++ 6.1 + INET 4.5; 5 reps/config (10 for the dynamic scenario), averaged.
>
> **Structure (5 parts):** 1) Introduction · 2) Background (succinct) + Problem definition ·
> 3) Solution (algorithm pseudo-code + high-level math) · 4) Analysis & discussion · 5) Comparison / demo.

---

## Speaker notes (delete before exporting slides)

Each slide has two parts:
- **On slide** — the text actually on the slide. Keep it short; don't read it word for word.
- **Say** — what I actually say. `(~Xs)` is a rough time estimate.
- `[Figure: …]` — the figure to show; each one has a backup table.

**Timing (~14 min, leaves buffer). `[CORE]` = always cover · `[IF TIME]` = skip first if short on time.**

| Part | Topic | Slides | Budget | Running |
|---|---|---|---|---|
| 1 | Introduction | 1-1 … 1-3 | 1:30 | 1:30 |
| 2 | Background + problem | 2-1, 2-2 | 2:00 | 3:30 |
| 3 | Solution: pseudo-code + math | 3-1 … 3-4 | 3:30 | 7:00 |
| 4 | Analysis & discussion | 4-1 … 4-6 | 5:00 | 12:00 |
| 5 | Comparison / demo | 5-1 … 5-3 | 2:00 | 14:00 |

**If only 10 minutes:** 1-2 → 2-1 → 2-2 → 3-1 → 3-4 → 4-1 → 4-4 → 4-5 → 4-6 → 5-2 → 5-3.
**Cut order if over time:** 3-2 → 3-3 → 4-3 → 4-2 → 5-1. Slide 4-4 (the ceiling) is a main point — slow down on Part 4.

---
---

# Part 1 — Introduction · `[CORE]` · 1:30

### Slide 1-1: Title
**On slide:**
- **QAD-EDCA: Queue-Aware Dynamic EDCA**
- Dynamic EDCA Parameter Adaptation for Starvation Avoidance in IEEE 802.11 WLANs
- CSE625, NSYSU, Spring 2026

**Say (~10s):**
> Hi everyone. Our project is on the starvation problem in 802.11 EDCA: a lightweight controller at the AP that detects starvation and adjusts the EDCA parameters at runtime.

---

### Slide 1-2: Motivation — why starvation happens `[CORE]`
**On slide:**
- One Wi-Fi link carries voice / video / web / background at the same time
- EDCA prioritizes with **static** parameters: VO > VI > BE > BK [1]
- Under heavy load, **VO/VI monopolize the channel** → BE/BK get near-zero throughput + excessive loss = **starvation** [2][3]
- Still a problem in Wi-Fi 6/7 (MU-EDCA, MLO) [10]
- **IEEE 802.11 has NO built-in feedback** to detect or fix starvation

**Say (~35s):**
> Modern Wi-Fi runs voice, video, web, and background traffic on the same channel. EDCA separates them into four priority classes, but the parameters are static — once you associate, they're fixed. When the load gets high, the high-priority classes monopolize the channel, and the low-priority ones, BE and BK, basically starve: throughput close to zero, high loss — a well-documented effect (Ugwu et al. [2], Mammeri et al. [3]). This is still around in Wi-Fi 6 and 7. The key gap: IEEE 802.11 has no feedback — nothing detects starvation and nothing corrects it. That's what we're filling.

---

### Slide 1-3: Goal & contributions `[CORE]`
**On slide:**
- **QAD-EDCA**: AP monitors queues → detects starvation → adjusts EDCA → exponentially recovers once it clears
- Goals: relieve starvation / no manual tuning / preserve VO/VI QoS / O(1) cost
- Contributions:
  1. A formal starvation predicate (queue **OR** loss)
  2. A complete O(1) closed-loop controller
  3. A negative result: feedback can't beat tuned static in steady state, and we explain why
  4. Positioning vs static and DRL

**Say (~30s):**
> Our method is QAD-EDCA, and it runs only at the AP: every beacon interval it reads the queues, checks for starvation, adjusts a few parameters, and decays back to default when there's no problem. There are four contributions. The third one is a negative result — in steady state, this kind of feedback control actually can't beat a well-tuned static configuration, and we'll explain why that happens.

---
---

# Part 2 — Background (succinct) + Problem definition · 2:00

### Slide 2-1: EDCA defaults & the starvation problem (measured) `[CORE]`
**On slide:**
- IEEE 802.11-2020 defaults (OFDM PHY); lower CWmin/AIFSN ⇒ wins the channel more easily:

| AC | CWmin | AIFSN | TXOP |
|----|-------|-------|------|
| VO | 3 | 2 | 1.504 ms |
| VI | 7 | 2 | 3.008 ms |
| BE | 15 | 3 | 0 |
| BK | 15 | 7 | 0 |

- Measured (N=10, 1VO/1VI/4BE/4BK): Standard EDCA → **BE loss ≈ 94.7%, delay ≈ 1086 ms**
- Ugwu et al. [2]: **AIFSN has greatest influence** on this disparity
- Mammeri et al. [3] proposed SDMA: relies on **channel bonding** — N/A to single-channel BSS

**Say (~45s):**
> Quick background. These are the standard EDCA defaults [1]. The smaller the CWmin and AIFSN, the easier it is to win the channel, so VO and VI win. Below that is our own simulation: with N=10 and four saturated BE stations, standard EDCA gives BE about 94.7% loss and over a second of delay, so it's basically starved. The literature agrees: Ugwu et al. [2] show AIFSN has the biggest effect on the disparity, and Mammeri et al. [3] propose SDMA, but it needs channel bonding, so it doesn't apply to our single-channel BSS.

---

### Slide 2-2: Problem definition `[CORE]`
**On slide:**
- Starvation predicate (the detector):
$$\text{Starv}(AC_i) \iff \Big(\tfrac{Q_i}{Q_{cap}} > Q_{th}\Big) \lor \big(P_{loss,i} > P_{th}\big),\quad Q_{th}=0.8,\ P_{th}=0.1$$
- Two complementary indicators, OR-combined: occupancy = sustained pressure · loss = packets can't get in
- Why static falls short: access prob $\tau \approx \tfrac{2}{\text{CWmin}+1}$ → VO 0.5 vs BE 0.125
- A trap (returns in Part 4): relieving starvation drains the queue, which removes its own trigger

**Say (~50s):**
> Next we make starvation something we can actually test. A class is starving if its AP queue occupancy is over 80%, or its loss rate is over 10%. We use both because they're complementary — a full queue means sustained pressure, and high loss means packets can't even get into the queue — so we combine them with OR. Why is static guaranteed to fall short? The access probability is roughly 2 over CWmin plus 1, so VO is around 0.5 and BE is only 0.125, and there's no feedback to fix it. One more thing worth saying up front: any feedback controller that successfully relieves starvation will drain the queue it's watching, which removes its own trigger. We come back to this in Part 4.

---
---

# Part 3 — Solution: pseudo-code + high-level math · `[CORE]` · 3:30

### Slide 3-1: Architecture `[CORE]`
**On slide:**
```
┌──────────────── QAD-EDCA Manager (at the AP) ────────────────┐
│  Monitor ──→  Detect ──→  Adjust ──→  Recover                │
│ queue/loss   starving?  AIFSN/CW/TXOP  exp. decay            │
└──────────────────────────────────────────────────────────────┘
       one control loop every T_mon = 100 ms · AP-side only
```
- The AP already broadcasts the EDCA Parameter Set in beacons → stations unchanged
- Implemented as an INET `Hcf→Edca→Edcaf→TxopProcedure` subclass chain

**Say (~25s):**
> The system is just a manager added at the AP that closes the loop the standard is missing: monitor, detect, adjust, recover, once every 100 ms. Since it only touches the AP, and the AP already broadcasts EDCA parameters in beacons, the clients don't need any changes.

---

### Slide 3-2: Mitigation — three parameters, three phases of access `[IF TIME]`
**On slide:**
On detecting starvation, all three at once:
1. Lower BE/BK AIFSN (−1 per cycle, floor 2) → contend earlier
2. Bidirectional CWmin: raise VO/VI (×α, cap 15), lower BE/BK (÷α, floor 7)
3. Lower VO/VI TXOP (×β, floor 0.5 ms) → release the channel earlier

> AIFSN = when contention starts · CWmin = how long you back off · TXOP = how long you hold the channel

**Say (~35s):**
> Why three parameters? Because channel access has three phases, and each parameter covers one. AIFSN is when you start contending — we shorten it for the starved classes. CWmin is how long you back off — here we move it both ways, up for VO/VI and down for BE/BK, but with bounds so they never cross, so the priority order is preserved. TXOP is how long you hold the channel after winning — we shorten it for VO/VI so they release it sooner.

---

### Slide 3-3: Recovery · safety valve · hysteresis `[IF TIME]`
**On slide:**
- Exponential recovery (no starvation): $P \leftarrow P + \gamma(P_{def}-P)$, $\gamma=0.3$
- QoS safety valve: if $d_{VO}$ or $d_{VI} > 150$ ms → pull halfway back, QoS first
- Schmitt hysteresis: trigger at threshold, release only below 0.4×, to avoid flapping

**Say (~30s):**
> There are also three things that keep it stable. First, when there's no starvation, parameters decay back gradually instead of snapping back, which avoids oscillation. Second, a safety valve: if VO or VI delay goes over 150 ms, we pull the adjustment halfway back — QoS comes first. Third, Schmitt hysteresis: it triggers at the threshold but only releases once it drops well below, so short fluctuations don't make it switch on and off repeatedly.

---

### Slide 3-4: Algorithm + math `[CORE]`
**On slide:**
```
Every T_mon (=100 ms, beacon-aligned), at the AP:
  1. for i ∈ {BE,BK}: read Q_i/Q_cap and P_loss_i
  2. if Starv(BE) ∨ Starv(BK):                    // 3-D adjust
        AIFSN_{BE,BK} = max(AIFSN−1, 2)
        CWmin_{VO,VI} = min(CWmin·α, 15)           // throttle high prio
        CWmin_{BE,BK} = max(CWmin/α, 7)            // speed up low prio
        TXOP_{VO,VI}  = max(TXOP·β, TXOP_min)
     else:                                         // exponential recovery
        P ← P + γ·(P_default − P)
  3. broadcast the new EDCA set via beacon
  4. if d_VO>150ms ∨ d_VI>150ms:  P ← (P+P_default)/2   // QoS valve
```
- Math: $\tau \approx \tfrac{2}{\text{CWmin}+1}$; CWmin 3→15 takes access prob from 0.5 to 0.125
- O(1): each cycle reads 4 queues + 4 loss rates + threshold checks, no training (vs DRL's O(inference))

**Say (~50s):**
> This is the full algorithm. Every 100 ms we read eight numbers; if BE or BK is starving, we do those three adjustments; otherwise we decay the parameters back to default. Then we broadcast via the beacon, and run the QoS valve at the end. The math is just this access-probability formula: taking CWmin from 3 to 15 drops the probability from 0.5 to 0.125, and that's the basis for throttling the high-priority classes. The complexity is O(1) — each cycle is a few reads and comparisons, no training, and that's the main difference from the DRL approaches.

---
---

# Part 4 — Analysis & discussion · 5:00

> This is the longest part. Slow down on 4-4 (the ceiling).

### Slide 4-1: Steady-state results `[CORE]`
**On slide:**
[Figure: throughput_comparison.png · delay_comparison.png · packet_loss.png]
N=10, 1 VO/1 VI/4 BE/4 BK (only BE saturated):

| AC | Tput Std/Tuned/QAD (Mbps) | Delay Std/Tuned/QAD (ms) |
|---|---|---|
| VO | 0.06 / 0.06 / 0.06 | 19.9 / 19.4 / 19.6 |
| VI | 1.02 / 1.02 / 1.02 | 21.7 / 21.6 / 21.3 |
| **BE** | 2.53 / 5.80 / **5.44** | 1086 / 832 / 957 |
| BK | 0.16 / 0.16 / 0.16 | 75 / 60 / **152** |

- BE loss 94.7% → 88.6% · BE throughput ~2.15× · VO/VI unaffected
- Baselines: Standard · Tuned Static (hand-tuned, assumes load is known) · QAD

**Say (~45s):**
> First the steady-state results. BE throughput goes from 2.53 to 5.44, so a bit over 2x, and loss comes down from 94.7%. In the top two rows you can see VO and VI are almost identical across all three schemes, so we relieve starvation without hurting the real-time traffic. BK delay does go up to 152 ms, but background traffic has no delay requirement, so that's acceptable. There's a third baseline here, Tuned — the best static configuration we could hand-tune, which effectively assumes the load is already known. You can see QAD's 5.44 is still below its 5.80, and I'll explain that gap in a moment.

---

### Slide 4-2: Scaling `[IF TIME]`
**On slide:**
[Figure: n_scaling.png] — AC_BE throughput (Mbps), fixed 20% high-priority share:

| N | Standard | Tuned | **QAD** |
|---|---|---|---|
| 5 | 3.74 | 5.96 | **5.63** |
| 10 | 2.53 | 5.80 | **5.44** |
| 15 | 1.84 | 5.11 | **4.83** |
| 20 | 1.57 | 4.86 | **4.71** |

- Standard drops 3.74→1.57; QAD roughly holds (5.63→4.71); ratio over Standard grows 1.5× → 3.0×

**Say (~25s):**
> It also holds up with size. As the number of stations goes from 5 to 20, standard EDCA's BE drops down to 1.57, while QAD roughly holds, so our ratio over Standard actually grows from about 1.5x to 3x. It stays around 6% below Tuned, same as before.

---

### Slide 4-3: Parameter sensitivity `[IF TIME]`
**On slide:**
[Figure: sweep_cwscale · sweep_recoveryfactor · sweep_monitorinterval · threshold_sweep_heatmap]

| Param | Range | BE change |
|---|---|---|
| cwScale | 1.5–4.0 | ~0% |
| recovery γ | 0.1–0.7 | ~1.5% |
| monitor T | 50–500 ms | ~0.8% |
| queue Q_th | 0.5–0.9 | ~0.7% |

- All four within 1.5% → little per-deployment tuning needed (measured while the algorithm is firing)

**Say (~25s):**
> Since those five constants were our own choice, we did a parameter sweep. In steady state BE changes by at most 1.5%, and always in a sensible direction. So you don't really need to tune QAD for different deployments — any reasonable value gives about the same result, and this is measured while the algorithm is actually firing.

---

### Slide 4-4: The steady-state ceiling `[CORE]`
> Slow down here.

**On slide:**
- We added bidirectional CWmin + hysteresis to chase Tuned; BE 5.34 → 5.44, still below 5.80
- Structural, not under-tuning: once relieved, the queue drains → detector sees no starvation → boost decays (trigger 64% → ~15%)

| BE throughput (Mbps) | Standard | QAD | Tuned |
|---|---|---|---|
| 1VO/1VI/4BE/4BK | 2.53 | **5.44** | 5.80 |
| 2VO/2VI/3BE/3BK | 2.59 | **4.82** | 5.20 |
| 3VO/3VI/2BE/2BK | 2.78 | **4.22** | 4.54 |
| 4VO/4VI/1BE/1BK | 3.32 | **3.58** | 3.67 |

- Tuned wins in every mix; the gap is stable and narrows as the high-priority share grows
- For feedback to beat static in steady state, it would have to hold max boost unconditionally — i.e. become static

**Say (~55s):**
> Now the deeper result. We added bidirectional CWmin and hysteresis to try to catch Tuned, but BE only went from 5.34 to 5.44, still below 5.80, and it loses in every mix. This isn't a matter of tuning harder — it's structural. The reason is the trap from earlier: as soon as QAD drains BE's queue, the detector no longer sees starvation, so the boost decays, and the trigger rate drops from 64% to about 15%. In other words, for feedback control to beat the static optimum in steady state, it would have to hold the maximum adjustment unconditionally, but then it's just become a static method and lost its adaptivity. So this is a fundamental limit of feedback versus feedforward, and it leads into the next part, where feedback does have an advantage.

---

### Slide 4-5: Dynamic load — BE tracks the oracle with no tuning `[CORE]`
**On slide:**
[Figure: fig_dynamic_be_throughput.png · (optional) fig_dynamic_qad_adapt.png]
- Scenario: 60 s, calm[0,20) → surge[20,40) → calm[40,60), 10 reps
- Trace: VO/VI CWmin 3/7 → ~6–10, BE AIFSN → 2, so the parameters really do move

| Phase | Standard | Tuned | QAD |
|---|---|---|---|
| calm | 2.6 | 6.0 | **5.6** |
| surge | 1.9 | 4.0 | **3.7** |

- QAD tracks Tuned throughout (~2.15×), but Tuned needs the load known in advance and QAD doesn't

**Say (~45s):**
> Where feedback has an advantage is when the load changes. This scenario has three phases: calm, surge, calm. You can see QAD's BE throughput tracks Tuned the whole way, about 2x Standard. The difference is that Tuned is tuned for one fixed operating point and doesn't change, whereas QAD needs no prior knowledge of the load — when the surge comes it follows, and when it ends it relaxes. The trace on top also shows the parameters actually moving.

---

### Slide 4-6: QAD recovers a QoS violation `[CORE]`
**On slide:**
[Figure: fig_dynamic_hi_delay.png]
- Looking only at mean delay: all three keep VO/VI < 150 ms (Standard surge ~33 ms), looks fine
- Looking at the time series: Standard spikes to ~240 ms during the surge, above the VO 150 ms bound
- Tuned and QAD both hold it down; QAD has only a ~70 ms blip at the surge start
- QAD doesn't beat Tuned here either; what it wins is no foreknowledge and no tuning

**Say (~45s):**
> This slide is about QoS. If you only look at mean delay, all three are under 150 ms and look fine. But the time series is different: standard EDCA spikes to about 240 ms during the surge, which is over the VO 150 ms bound, so it's a real QoS violation. Tuned and QAD both keep it down — QAD only has a 70 ms blip right at the start of the surge and then flattens. That's the safety valve making sure we don't sacrifice VO when we throttle BE. QAD doesn't beat Tuned here either, which is consistent with the steady-state result; what it wins is not needing to know the load in advance and not needing manual tuning.

---
---

# Part 5 — Comparison / Demo · 2:00

### Slide 5-1: Demo — watch the controller adapt `[IF TIME]`
**On slide:**
[Demo: walk through the dynamic run — `fig_dynamic_qad_adapt.png` (params) next to `fig_dynamic_hi_delay.png` (delay)]
- calm → surge → calm, narrated:
  1. surge starts → VO/VI CWmin rises, BE AIFSN drops (controller reacting)
  2. Standard's VO delay spikes to ~240 ms; QAD stays flat
  3. surge ends → parameters decay back to default

> If a screen recording of the OMNeT++ Qtenv run is available, play it here instead of the figures.

**Say (~35s):**
> A quick demo. I'll just walk through the dynamic run: when the surge starts, on the left you can see VO/VI CWmin going up and BE AIFSN going down — that's the controller reacting. On the right, standard delay spikes to 240 ms while QAD stays flat. After the surge ends, the parameters decay back to default on their own.

---

### Slide 5-2: Comparison & positioning `[CORE]`
**On slide:**
[Figure: positioning_tradeoff.png]

| | Standard | **QAD** | Tuned oracle | PDCF-DRL [6] |
|---|---|---|---|---|
| Adaptive at runtime | no | **yes** | no | yes |
| Needs foreknowledge | no | **no** | **yes** | no |
| Needs training | no | **no** | no | **yes** |
| Per-cycle cost | O(1) | **O(1)** | O(1) | O(DRL) |
| BE relief | none | **2.15×** | ~2.3× | near-equal |

- DRL [6] (cited, different setup): collision 6.9–16.4%, normalized tput 76–85%, near-equal ACs, but thousands of training episodes
- Among methods that need no foreknowledge, no training, and deploy directly, QAD is the better option

**Say (~45s):**
> This slide compares against other methods. Look at the QAD column: adaptive at runtime, no foreknowledge of the load, no training, O(1), and BE roughly doubled. The DRL methods, like PDCF-DRL, perform better — they can nearly equalize all four ACs — but they need thousands of training episodes, can be worse than standard before they converge, and their setup is different from ours, so we use them only as a reference upper bound. The two methods that beat QAD each need something first — one needs the load known in advance, the other needs training. So among methods that need neither and can be deployed directly, QAD is the better choice.

---

### Slide 5-3: Conclusion `[CORE]`
**On slide:**
1. QAD-EDCA: starved BE ~2.15×, loss 94.7→88.6%, VO/VI unaffected, no tuning, O(1)
2. ~6% below the tuned oracle and DRL in steady state, but this is a structural limit of feedback (stable across mixes)
3. Robust to its own constants (≤1.5%)
- Future: detect using uplink/airtime · non-stationary loads · QAD as a DRL warm-start

**Say (~30s):**
> To wrap up. QAD-EDCA roughly doubles the starved BE throughput without hurting VO/VI QoS, with no tuning and O(1) cost. In steady state it is about 6% below the hand-tuned Tuned and below DRL, but we showed that's a structural limit of feedback control, not us tuning it badly. So QAD is best seen as a plug-and-play option — no foreknowledge of the load, no training. That's our presentation, thank you, and I'm happy to take questions.

---
---

## Q&A Preparation (~5 min)

**Q1 — QAD still doesn't beat Tuned Static in steady state, so what's the value?**
> Tuned is hand-tuned and assumes the load is already known and won't change. QAD gets within 6% of it with no tuning and automatic adaptation, and it doubles the starved throughput over Standard. We also showed that in saturated steady state, pure feedback simply can't beat a tuned static config — the gap is stable across every mix and size — so it's a structural result, not bad tuning.

**Q2 — How do you know QAD actually adapts under load?**
> We logged `starvationDetected` and the adjusted AIFSN/CWmin with vectors; under load it fires and the parameters change over time (`fig_dynamic_qad_adapt`). The dynamic scenario in Part 4 also shows it tracking the load as it shifts from calm to surge and back.

**Q3 — Why not just use DRL like PDCF-DRL [6]?**
> DRL has a higher performance ceiling, but it needs thousands of training episodes and compute, and can be worse than standard before it converges, which a resource-limited AP may not afford. QAD is O(1), needs no training, and works from the first cycle; it could even bridge the gap while a DRL agent trains. Its setup differs from ours, so we treat it as a reference bound, not a head-to-head.

**Q4 — Isn't a 100 ms monitoring interval too slow?**
> It's aligned with the beacon, so there's no extra overhead. The sweep shows 50–500 ms changes steady-state BE by under 1%. Going faster just costs more compute and is more prone to oscillation.

**Q5 — Why does the cross-AC Jain index [9] drop when you help BE?**
> Because raising BE, which is already the second-highest, makes the four ACs less even. Jain's index [9] isn't the right metric for starvation relief here; the right thing is whether BE/BK escape starvation, i.e. throughput recovers and loss drops (`fairness_index`).

**Q6 — How far is this from a real deployment?**
> We assume an ideal channel, instantaneous beacon propagation, and a wireless two-hop path to the server (which also causes the detector limitation in Part 4 — the AP only sees the downlink queue). A real environment has fading and interference; future work could combine with 802.11ax [10] TWT and use airtime for detection.

---

## References
[1] IEEE Std 802.11-2020. · [2] Ugwu et al., *J. Eng. Appl. Sci.*, 2022. · [3] Mammeri et al., *Comput. Electr. Eng.*, 2021. · [4] Tuan et al., *Wireless Netw.*, 2023. · [5] "Intelligent Multi-link EDCA Optimization for Delay-Bounded QoS in Wi-Fi 7," arXiv:2509.25855, 2025. · [6] Zuo et al., "PDCF-DRL," *J. Supercomput.*, 2025. · [7] Du et al., arXiv:2409.01004, 2024. · [8] Li et al., "ReinWiFi," arXiv:2405.03526, 2024. · [9] Jain et al., DEC TR-301, 1984. · [10] IEEE Std 802.11ax-2021.

- Standards alignment: `docs/standards-alignment-2026-05-28.md` (IEEE 802.11-2020 / 3GPP TS 23.501·26.114·TR 38.901 / ITU-T G.114·G.711 / IEEE 802.3 / RFC 3551).
- Baselines: Tuned Static = same-condition OMNeT++ simulation; PDCF-DRL [6] = published values (different setup, trend reference).
