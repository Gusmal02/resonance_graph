"""Verify installed distribution and deterministic demo; write an audit receipt."""
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]

def main():
    suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():raise SystemExit(1)
    env={**os.environ, 'PYTHONIOENCODING':'utf-8'}
    outputs=[subprocess.check_output([sys.executable,'-B',str(ROOT/'examples/quickstart.py')],text=True,encoding='utf-8',env=env) for _ in range(2)]
    assert outputs[0]==outputs[1], 'Demo changed across identical runs'
    demo=json.loads(outputs[0])
    assert demo['nodes']==4 and demo['edges']==4 and demo['feedback_updates']==1
    assert [r['id'] for r in demo['hits']]==['revision','alcance']
    provenance=json.loads((ROOT/'docs/code_provenance.json').read_text(encoding='utf-8'))
    for item in provenance['core_files']:
        data=(ROOT/item['package_file']).read_text(encoding='utf-8').replace('\r\n','\n')
        assert hashlib.sha256(data.encode()).hexdigest()==item['normalized_sha256'],item
    receipt={'python':platform.python_version(),'platform':platform.platform(),
             'packages':{name:importlib.metadata.version(name) for name in ('resonance-graph','numpy','networkx')},
             'tests_run':result.testsRun,'tests_passed':result.wasSuccessful(),'demo_identical_twice':True,
             'demo':demo,'core_provenance_verified':True,
             'scope':'Installed library, portable core tests and synthetic demo; no historical research rerun.'}
    target=ROOT/'docs/build_verification.json'
    target.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(receipt,ensure_ascii=False))

if __name__=='__main__':main()
