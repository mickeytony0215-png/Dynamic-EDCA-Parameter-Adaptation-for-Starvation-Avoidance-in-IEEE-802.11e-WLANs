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

// Physical layout: 120 m x 50 m indoor office, matching the Indoor Hotspot
// (InH) / Indoor-office scenario in 3GPP TR 38.901 Table 7.2-2.
// 1 px in @display = 1 m via StationaryMobility's initFromDisplayString.
network EdcaFairnessNetwork
{
    parameters:
        int numVoStations = default(2);   // Number of Voice stations
        int numViStations = default(2);   // Number of Video stations
        int numBeStations = default(3);   // Number of Best Effort stations
        int numBkStations = default(3);   // Number of Background stations
        bool hasQadManager = default(false);  // Enable QAD-EDCA manager
        @display("bgb=120,50");

    submodules:
        qadManager: QadEdcaManager if hasQadManager {
            parameters:
                apModule = "ap";
                @display("p=5,5");
        }

        configurator: Ipv4NetworkConfigurator {
            @display("p=5,15");
        }

        radioMedium: Ieee80211ScalarRadioMedium {
            @display("p=5,25");
        }

        visualizer: IntegratedVisualizer {
            @display("p=5,35");
        }

        // Physical coordinates (m). AP at room centre, server next to AP,
        // four AC clusters within the 120 m x 50 m floor (max STA-AP distance ~33 m).
        ap: AccessPoint {
            parameters:
                @display("p=60,25;r=,,#707070");
        }

        server: WirelessHost {
            parameters:
                @display("p=60,10;r=,,#707070");
        }

        voSta[numVoStations]: WirelessHost {
            parameters:
                @display("p=30,20");
        }

        viSta[numViStations]: WirelessHost {
            parameters:
                @display("p=90,20");
        }

        beSta[numBeStations]: WirelessHost {
            parameters:
                @display("p=30,40");
        }

        bkSta[numBkStations]: WirelessHost {
            parameters:
                @display("p=90,40");
        }
}
