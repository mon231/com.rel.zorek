# Development

```
python tests/test_core.py                       # backend tests
docker build -t zorek-native native             # Linux NDK + vcpkg image
docker run --rm -v zorek-work:/work -v "$PWD/native/out:/out" zorek-native   # libziti.so per ABI
./gradlew assembleDebug                         # needs JDK 17+ and Android SDK 35
```

CI (`.github/workflows`): `build.yml` (tests + APK), `desktop.yml` (PyInstaller on Linux and Windows),
`release.yml` (tag `v*` publishes APK and desktop binaries), `docs.yml` (this site, published to GitHub Pages).
