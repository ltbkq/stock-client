# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for stock-client.

Builds a single-file, windowed (no console) executable named ``stock-client``
from the repository entry point ``run.py``. Run via ``packaging/build.sh`` or
directly:

    pyinstaller packaging/stockclient.spec --noconfirm

PySide6 ships its own PyInstaller hooks; pyqtgraph's graphics items are
imported dynamically, so they are listed explicitly as hidden imports.
"""

from PyInstaller.utils.hooks import collect_data_files
import os

block_cipher = None

# ship the editable data-source config beside the package (datasource.py reads it
# via Path(__file__).with_name("data_sources.json"))
_repo_root = os.path.abspath(os.path.join(SPECPATH, os.pardir))
_pkg_dir = os.path.join(_repo_root, "stockclient")
stockclient_datas = [(os.path.join(_pkg_dir, "data_sources.json"), "stockclient")]

# pyqtgraph loads many graphics item classes by name at runtime; make sure
# they are all bundled even if static analysis misses them.
pyqtgraph_hidden = [
    "pyqtgraph.graphicsItems",
    "pyqtgraph.graphicsItems.GraphicsItem",
    "pyqtgraph.graphicsItems.GraphicsObject",
    "pyqtgraph.graphicsItems.GraphicsWidget",
    "pyqtgraph.graphicsItems.GraphicsWidgetAnchor",
    "pyqtgraph.graphicsItems.GraphicsLayout",
    "pyqtgraph.graphicsItems.GraphicsScene",
    "pyqtgraph.graphicsItems.GraphicsView",
    "pyqtgraph.graphicsItems.ViewBox",
    "pyqtgraph.graphicsItems.PlotItem",
    "pyqtgraph.graphicsItems.AxisItem",
    "pyqtgraph.graphicsItems.LabelItem",
    "pyqtgraph.graphicsItems.LegendItem",
    "pyqtgraph.graphicsItems.ScatterPlotItem",
    "pyqtgraph.graphicsItems.TextItem",
    "pyqtgraph.graphicsItems.InfiniteLine",
    "pyqtgraph.graphicsItems.LinearRegionItem",
    "pyqtgraph.graphicsItems.HistogramLUTItem",
    "pyqtgraph.graphicsItems.BarGraphItem",
    "pyqtgraph.graphicsItems.FillBetweenItem",
    "pyqtgraph.graphicsItems.IsocurveItem",
    "pyqtgraph.graphicsItems.PlotCurveItem",
    "pyqtgraph.graphicsItems.PlotDataItem",
    "pyqtgraph.graphicsItems.ImageItem",
    "pyqtgraph.graphicsItems.GradientEditorItem",
    "pyqtgraph.graphicsItems.ColorBarItem",
    "pyqtgraph.graphicsItems.ArrowItem",
    "pyqtgraph.graphicsItems.TargetItem",
    "pyqtgraph.graphicsItems.ButtonItem",
    "pyqtgraph.graphicsItems.DateAxisItem",
    "pyqtgraph.graphicsItems.MultiPlotItem",
    "pyqtgraph.graphicsItems.NonUniformImage",
    "pyqtgraph.graphicsItems.PColorMeshItem",
    "pyqtgraph.graphicsItems.ROI",
    "pyqtgraph.graphicsItems.ScaleBar",
    "pyqtgraph.exporters",
    "pyqtgraph.exporters.ImageExporter",
    "pyqtgraph.exporters.SVGExporter",
    "pyqtgraph.exporters.CSVExporter",
    "pyqtgraph.exporters.PrintExporter",
    "pyqtgraph.exporters.HDF5Exporter",
    "pyqtgraph.exporters.MatplotlibExporter",
]

a = Analysis(
    [os.path.join(_repo_root, "run.py")],
    pathex=[],
    binaries=[],
    datas=collect_data_files("pyqtgraph", includes=["**/*.ui", "**/*.qss", "**/*.png"])
    + stockclient_datas,
    hiddenimports=pyqtgraph_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="stock-client",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
