from dataclasses import dataclass, field
from typing import Optional

from dataclasses_json import dataclass_json, LetterCase, Undefined, DataClassJsonMixin


@dataclass_json(letter_case=LetterCase.CAMEL, undefined=Undefined.EXCLUDE)
@dataclass
class Preference(DataClassJsonMixin):
    name: str
    value: Optional[str] = field(default=None)
