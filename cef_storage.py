"""One-way copy into a fresh CEF profile; never modify the Qt session source."""
import json
import os
from pathlib import Path
import shutil
import tempfile


def prepare_cef_storage(session):
    session = Path(session)
    destination = session / 'cef'
    if destination.is_symlink():
        raise ValueError('O armazenamento CEF não pode ser um link.')
    if destination.exists():
        destination.chmod(0o700)
        return destination
    temporary = Path(tempfile.mkdtemp(prefix='.cef-migration-', dir=session))
    try:
        source = session / 'storage'
        if source.exists():
            if source.is_symlink():
                raise ValueError('A sessão antiga não pode ser um link.')
            # These files belong to a running process, cache, or Chromium version.
            ignore = shutil.ignore_patterns('Singleton*', 'LOCK', 'lockfile', 'Cache', 'Code Cache', 'GPUCache', 'Dawn*', 'DevToolsActivePort')
            shutil.copytree(source, temporary/'profile', ignore=ignore, symlinks=False)
        (temporary/'migration.json').write_text(json.dumps({'source':'qt-storage-copy', 'engine':'cef152', 'original_preserved':True})+'\n')
        for folder, dirs, files in os.walk(temporary):
            Path(folder).chmod(0o700)
            for filename in files:
                (Path(folder)/filename).chmod(0o600)
        os.rename(temporary, destination)
    finally:
        if temporary.exists():shutil.rmtree(temporary)
    return destination
