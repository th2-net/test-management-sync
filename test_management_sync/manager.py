from collections import defaultdict
from pathlib import Path
from typing import Any

from test_management_sync.model import Requirement, Folder, TestCase, Cycle, RootFolder, ExecutionStatus, AttachedFile
from test_management_sync.service import Service
from test_management_sync.util import group_tc_by_folder


class Manager:
    """
    Manager class provides API for test management
    """

    def __init__(self, service: Service):
        if service is None:
            raise TypeError("service is none")
        self.service = service

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.service is not None:
            self.service.close()

    def close(self):
        self.service.close()

    def create_requirements(self, requirements: list[Requirement], force: bool = False):
        req_by_folder = defaultdict[Folder, list[Requirement]](list)
        for req in requirements:
            req_by_folder[req.folder].append(req)

        for folder, reqs in req_by_folder.items():
            self.service.create_requirement_folder_if_not_exists(folder)
            if force:
                self.service.remove_requirements(folder)
                req_to_create = reqs
            else:
                existing_req = self.service.get_requirements(folder)
                req_to_create = [req for req in reqs if req not in existing_req]

            if req_to_create:
                self.service.create_requirements(folder, req_to_create)

    def create_test_cases(self, test_cases: list[TestCase], force: bool = False):
        tcs_by_folder = group_tc_by_folder(test_cases)

        for folder, tcs in tcs_by_folder.items():
            self.service.create_testcase_folder_if_not_exists(folder)
            if force:
                self.service.remove_testcases(folder)
                tc_to_create = tcs
            else:
                existing_tc = self.service.get_testcases(folder)
                tc_to_create = [tc for tc in tcs if tc not in existing_tc]

            if tc_to_create:
                self.service.create_testcases(folder, tc_to_create)

    def map_test_cases_to_requirements(self, mapping: dict[Requirement, list[TestCase]]):
        for req, testcases in mapping.items():
            grouped_tcs = group_tc_by_folder(testcases)
            for tc_folder, tcs in grouped_tcs.items():
                self.service.map_testcases_to_requirement(req, tc_folder, tcs)

    def create_cycle(self, cycle: Cycle, force: bool = False):
        self.service.create_cycle_if_not_exist(cycle, force)

    def create_phase_from_testcase_tree(self, cycle: Cycle, phase_root: RootFolder):
        self.service.create_phase_if_not_exist(cycle, phase_root)
        self.service.assign_test_cases_in_phase(cycle, phase_root.name)

    def create_phase_from_testcases(self, cycle: Cycle, phase_name: str, test_cases: list[TestCase]):
        self.service.create_free_phase_if_not_exist(cycle, phase_name, test_cases)
        self.service.assign_test_cases_in_phase(cycle, phase_name)

    def execution_statuses(self) -> list[ExecutionStatus]:
        return self.service.execution_statuses()

    def execution_status_for_name(self, name: str) -> ExecutionStatus:
        name_casefold = name.casefold()
        return next((status for status in self.execution_statuses() if status.name.casefold() == name_casefold), None)

    def execute_testcases(self, cycle: Cycle, status: ExecutionStatus, test_cases: list[TestCase]):
        tc_by_folder = group_tc_by_folder(test_cases)
        self.service.execute_all_test_cases(cycle, status, tc_by_folder)

    def get_last_execution_status_for_testcases(self, cycle: Cycle,
                                                test_cases: list[TestCase]) -> dict[TestCase, ExecutionStatus]:
        tc_by_folder = group_tc_by_folder(test_cases)
        last_statuses = dict[TestCase, ExecutionStatus]()
        for folder, tcs in tc_by_folder.items():
            result = self.service.get_executions_for_test_cases(cycle, folder, tcs)
            last_statuses.update(result)

        return last_statuses

    def get_last_execution_status_for_cycle_testcases(self, cycle: Cycle) -> dict[TestCase, ExecutionStatus]:
        return self.service.get_executions_for_cycle(cycle)

    def attach_files_to_requirements(self, attachments: dict[Requirement, list[Path]], replace_existing: bool = False):
        Manager.__check_all_files_unique(attachments)
        remove_old = dict[Requirement, list[AttachedFile]]()
        if replace_existing:
            for req, files in attachments.items():
                req_attachments = self.service.get_requirement_attachments(req)
                remove_old[req] = self.__find_attached_files(files, req_attachments)

        self.service.attache_files_to_requirements(attachments)
        if remove_old:
            for req, old_files in remove_old.items():
                for old_file in old_files:
                    self.service.remove_requirement_attachment(req, old_file)

    def attach_files_to_testcases(self, attachments: dict[TestCase, list[Path]], replace_existing: bool = False):
        Manager.__check_all_files_unique(attachments)
        remove_old = dict[TestCase, list[AttachedFile]]()
        if replace_existing:
            for tc, files in attachments.items():
                req_attachments = self.service.get_testcase_attachments(tc)
                remove_old[tc] = self.__find_attached_files(files, req_attachments)

        self.service.attache_files_to_testcases(attachments)

        if remove_old:
            for tc, old_files in remove_old.items():
                for old_file in old_files:
                    self.service.remove_testcase_attachment(tc, old_file)

    def attach_files_to_executions(self, cycle: Cycle, attachments: dict[TestCase, list[Path]],
                                   replace_existing: bool = False):
        Manager.__check_all_files_unique(attachments)
        remove_old = dict[TestCase, list[AttachedFile]]()
        if replace_existing:
            for tc, files in attachments.items():
                req_attachments = self.service.get_execution_attachments(cycle, tc)
                remove_old[tc] = self.__find_attached_files(files, req_attachments)

        self.service.attache_files_to_testcases_executions(cycle, attachments)

        if remove_old:
            for tc, old_files in remove_old.items():
                for old_file in old_files:
                    self.service.remove_execution_attachment(cycle, tc, old_file)

    @staticmethod
    def __find_attached_files(files: list[Path], attachments: list[AttachedFile]) -> list[AttachedFile]:
        attached_files = []
        for attachment in attachments:
            for file in files:
                if file.name == attachment.name:
                    attached_files.append(attachment)
                    break
        return attached_files

    @staticmethod
    def __check_all_files_unique(attachments: dict[Any, list[Path]]):
        for key, files in attachments.items():
            unique_files = set[Path]()
            duplicates = list[Path]()
            for f in files:
                if f in unique_files:
                    duplicates.append(f)
                else:
                    unique_files.add(f)
            if duplicates:
                duplicated_paths = list(map(lambda d: str(d), duplicates))
                raise ValueError(f'duplicated files in attachments: {duplicated_paths}')
