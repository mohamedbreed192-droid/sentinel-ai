"""Checks for the explicit isolated-test container, not the analysis pipeline."""
import os
from pathlib import Path
import socket
import pytest

def test_unprivileged_read_only_repository():
    assert os.geteuid() != 0
    with pytest.raises(OSError):
        Path('/repo/should-not-be-created').write_text('blocked')
    with pytest.raises(OSError):
        Path('/etc/should-not-be-created').write_text('blocked')
    assert not Path('/var/run/docker.sock').exists()

def test_no_network():
    with socket.socket() as connection:
        connection.settimeout(.2)
        with pytest.raises(OSError):
            connection.connect(('1.1.1.1',443))

def test_ephemeral_temporary_storage():
    file=Path('/tmp/sentinel-sandbox-test')
    file.write_text('temporary')
    assert file.read_text() == 'temporary'
    file.unlink()
