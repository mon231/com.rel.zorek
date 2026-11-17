# Android

- Package: `com.rel.zorek`, minSdk 28, ABIs `arm64-v8a`, `armeabi-v7a`, `x86_64`.
- Python runs inside the app through [Chaquopy](https://chaquo.com/chaquopy/); `libziti.so` is built with the NDK.
- The config lives in the app's private files directory (`shares.json`) and is edited from the app.
- On an emulator the host machine is `10.0.2.2`, e.g. `"tunnel_ip": "10.0.2.2"`.
