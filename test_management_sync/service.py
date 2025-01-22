from abc import ABC
from pathlib import Path

from test_management_sync.model import Folder, Requirement, TestCase, Cycle, RootFolder, ExecutionStatus, AttachedFile


class Service(ABC):
    """
    Service class provides API to access the test management platform
    """

    def create_requirement_folder_if_not_exists(self, folder: Folder):
        pass

    def create_requirements(self, folder: Folder, requirements: list[Requirement]):
        pass

    def get_requirements(self, folder: Folder) -> list[Requirement]:
        pass

    def remove_requirements(self, folder: Folder):
        pass

    def create_testcase_folder_if_not_exists(self, folder: Folder):
        pass

    def remove_testcases(self, folder: Folder):
        pass

    def get_testcases(self, folder: Folder) -> list[TestCase]:
        pass

    def create_testcases(self, folder: Folder, tc_to_create: list[TestCase]):
        pass

    def map_testcases_to_requirement(self, req: Requirement, tc_folder: Folder, tcs: list[TestCase]):
        pass

    def create_cycle_if_not_exist(self, cycle: Cycle, delete_if_exist: bool):
        pass

    def create_phase_if_not_exist(self, cycle: Cycle, phase_root: RootFolder):
        pass

    def create_free_phase_if_not_exist(self, cycle: Cycle, phase_name: str, test_cases: list[TestCase]):
        pass

    def execution_statuses(self) -> list[ExecutionStatus]:
        pass

    def execute_test_case(self, cycle: Cycle, status: ExecutionStatus, folder: Folder, tcs: list[TestCase]):
        pass

    def execute_all_test_cases(self, cycle: Cycle, status: ExecutionStatus, tcs_by_folder: dict[Folder, list[TestCase]]):
        pass

    def close(self):
        pass

    def assign_test_cases_in_phase(self, cycle: Cycle, phase_name: str):
        pass

    def attache_files_to_requirements(self, attachments: dict[Requirement, list[Path]]):
        pass

    def attache_files_to_testcases(self, attachments: dict[TestCase, list[Path]]):
        pass

    def attache_files_to_testcases_executions(self, cycle: Cycle, attachments: dict[TestCase, list[Path]]):
        pass

    def get_requirement_attachments(self, req: Requirement) -> list[AttachedFile]:
        pass

    def remove_requirement_attachment(self, req: Requirement, old_file: AttachedFile):
        pass

    def get_testcase_attachments(self, tc: TestCase) -> list[AttachedFile]:
        pass

    def remove_testcase_attachment(self, tc: TestCase, old_file: AttachedFile):
        pass

    def get_execution_attachments(self, cycle: Cycle, tc: TestCase) -> list[AttachedFile]:
        pass

    def remove_execution_attachment(self, cycle: Cycle, tc: TestCase, old_file: AttachedFile):
        pass

    def get_executions_for_test_cases(self, cycle: Cycle, folder: Folder,
                                      tcs: list[TestCase]) -> dict[TestCase, ExecutionStatus]:
        pass

    def get_executions_for_cycle(self, cycle: Cycle) -> dict[TestCase, ExecutionStatus]:
        pass

