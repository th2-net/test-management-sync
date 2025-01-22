from dataclasses import dataclass, field

from dataclasses_json import dataclass_json, LetterCase, Undefined, DataClassJsonMixin


@dataclass_json(letter_case=LetterCase.CAMEL, undefined=Undefined.EXCLUDE)
@dataclass
class UserInfo(DataClassJsonMixin):
    id: int
    username: str
    title: str = field(default='')
