#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
SDK_DIR="${ANDROID_SDK_ROOT:-${ANDROID_HOME:-}}"
BUILD_TOOLS_VERSION="${BUILD_TOOLS_VERSION:-35.0.1}"
APP_DIR="$PROJECT_DIR/app/src/main"
BUILD_DIR="$PROJECT_DIR/build"
APK_FILE="${1:-$BUILD_DIR/ciclo-de-radio.apk}"

if [[ -z "$SDK_DIR" ]]; then
  echo 'Defina ANDROID_SDK_ROOT ou ANDROID_HOME para seu Android SDK.' >&2
  exit 1
fi
BUILD_TOOLS="$SDK_DIR/build-tools/$BUILD_TOOLS_VERSION"
ANDROID_JAR="$SDK_DIR/platforms/android-35/android.jar"
for required in "$ANDROID_JAR" "$BUILD_TOOLS/aapt2" "$BUILD_TOOLS/zipalign" \
    "$BUILD_TOOLS/lib/d8.jar" "$BUILD_TOOLS/lib/apksigner.jar"; do
  if [[ ! -f "$required" ]]; then
    echo "Arquivo do Android SDK ausente: $required" >&2
    exit 1
  fi
done
for program in java javac keytool python3; do
  if ! command -v "$program" >/dev/null 2>&1; then
    echo "Programa necessário não encontrado: $program" >&2
    exit 1
  fi
done

mkdir -p "$BUILD_DIR/classes" "$BUILD_DIR/generated" "$BUILD_DIR/dex"
find "$BUILD_DIR/classes" "$BUILD_DIR/generated" "$BUILD_DIR/dex" -type f -delete
"$BUILD_TOOLS/aapt2" compile --dir "$APP_DIR/res" -o "$BUILD_DIR/resources.zip"
"$BUILD_TOOLS/aapt2" link -o "$BUILD_DIR/base.apk" \
  -I "$ANDROID_JAR" --manifest "$APP_DIR/AndroidManifest.xml" \
  --java "$BUILD_DIR/generated" --min-sdk-version 26 --target-sdk-version 35 \
  "$BUILD_DIR/resources.zip"

# Loop arrays also work with the Bash 3.2 supplied by macOS.
sources=()
while IFS= read -r -d '' source; do sources+=("$source"); done \
  < <(find "$APP_DIR/java" "$BUILD_DIR/generated" -type f -name '*.java' -print0)
javac -encoding UTF-8 -source 8 -target 8 -Xlint:-options \
  -classpath "$ANDROID_JAR" -d "$BUILD_DIR/classes" "${sources[@]}"
classes=()
while IFS= read -r -d '' class_file; do classes+=("$class_file"); done \
  < <(find "$BUILD_DIR/classes" -type f -name '*.class' -print0)
java -cp "$BUILD_TOOLS/lib/d8.jar" com.android.tools.r8.D8 \
  --min-api 26 --lib "$ANDROID_JAR" --output "$BUILD_DIR/dex" "${classes[@]}"

cp "$BUILD_DIR/base.apk" "$BUILD_DIR/unaligned.apk"
python3 - "$BUILD_DIR/unaligned.apk" "$BUILD_DIR/dex" <<'PY'
import pathlib, sys, zipfile
with zipfile.ZipFile(sys.argv[1], 'a', compression=zipfile.ZIP_DEFLATED) as apk:
    for path in sorted(pathlib.Path(sys.argv[2]).glob('*.dex')):
        apk.write(path, path.name)
PY
"$BUILD_TOOLS/zipalign" -f 4 "$BUILD_DIR/unaligned.apk" "$BUILD_DIR/aligned.apk"

if [[ -z "${KEYSTORE_FILE:-}" ]]; then
  KEYSTORE_FILE="$PROJECT_DIR/.local-signing/development.jks"
  KEY_ALIAS="androiddebugkey"
  KEYSTORE_PASSWORD="android"
  KEY_PASSWORD="android"
  if [[ ! -f "$KEYSTORE_FILE" ]]; then
    mkdir -p "$(dirname "$KEYSTORE_FILE")"
    keytool -genkeypair -noprompt -keystore "$KEYSTORE_FILE" \
      -storepass "$KEYSTORE_PASSWORD" -keypass "$KEY_PASSWORD" \
      -alias "$KEY_ALIAS" -keyalg RSA -keysize 2048 -validity 10000 \
      -dname 'CN=Ciclo de radio Local Development'
  fi
else
  : "${KEY_ALIAS:?Defina KEY_ALIAS para sua chave.}"
  : "${KEYSTORE_PASSWORD:?Defina KEYSTORE_PASSWORD para sua chave.}"
  KEY_PASSWORD="${KEY_PASSWORD:-$KEYSTORE_PASSWORD}"
fi
export KEYSTORE_PASSWORD KEY_PASSWORD
mkdir -p "$(dirname "$APK_FILE")"
java -jar "$BUILD_TOOLS/lib/apksigner.jar" sign \
  --ks "$KEYSTORE_FILE" --ks-key-alias "$KEY_ALIAS" \
  --ks-pass env:KEYSTORE_PASSWORD --key-pass env:KEY_PASSWORD \
  --out "$APK_FILE" "$BUILD_DIR/aligned.apk"
java -jar "$BUILD_TOOLS/lib/apksigner.jar" verify --verbose "$APK_FILE"
"$BUILD_TOOLS/zipalign" -c 4 "$APK_FILE"
python3 - "$APK_FILE" <<'PY'
import hashlib, pathlib, sys
path = pathlib.Path(sys.argv[1])
print(hashlib.sha256(path.read_bytes()).hexdigest(), path)
PY
