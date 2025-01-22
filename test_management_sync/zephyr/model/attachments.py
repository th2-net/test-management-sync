from dataclasses import dataclass

from dataclasses_json import dataclass_json, LetterCase, Undefined, DataClassJsonMixin


@dataclass_json(letter_case=LetterCase.CAMEL, undefined=Undefined.EXCLUDE)
@dataclass
class UploadResult(DataClassJsonMixin):
    file_name: str
    field_name: str
    temp_file_path: str
    content_type: str


@dataclass_json(letter_case=LetterCase.CAMEL, undefined=Undefined.EXCLUDE)
@dataclass
class AttachmentRequest(DataClassJsonMixin):
    name: str
    content_type: str
    item_type: str
    temp_path: str
    item_id: int
    # create_by: int
    # file_size: int


@dataclass_json(letter_case=LetterCase.CAMEL, undefined=Undefined.EXCLUDE)
@dataclass
class Attachment(DataClassJsonMixin):
    id: int
    name: str
    link: bool
