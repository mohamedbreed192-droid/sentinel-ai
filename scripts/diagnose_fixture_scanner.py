"""CI-only diagnostics on the fixed synthetic fixture; never on imported repositories."""
from pathlib import Path
import json
import subprocess
from sentinel import scanners
from sentinel.pipeline import RULES

original = subprocess.Popen

def traced(*args, **kwargs):
    process = original(*args, **kwargs)
    original_wait = process.wait
    def wait(*a, **kw):
        code = original_wait(*a, **kw)
        if code not in (0, 1):
            stream = kwargs['stderr']
            stream.seek(0)
            text = stream.read(4000).decode(errors='replace')
            print('Fixture-only scanner stderr:', text.replace('SENTINEL_SYNTHETIC_CREDENTIAL_DO_NOT_USE', '[REDACTED]'))
            stream = kwargs['stdout']
            stream.seek(0)
            try:
                data = json.loads(stream.read())
                print('Fixture-only scanner error metadata:', data.get('errors', []))
            except ValueError:
                print('Scanner emitted no JSON')
        return code
    process.wait = wait
    return process

scanners.subprocess.Popen = traced
root = Path(__file__).resolve().parents[1] / 'fixtures/demo'
print(scanners.scan(root, RULES)[1])
