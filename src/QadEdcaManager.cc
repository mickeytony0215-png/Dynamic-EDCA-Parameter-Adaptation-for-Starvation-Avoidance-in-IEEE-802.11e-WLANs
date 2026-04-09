//
// QAD-EDCA Manager: Queue-Aware Dynamic EDCA Parameter Adjustment
//

#include "QadEdcaManager.h"
#include "inet/common/ModuleAccess.h"

Define_Module(QadEdcaManager);

QadEdcaManager::~QadEdcaManager()
{
    cancelAndDelete(monitorTimer);
}

void QadEdcaManager::initialize(int stage)
{
    if (stage == INITSTAGE_LOCAL) {
        // Read parameters from NED
        monitorInterval = par("monitorInterval");
        queueThreshold = par("queueThreshold");
        lossThreshold = par("lossThreshold");
        aifsStep = par("aifsStep");
        cwScaleFactor = par("cwScaleFactor");
        txopScaleFactor = par("txopScaleFactor");
        recoveryFactor = par("recoveryFactor");
        minAifsn = par("minAifsn");
        minTxopLimit = par("minTxopLimit");
        voDelayBound = par("voDelayBound");
        viDelayBound = par("viDelayBound");

        // Register signals
        starvationDetectedSignal = registerSignal("starvationDetected");
        adjustedCwMinVoSignal = registerSignal("adjustedCwMinVo");
        adjustedCwMinViSignal = registerSignal("adjustedCwMinVi");
        adjustedAifsnBeSignal = registerSignal("adjustedAifsnBe");
        adjustedAifsnBkSignal = registerSignal("adjustedAifsnBk");

        // Schedule first monitoring event
        monitorTimer = new cMessage("QadEdcaMonitorTimer");
        scheduleAt(simTime() + monitorInterval, monitorTimer);
    }
    else if (stage == INITSTAGE_LINK_LAYER) {
        // Save default EDCA parameters from the MAC module
        // These are the standard 802.11e defaults that we'll modify and restore

        // Default parameters per IEEE 802.11e (for 802.11a/g, aCWmin=15, aCWmax=1023)
        // AC_BK: CWmin=15, CWmax=1023, AIFSN=7
        defaultParams[0] = {15, 1023, 7, SimTime(0)};
        // AC_BE: CWmin=15, CWmax=1023, AIFSN=3
        defaultParams[1] = {15, 1023, 3, SimTime(0)};
        // AC_VI: CWmin=7, CWmax=15, AIFSN=2, TXOP=3.008ms
        defaultParams[2] = {7, 15, 2, SimTime(3008, SIMTIME_US)};
        // AC_VO: CWmin=3, CWmax=7, AIFSN=2, TXOP=1.504ms
        defaultParams[3] = {3, 7, 2, SimTime(1504, SIMTIME_US)};

        // Initialize current parameters to defaults
        for (int i = 0; i < 4; i++)
            currentParams[i] = defaultParams[i];

        EV_INFO << "QAD-EDCA Manager initialized. Monitor interval = "
                << monitorInterval << "s" << endl;
    }
}

void QadEdcaManager::handleMessage(cMessage *msg)
{
    if (msg == monitorTimer) {
        monitorAndAdjust();
        scheduleAt(simTime() + monitorInterval, monitorTimer);
    }
}

void QadEdcaManager::monitorAndAdjust()
{
    bool starving = detectStarvation();

    if (starving) {
        if (!starvationActive) {
            EV_WARN << "Starvation detected at t=" << simTime() << endl;
            starvationActive = true;
        }
        emit(starvationDetectedSignal, true);
        applyStarvationMitigation();

        // Safety check: ensure VO/VI QoS is still met
        if (!checkQosConstraints()) {
            EV_WARN << "QoS constraints violated, partially reverting adjustments" << endl;
            revertPartialAdjustment();
        }
    }
    else {
        if (starvationActive) {
            EV_INFO << "Starvation resolved at t=" << simTime() << endl;
            starvationActive = false;
        }
        emit(starvationDetectedSignal, false);
        applyRecovery();
    }

    // Apply the adjusted parameters to the MAC modules
    applyParameters();

    // Emit current parameter values for recording
    emit(adjustedCwMinVoSignal, (long)currentParams[3].cwMin);
    emit(adjustedCwMinViSignal, (long)currentParams[2].cwMin);
    emit(adjustedAifsnBeSignal, (long)currentParams[1].aifsn);
    emit(adjustedAifsnBkSignal, (long)currentParams[0].aifsn);
}

bool QadEdcaManager::detectStarvation()
{
    // Check if BE or BK queues exceed threshold or loss rate is too high
    int qLenBe = getQueueLength(AC_BE);
    int qLenBk = getQueueLength(AC_BK);
    double lossBe = getPacketLossRate(AC_BE);
    double lossBk = getPacketLossRate(AC_BK);

    // TODO: Get actual queue capacity from the module to compute ratio
    int queueCapacity = 100;  // Default PendingQueue capacity in INET

    bool beStarving = (double(qLenBe) / queueCapacity > queueThreshold)
                      || (lossBe > lossThreshold);
    bool bkStarving = (double(qLenBk) / queueCapacity > queueThreshold)
                      || (lossBk > lossThreshold);

    return beStarving || bkStarving;
}

