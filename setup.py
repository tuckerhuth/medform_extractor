from setuptools import setup
import os

APP = ['launch.py']
DATA_FILES = [
    ('disease_keywords', ['disease_keywords/keywords.md']),
    ('src', ['src/process_ocr.py', 'src/ui.py']),
]

OPTIONS = {
    'argv_emulation': False,
    'packages': ['PySide6', 'pandas'],
    'includes': [],
    'excludes': [
        'PySide6.QtBluetooth',
        'PySide6.QtNfc',
        'PySide6.QtNetworkAuth',
        'PySide6.QtPositioning',
        'PySide6.QtQuick',
        'PySide6.QtQml',
        'PySide6.QtOpenGLWidgets',
        'PySide6.QtSensors',
        'PySide6.QtSerialPort',
        'PySide6.QtWebChannel',
        'PySide6.QtWebEngineCore',
        'PySide6.QtWebEngineWidgets',
        'PySide6.QtWebSockets',
        'PySide6.QtXmlPatterns',
        'PySide6.QtOpenGL',
        'PySide6.QtSvg',
        'PySide6.Qt3DExtras',
        'PySide6.QtDesigner',
        'PySide6.QtDBus',
        'PySide6.QtTextToSpeech',
        'PySide6.QtCharts',
        'PySide6.QtQuickControls2',
    ],
    'resources': [],
    'iconfile': None,
    'plist': {
        'CFBundleName': 'ImageExtractor',
        'CFBundleDisplayName': 'ImageExtractor',
        'CFBundleIdentifier': 'com.imageextractor.app',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHighResolutionCapable': True,
        'NSRequiresAquaSystemAppearance': False
    },
}

setup(
    name="ImageExtractor",
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
) 