//
// QadTxopProcedure: Subclass of INET's TxopProcedure
//

#include "QadTxopProcedure.h"

Define_Module(QadTxopProcedure);

void QadTxopProcedure::initialize(int stage)
{
    TxopProcedure::initialize(stage);
    // The actual AC-specific TXOP limit (IEEE 802.11-2020 Table 9-155)
    // is set by QadEdcaManager in INITSTAGE_LINK_LAYER via setTxopLimit().
}
