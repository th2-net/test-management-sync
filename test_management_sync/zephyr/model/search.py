from dataclasses import dataclass

from dataclasses_json import dataclass_json, LetterCase, Undefined, config, DataClassJsonMixin


@dataclass_json(letter_case=LetterCase.CAMEL, undefined=Undefined.EXCLUDE)
@dataclass
class SearchResult(DataClassJsonMixin):
    first_result: int
    result_size: int
    page_number: int
    results: list[dict]
