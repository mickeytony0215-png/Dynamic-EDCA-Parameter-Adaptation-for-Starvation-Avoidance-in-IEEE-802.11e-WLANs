//
// QAD-EDCA Manager: Queue-Aware Dynamic EDCA Parameter Adjustment
//

#include "QadEdcaManager.h"
#include "QadEdcaf.h"
#include "QadTxopProcedure.h"

#include "inet/common/ModuleAccess.h"
#include "inet/common/Simsignals.h"
#include "inet/common/Simsignals_m.h"
#include "inet/common/packet/Packet.h"
#include "inet/linklayer/ieee80211/mac/Ieee80211Frame_m.h"

Define_Module(QadEdcaManager);

QadEdcaManager::~QadEdcaManager()
{
    cancelAndDelete(monitorTimer);
    unsubscribeFromSignals();  // [FIX-LOW] ensure cleanup even on abnormal termination
}

void QadEdcaManager::initialize(int stage)
{
    if (stage == INITSTAGE_LOCAL) {
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

        starvationDetectedSignal = registerSignal("starvationDetected");
        adjustedCwMinVoSignal = registerSignal("adjustedCwMinVo");
        adjustedCwMinViSignal = registerSignal("adjustedCwMinVi");
        adjustedAifsnBeSignal = registerSignal("adjustedAifsnBe");
        adjustedAifsnBkSignal = registerSignal("adjustedAifsnBk");

        monitorTimer = new cMessage("QadEdcaMonitorTimer");
        scheduleAt(simTime() + monitorInterval, monitorTimer);
    }
    else if (stage == INITSTAGE_LINK_LAYER) {
        std::string apPath = par("apModule").stdstringValue();
        cModule *edca = getModuleByPath(
            (apPath + ".wlan[0].mac.hcf.edca").c_str());
        if (!edca)
            throw cRuntimeError("Cannot find EDCA module at path '%s.wlan[0].mac.hcf.edca'",
                                apPath.c_str());

        for (int i = 0; i < 4; i++) {
            cModule *edcafMod = edca->getSubmodule("edcaf", i);
            edcafs[i] = check_and_cast<Edcaf *>(edcafMod);
            queues[i] = edcafs[i]->getPendingQueue();
            txops[i] = edcafs[i]->getTxopProcedure();
            edcafModules[i] = edcafMod;
            queueModules[i] = edcafMod->getSubmodule("pendingQueue");
        }

        hcfModule = getModuleByPath(
            (apPath + ".wlan[0].mac.hcf").c_str());

        // ---- Subscribe to signals ----
        // [FIX-CRITICAL] Only subscribe packetDroppedSignal on hcf.
        // Signals propagate UP the hierarchy, so hcf receives drops from
        // descendant pendingQueues too. No double subscription needed.
        hcfModule->subscribe(packetDroppedSignal, this);

        // packetPushedInSignal on each pendingQueue (enqueue tracking)
        for (int i = 0; i < 4; i++)
            queueModules[i]->subscribe(packetPushedInSignal, this);

        // packetSentToPeerSignal on each edcaf (delay tracking)
        for (int i = 0; i < 4; i++)
            edcafModules[i]->subscribe(packetSentToPeerSignal, this);

        subscribedToSignals = true;

        // ---- Default parameters (IEEE 802.11-2020 Table 9-155, OFDM PHY) ----
        defaultParams[AC_BK] = {15, 1023, 7, SimTime(2528, SIMTIME_US)};
        defaultParams[AC_BE] = {15, 1023, 3, SimTime(2528, SIMTIME_US)};
        defaultParams[AC_VI] = {7,   15,  2, SimTime(4096, SIMTIME_US)};
        defaultParams[AC_VO] = {3,    7,  2, SimTime(2080, SIMTIME_US)};

        for (int i = 0; i < 4; i++) {
            currentParams[i] = defaultParams[i];
            prevAppliedParams[i] = {-1, -1, -1, SIMTIME_ZERO};  // force first apply

            // [FIX-HIGH] Initialize double accumulators
            smoothParams[i].cwMin = defaultParams[i].cwMin;
            smoothParams[i].aifsn = defaultParams[i].aifsn;
        }

        // Set TXOP limits on QadTxopProcedure submodules
        for (int i = 0; i < 4; i++) {
            auto *qadTxop = dynamic_cast<QadTxopProcedure *>(txops[i]);
            if (qadTxop)
                qadTxop->setTxopLimit(defaultParams[i].txopLimit);
        }

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

// ============================================================
// Signal reception
// ============================================================

int QadEdcaManager::findAcForQueue(cComponent *source)
{
    for (int i = 0; i < 4; i++)
        if (source == queueModules[i])
            return i;
    return -1;
}

int QadEdcaManager::findAcForEdcaf(cComponent *source)
{
    for (int i = 0; i < 4; i++)
        if (source == edcafModules[i])
            return i;
    return -1;
}

void QadEdcaManager::receiveSignal(cComponent *source, simsignal_t signalID,
                                   cObject *obj, cObject *details)
{
    if (signalID == packetDroppedSignal) {
        // [FIX-CRITICAL] All drops arrive via hcf subscription (signal propagation).
        // Identify AC by checking if source is a known pendingQueue.
        int ac = findAcForQueue(source);
        if (ac >= 0) {
            dropCount[ac]++;
            return;
        }

        // Drop emitted by hcf itself (retry limit exceeded)
        if (source == hcfModule) {
            auto *dropDetails = dynamic_cast<PacketDropDetails *>(details);
            if (!dropDetails || dropDetails->getReason() != RETRY_LIMIT_REACHED)
                return;

            auto *packet = dynamic_cast<inet::Packet *>(obj);
            if (!packet) return;

            auto header = packet->peekAtFront<Ieee80211DataOrMgmtHeader>();
            auto dataHeader = dynamicPtrCast<const Ieee80211DataHeader>(header);
            if (dataHeader) {
                int tid = dataHeader->getTid();
                int mappedAc;
                switch (tid) {
                    case 1: case 2: mappedAc = AC_BK; break;
                    case 0: case 3: mappedAc = AC_BE; break;
                    case 4: case 5: mappedAc = AC_VI; break;
                    case 6: case 7: mappedAc = AC_VO; break;
                    default: mappedAc = AC_BE; break;
                }
                dropCount[mappedAc]++;
            }
        }
    }
    else if (signalID == packetPushedInSignal) {
        int ac = findAcForQueue(source);
        if (ac >= 0)
            enqueueCount[ac]++;
    }
    else if (signalID == packetSentToPeerSignal) {
        int ac = findAcForEdcaf(source);
        if (ac >= 0) {
            auto *packet = dynamic_cast<inet::Packet *>(obj);
            if (packet) {
                totalDelay[ac] += simTime() - packet->getCreationTime();
                delayCount[ac]++;
            }
        }
    }
}

// ============================================================
// Core algorithm
// ============================================================

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

        if (!checkQosConstraints()) {
            EV_WARN << "QoS constraints violated, partially reverting" << endl;
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

    applyParameters();

    emit(adjustedCwMinVoSignal, (long)currentParams[AC_VO].cwMin);
    emit(adjustedCwMinViSignal, (long)currentParams[AC_VI].cwMin);
    emit(adjustedAifsnBeSignal, (long)currentParams[AC_BE].aifsn);
    emit(adjustedAifsnBkSignal, (long)currentParams[AC_BK].aifsn);

    // [FIX-LOW] Reset ALL interval counters at the end of each cycle
    resetIntervalCounters();
}

// ============================================================
// Starvation detection (proposal §3.1)
// ============================================================

bool QadEdcaManager::detectStarvation()
{
    for (int ac : {AC_BE, AC_BK}) {
        int qLen = queues[ac]->getNumPackets();
        int qCap = queues[ac]->getMaxNumPackets();
        if (qCap <= 0) qCap = 100;

        // [FIX-LOW] Read loss rate without side-effect reset (reset is done centrally)
        long total = enqueueCount[ac];
        double lossRate = (total > 0) ? double(dropCount[ac]) / total : 0.0;

        bool starving = (double(qLen) / qCap > queueThreshold)
                        || (lossRate > lossThreshold);
        if (starving) return true;
    }
    return false;
}

// ============================================================
// Three-stage starvation mitigation (proposal §3.3)
// ============================================================

void QadEdcaManager::applyStarvationMitigation()
{
    // Strategy 1: Reduce AIFSN for BE and BK
    smoothParams[AC_BE].aifsn = std::max(smoothParams[AC_BE].aifsn - aifsStep, (double)minAifsn);
    smoothParams[AC_BK].aifsn = std::max(smoothParams[AC_BK].aifsn - aifsStep, (double)minAifsn);
    currentParams[AC_BE].aifsn = (int)std::round(smoothParams[AC_BE].aifsn);
    currentParams[AC_BK].aifsn = (int)std::round(smoothParams[AC_BK].aifsn);

    // Strategy 2: Increase CWmin for VO and VI
    int maxCw = defaultParams[AC_BE].cwMin;
    smoothParams[AC_VO].cwMin = std::min(smoothParams[AC_VO].cwMin * cwScaleFactor, (double)maxCw);
    smoothParams[AC_VI].cwMin = std::min(smoothParams[AC_VI].cwMin * cwScaleFactor, (double)maxCw);
    currentParams[AC_VO].cwMin = (int)std::round(smoothParams[AC_VO].cwMin);
    currentParams[AC_VI].cwMin = (int)std::round(smoothParams[AC_VI].cwMin);

    // Strategy 3: Reduce TXOP limit for VO and VI
    currentParams[AC_VO].txopLimit = std::max(currentParams[AC_VO].txopLimit * txopScaleFactor, minTxopLimit);
    currentParams[AC_VI].txopLimit = std::max(currentParams[AC_VI].txopLimit * txopScaleFactor, minTxopLimit);
}

// ============================================================
// Exponential decay recovery (proposal §3.4)
// [FIX-HIGH] Use double accumulators to avoid integer truncation
// ============================================================

void QadEdcaManager::applyRecovery()
{
    for (int i = 0; i < 4; i++) {
        // P(t+1) = P(t) + gamma * (P_default - P(t))  in double space
        smoothParams[i].aifsn += recoveryFactor
            * (defaultParams[i].aifsn - smoothParams[i].aifsn);
        smoothParams[i].cwMin += recoveryFactor
            * (defaultParams[i].cwMin - smoothParams[i].cwMin);

        // Round to integer for actual use
        currentParams[i].aifsn = (int)std::round(smoothParams[i].aifsn);
        currentParams[i].cwMin = (int)std::round(smoothParams[i].cwMin);

        // TXOP is already simtime_t (double), no truncation issue
        simtime_t diff = defaultParams[i].txopLimit - currentParams[i].txopLimit;
        currentParams[i].txopLimit += diff * recoveryFactor;
    }
}

// ============================================================
// QoS constraint check
// ============================================================

bool QadEdcaManager::checkQosConstraints()
{
    // [FIX-LOW] Pure read, no side-effect reset
    double delayVo = (delayCount[AC_VO] > 0)
        ? totalDelay[AC_VO].dbl() / delayCount[AC_VO] : 0.0;
    double delayVi = (delayCount[AC_VI] > 0)
        ? totalDelay[AC_VI].dbl() / delayCount[AC_VI] : 0.0;

    return (delayVo < voDelayBound.dbl()) && (delayVi < viDelayBound.dbl());
}

// ============================================================
// Safety valve: partial revert (proposal §3.5)
// ============================================================

void QadEdcaManager::revertPartialAdjustment()
{
    for (int ac : {AC_VI, AC_VO}) {
        smoothParams[ac].cwMin =
            (smoothParams[ac].cwMin + defaultParams[ac].cwMin) / 2.0;
        smoothParams[ac].aifsn =
            (smoothParams[ac].aifsn + defaultParams[ac].aifsn) / 2.0;

        currentParams[ac].cwMin = (int)std::round(smoothParams[ac].cwMin);
        currentParams[ac].aifsn = (int)std::round(smoothParams[ac].aifsn);
        currentParams[ac].txopLimit =
            (currentParams[ac].txopLimit + defaultParams[ac].txopLimit) / 2;
    }
}

// ============================================================
// Parameter access helpers
// ============================================================

int QadEdcaManager::getQueueLength(AccessCategory ac)
{
    return queues[ac]->getNumPackets();
}

// [FIX-LOW] Getters are now pure reads; reset is done by resetIntervalCounters()
double QadEdcaManager::getPacketLossRate(AccessCategory ac)
{
    long total = enqueueCount[ac];
    if (total == 0) return 0.0;
    return double(dropCount[ac]) / total;
}

double QadEdcaManager::getAverageDelay(AccessCategory ac)
{
    if (delayCount[ac] == 0) return 0.0;
    return totalDelay[ac].dbl() / delayCount[ac];
}

void QadEdcaManager::applyParameters()
{
    for (int i = 0; i < 4; i++) {
        // [FIX-MEDIUM] Only apply when parameters actually changed
        if (currentParams[i].cwMin == prevAppliedParams[i].cwMin &&
            currentParams[i].cwMax == prevAppliedParams[i].cwMax &&
            currentParams[i].aifsn == prevAppliedParams[i].aifsn &&
            currentParams[i].txopLimit == prevAppliedParams[i].txopLimit)
            continue;

        auto *qadEdcaf = dynamic_cast<QadEdcaf *>(edcafs[i]);
        if (qadEdcaf)
            qadEdcaf->setEdcaParameters(
                currentParams[i].cwMin,
                currentParams[i].cwMax,
                currentParams[i].aifsn);

        auto *qadTxop = dynamic_cast<QadTxopProcedure *>(txops[i]);
        if (qadTxop)
            qadTxop->setTxopLimit(currentParams[i].txopLimit);

        prevAppliedParams[i] = currentParams[i];
    }
}

// ============================================================
// [FIX-LOW] Centralized counter reset
// ============================================================

void QadEdcaManager::resetIntervalCounters()
{
    for (int i = 0; i < 4; i++) {
        dropCount[i] = 0;
        enqueueCount[i] = 0;
        totalDelay[i] = SIMTIME_ZERO;
        delayCount[i] = 0;
    }
}

// ============================================================
// Cleanup
// ============================================================

void QadEdcaManager::unsubscribeFromSignals()
{
    if (!subscribedToSignals) return;
    subscribedToSignals = false;

    if (hcfModule)
        hcfModule->unsubscribe(packetDroppedSignal, this);

    for (int i = 0; i < 4; i++) {
        if (queueModules[i])
            queueModules[i]->unsubscribe(packetPushedInSignal, this);
        if (edcafModules[i])
            edcafModules[i]->unsubscribe(packetSentToPeerSignal, this);
    }
}

void QadEdcaManager::finish()
{
    unsubscribeFromSignals();
    EV_INFO << "QAD-EDCA Manager finished." << endl;
}
