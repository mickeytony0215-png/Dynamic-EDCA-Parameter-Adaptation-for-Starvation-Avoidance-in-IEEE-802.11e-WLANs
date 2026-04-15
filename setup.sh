#!/bin/bash
#
# QAD-EDCA 專案環境安裝腳本（Ubuntu 22.04）
# 安裝 OMNeT++ 6.1 + INET 4.5 + 編譯專案
#
# 用法：
#   chmod +x setup.sh
#   ./setup.sh
#
# 預計耗時：30~60 分鐘（視網速和 CPU 而定）
#

set -e

INSTALL_DIR="$HOME/simulation"
OMNETPP_VER="omnetpp-6.1"
INET_VER="inet-4.5.4"
OMNETPP_URL="https://github.com/omnetpp/omnetpp/releases/download/omnetpp-6.1.0/omnetpp-6.1.0-linux-x86_64.tgz"
INET_URL="https://github.com/inet-framework/inet/releases/download/v4.5.4/inet-4.5.4-src.tgz"
NPROC=$(nproc)

echo "========================================"
echo " QAD-EDCA 環境安裝腳本"
echo " OMNeT++ 6.1 + INET 4.5"
echo " 目標目錄：$INSTALL_DIR"
echo " 編譯使用 $NPROC 核心"
echo "========================================"
echo ""

# ============================================================
# Step 1: 安裝系統依賴
# ============================================================
echo "[1/5] 安裝系統依賴套件..."
sudo apt-get update
sudo apt-get install -y \
    build-essential clang lld gdb bison flex perl \
    python3 python3-pip python3-venv \
    libxml2-dev zlib1g-dev \
    qt6-base-dev libqt6opengl6-dev \
    libopenscenegraph-dev \
    libwebkit2gtk-4.0-dev \
    xdg-utils \
    wget curl git
echo "  系統依賴安裝完成。"
echo ""

# ============================================================
# Step 2: 下載並安裝 OMNeT++ 6.1
# ============================================================
mkdir -p "$INSTALL_DIR"

if [ -d "$INSTALL_DIR/$OMNETPP_VER" ]; then
    echo "[2/5] OMNeT++ 6.1 已存在於 $INSTALL_DIR/$OMNETPP_VER，跳過下載。"
else
    echo "[2/5] 下載 OMNeT++ 6.1..."
    cd "$INSTALL_DIR"
    wget -c --show-progress -O omnetpp-6.1.0.tgz "$OMNETPP_URL"
    echo "  解壓中..."
    tar xzf omnetpp-6.1.0.tgz
    # 解壓後目錄可能是 omnetpp-6.1.0，重新命名為 omnetpp-6.1
    [ -d "omnetpp-6.1.0" ] && mv omnetpp-6.1.0 omnetpp-6.1
    rm -f omnetpp-6.1.0.tgz

    echo "  編譯 OMNeT++ 6.1（這需要一些時間）..."
    cd "$INSTALL_DIR/$OMNETPP_VER"
    source setenv
    ./configure
    make -j$NPROC
    echo "  OMNeT++ 6.1 編譯完成。"
fi
echo ""

# ============================================================
# Step 3: 下載並安裝 INET 4.5
# ============================================================
if [ -d "$INSTALL_DIR/inet4.5" ]; then
    echo "[3/5] INET 4.5 已存在於 $INSTALL_DIR/inet4.5，跳過下載。"
else
    echo "[3/5] 下載 INET 4.5..."
    cd "$INSTALL_DIR"

    # 確保 OMNeT++ 環境已載入
    source "$INSTALL_DIR/$OMNETPP_VER/setenv"

    wget -q --show-progress -O inet-4.5.4.tgz "$INET_URL"
    echo "  解壓中..."
    tar xzf inet-4.5.4.tgz
    mv inet4.5 inet4.5 2>/dev/null || mv $INET_VER inet4.5 2>/dev/null || true
    rm -f inet-4.5.4.tgz

    echo "  編譯 INET 4.5（這需要較長時間）..."
    cd "$INSTALL_DIR/inet4.5"
    source setenv
    make makefiles
    make -j$NPROC
    echo "  INET 4.5 編譯完成。"
fi
echo ""

# ============================================================
# Step 4: 編譯專案
# ============================================================
echo "[4/5] 編譯 QAD-EDCA 專案..."
PROJECT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT"
source "$INSTALL_DIR/$OMNETPP_VER/setenv"

opp_makemake -f --deep -e cc -O out -o edcafairness --make-so \
    -X venv -X results -X analysis -X references -X proposal -X docs \
    -I$INSTALL_DIR/inet4.5/src \
    -L$INSTALL_DIR/inet4.5/src \
    -lINET \
    -KINET_PROJ=$INSTALL_DIR/inet4.5

make -j$NPROC
echo "  專案編譯完成。"
echo ""

# ============================================================
# Step 5: 驗證
# ============================================================
echo "[5/5] 驗證安裝..."
cd "$PROJECT/simulations"
RESULT=$(opp_run -m -u Cmdenv -c Baseline_N10 --sim-time-limit=1s -r 0 \
    -n "$PROJECT:$INSTALL_DIR/inet4.5/src" \
    -l "$INSTALL_DIR/inet4.5/src/INET" \
    -l "$PROJECT/out/clang-release/edcafairness" \
    omnetpp.ini scenarios/baseline.ini 2>&1 | grep "End\.")

if [ "$RESULT" = "End." ]; then
    echo "  驗證成功！"
else
    echo "  驗證失敗，請檢查上方錯誤訊息。"
    exit 1
fi

echo ""
echo "========================================"
echo " 安裝完成！"
echo ""
echo " 使用方式："
echo "   cd \"$PROJECT\""
echo "   ./run.sh Baseline_N10 baseline          # GUI 模式"
echo "   ./run.sh QadEdca_N10 qad_edca           # QAD-EDCA"
echo "   ./run.sh Baseline_N10 baseline 0 --cli  # CLI 批次"
echo ""
echo " 每次開新終端記得先執行："
echo "   source ~/simulation/omnetpp-6.1/setenv"
echo "========================================"
