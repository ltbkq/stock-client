#!/usr/bin/env bash
# Build Linux distribution packages from an already-built PyInstaller binary.
#
#   packaging/build.sh                 # 1) build dist/stock-client (one-file)
#   packaging/make-packages.sh 0.4.2   # 2) -> dist/packages/*.tar.gz *.deb *.rpm
#
# Produces:
#   stock-client_<ver>_linux_<arch>.tar.gz   portable tarball
#   stock-client_<ver>_<debarch>.deb         Debian/Ubuntu installer  (dpkg-deb)
#   stock-client_<ver>-1.<rpmarch>.rpm       Fedora/RHEL installer    (rpmbuild, if present)
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

BIN="dist/stock-client"
if [[ ! -x "$BIN" ]]; then
    echo "error: $BIN not found — run packaging/build.sh first" >&2
    exit 1
fi

VERSION="${1:-$(git describe --tags --abbrev=0 2>/dev/null | sed 's/^v//' || true)}"
VERSION="${VERSION:-0.0.0}"

MACHINE="$(uname -m)"
case "$MACHINE" in
    x86_64)  DEB_ARCH=amd64; RPM_ARCH=x86_64 ;;
    aarch64) DEB_ARCH=arm64; RPM_ARCH=aarch64 ;;
    *)       DEB_ARCH="$MACHINE"; RPM_ARCH="$MACHINE" ;;
esac

OUT="dist/packages"
rm -rf "$OUT"
mkdir -p "$OUT"

echo "==> tarball"
tar -C dist -czf "$OUT/stock-client_${VERSION}_linux_${MACHINE}.tar.gz" stock-client

echo "==> deb"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
mkdir -p "$STAGE/usr/bin" \
         "$STAGE/usr/share/applications" \
         "$STAGE/usr/share/icons/hicolor/256x256/apps" \
         "$STAGE/usr/share/doc/stock-client" \
         "$STAGE/DEBIAN"
install -m0755 "$BIN" "$STAGE/usr/bin/stock-client"
install -m0644 packaging/linux/stock-client.desktop "$STAGE/usr/share/applications/"
install -m0644 packaging/linux/stock-client.png "$STAGE/usr/share/icons/hicolor/256x256/apps/"
install -m0644 LICENSE "$STAGE/usr/share/doc/stock-client/copyright"
cat > "$STAGE/DEBIAN/control" <<EOF
Package: stock-client
Version: $VERSION
Section: utils
Priority: optional
Architecture: $DEB_ARCH
Maintainer: ltbkq <ltbkq@users.noreply.github.com>
Depends: libegl1, libgl1, libxkbcommon0, libdbus-1-3, libfontconfig1, libglib2.0-0
Homepage: https://github.com/ltbkq/stock-client
Description: A-share watchlist and chart client (East Money)
 Desktop PySide6/Qt client for A-share watchlists: candlestick charts with
 MA/BOLL, volume and MACD/KDJ/RSI sub-charts, level-5 order book, intraday
 line, price alerts and an offline demo mode.
EOF
dpkg-deb --build --root-owner-group "$STAGE" "$OUT/stock-client_${VERSION}_${DEB_ARCH}.deb"

echo "==> rpm"
if command -v rpmbuild >/dev/null 2>&1; then
    TOP="$(mktemp -d)"
    mkdir -p "$TOP"/{BUILD,RPMS,SOURCES,SPECS,SRPMS,BUILDROOT}
    rpmbuild -bb packaging/linux/stock-client.rpm.spec \
        --define "_version $VERSION" \
        --define "_srcdir $REPO_ROOT" \
        --define "_topdir $TOP" \
        --define "_arch $RPM_ARCH" \
        --define "debug_package %{nil}"
    find "$TOP/RPMS" -name '*.rpm' -exec cp {} "$OUT/" \;
    rm -rf "$TOP"
else
    echo "   rpmbuild not found — skipping .rpm (install the 'rpm' package)" >&2
fi

echo
echo "packages in $OUT:"
ls -lh "$OUT"
