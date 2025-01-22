from dataclasses import dataclass, field
from typing import Optional

from dataclasses_json import dataclass_json, LetterCase, Undefined, CatchAll, config, DataClassJsonMixin

from test_management_sync.zephyr.model.field_util import exclude_if_none, exclude_if_empty


@dataclass_json(letter_case=LetterCase.CAMEL, undefined=Undefined.EXCLUDE)
@dataclass
class Requirement(DataClassJsonMixin):
    """
    Class that corresponds to a requirement
    """
    name: str
    details: str
    requirement_tree_id: Optional[int] = field(default=None)
    id: Optional[int] = field(default=None, metadata=config(exclude=exclude_if_none))
    release_ids: list[int] = field(default_factory=lambda: [])
    requirement_tree_ids: list[int] = field(default_factory=lambda: [])
    custom_properties: dict[str, CatchAll] = field(default_factory=lambda: {})


@dataclass_json(letter_case=LetterCase.CAMEL, undefined=Undefined.EXCLUDE)
@dataclass
class RequirementTreeNode(DataClassJsonMixin):
    """
    Class that corresponds to a requirement tree node
    """
    name: str
    description: str
    project_id: int
    id: Optional[int] = field(default=None, metadata=config(exclude=exclude_if_none))
    type: str = field(default="req")
    release_ids: list[str] = field(default_factory=lambda: [], metadata=config(exclude=exclude_if_empty))
    parent_id: int = field(default=0)
    categories: list['RequirementTreeNode'] = \
        field(default_factory=lambda: [], metadata=config(exclude=exclude_if_empty))
    release_id: Optional[int] = field(default=None, metadata=config(exclude=exclude_if_none))


TreePath = list[int]


@dataclass_json(letter_case=LetterCase.CAMEL, undefined=Undefined.EXCLUDE)
@dataclass
class BulkRequirementTestCasesMapping(DataClassJsonMixin):
    mod_tcr_catalog_tree: list[TreePath] = field(metadata=config(field_name='modTCRCatalogTree'))
    requirement_id: int
    mod_testcase: list[TreePath]
    release_id: int


@dataclass_json(letter_case=LetterCase.CAMEL, undefined=Undefined.EXCLUDE)
@dataclass
class DeleteAllRequest(DataClassJsonMixin):
    selected_all: int = field(default=0)
    ids: list[int] = field(default_factory=lambda: [])