void QadEdcaManager::applyStarvationMitigation()
{
    // Strategy 1: Reduce AIFSN for BE and BK
    currentParams[1].aifsn = std::max(currentParams[1].aifsn - aifsStep, minAifsn);  // AC_BE
    currentParams[0].aifsn = std::max(currentParams[0].aifsn - aifsStep, minAifsn);  // AC_BK

    // Strategy 2: Increase CWmin for VO and VI
    int maxCwForVo = defaultParams[1].cwMin;  // Cap at BE's default CWmin
    currentParams[3].cwMin = std::min((int)(currentParams[3].cwMin * cwScaleFactor), maxCwForVo);  // AC_VO
    currentParams[2].cwMin = std::min((int)(currentParams[2].cwMin * cwScaleFactor), maxCwForVo);  // AC_VI

    // Strategy 3: Reduce TXOP limit for VO and VI
    simtime_t newTxopVo = currentParams[3].txopLimit * txopScaleFactor;
    simtime_t newTxopVi = currentParams[2].txopLimit * txopScaleFactor;
    currentParams[3].txopLimit = std::max(newTxopVo, minTxopLimit);  // AC_VO
    currentParams[2].txopLimit = std::max(newTxopVi, minTxopLimit);  // AC_VI
}

void QadEdcaManager::applyRecovery()
{
    // Exponential decay toward default values
    for (int i = 0; i < 4; i++) {
        // Recover AIFSN
        currentParams[i].aifsn = currentParams[i].aifsn
            + (int)(recoveryFactor * (defaultParams[i].aifsn - currentParams[i].aifsn));

        // Recover CWmin
        currentParams[i].cwMin = currentParams[i].cwMin
            + (int)(recoveryFactor * (defaultParams[i].cwMin - currentParams[i].cwMin));

        // Recover TXOP limit
        simtime_t diff = defaultParams[i].txopLimit - currentParams[i].txopLimit;
        currentParams[i].txopLimit = currentParams[i].txopLimit + diff * recoveryFactor;
    }
}

bool QadEdcaManager::checkQosConstraints()
{
    double delayVo = getAverageDelay(AC_VO);
    double delayVi = getAverageDelay(AC_VI);

    return (delayVo < voDelayBound.dbl()) && (delayVi < viDelayBound.dbl());
}

void QadEdcaManager::revertPartialAdjustment()
{
    // Revert halfway toward defaults for high-priority ACs
    for (int ac : {2, 3}) {  // AC_VI, AC_VO
        currentParams[ac].cwMin = (currentParams[ac].cwMin + defaultParams[ac].cwMin) / 2;
        currentParams[ac].txopLimit = (currentParams[ac].txopLimit + defaultParams[ac].txopLimit) / 2;
    }
}

// ============================================================
// Helper functions - these need to access INET's internal modules
// ============================================================

int QadEdcaManager::getQueueLength(AccessCategory ac)
{
    // TODO: Navigate the module hierarchy to find the Edcaf submodule
    // for the given AC, then query its pendingQueue length.
    //
    // Example path from AP:
    //   ap.wlan[0].mac.hcf.edca.edcaf[acIndex].pendingQueue.getNumPackets()
    //
    // Placeholder implementation:
    return 0;
}

double QadEdcaManager::getPacketLossRate(AccessCategory ac)
{
    // TODO: Compute loss rate from packet counters.
    // Track packets enqueued vs packets successfully transmitted
    // over the monitoring interval.
    //
    // Placeholder implementation:
    return 0.0;
}

double QadEdcaManager::getAverageDelay(AccessCategory ac)
{
    // TODO: Compute average delay from the delay statistics
    // maintained by the MAC module for each AC.
    //
    // Placeholder implementation:
    return 0.0;
}

void QadEdcaManager::applyParameters()
{
    // TODO: Navigate to each Edcaf submodule and update:
    //   - cwMin, cwMax via par() or direct member access
    //   - AIFSN via par() or recalculating IFS
    //   - TXOP limit via TxopProcedure par()
    //
    // For a real implementation, this requires either:
    //   1. Modifying INET's Edcaf class to support runtime parameter changes
    //   2. Using OMNeT++ par().setIntValue() if parameters are volatile
    //   3. Sending parameter-update messages to the MAC module
    //
    // Example approach:
    //   cModule *hcf = getParentModule()->getSubmodule("wlan", 0)
    //                     ->getSubmodule("mac")->getSubmodule("hcf");
    //   cModule *edca = hcf->getSubmodule("edca");
    //   for (int i = 0; i < 4; i++) {
    //       cModule *edcaf = edca->getSubmodule("edcaf", i);
    //       edcaf->par("cwMin") = currentParams[i].cwMin;
    //       edcaf->par("cwMax") = currentParams[i].cwMax;
    //       edcaf->par("aifsn") = currentParams[i].aifsn;
    //   }

    EV_DEBUG << "QAD-EDCA parameters applied: "
             << "VO CWmin=" << currentParams[3].cwMin
             << " VI CWmin=" << currentParams[2].cwMin
             << " BE AIFSN=" << currentParams[1].aifsn
             << " BK AIFSN=" << currentParams[0].aifsn << endl;
}

void QadEdcaManager::finish()
{
    EV_INFO << "QAD-EDCA Manager finished. Total starvation events recorded." << endl;
}
