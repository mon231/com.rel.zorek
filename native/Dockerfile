FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends build-essential cmake ninja-build git curl ca-certificates \
    zip unzip tar pkg-config autoconf automake libtool python3 bison flex && rm -rf /var/lib/apt/lists/*
# Linux NDK, same version as the Windows one in C:\tools\ndk
RUN curl -sL https://dl.google.com/android/repository/android-ndk-r28b-linux.zip -o /tmp/ndk.zip && unzip -q /tmp/ndk.zip -d /opt && rm /tmp/ndk.zip
ENV ANDROID_NDK_HOME=/opt/android-ndk-r28b
COPY build_libziti.sh /usr/local/bin/build_libziti.sh
CMD ["bash", "/usr/local/bin/build_libziti.sh"]
