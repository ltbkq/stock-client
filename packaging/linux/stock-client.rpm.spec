# RPM spec for stock-client (built with rpmbuild).
#
#   rpmbuild -bb packaging/linux/stock-client.rpm.spec \
#       --define "_version 0.4.2" \
#       --define "_srcdir $PWD" \
#       --define "_topdir $(mktemp -d)" \
#       --define "debug_package %{nil}"
#
# The PyInstaller one-file binary must already exist at %{_srcdir}/dist/stock-client.

Name:           stock-client
Version:        %{_version}
Release:        1%{?dist}
Summary:        A-share watchlist and chart client (East Money)
License:        MIT
URL:            https://github.com/ltbkq/stock-client
BuildArch:      x86_64
Requires:       mesa-libEGL mesa-libGL libxkbcommon dbus-libs fontconfig glib2

%description
Desktop PySide6/Qt client for A-share watchlists: candlestick charts with
MA/BOLL, volume and MACD/KDJ/RSI sub-charts, level-5 order book, intraday line,
price alerts and an offline demo mode.  Data source: East Money public API.

%prep

%build

%install
rm -rf %{buildroot}
mkdir -p %{buildroot}/usr/bin
mkdir -p %{buildroot}/usr/share/applications
mkdir -p %{buildroot}/usr/share/icons/hicolor/256x256/apps
mkdir -p %{buildroot}/usr/share/doc/stock-client
install -m0755 %{_srcdir}/dist/stock-client %{buildroot}/usr/bin/stock-client
install -m0644 %{_srcdir}/packaging/linux/stock-client.desktop %{buildroot}/usr/share/applications/stock-client.desktop
install -m0644 %{_srcdir}/packaging/linux/stock-client.png %{buildroot}/usr/share/icons/hicolor/256x256/apps/stock-client.png
install -m0644 %{_srcdir}/LICENSE %{buildroot}/usr/share/doc/stock-client/LICENSE

%files
/usr/bin/stock-client
/usr/share/applications/stock-client.desktop
/usr/share/icons/hicolor/256x256/apps/stock-client.png
/usr/share/doc/stock-client/LICENSE

%changelog
* Sun Sep 27 2026 ltbkq <ltbkq@users.noreply.github.com> - %{version}-1
- Initial package
