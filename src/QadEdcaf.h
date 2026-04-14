//
// QadEdcaf: Subclass of INET's Edcaf that allows runtime
// modification of EDCA timing parameters by QadEdcaManager.
//

#ifndef __EDCAFAIRNESS_QADEDCAF_H
#define __EDCAFAIRNESS_QADEDCAF_H

#include "inet/linklayer/ieee80211/mac/channelaccess/Edcaf.h"
#include "inet/linklayer/ieee80211/mac/Ieee80211Frame_m.h"

using namespace inet;
using namespace inet::ieee80211;

class QadEdcaf : public Edcaf
{
  public:
    /**
     * Directly update EDCA parameters and recalculate timing.
     * [FIX-MEDIUM] cw is only clamped upward — does NOT reset ongoing backoff.
     */
    void setEdcaParameters(int newCwMin, int newCwMax, int newAifsn) {
        cwMin = newCwMin;
        cwMax = newCwMax;
        if (cw < cwMin) cw = cwMin;  // only clamp up, preserve backoff state

        // Recalculate IFS based on new AIFSN
        simtime_t aifs = sifs + newAifsn * slotTime;
        ifs = aifs;
        eifs = sifs + aifs + modeSet->getSlowestMandatoryMode()->getDuration(LENGTH_ACK);
    }
};

#endif
