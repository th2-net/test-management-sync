import json
import logging
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

from test_management_sync.model import ExecutionStatus, Cycle, TestCase, RootFolder, Requirement, Folder, AttachedFile
from test_management_sync.service import Service
from test_management_sync.util import group_tc_by_folder
from test_management_sync.zephyr.actions import (user, planning, testcase, testcase_tree, requirement_tree,
                                                 attachments as file_attachment, preferences)
from test_management_sync.zephyr.actions import requirement
from test_management_sync.zephyr.model.attachments import AttachmentRequest, Attachment
from test_management_sync.zephyr.model.planning import Cycle as ZephyrCycle, Phase, TestCasesAssignment
from test_management_sync.zephyr.model.requirements import RequirementTreeNode, Requirement as ZephyrRequirement
from test_management_sync.zephyr.model.testcases import TestCaseTreeNode, TestCaseInTree, TestCase as ZephyrTestCase
from test_management_sync.zephyr.session import ZephyrSession

_EXECUTION_STATUSES_PREFERENCE_NAME = 'testresult.testresultStatus.LOV'

_logger = logging.getLogger(__name__)

class ZephyrService(Service):
    __req_tree_cache: dict[Folder, RequirementTreeNode] = {}
    __tc_tree_cache: dict[Folder, TestCaseTreeNode] = {}
    __tc_cache: dict[Folder, list[TestCaseInTree]] = defaultdict(list)
    __req_cache: dict[Folder, list[ZephyrRequirement]] = defaultdict(list)
    __cycle_cache: dict[Cycle, ZephyrCycle] = {}
    __phase_cache: dict[Cycle, dict[str, Phase]] = defaultdict(dict)
    __batch_size: int = 1000

    def __init__(self, zephyr_url: str, api_token: str, project_id: int,
                 release_id: int, execution_statuses: list[ExecutionStatus] = None):
        if len(zephyr_url) == 0:
            raise ValueError('empty zephyr url')
        if len(api_token) == 0:
            raise ValueError('empty api token')
        self.__session = ZephyrSession(prefix_url=zephyr_url, api_token=api_token)
        self.__project_id = project_id
        self.__release_id = release_id
        self.__execution_statuses = \
            ZephyrService.__to_dict(
                execution_statuses if execution_statuses is not None else self.__load_execution_statuses()
            )
        self.__tester_id = user.get_user_id(self.__session)
        self.__load_existing_data()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        self.__session.close()

    def create_requirement_folder_if_not_exists(self, folder: Folder):
        if folder in self.__req_tree_cache:
            _logger.debug('folder %s found in cache', folder)
            return
        if folder.parent is not None:
            self.create_requirement_folder_if_not_exists(folder.parent)

        parent = None if folder.parent is None else self.__req_tree_cache[folder.parent]
        node = RequirementTreeNode(name=folder.name, description='', project_id=self.__project_id,
                                   release_ids=[str(self.__release_id)], parent_id=0 if parent is None else parent.id)
        node = requirement_tree.new_requirement_tree_node(self.__session, node)
        self.__req_tree_cache[folder] = node

    def create_requirements(self, folder: Folder, requirements: list[Requirement]):
        _logger.info('creating %s requirement(s) in folder %s', len(requirements), folder.name)
        req_folder = self.__req_tree_cache[folder]
        for req in requirements:
            _logger.debug("creating requirement %s", req)
            zephyr_req = ZephyrRequirement(
                requirement_tree_id=req_folder.id,
                name=req.name,
                details=req.description,
                release_ids=[self.__release_id],
            )
            zephyr_req = requirement.new_requirement(self.__session, zephyr_req)
            self.__req_cache[folder].append(zephyr_req)

    def get_requirements(self, folder: Folder) -> list[Requirement]:
        _logger.info("getting requirements in folder %s", folder.name)
        if folder in self.__req_cache:
            return ZephyrService.__to_model_req(folder, self.__req_cache[folder])
        req_folder = self.__req_tree_cache[folder]
        zephyr_reqs = requirement.find_requirements(self.__session, self.__release_id, req_folder)
        self.__req_cache[folder].extend(zephyr_reqs)
        return ZephyrService.__to_model_req(folder, zephyr_reqs)

    def remove_requirements(self, folder: Folder):
        _logger.info("removing requirements in folder %s", folder.name)
        req_node = self.__req_tree_cache.get(folder, None)
        if req_node is None:
            return
        requirement.delete_all_for_tree(self.__session, self.__release_id, req_node)
        if folder in self.__req_cache:
            del self.__req_cache[folder]

    def create_testcase_folder_if_not_exists(self, folder: Folder):
        if folder in self.__tc_tree_cache:
            return
        if folder.parent is not None:
            self.create_testcase_folder_if_not_exists(folder.parent)
        parent = None if folder.parent is None else self.__tc_tree_cache[folder.parent]
        node = TestCaseTreeNode(name=folder.name, release_id=self.__release_id)
        node = testcase_tree.create_test_case_tree_node(self.__session, node, parent)
        self.__tc_tree_cache[folder] = node

    def remove_testcases(self, folder: Folder):
        _logger.info("removing test cases in folder %s", folder.name)
        tc_node = self.__tc_tree_cache.get(folder, None)
        if tc_node is None:
            return
        testcase.delete_all_for_tree(self.__session, tc_node)
        if folder in self.__tc_cache:
            del self.__tc_cache[folder]

    def get_testcases(self, folder: Folder) -> list[TestCase]:
        _logger.info("getting test cases in folder %s", folder.name)
        zephyr_testcases = self.__get_zephyr_testcases(folder)
        return ZephyrService.__to_model_tcs(folder, zephyr_testcases)

    def create_testcases(self, folder: Folder, tc_to_create: list[TestCase]):
        if not tc_to_create:
            return
        _logger.info("creating %s test case(s) in folder %s", len(tc_to_create), folder.name)
        zephyr_tc_node = self.__tc_tree_cache[folder]
        zephyr_tcs_in_tree = list(map(
            lambda tc: TestCaseInTree(
                tcr_catalog_tree_id=zephyr_tc_node.id,
                testcase=ZephyrTestCase(name=tc.name, description=tc.description, project_id=self.__project_id,
                                        comments=tc.description if len(tc.description) > 0 else None)),
            tc_to_create,
        ))
        created_tcs = testcase.new_test_cases(self.__session, zephyr_tcs_in_tree)
        self.__tc_cache[folder].extend(created_tcs)

    def map_testcases_to_requirement(self, req: Requirement, tc_folder: Folder, tcs: list[TestCase]):
        _logger.info("mapping requirement %s to %s test case(s) in folder %s", req.name, len(tcs), tc_folder.name)
        zephyr_reqs = self.__req_cache[req.folder]
        zephyr_req = None
        for zephyr_r in zephyr_reqs:
            if zephyr_r.name == req.name and zephyr_r.details == req.description:
                zephyr_req = zephyr_r
                break
        if zephyr_req is None:
            raise Exception(f'cannot find requirement {req}')

        tc_tree_nodes = []
        start = tc_folder
        while start is not None:
            tc_tree_nodes.append(self.__tc_tree_cache[start])
            start = start.parent
        tc_tree_nodes.reverse()

        zephyr_tcs = self.__tc_cache[tc_folder]

        def find_test_case(zephyr_tc: TestCaseInTree) -> bool:
            for tc in tcs:
                if tc.name == zephyr_tc.testcase.name and tc.description == zephyr_tc.testcase.description:
                    return True
            return False

        filtered_test_cases = list(filter(find_test_case, zephyr_tcs))
        requirement.map_requirement_to_test_cases(self.__session, self.__release_id, zephyr_req,
                                                  filtered_test_cases, tc_tree_nodes)

    def create_cycle_if_not_exist(self, cycle: Cycle, delete_if_exist: bool):
        if cycle in self.__cycle_cache:
            if delete_if_exist:
                zephyr_cycle = self.__cycle_cache.get(cycle, None)
                if zephyr_cycle is not None:
                    planning.delete_cycle(self.__session, zephyr_cycle)
                    del self.__cycle_cache[cycle]
                    del self.__phase_cache[cycle]
            else:
                return
        zephyr_cycle = ZephyrCycle(
            name=cycle.name,
            cycle_start_date=ZephyrService.__format_date(cycle.start_date),
            cycle_end_date=ZephyrService.__format_date(cycle.end_date),
            release_id=self.__release_id,
        )
        zephyr_cycle = planning.create_cycle(self.__session, zephyr_cycle)
        self.__cycle_cache[cycle] = zephyr_cycle

    def create_phase_if_not_exist(self, cycle: Cycle, phase_root: RootFolder):
        cycle_phases = self.__phase_cache[cycle]
        if phase_root.name in cycle_phases:
            return
        zephyr_cycle = self.__cycle_cache[cycle]
        if phase_root not in self.__tc_tree_cache:
            raise KeyError(f'cannot find folder with name {phase_root.name}')
        tc_tree_node = self.__tc_tree_cache[phase_root]
        phase = planning.create_cycle_phase_from_test_case_tree(self.__session, zephyr_cycle, tc_tree_node)
        cycle_phases[phase_root.name] = phase

    def create_free_phase_if_not_exist(self, cycle: Cycle, phase_name: str, test_cases: list[TestCase]):
        _logger.info("creating phase %s in cycle %s with %s test case(s)", phase_name, cycle.name, len(test_cases))
        cycle_phases = self.__phase_cache[cycle]
        if phase_name not in cycle_phases:
            zephyr_cycle = self.__cycle_cache[cycle]
            phase = planning.create_cycle_phase_free_form(self.__session, zephyr_cycle, phase_name)
            cycle_phases[phase_name] = phase
        else:
            phase = cycle_phases[phase_name]

        def assign(assignments: list[TestCasesAssignment]):
            planning.assign_test_cases_to_phase(
                self.__session,
                phase,
                assignments,
                include_hierarchy=True,
            )

        tc_by_folder = group_tc_by_folder(test_cases)
        tc_assignments = list[TestCasesAssignment]()
        tcs_in_assignment: int = 0
        for folder, testcases in tc_by_folder.items():
            tc_tree_node = self.__tc_tree_cache[folder]
            tc_ids: dict[int, TestCase] = self.__collect_testcase_ids(folder, testcases)

            if tcs_in_assignment >= self.__batch_size:
                assign(tc_assignments)
                tc_assignments.clear()
                tcs_in_assignment = 0

            testcase_ids = list(tc_ids.keys())
            tc_assignments.append(
                TestCasesAssignment(
                    tree_id=tc_tree_node.id,
                    testcase_ids=testcase_ids,
                    is_exclusion=True,
                )
            )
            tcs_in_assignment += len(testcase_ids)

        if not tc_assignments:
            return

        assign(tc_assignments)

    def assign_test_cases_in_phase(self, cycle: Cycle, phase_name: str):
        _logger.info("assigning test cases from % phase in cycle %s to execution", phase_name, cycle.name)
        phases = self.__phase_cache[cycle]
        phase = phases[phase_name]
        assignment_tree = planning.get_assignment_tree(self.__session, phase)
        planning.assign_all_unassigned_to_user(self.__session, phase=phase,
                                               assignment_node=assignment_tree, user_id=self.__tester_id)

    def execution_statuses(self) -> list[ExecutionStatus]:
        return [s for s in self.__execution_statuses.values()]

    def execute_test_case(self, cycle: Cycle, status: ExecutionStatus, folder: Folder, tcs: list[TestCase]):
        _logger.info("executing %s test case(s) in folder %s from cycle %s with status %s",
                     len(tcs), folder.name, cycle.name, status.name)
        execution_id_by_testcase = self.__find_execution_ids_for_testcases(cycle, folder, tcs)
        if len(execution_id_by_testcase) != len(tcs):
            missing_test_cases = list(
                filter(
                    lambda t_case: t_case not in execution_id_by_testcase,
                    tcs,
                )
            )
            raise Exception(f'executions for some test cases were not found: {missing_test_cases}')

        self.__execute_by_ids(status, execution_id_by_testcase)

    def execute_all_test_cases(self, cycle: Cycle, status: ExecutionStatus, tcs_by_folder: dict[Folder, list[TestCase]]):
        _logger.info("executing test cases in %s folder(s) from cycle %s with status %s",
                     len(tcs_by_folder), cycle.name, status.name)
        tcs_by_id = dict[int, TestCase]()
        _logger.debug("collecting test cases ids")
        for folder, tc in tcs_by_folder.items():
            tcs_by_id.update(self.__collect_testcase_ids(folder, tc))

        _logger.debug("collecting execution ids")
        execution_id_by_testcase = self.__find_execution_ids(cycle, tcs_by_id)

        if len(execution_id_by_testcase) != len(tcs_by_id):
            missing_test_cases = list(
                filter(
                    lambda t_case: t_case not in execution_id_by_testcase,
                    tcs_by_id.values(),
                )
            )
            raise Exception(f'executions for some test cases were not found: {missing_test_cases}')

        self.__execute_by_ids(status, execution_id_by_testcase)

    def get_executions_for_test_cases(self, cycle: Cycle, folder: Folder,
                                      tcs: list[TestCase]) -> dict[TestCase, ExecutionStatus]:
        tcs_ids = self.__collect_testcase_ids(folder, tcs)
        return self.__get_executions(cycle, tcs_ids)

    def get_executions_for_cycle(self, cycle: Cycle) -> dict[TestCase, ExecutionStatus]:
        return self.__get_executions(cycle, self.__collect_all_testcase_ids())

    def attache_files_to_requirements(self, attachments: dict[Requirement, list[Path]]):
        _logger.info("attaching files to %s requirements", len(attachments))
        attachment_requests = list[AttachmentRequest]()
        for req, files in attachments.items():
            _logger.debug("uploading files %s for %s", files, req)
            upload_results = file_attachment.upload_files(self.__session,
                                                          file_attachment.ItemType.REQUIREMENT, files)
            zephyr_reqs = self.__req_cache[req.folder]
            zephyr_req = self.__find_req(req, zephyr_reqs)
            for file in files:
                upload_result = upload_results[file]
                attachment_requests.append(
                    AttachmentRequest(
                        name=upload_result.file_name,
                        content_type=upload_result.content_type,
                        item_type=file_attachment.ItemType.REQUIREMENT.http_type,
                        temp_path=upload_result.temp_file_path,
                        item_id=zephyr_req.id,
                    )
                )
            _logger.debug("attaching files to requirement: %s", attachment_requests)
            file_attachment.attach_files(self.__session, attachment_requests)
            attachment_requests.clear()

    def attache_files_to_testcases(self, attachments: dict[TestCase, list[Path]]):
        _logger.info("attaching files to %s test case(s)", len(attachments))
        attachment_requests = list[AttachmentRequest]()
        for tc, files in attachments.items():
            _logger.debug("uploading files %s for %s", files, tc)
            upload_results = file_attachment.upload_files(self.__session,
                                                          file_attachment.ItemType.TEST_CASE, files)
            zephyr_tcs = self.__tc_cache[tc.folder]
            zephyr_tc = self.__find_tc(tc, zephyr_tcs)
            for file in files:
                upload_result = upload_results[file]
                attachment_requests.append(
                    AttachmentRequest(
                        name=upload_result.file_name,
                        content_type=upload_result.content_type,
                        item_type=file_attachment.ItemType.TEST_CASE.http_type,
                        temp_path=upload_result.temp_file_path,
                        item_id=zephyr_tc.testcase.testcase_id,
                    )
                )
            _logger.debug("attaching files to testcases: %s", attachment_requests)
            file_attachment.attach_files(self.__session, attachment_requests)
            attachment_requests.clear()

    def attache_files_to_testcases_executions(self, cycle: Cycle, attachments: dict[TestCase, list[Path]]):
        _logger.info("attaching files to %s executions(s) in cycle %s", len(attachments), cycle.name)
        attachment_requests = list[AttachmentRequest]()
        tc_by_folder = group_tc_by_folder(list(attachments.keys()))

        tcs_by_id: dict[int, TestCase] = dict()

        for folder, tcs in tc_by_folder.items():
            """
            collect all the test case ids to make only one request for executions
            """
            tcs_by_id.update(self.__collect_testcase_ids(folder, tcs))

        execution_id_for_tc = self.__find_execution_ids(cycle, tcs_by_id)

        def attach_files(files_to_attach: list[AttachmentRequest]):
            file_attachment.attach_files(self.__session, files_to_attach)

        for tc, files in attachments.items():
            _logger.debug("uploading files %s for %s", files, tc)
            upload_results = file_attachment.upload_files(self.__session,
                                                          file_attachment.ItemType.RELEASE_TEST_SCHEDULE,
                                                          files)
            execution_id = execution_id_for_tc[tc]
            for file in files:
                upload_result = upload_results[file]
                attachment_requests.append(
                    AttachmentRequest(
                        name=upload_result.file_name,
                        content_type=upload_result.content_type,
                        item_type=file_attachment.ItemType.RELEASE_TEST_SCHEDULE.http_type,
                        temp_path=upload_result.temp_file_path,
                        item_id=execution_id,
                    )
                )

            if len(attachment_requests) >= self.__batch_size:
                _logger.info("attaching %s files to executions", len(attachment_requests))
                _logger.debug("attaching files to executions: %s", attachment_requests)
                attach_files(attachment_requests)
                attachment_requests.clear()

        if attachment_requests:
            attach_files(attachment_requests)

    def get_requirement_attachments(self, req: Requirement) -> list[AttachedFile]:
        zephyr_reqs = self.__req_cache[req.folder]
        zephyr_req = self.__find_req(req, zephyr_reqs)
        files = file_attachment.get_attached_files(
            self.__session,
            file_attachment.ItemType.REQUIREMENT,
            zephyr_req.id,
            is_link=False,
        )
        return self.__to_attached_files(files)

    def remove_requirement_attachment(self, req: Requirement, old_file: AttachedFile):
        file_attachment.delete_attachment(self.__session, int(old_file.id))

    def get_testcase_attachments(self, tc: TestCase) -> list[AttachedFile]:
        zephyrs_tcs = self.__tc_cache[tc.folder]
        zephyr_tc = self.__find_tc(tc, zephyrs_tcs)
        files = file_attachment.get_attached_files(
            self.__session,
            file_attachment.ItemType.TEST_CASE,
            zephyr_tc.testcase.testcase_id,
            is_link=False,
        )
        return self.__to_attached_files(files)

    def remove_testcase_attachment(self, tc: TestCase, old_file: AttachedFile):
        file_attachment.delete_attachment(self.__session, int(old_file.id))

    def get_execution_attachments(self, cycle: Cycle, tc: TestCase) -> list[AttachedFile]:
        exec_ids = self.__find_execution_ids_for_testcases(cycle, tc.folder, [tc])
        exec_id = exec_ids[tc]
        files = file_attachment.get_attached_files(
            self.__session,
            file_attachment.ItemType.RELEASE_TEST_SCHEDULE,
            exec_id,
            is_link=False,
        )
        return self.__to_attached_files(files)

    def remove_execution_attachment(self, cycle: Cycle, tc: TestCase, old_file: AttachedFile):
        file_attachment.delete_attachment(self.__session, int(old_file.id))

    def __execute_by_ids(self, status: ExecutionStatus, execution_id_by_testcase: dict[TestCase, int]):
        _logger.debug("executing test cases")

        def execute(ids: list[int]):
            planning.execute_test_cases(self.__session, status.id, self.__tester_id, ids)

        ids_to_execute = list[int]()
        for exec_id in execution_id_by_testcase.values():
            if len(ids_to_execute) >= self.__batch_size:
                execute(ids_to_execute)
                ids_to_execute.clear()
            ids_to_execute.append(exec_id)

        if ids_to_execute:
            execute(ids_to_execute)

    def __get_zephyr_testcases(self, folder):
        if folder in self.__tc_cache:
            zephyr_testcases = self.__tc_cache[folder]
        else:
            tc_folder = self.__tc_tree_cache[folder]
            zephyr_testcases = testcase.get_test_cases_for_node(self.__session, tc_folder)
            self.__tc_cache[folder].extend(zephyr_testcases)
        return zephyr_testcases

    def __get_executions(self, cycle: Cycle, tcs_by_id: dict[int, TestCase]) -> dict[TestCase, ExecutionStatus]:
        cycle_phases = self.__phase_cache[cycle]
        tcs_last_status = dict[TestCase, ExecutionStatus]()
        for phase_name, phase in cycle_phases.items():
            phase_executions = planning.get_executions_for_cycle_phase(self.__session, self.__release_id, phase)
            for execution in phase_executions:
                testcase_id = execution.tcr_tree_testcase.testcase.id
                if testcase_id not in tcs_by_id:
                    continue
                last_execution_result = execution.last_test_result
                if last_execution_result is None:
                    continue
                status = self.__execution_statuses.get(last_execution_result.execution_status, None)
                if status is None:
                    continue

                tc = tcs_by_id[testcase_id]
                tcs_last_status[tc] = status

        return tcs_last_status

    def __find_execution_ids_for_testcases(self, cycle: Cycle,
                                           folder: Folder, tcs: list[TestCase]) -> dict[TestCase, int]:
        tc_by_id: dict[int, TestCase] = self.__collect_testcase_ids(folder, tcs)
        return self.__find_execution_ids(cycle, tc_by_id)

    def __find_execution_ids(self, cycle: Cycle, tc_by_id: dict[int, TestCase]) -> dict[TestCase, int]:
        cycle_phases = self.__phase_cache[cycle]
        execution_id_by_testcase: dict[TestCase, int] = {}
        for phase_name, phase in cycle_phases.items():
            phase_executions = planning.get_executions_for_cycle_phase(self.__session, self.__release_id, phase)
            for execution in phase_executions:
                testcase_id = execution.tcr_tree_testcase.testcase.id
                if testcase_id not in tc_by_id:
                    continue
                tc = tc_by_id[testcase_id]
                execution_id_by_testcase[tc] = execution.id
        return execution_id_by_testcase

    def __collect_testcase_ids(self, folder: Folder, testcases: list[TestCase]) -> dict[int, TestCase]:
        known_tcs = self.__get_zephyr_testcases(folder)
        tc_ids = {}
        for tc in testcases:
            found = False
            for zephyr_tc in known_tcs:
                if zephyr_tc.testcase.name == tc.name and zephyr_tc.testcase.description == tc.description:
                    found = True
                    tc_ids[zephyr_tc.testcase.id] = tc
                    break

            if not found:
                raise KeyError(f'cannot find test case {tc}')
        return tc_ids

    def __collect_all_testcase_ids(self) -> dict[int, TestCase]:
        result = dict[int, TestCase]()
        for folder in self.__tc_tree_cache.keys():
            for tc in self.__get_zephyr_testcases(folder):
                result[tc.testcase.id] = ZephyrService.__zephyr_tc_to_model(tc, folder)
        return result

    def __load_existing_data(self):
        _logger.info("loading existing requirement folders")
        root_req_nodes = requirement_tree.get_requirement_tree_root_nodes(self.__session,
                                                                          self.__project_id, self.__release_id)
        for root_node in root_req_nodes:
            folder = RootFolder(root_node.name)
            node_id = root_node.id
            self.__load_req_node(folder, node_id)

        _logger.info("loading existing test case folders")
        root_tc_tree_nodes = testcase_tree.get_test_case_tree_root_nodes(self.__session, self.__release_id)
        for root_node in root_tc_tree_nodes:
            folder = RootFolder(root_node.name)
            self.__tc_tree_cache[folder] = root_node
            self.__load_tc_tree_node(folder, root_node)

        _logger.info("loading existing cycles")
        existing_cycles = planning.get_cycles_for_release(self.__session, self.__release_id)
        for zephyr_cycle in existing_cycles:
            cycle = Cycle(
                name=zephyr_cycle.name,
                start_date=ZephyrService.__parse_date(zephyr_cycle.cycle_start_date),
                end_date=ZephyrService.__parse_date(zephyr_cycle.cycle_end_date),
            )
            self.__cycle_cache[cycle] = zephyr_cycle
            for zephyr_phase in zephyr_cycle.cycle_phases:
                self.__phase_cache[cycle][zephyr_phase.name] = zephyr_phase
        _logger.info("loading existing data complete")

    def __load_tc_tree_node(self, folder: Folder, root_node: TestCaseTreeNode):
        sub_nodes = testcase_tree.get_test_case_tree_sub_nodes(self.__session, self.__release_id, root_node)
        for sub_node in sub_nodes:
            sub_folder = folder / sub_node.name
            self.__tc_tree_cache[sub_folder] = sub_node
            self.__load_tc_tree_node(sub_folder, sub_node)

    def __load_req_node(self, folder: Folder, node_id: int):
        node_details = requirement_tree.get_requirement_tree_node_details(self.__session, node_id)
        self.__req_tree_cache[folder] = node_details
        for sub_node in node_details.categories:
            sub_folder = folder / sub_node.name
            self.__load_req_node(sub_folder, sub_node.id)

    def __load_execution_statuses(self) -> list[ExecutionStatus]:
        zephyr_prefs = preferences.get_system_preferences(self.__session)
        for pref in zephyr_prefs:
            if pref.name == _EXECUTION_STATUSES_PREFERENCE_NAME:
                zephyr_statuses = json.loads(pref.value)
                statuses = []
                for status in zephyr_statuses:
                    statuses.append(
                        ExecutionStatus(
                            name=status['value'],
                            id=str(status['id']),
                        )
                    )
                return statuses
        raise Exception(f'could not found {_EXECUTION_STATUSES_PREFERENCE_NAME} preference in the list')

    @staticmethod
    def __zephyr_tc_to_model(zephyr_tc_in_tree: TestCaseInTree, folder: Folder) -> TestCase:
        return TestCase(name=zephyr_tc_in_tree.testcase.name,
                        description=zephyr_tc_in_tree.testcase.description, folder=folder)

    @staticmethod
    def __zephyr_req_to_model(zephyr_req: ZephyrRequirement, folder: Folder) -> Requirement:
        return Requirement(name=zephyr_req.name, description=zephyr_req.details, folder=folder)

    @staticmethod
    def __to_model_tcs(folder: Folder, zephyr_testcases: list[TestCaseInTree]) -> list[TestCase]:
        return list(map(lambda tc: ZephyrService.__zephyr_tc_to_model(tc, folder), zephyr_testcases))

    @staticmethod
    def __to_model_req(folder: Folder, zephyr_reqs: list[ZephyrRequirement]) -> list[Requirement]:
        return list(map(lambda req: ZephyrService.__zephyr_req_to_model(req, folder), zephyr_reqs))

    @staticmethod
    def __format_date(value: date) -> str:
        return value.strftime('%m/%d/%Y')

    @staticmethod
    def __parse_date(date_str: str) -> date:
        return datetime.strptime(date_str, '%m/%d/%Y').date()

    @staticmethod
    def __find_req(req: Requirement, requirements: list[ZephyrRequirement]) -> ZephyrRequirement:
        for zephyr_req in requirements:
            if zephyr_req.name == req.name and zephyr_req.details == req.description:
                return zephyr_req
        raise KeyError(f'cannot find requirement {req}')

    @staticmethod
    def __find_tc(tc: TestCase, testcases: list[TestCaseInTree]) -> TestCaseInTree:
        for zephyr_tc in testcases:
            if zephyr_tc.testcase.name == tc.name and zephyr_tc.testcase.description == tc.description:
                return zephyr_tc
        raise KeyError(f'cannot find testcase {tc}')

    @staticmethod
    def __to_attached_files(attachments: list[Attachment]) -> list[AttachedFile]:
        return list(AttachedFile(id=str(f.id), name=f.name) for f in attachments)

    @staticmethod
    def __to_dict(executions: list[ExecutionStatus]) -> dict[str, ExecutionStatus]:
        return {status.id: status for status in executions}
