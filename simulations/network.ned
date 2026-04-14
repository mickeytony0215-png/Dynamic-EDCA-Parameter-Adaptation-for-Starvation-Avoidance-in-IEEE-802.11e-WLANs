//
// EDCA Fairness Project - Network Topology
// 1 AP + N STAs in infrastructure BSS mode
//

package edcafairness.simulations;

import inet.networklayer.configurator.ipv4.Ipv4NetworkConfigurator;
import inet.node.inet.WirelessHost;
import inet.node.wireless.AccessPoint;
import inet.physicallayer.wireless.ieee80211.packetlevel.Ieee80211ScalarRadioMedium;
import inet.visualizer.common.IntegratedVisualizer;
import edcafairness.src.QadEdcaManager;

network EdcaFairnessNetwork
{
    parameters:
        int numVoStations = default(2);   // Number of Voice stations
        int numViStations = default(2);   // Number of Video stations
        int numBeStations = default(3);   // Number of Best Effort stations
        int numBkStations = default(3);   // Number of Background stations
        bool hasQadManager = default(false);  // Enable QAD-EDCA manager
        @display("bgb=800,600");

    submodules:
        qadManager: QadEdcaManager if hasQadManager {
            parameters:
                apModule = "ap";
                @display("p=400,50");
        }

        configurator: Ipv4NetworkConfigurator {
            @display("p=50,50");
        }

        radioMedium: Ieee80211ScalarRadioMedium {
            @display("p=50,120");
        }

        visualizer: IntegratedVisualizer {
            @display("p=50,190");
        }

        ap: AccessPoint {
            parameters:
                @display("p=400,300;r=,,#707070");
        }

        // Sink server (wired or wireless host receiving all traffic)
        server: WirelessHost {
            parameters:
                @display("p=400,150;r=,,#707070");
        }

        // Voice stations (AC_VO)
        voSta[numVoStations]: WirelessHost {
            parameters:
                @display("p=200,200");
        }

        // Video stations (AC_VI)
        viSta[numViStations]: WirelessHost {
            parameters:
                @display("p=600,200");
        }

        // Best Effort stations (AC_BE)
        beSta[numBeStations]: WirelessHost {
            parameters:
                @display("p=200,450");
        }

        // Background stations (AC_BK)
        bkSta[numBkStations]: WirelessHost {
            parameters:
                @display("p=600,450");
        }
}
