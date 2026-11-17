#!/bin/bash
# Runs inside the native/Dockerfile image. Builds libziti.so (ziti-sdk-c 1.18.3: the version openziti-py 1.7.1 expects)
# for the 3 Android ABIs into /out/<abi>/libziti.so. /work is a cached volume (vcpkg, sources, build trees).
set -e
W=/work; OUT=/out; mkdir -p $W $OUT; cd $W

[ -d vcpkg ] || { git clone -q https://github.com/microsoft/vcpkg.git && ./vcpkg/bootstrap-vcpkg.sh -disableMetrics; }
[ -d ziti-sdk-c ] || git clone -q --depth 1 --branch 1.18.3 https://github.com/openziti/ziti-sdk-c.git
export VCPKG_ROOT=$W/vcpkg

git -C ziti-sdk-c checkout -q library/sdk_info.c  # undo an earlier local patch (API 28 has getdomainname)

# always define the shared target (ziti_dll) without making every dependency shared
sed -i 's/^if (BUILD_SHARED_LIBS)$/if (TRUE)/' ziti-sdk-c/library/CMakeLists.txt

# release-only copies of the stock Android triplets: halves the dependency build time
mkdir -p triplets
for t in arm64-android arm-neon-android x64-android; do
  cp "$(find vcpkg/triplets -name $t.cmake | head -1)" triplets/$t.cmake
  grep -q VCPKG_BUILD_TYPE triplets/$t.cmake || echo 'set(VCPKG_BUILD_TYPE release)' >> triplets/$t.cmake
done

build() {  # abi triplet
  abi=$1; trip=$2
  cmake -S ziti-sdk-c -B build-$abi -G Ninja -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_TOOLCHAIN_FILE=$W/vcpkg/scripts/buildsystems/vcpkg.cmake \
    -DVCPKG_CHAINLOAD_TOOLCHAIN_FILE=$ANDROID_NDK_HOME/build/cmake/android.toolchain.cmake \
    -DVCPKG_OVERLAY_TRIPLETS=$W/triplets -DVCPKG_TARGET_TRIPLET=$trip \
    -DANDROID_ABI=$abi -DANDROID_PLATFORM=android-28 -DANDROID_STL=c++_static \
    -DBUILD_TESTING=OFF -DBUILD_EXAMPLES=OFF -DZITI_BUILD_PROGRAMS=OFF
  cmake --build build-$abi --target ziti_dll
  mkdir -p $OUT/$abi
  find build-$abi -name 'libziti.so' -exec cp {} $OUT/$abi/ \;
  $ANDROID_NDK_HOME/toolchains/llvm/prebuilt/linux-x86_64/bin/llvm-strip --strip-unneeded $OUT/$abi/libziti.so
  ls -la $OUT/$abi
}
build arm64-v8a   arm64-android
build armeabi-v7a arm-neon-android
build x86_64      x64-android
