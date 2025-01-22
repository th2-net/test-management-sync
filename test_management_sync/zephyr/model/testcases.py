from dataclasses import dataclass, field
from typing import Optional

from dataclasses_json import dataclass_json, LetterCase, Undefined, config, DataClassJsonMixin

from test_management_sync.zephyr.model.field_util import exclude_if_none


@dataclass_json(letter_case=LetterCase.CAMEL, undefined=Undefined.EXCLUDE)
@dataclass
class TestCase(DataClassJsonMixin):
    """
    Class corresponds to test case in zephyr
    """
    name: str
    description: str
    project_id: int
    release_id: Optional[int] = field(default=None, metadata=config(exclude=exclude_if_none))
    writer_id: Optional[int] = field(default=None, metadata=config(exclude=exclude_if_none))
    testcase_id: Optional[int] = field(default=None, metadata=config(exclude=exclude_if_none))
    automated: bool = field(default=False)
    requirement_ids: list[int] = field(default_factory=lambda: [])
    id: Optional[int] = field(default=None, metadata=config(exclude=exclude_if_none))
    comments: Optional[str] = field(default=None, metadata=config(exclude=exclude_if_none))


@dataclass_json(letter_case=LetterCase.CAMEL, undefined=Undefined.EXCLUDE)
@dataclass
class TestCaseInTree(DataClassJsonMixin):
    """
    Class corresponds to test case in a particular place in test cases tree
    """
    tcr_catalog_tree_id: int
    testcase: TestCase


@dataclass_json(letter_case=LetterCase.CAMEL, undefined=Undefined.EXCLUDE)
@dataclass
class TestCaseTreeNode(DataClassJsonMixin):
    """
    Class corresponds to a node in test case tree
    """
    name: str
    release_id: int
    description: str = field(default='')
    id: Optional[int] = field(default=None, metadata=config(exclude=exclude_if_none))
    linked_tcp_catalog_tree_id: Optional[int] =\
        field(default=None, metadata=config(exclude=exclude_if_none, field_name='linkedTCRCatalogTreeId'))
    type: str = field(default='Phase')


@dataclass_json(letter_case=LetterCase.CAMEL, undefined=Undefined.EXCLUDE)
@dataclass
class DeleteAllRequest(DataClassJsonMixin):
    selected_all: int = field(default=0)
    ids: list[int] = field(default_factory=lambda: [])
