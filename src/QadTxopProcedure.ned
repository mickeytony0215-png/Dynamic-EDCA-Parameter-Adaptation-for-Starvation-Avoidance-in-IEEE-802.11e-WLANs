//
// QadTxopProcedure: extends TxopProcedure to allow runtime
// TXOP limit adjustment by QadEdcaManager.
//

package edcafairness.src;

import inet.linklayer.ieee80211.mac.originator.TxopProcedure;

simple QadTxopProcedure extends TxopProcedure
{
    parameters:
        @class(QadTxopProcedure);
}
