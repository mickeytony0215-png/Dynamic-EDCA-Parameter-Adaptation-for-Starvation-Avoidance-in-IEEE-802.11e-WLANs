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
        int minAifsn = default(2);               // Minimum AIFSN (cannot go below SIFS + 2 slots)
        double minTxopLimit @unit(s) = default(0.5ms);  // Minimum TXOP limit

        // QoS constraints
        double voDelayBound @unit(s) = default(0.15s);  // Voice delay upper bound
        double viDelayBound @unit(s) = default(0.3s);    // Video delay upper bound

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
