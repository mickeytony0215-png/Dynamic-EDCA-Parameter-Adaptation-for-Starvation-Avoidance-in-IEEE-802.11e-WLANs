//
// QadTxopProcedure: Subclass of INET's TxopProcedure that exposes
// setTxopLimit() for dynamic TXOP limit adjustment at runtime.
//

#ifndef __EDCAFAIRNESS_QADTXOPPROCEDURE_H
#define __EDCAFAIRNESS_QADTXOPPROCEDURE_H

#include <omnetpp.h>
#include "inet/linklayer/ieee80211/mac/originator/TxopProcedure.h"

using namespace omnetpp;
using namespace inet::ieee80211;

class QadTxopProcedure : public TxopProcedure
{
  protected:
    virtual void initialize(int stage) override;

  public:
    /**
     * Dynamically set the TXOP limit.
     * Called by QadEdcaManager during parameter adjustment.
     */
    void setTxopLimit(simtime_t newLimit) { limit = newLimit; }
};

#endif
