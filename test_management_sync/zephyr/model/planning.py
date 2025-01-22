from dataclasses import dataclass, field
from typing import Optional, List

from dataclasses_json import dataclass_json, LetterCase, Undefined, config, DataClassJsonMixin

from test_management_sync.zephyr.model.field_util import exclude_if_none, exclude_if_empty
from test_management_sync.zephyr.model.testcases import TestCaseInTree


@dataclass_json(letter_case=LetterCase.CAMEL, undefined=Undefined.EXCLUDE)
@dataclass
class Phase(DataClassJsonMixin):
    phase_start_date: str
    phase_end_date: str
    cycle_id: int
    name: str
    release_id: Optional[int] = field(default=None)
    tcr_catalog_tree_id: Optional[int] = field(default=None, metadata=config(exclude=exclude_if_none))
    free_form: bool = field(default=False)
    id: Optional[int] = field(default=None, metadata=config(exclude=exclude_if_none))


@dataclass_json(letter_case=LetterCase.CAMEL, undefined=Undefined.EXCLUDE)
@dataclass
class Cycle(DataClassJsonMixin):
    name: str
    cycle_start_date: str
    cycle_end_date: str
    release_id: int
    id: Optional[int] = field(default=None, metadata=config(exclude=exclude_if_none))
    cycle_phases: list['Phase'] = field(default_factory=lambda: [], metadata=config(exclude=exclude_if_empty))


@dataclass_json(letter_case=LetterCase.CAMEL, undefined=Undefined.EXCLUDE)
@dataclass
class ExecutionTestResult(DataClassJsonMixin):
    execution_status: str


@dataclass_json(letter_case=LetterCase.CAMEL, undefined=Undefined.EXCLUDE)
@dataclass
class Execution(DataClassJsonMixin):
    id: int
    tester_id: int
    tcr_tree_testcase: TestCaseInTree
    last_test_result: ExecutionTestResult = field(default=None)


@dataclass_json(letter_case=LetterCase.CAMEL, undefined=Undefined.EXCLUDE)
@dataclass
class AssignmentTree(DataClassJsonMixin):
    id: int
    type: str
    name: str
    categories: List['AssignmentTree']
    release_id: int
    testcase_count: int


@dataclass_json(letter_case=LetterCase.CAMEL, undefined=Undefined.EXCLUDE)
@dataclass
class TestCasesAssignment(DataClassJsonMixin):
    tree_id: int = field(metadata=config(field_name='treeid'))
    testcase_ids: list[int] = field(default_factory=lambda: [], metadata=config(field_name='tctIds'))
    is_exclusion: bool = field(default=False)


@dataclass_json(letter_case=LetterCase.CAMEL, undefined=Undefined.EXCLUDE)
@dataclass
class ExecutionsStatusUpdate(DataClassJsonMixin):
    ids: list[int]
    teststep_update: bool = field(default=False)
    teststep_status_id: int = field(default=1)
