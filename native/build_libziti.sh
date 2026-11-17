#!/bin/bash
# Build libziti.so (ziti-sdk-c 1.18.3, the version openziti-py 1.7.1 expects) for the 3 Android ABIs with the NDK.
# Needs: git, python (pip cmake ninja). Output: native/out/<abi>/libziti.so
set -e
export ANDROID_NDK_HOME=${ANDROID_NDK_HOME:-C:/tools/ndk/android-ndk-r28b}
VCPKG=${VCPKG:-C:/v}
SRC=${ZITI_SRC:-C:/Users/avart/Desktop/ziti-sdk-c}
OUT="$(cd "$(dirname "$0")" && pwd)/out"

[ -d "$VCPKG" ] || git clone -q https://github.com/microsoft/vcpkg.git "$VCPKG"
[ -f "$VCPKG/vcpkg.exe" ] || cmd //c "$(cygpath -w $VCPKG)\bootstrap-vcpkg.bat -disableMetrics"
[ -d "$SRC" ] || git clone -q --depth 1 --branch 1.18.3 https://github.com/openziti/ziti-sdk-c.git "$SRC"

build() {  # abi triplet
  abi=$1; trip=$2
  cmake -S "$SRC" -B "$SRC/build-$abi" -G Ninja -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_TOOLCHAIN_FILE="$VCPKG/scripts/buildsystems/vcpkg.cmake" \
    -DVCPKG_CHAINLOAD_TOOLCHAIN_FILE="$ANDROID_NDK_HOME/build/cmake/android.toolchain.cmake" \
    -DVCPKG_TARGET_TRIPLET=$trip -DANDROID_ABI=$abi -DANDROID_PLATFORM=android-24 -DANDROID_STL=c++_static \
    -DBUILD_TESTING=OFF -DBUILD_EXAMPLES=OFF -DZITI_BUILD_PROGRAMS=OFF
  cmake --build "$SRC/build-$abi" --target ziti
  mkdir -p "$OUT/$abi"
  find "$SRC/build-$abi" -name 'libziti.so' -exec cp {} "$OUT/$abi/" \;
  ls -la "$OUT/$abi"
}
build arm64-v8a   arm64-android
build armeabi-v7a arm-neon-android
build x86_64      x64-android
