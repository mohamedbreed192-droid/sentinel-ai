import io
from pathlib import Path
import tarfile
import pytest
from sentinel.importer import ImportFailure, extract_snapshot, parse_url

@pytest.mark.parametrize("url", ["http://github.com/a/b", "https://github.com.evil.com/a/b", "https://github.com/a/b?x=1", "https://github.com/a/..", "https://user@github.com/a/b", "file:///etc/passwd", "https://127.0.0.1/a/b"])
def test_rejects_untrusted_urls(url):
    with pytest.raises(ImportFailure):
        parse_url(url)

def test_public_url():
    assert parse_url("https://github.com/acme/api.git") == ("acme", "api")

def archive(name, kind=None, size=2):
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w:gz") as tar:
        info = tarfile.TarInfo(name)
        if kind:
            info.type = kind
            info.linkname = "/etc/passwd"
            tar.addfile(info)
        else:
            info.size = size
            tar.addfile(info, io.BytesIO(b"x" * size))
    return stream.getvalue()

@pytest.mark.parametrize("name,kind", [("root/../../escape.py",None),("/tmp/escape.py",None),("root/link.py",tarfile.SYMTYPE),("root/device.py",tarfile.CHRTYPE)])
def test_archive_escape_and_special_files(tmp_path, name, kind):
    with pytest.raises(ImportFailure):
        extract_snapshot(archive(name,kind),tmp_path)

def test_size_limit(tmp_path):
    with pytest.raises(ImportFailure):
        extract_snapshot(archive("root/big.py", size=2_000_001),tmp_path)

def test_extracts_only_supported_files(tmp_path):
    extract_snapshot(archive("root/src/app.py"),tmp_path)
    assert (tmp_path/"src/app.py").read_text() == "xx"
    extract_snapshot(archive("root/unsafe.sh"),tmp_path)
    assert not (tmp_path/"unsafe.sh").exists()

def test_import_rejects_private_metadata(tmp_path, monkeypatch):
    import httpx
    from sentinel import importer
    def handler(request):
        return httpx.Response(200,json={"full_name":"a/b","private":True})
    original = httpx.Client
    monkeypatch.setattr(importer.httpx,"Client",lambda **kw: original(transport=httpx.MockTransport(handler),**kw))
    with pytest.raises(ImportFailure, match="public repository"):
        importer.import_public("https://github.com/a/b",tmp_path)

def test_import_pins_commit(tmp_path, monkeypatch):
    import httpx
    from sentinel import importer
    requests=[]
    sha="a"*40
    def handler(request):
        requests.append(str(request.url))
        if request.url.host=="codeload.github.com":
            return httpx.Response(200,content=archive("root/main.py"))
        if request.url.path.endswith("/commits"):
            return httpx.Response(200,json=[{"sha":sha}])
        return httpx.Response(200,json={"full_name":"a/b","private":False})
    original=httpx.Client
    monkeypatch.setattr(importer.httpx,"Client",lambda **kw:original(transport=httpx.MockTransport(handler),**kw))
    result=importer.import_public("https://github.com/a/b",tmp_path)
    assert result["commit"]==sha
    assert requests[-1].endswith(sha)
    assert (tmp_path/"main.py").exists()


def test_github_archive_root_directory(tmp_path):
    stream=io.BytesIO()
    with tarfile.open(fileobj=stream,mode="w:gz") as tar:
        folder=tarfile.TarInfo("project-commit/");folder.type=tarfile.DIRTYPE;tar.addfile(folder)
        file=tarfile.TarInfo("project-commit/app.py");file.size=2;tar.addfile(file,io.BytesIO(b"ok"))
    extract_snapshot(stream.getvalue(),tmp_path)
    assert (tmp_path/"app.py").read_text()=="ok"
