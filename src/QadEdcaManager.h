//
// QAD-EDCA Manager: Queue-Aware Dynamic EDCA Parameter Adjustment
//

#ifndef __EDCAFAIRNESS_QADEDCAMANAGER_H
#define __EDCAFAIRNESS_QADEDCAMANAGER_H

#include <omnetpp.h>
#include "inet/linklayer/ieee80211/mac/channelaccess/Edcaf.h"
#include "inet/linklayer/ieee80211/mac/common/AccessCategory.h"

using namespace omnetpp;
using namespace inet;
using namespace inet::ieee80211;

/**
 * QAD-EDCA Manager module.
 *
 * Placed inside the AP module. Periodically monitors per-AC queue lengths
 * and packet loss rates. When starvation of low-priority ACs is detected,
 * dynamically adjusts EDCA parameters across all ACs to restore fairness
 * while preserving high-priority QoS guarantees.
 */
class QadEdcaManager : public cSimpleModule
{
  protected:
    // Self-messages
    cMessage *monitorTimer = nullptr;

    // Configuration
    simtime_t monitorInterval;
    double queueThreshold;
    double lossThreshold;
    int aifsStep;
    double cwScaleFactor;
    double txopScaleFactor;
    double recoveryFactor;
    int minAifsn;
    simtime_t minTxopLimit;
    simtime_t voDelayBound;
    simtime_t viDelayBound;

    // Default EDCA parameters (saved at initialization)
    struct EdcaParams {
        int cwMin;
        int cwMax;
        int aifsn;
        simtime_t txopLimit;
    };
    EdcaParams defaultParams[4];  // AC_BK=0, AC_BE=1, AC_VI=2, AC_VO=3
    EdcaParams currentParams[4];

    // Monitoring state
    long prevTxPackets[4] = {0, 0, 0, 0};
    long prevDropPackets[4] = {0, 0, 0, 0};
    bool starvationActive = false;

    // Signals
    simsignal_t starvationDetectedSignal;
    simsignal_t adjustedCwMinVoSignal;
    simsignal_t adjustedCwMinViSignal;
    simsignal_t adjustedAifsnBeSignal;
    simsignal_t adjustedAifsnBkSignal;

  protected:
    virtual void initialize(int stage) override;
    virtual int numInitStages() const override { return NUM_INIT_STAGES; }
    virtual void handleMessage(cMessage *msg) override;
    virtual void finish() override;

    // Core algorithm
    virtual void monitorAndAdjust();
    virtual bool detectStarvation();
    virtual void applyStarvationMitigation();
    virtual void applyRecovery();
    virtual bool checkQosConstraints();
    virtual void revertPartialAdjustment();

    // Parameter access helpers
    virtual int getQueueLength(AccessCategory ac);
    virtual double getPacketLossRate(AccessCategory ac);
    virtual double getAverageDelay(AccessCategory ac);
    virtual void applyParameters();

  public:
    virtual ~QadEdcaManager();
};

#endif
