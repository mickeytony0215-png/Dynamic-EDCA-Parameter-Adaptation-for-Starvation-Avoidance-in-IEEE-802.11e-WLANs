//
// QAD-EDCA Manager: Queue-Aware Dynamic EDCA Parameter Adjustment
//

#ifndef __EDCAFAIRNESS_QADEDCAMANAGER_H
#define __EDCAFAIRNESS_QADEDCAMANAGER_H

#include <cmath>
#include <omnetpp.h>
#include "inet/linklayer/ieee80211/mac/channelaccess/Edcaf.h"
#include "inet/linklayer/ieee80211/mac/originator/TxopProcedure.h"
#include "inet/linklayer/ieee80211/mac/common/AccessCategory.h"
#include "inet/queueing/contract/IPacketQueue.h"

using namespace omnetpp;
using namespace inet;
using namespace inet::ieee80211;

class QadEdcaManager : public cSimpleModule, public cListener
{
  protected:
    cMessage *monitorTimer = nullptr;

    // Cached module pointers
    Edcaf *edcafs[4] = {nullptr};
    queueing::IPacketQueue *queues[4] = {nullptr};
    TxopProcedure *txops[4] = {nullptr};
    cModule *hcfModule = nullptr;
    cModule *queueModules[4] = {nullptr};
    cModule *edcafModules[4] = {nullptr};

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

    // EDCA parameters (integer form, sent to setEdcaParameters)
    struct EdcaParams {
        int cwMin;
        int cwMax;
        int aifsn;
        simtime_t txopLimit;
    };
    EdcaParams defaultParams[4];
    EdcaParams currentParams[4];
    EdcaParams prevAppliedParams[4];  // [FIX-MEDIUM] track previous to avoid unnecessary apply

    // [FIX-HIGH] Double accumulators for recovery (avoid integer truncation)
    struct EdcaParamsDouble {
        double cwMin;
        double aifsn;
    };
    EdcaParamsDouble smoothParams[4];

    // Per-interval monitoring counters
    long dropCount[4] = {0, 0, 0, 0};
    long enqueueCount[4] = {0, 0, 0, 0};
    simtime_t totalDelay[4] = {SIMTIME_ZERO, SIMTIME_ZERO, SIMTIME_ZERO, SIMTIME_ZERO};
    long delayCount[4] = {0, 0, 0, 0};

    bool starvationActive = false;
    bool subscribedToSignals = false;  // [FIX-LOW] guard for unsubscribe

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

    virtual void receiveSignal(cComponent *source, simsignal_t signalID,
                               cObject *obj, cObject *details) override;

    virtual void monitorAndAdjust();
    virtual bool detectStarvation();
    virtual void applyStarvationMitigation();
    virtual void applyRecovery();
    virtual bool checkQosConstraints();
    virtual void revertPartialAdjustment();

    virtual int getQueueLength(AccessCategory ac);
    virtual double getPacketLossRate(AccessCategory ac);
    virtual double getAverageDelay(AccessCategory ac);
    virtual void applyParameters();

    // [FIX-LOW] Explicit reset for all AC counters
    void resetIntervalCounters();
    void unsubscribeFromSignals();

    int findAcForQueue(cComponent *source);
    int findAcForEdcaf(cComponent *source);

  public:
    virtual ~QadEdcaManager();
};

#endif
