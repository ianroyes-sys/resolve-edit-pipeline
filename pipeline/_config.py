"""Shared tool locations. Override any of them with environment variables."""
import os
import shutil
import sys

FFMPEG = os.environ.get('FFMPEG', shutil.which('ffmpeg') or 'ffmpeg')
FFPROBE = os.environ.get('FFPROBE', shutil.which('ffprobe') or 'ffprobe')
WHISPER_CLI = os.environ.get('WHISPER_CLI', shutil.which('whisper-cli') or 'whisper-cli')
WHISPER_MODEL = os.environ.get('WHISPER_MODEL', '')
RESOLVE_SCRIPT_MODULES = os.environ.get(
    'RESOLVE_SCRIPT_MODULES',
    '/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Modules')


def resolve_app():
    """Connect to a running DaVinci Resolve Studio instance."""
    if RESOLVE_SCRIPT_MODULES not in sys.path:
        sys.path.insert(0, RESOLVE_SCRIPT_MODULES)
    import DaVinciResolveScript as dvr  # noqa: E402  (provided by Resolve)
    r = dvr.scriptapp('Resolve')
    if not r:
        raise SystemExit('DaVinci Resolve is not running or external scripting is disabled')
    return r
