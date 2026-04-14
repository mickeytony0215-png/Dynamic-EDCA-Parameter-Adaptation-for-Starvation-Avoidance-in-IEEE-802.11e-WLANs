//
// QadEdca: Copy of INET's Edca module structure
// with QadEdcaf replacing Edcaf in the edcaf[] submodule array.
//

package edcafairness.src;

import inet.linklayer.ieee80211.mac.contract.ICollisionController;
import inet.linklayer.ieee80211.mac.originator.NonQosRecoveryProcedure;
import edcafairness.src.QadEdcaf;

module QadEdca
{
    parameters:
        int numEdcafs = default(4);
        string rxModule;
        string rateSelectionModule;

        *.rateSelectionModule = "^." + this.rateSelectionModule;
        *.rxModule = "^." + this.rxModule;
        *.collisionControllerModule = "^.collisionController";

        edcaf[0].accessCategory = default("AC_BK");
        edcaf[1].accessCategory = default("AC_BE");
        edcaf[2].accessCategory = default("AC_VI");
        edcaf[3].accessCategory = default("AC_VO");

        @class(inet::ieee80211::Edca);
        @display("i=block/star");
    submodules:
        edcaf[numEdcafs]: QadEdcaf {
            parameters:
                @display("p=100,100,row,150");
        }
        collisionController: <default("EdcaCollisionController")> like ICollisionController {
            parameters:
                @display("p=100,200");
        }
        mgmtAndNonQoSRecoveryProcedure: NonQosRecoveryProcedure {
            parameters:
                cwCalculatorModule = "^.edcaf[1]"; // best effort
                rtsPolicyModule = "^.^.rtsPolicy";
                @display("p=400,200");
        }
}
