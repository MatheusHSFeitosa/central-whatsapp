#!/usr/bin/env python3
"""Download a pinned, digest-verified CEF SDK and build the local C API host."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import shlex
import subprocess
import urllib.request
import zipfile

BASE=Path(__file__).resolve().parents[1]
NAME='cef_binary_152.0.6+g708dc14+chromium-152.0.7977.83_linux64_minimal'
URL='https://github.com/tobagin/karere/releases/download/cef-152.0.6-proprietary-codecs/'+NAME.replace('+','%2B')+'.zip'
DIGEST='3d64f6fac8911a368ffa415e3ee53d002cbd792866f08ed6578dae1e252cbac8'

def main():
    build=BASE/'build';build.mkdir(exist_ok=True)
    sdk=Path(os.environ.get('CENTRAL_CEF_SDK',str(build/NAME))).resolve()
    if not (sdk/'include/cef_api_hash.h').is_file():
        archive=build/(NAME+'.zip')
        if not archive.exists():
            temporary=archive.with_suffix('.part')
            print('Baixando o motor CEF fixado…',flush=True)
            urllib.request.urlretrieve(URL,temporary)
            temporary.rename(archive)
        digest=hashlib.file_digest(archive.open('rb'),'sha256').hexdigest() if hasattr(hashlib,'file_digest') else hashlib.sha256(archive.read_bytes()).hexdigest()
        if digest!=DIGEST:raise SystemExit('SHA-256 do CEF divergente. Arquivo rejeitado.')
        with zipfile.ZipFile(archive) as bundle:
            for item in bundle.infolist():
                path=(build/item.filename).resolve()
                if not path.is_relative_to(build.resolve()):raise SystemExit('Caminho inválido no SDK CEF.')
            bundle.extractall(build)
    destination=build/'cef-runtime';destination.mkdir(exist_ok=True)
    for directory in ('Release','Resources'):
        for source in (sdk/directory).iterdir():
            if source.name=='chrome-sandbox':continue
            target=destination/source.name
            if source.is_dir():shutil.copytree(source,target,dirs_exist_ok=True)
            else:shutil.copy2(source,target)
    shutil.copy2(BASE/'cef/bridge.js',destination/'bridge.js')
    shutil.copy2(BASE/'cef/THIRD-PARTY.md',destination/'THIRD-PARTY.md')
    shutil.copy2(BASE/'cef/json.hpp',destination/'json.hpp.license-source')
    shutil.copy2(sdk/'LICENSE.txt',destination/'LICENSE.cef.txt')
    licenses=sdk/'Resources'/'LICENSES'
    if licenses.exists():shutil.copytree(licenses,destination/'LICENSES',dirs_exist_ok=True)
    # Chromium's complete third-party notices ship as part of the SDK when available.
    for name in ('LICENSES.txt','CREDITS.html','README.txt'):
        if (sdk/name).exists():shutil.copy2(sdk/name,destination/name)
    glib_flags=shlex.split(subprocess.check_output(['pkg-config','--cflags','--libs','glib-2.0'],text=True))
    subprocess.run(['c++','-std=c++20','-O2','-pthread','-DCEF_API_VERSION=15200','-I'+str(sdk),str(BASE/'cef/host.cc'),str(destination/'libcef.so'),'-Wl,-rpath,$ORIGIN','-o',str(destination/'central-cef-host')]+glib_flags,check=True)
    (destination/'provenance.json').write_text(json.dumps({'url':URL,'sha256':DIGEST,'cef':'152.0.6','chromium':'152.0.7977.83','source':'tobagin/karere codec build','host':'Central Chats C API integration'},indent=2)+'\n')
    print('Motor CEF preparado em '+str(destination))

if __name__=='__main__':main()
