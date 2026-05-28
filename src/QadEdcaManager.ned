//
// QAD-EDCA Manager: Queue-Aware Dynamic EDCA Parameter Adjustment
//
// Monitors per-AC queue occupancy and packet loss at the AP,
// and dynamically adjusts EDCA parameters to prevent low-priority starvation.
//

package edcafairness.src;

simple QadEdcaManager
{
    parameters:
        // Module path to the AccessPoint
        string apModule = default("ap");

        // Monitoring
        double monitorInterval @unit(s) = default(0.1s);  // How often to check queue states

        // Starvation detection thresholds
        double queueThreshold = default(0.8);   // Queue occupancy ratio triggering adjustment
        double lossThreshold = default(0.1);     // Packet loss rate triggering adjustment

        // Adjustment parameters
        int aifsStep = default(1);               // AIFSN reduction step for BE/BK
        double cwScaleFactor = default(2.0);     // CWmin multiplier for VO/VI
        double txopScaleFactor = default(0.75);  // TXOP limit multiplier for VO/VI
        double recoveryFactor = default(0.3);    // Exponential recovery toward defaults

        // Safety bounds
        // minAifsn=2: per IEEE 802.11-2020 EDCA timing, AIFS = SIFS + AIFSN*aSlotTime;
        // AIFS must exceed DIFS = SIFS + 2*aSlotTime, so AIFSN >= 2.
        int minAifsn = default(2);
        double minTxopLimit @unit(s) = default(0.5ms);

        // QoS constraints
        // voDelayBound=150ms: ITU-T G.114 ("if delay can be kept below this figure,
        //   most applications will experience essentially transparent interactivity");
        //   3GPP TS 23.501 Table 5.7.4-1 5QI=1 PDB=100ms (one-way, end-to-end UE<->UPF/N6);
        //   3GPP TS 26.114 Annex E IMS VoIP transfer delay = 130ms.
        double voDelayBound @unit(s) = default(0.15s);

        // viDelayBound=150ms: 3GPP TS 23.501 Table 5.7.4-1 5QI=2 Conversational Video PDB=150ms;
        //   3GPP TS 26.114 Annex E IMS conversational video transfer delay = 170ms.
        //   (Previously 0.3s = 5QI=4 non-conversational, inconsistent with our 1 Mbps live stream traffic.)
        double viDelayBound @unit(s) = default(0.15s);

        @display("i=block/control");
        @class(QadEdcaManager);

        // Signals for result recording
        @signal[starvationDetected](type=bool);
        @signal[adjustedCwMinVo](type=long);
        @signal[adjustedCwMinVi](type=long);
        @signal[adjustedAifsnBe](type=long);
        @signal[adjustedAifsnBk](type=long);

        @statistic[starvationDetected](title="starvation detected"; record=count,vector; interpolationmode=sample-hold);
        @statistic[adjustedCwMinVo](title="adjusted CWmin VO"; record=vector; interpolationmode=sample-hold);
        @statistic[adjustedCwMinVi](title="adjusted CWmin VI"; record=vector; interpolationmode=sample-hold);
        @statistic[adjustedAifsnBe](title="adjusted AIFSN BE"; record=vector; interpolationmode=sample-hold);
        @statistic[adjustedAifsnBk](title="adjusted AIFSN BK"; record=vector; interpolationmode=sample-hold);
}
