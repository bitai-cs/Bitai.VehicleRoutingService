import json
from pathlib import Path

import pytest

from vehicle_routing_web.application.upload_service import UploadService
from vehicle_routing_web.data.storage import FileStorage
from vehicle_routing_web.domain.exceptions import (
    DuplicatePayloadError,
    DuplicateProcessIdError,
    InvalidPayloadError,
    InvalidProcessIdError,
    PayloadTooLargeError,
    StorageCorruptedError,
)

PAYLOAD = b'{"nodes": {"0": {"label": "depot"}}, "vehicle_capacities": [4, 4]}'
OTHER_PAYLOAD = b'{"vehicle_capacities": [6]}'


@pytest.fixture
def storage_root(tmp_path: Path) -> Path:
    return tmp_path / "storage"


@pytest.fixture
def storage(storage_root: Path) -> FileStorage:
    return FileStorage(storage_root)


@pytest.fixture
def service(storage: FileStorage) -> UploadService:
    return UploadService(storage, max_upload_bytes=1024)


def test_upload_creates_folder_payload_and_registry_entry(service, storage_root):
    result = service.upload("proc1", PAYLOAD)

    payload_file = storage_root / "payloads" / "proc1" / "proc1-payload.json"
    assert result.payload_path == payload_file.resolve()
    assert payload_file.read_bytes() == PAYLOAD  # stored exactly as uploaded
    assert (storage_root / "hashes.txt").read_text(encoding="utf-8") == f"{result.payload_hash} proc1\n"


def test_upload_creates_missing_storage_tree(service, storage_root):
    assert not storage_root.exists()
    service.upload("proc1", PAYLOAD)
    assert (storage_root / "payloads").is_dir()


def test_duplicate_hash_is_rejected_and_reports_existing_process(service, storage_root):
    first = service.upload("proc1", PAYLOAD)
    reformatted = json.dumps(json.loads(PAYLOAD), indent=4, sort_keys=True).encode()

    with pytest.raises(DuplicatePayloadError) as excinfo:
        service.upload("proc2", reformatted)

    assert excinfo.value.existing_process_id == "proc1"
    assert excinfo.value.payload_hash == first.payload_hash
    assert not (storage_root / "payloads" / "proc2").exists()
    assert (storage_root / "hashes.txt").read_text(encoding="utf-8").count("\n") == 1


def test_duplicate_process_id_is_rejected_without_changes(service, storage_root):
    service.upload("proc1", PAYLOAD)
    registry_before = (storage_root / "hashes.txt").read_text(encoding="utf-8")

    with pytest.raises(DuplicateProcessIdError):
        service.upload("proc1", OTHER_PAYLOAD)

    assert (storage_root / "hashes.txt").read_text(encoding="utf-8") == registry_before
    assert (storage_root / "payloads" / "proc1" / "proc1-payload.json").read_bytes() == PAYLOAD


def test_existing_folder_not_in_registry_blocks_process_id(service, storage_root):
    (storage_root / "payloads" / "orphan").mkdir(parents=True)

    with pytest.raises(DuplicateProcessIdError):
        service.upload("orphan", PAYLOAD)

    assert not (storage_root / "hashes.txt").exists()


def test_duplicate_hash_takes_precedence_over_duplicate_id(service):
    service.upload("proc1", PAYLOAD)
    with pytest.raises(DuplicatePayloadError):
        service.upload("proc1", PAYLOAD)


@pytest.mark.parametrize("bad_id", ["", "..", "../escape", "a/b", "a\\b", "C:\\x", "CON"])
def test_invalid_process_id_never_touches_disk(service, storage_root, bad_id):
    with pytest.raises(InvalidProcessIdError):
        service.upload(bad_id, PAYLOAD)
    assert not storage_root.exists()


@pytest.mark.parametrize("raw", [b"", b"nope", b"[]"])
def test_invalid_payload_never_touches_disk(service, storage_root, raw):
    with pytest.raises(InvalidPayloadError):
        service.upload("proc1", raw)
    assert not storage_root.exists()


def test_oversized_payload_is_rejected(storage, storage_root):
    small = UploadService(storage, max_upload_bytes=10)
    with pytest.raises(PayloadTooLargeError):
        small.upload("proc1", PAYLOAD)
    assert not storage_root.exists()


def test_registry_survives_new_storage_instance(storage_root):
    UploadService(FileStorage(storage_root), 1024).upload("proc1", PAYLOAD)

    with pytest.raises(DuplicatePayloadError):
        UploadService(FileStorage(storage_root), 1024).upload("proc2", PAYLOAD)


def test_registry_ignores_blank_lines(service, storage, storage_root):
    storage_root.mkdir()
    (storage_root / "hashes.txt").write_text("\n" + "a" * 64 + " legacy\n\n", encoding="utf-8")

    assert storage.read_registry() == {"a" * 64: "legacy"}
    service.upload("proc1", PAYLOAD)
    assert storage.read_registry()["a" * 64] == "legacy"


def test_malformed_registry_raises_storage_error(service, storage_root):
    storage_root.mkdir()
    (storage_root / "hashes.txt").write_text("only-one-token\n", encoding="utf-8")

    with pytest.raises(StorageCorruptedError):
        service.upload("proc1", PAYLOAD)


def test_failed_registry_write_rolls_back_folder(storage, storage_root, monkeypatch):
    original_open = Path.open

    def failing_open(self, *args, **kwargs):
        if self.name == "hashes.txt":
            raise OSError("disk full")
        return original_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", failing_open)

    with pytest.raises(OSError, match="disk full"):
        storage.add_payload("proc1", "f" * 64, PAYLOAD)

    monkeypatch.undo()
    assert not (storage_root / "payloads" / "proc1").exists()
    assert storage.read_registry() == {}


def test_process_dir_rejects_traversal_even_when_called_directly(storage):
    with pytest.raises(InvalidProcessIdError):
        storage.process_dir("../outside")
