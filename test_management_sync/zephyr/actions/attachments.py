import enum
from pathlib import Path

from requests import Session

from test_management_sync.zephyr.model.attachments import UploadResult, AttachmentRequest, Attachment


class ItemType(enum.Enum):
    REQUIREMENT = 'requirement'
    TEST_CASE = 'testcase'
    RELEASE_TEST_SCHEDULE = 'releaseTestSchedule'

    def __init__(self, representation: str):
        self._representation = representation

    @property
    def http_type(self) -> str:
        return self._representation


def upload_files(session: Session, item_type: ItemType, files_to_upload: list[Path]) -> dict[Path, UploadResult]:
    final_files = {}
    index = 0
    field_name_to_file = dict[str, Path]()
    upload_results = list[UploadResult]()
    batch_limit = 1024 * 1024  # 1MB
    batch_size_bytes = 0

    def upload():
        r = session.post(
            '/flex/upload/document/genericattachment',
            files=final_files,
        )
        r.raise_for_status()
        upload_results.extend(UploadResult.schema().load(r.json(), many=True))

    for file in files_to_upload:
        field_name = f'{item_type.http_type}{index}'
        index += 1
        final_files[field_name] = (
            file.name,
            file.read_bytes(),
            'text/plain',
        )
        field_name_to_file[field_name] = file
        batch_size_bytes += file.stat().st_size
        if batch_size_bytes < batch_limit:
            continue
        upload()
        final_files.clear()
        batch_size_bytes = 0

    if batch_size_bytes > 0:
        upload()
        final_files.clear()

    file_to_result = dict[Path, UploadResult]()
    for upload_result in upload_results:
        file = field_name_to_file[upload_result.field_name]
        file_to_result[file] = upload_result
    return file_to_result


def attach_files(session: Session, attachments: list[AttachmentRequest]):
    r = session.post(
        '/flex/services/rest/v3/attachment/list',
        json=AttachmentRequest.schema().dump(attachments, many=True),
    )
    r.raise_for_status()


def get_attached_files(session: Session, item_type: ItemType, item_id: int, is_link: bool) -> list[Attachment]:
    r = session.get(
        '/flex/services/rest/v3/attachment',
        params={
            'itemid': item_id,
            'type': item_type.http_type,
            'isLink': is_link,
        }
    )
    r.raise_for_status()
    return Attachment.schema().load(r.json(), many=True)


def delete_attachment(session: Session, attachment_id: int):
    r = session.delete(
        f'/flex/services/rest/v3/attachment/{attachment_id}'
    )
    r.raise_for_status()
