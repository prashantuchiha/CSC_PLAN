from uuid import uuid4

import pytest

from china_masters.domain.exceptions import ValidationError
from china_masters.infrastructure.filesystem.local import LocalFileStorage, slug


@pytest.mark.parametrize("name", ["../../evil", "CON", "张伟", "A/B:C*D?", "   "])
def test_sanitized_id_scoped_slugs(name):
    identity = uuid4()
    result = slug(name, identity)
    assert identity.hex in result
    assert not set("/\\:*?<>|. ").intersection(result)
    assert result != slug(name, uuid4())


@pytest.mark.parametrize(
    "path",
    [
        "../escape",
        "a/../../escape",
        "/absolute",
        "C:\\escape",
        "a\\..\\escape",
        "x:stream",
        "\\\\server\\share",
    ],
)
def test_traversal_rejected(tmp_path, path):
    with pytest.raises(ValidationError):
        LocalFileStorage(tmp_path).write_bytes(path, b"no")


def test_artifact_port_roundtrip(tmp_path):
    storage = LocalFileStorage(tmp_path)
    assert storage.write_bytes("sources/sample.txt", b"evidence") == "sources/sample.txt"
    assert storage.read_bytes("sources/sample.txt") == b"evidence"


def test_symlink_escape_rejected(tmp_path):
    root = tmp_path / "root"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    try:
        (root / "link").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("OS does not permit symlink creation")
    with pytest.raises(ValidationError):
        LocalFileStorage(root).write_bytes("link/escape.txt", b"no")
