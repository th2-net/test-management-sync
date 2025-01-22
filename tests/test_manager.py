import unittest
from pathlib import Path
from unittest.mock import MagicMock

from test_management_sync.manager import Manager
from test_management_sync.model import Requirement, RootFolder, TestCase as ModelTestCase
from test_management_sync.service import Service


def test_create_requirements():
    service_mock: Service = MagicMock()
    with Manager(service_mock) as manager:
        service_mock.get_requirements.return_value = []
        requirement = Requirement(name='Req 1', description='Descr 1', folder=RootFolder('A') / 'B' / 'C')
        manager.create_requirements(
            requirements=[requirement]
        )
        service_mock.get_requirements.assert_called_with(
            RootFolder('A') / 'B' / 'C'
        )
        service_mock.create_requirements.assert_called_with(
            RootFolder('A') / 'B' / 'C',
            [requirement]
        )
    service_mock.close.assert_called_once()


def test_does_not_create_requirements_if_exists():
    service_mock: Service = MagicMock()
    with Manager(service_mock) as manager:
        requirement = Requirement(name='Req 1', description='Descr 1', folder=RootFolder('A') / 'B' / 'C')
        service_mock.get_requirements.return_value = [requirement]
        manager.create_requirements(
            requirements=[requirement]
        )
        service_mock.get_requirements.assert_called_with(
            RootFolder('A') / 'B' / 'C'
        )
        service_mock.create_requirements.assert_not_called()
    service_mock.close.assert_called_once()


def test_does_not_create_requirements_if_exists_with_spaces_in_folder_and_name():
    service_mock: Service = MagicMock()
    with Manager(service_mock) as manager:
        requirement = Requirement(name='Req 1 ', description='Descr 1 ', folder=RootFolder('A ') / 'B ' / 'C ')
        service_mock.get_requirements.return_value = [
            Requirement(name='Req 1', description='Descr 1', folder=RootFolder('A') / 'B' / 'C')
        ]
        manager.create_requirements(
            requirements=[requirement]
        )
        service_mock.get_requirements.assert_called_with(
            RootFolder('A') / 'B' / 'C'
        )
        service_mock.create_requirements.assert_not_called()
    service_mock.close.assert_called_once()


def test_removes_old_requirements_for_folder():
    service_mock: Service = MagicMock()
    with Manager(service_mock) as manager:
        requirement = Requirement(name='Req 1', description='Descr 1', folder=RootFolder('A') / 'B' / 'C')
        manager.create_requirements(
            requirements=[requirement],
            force=True,
        )
        service_mock.get_requirements.assert_not_called()
        service_mock.remove_requirements.assert_called_with(
            RootFolder('A') / 'B' / 'C'
        )
        service_mock.create_requirements.assert_called_with(
            RootFolder('A') / 'B' / 'C',
            [requirement]
        )
    service_mock.close.assert_called_once()


def test_creates_test_case():
    service_mock: Service = MagicMock()
    with Manager(service_mock) as manager:
        testcase = ModelTestCase(name='TC 1', description='Descr 1', folder=RootFolder('A') / 'B' / 'C')
        service_mock.get_testcases.return_value = []
        manager.create_test_cases(
            test_cases=[testcase],
        )
        service_mock.get_testcases.assert_called_with(
            RootFolder('A') / 'B' / 'C'
        )
        service_mock.create_testcases.assert_called_with(
            RootFolder('A') / 'B' / 'C',
            [testcase]
        )
    service_mock.close.assert_called_once()


def test_does_not_create_test_case_if_exists():
    service_mock: Service = MagicMock()
    with Manager(service_mock) as manager:
        testcase = ModelTestCase(name='TC 1', description='Descr 1', folder=RootFolder('A') / 'B' / 'C')
        service_mock.get_testcases.return_value = [testcase]
        manager.create_test_cases(
            test_cases=[testcase],
        )
        service_mock.get_testcases.assert_called_with(
            RootFolder('A') / 'B' / 'C'
        )
        service_mock.create_testcases.assert_not_called()
    service_mock.close.assert_called_once()


def test_does_not_create_test_case_if_exists_with_spaces_in_folder_and_name():
    service_mock: Service = MagicMock()
    with Manager(service_mock) as manager:
        testcase = ModelTestCase(name='TC 1 ', description='Descr 1 ', folder=RootFolder('A ') / 'B ' / 'C ')
        service_mock.get_testcases.return_value = [
            ModelTestCase(name='TC 1', description='Descr 1', folder=RootFolder('A') / 'B' / 'C')
        ]
        manager.create_test_cases(
            test_cases=[testcase],
        )
        service_mock.get_testcases.assert_called_with(
            RootFolder('A') / 'B' / 'C'
        )
        service_mock.create_testcases.assert_not_called()
    service_mock.close.assert_called_once()


def test_removes_old_test_cases():
    service_mock: Service = MagicMock()
    with Manager(service_mock) as manager:
        testcase = ModelTestCase(name='TC 1', description='Descr 1', folder=RootFolder('A') / 'B' / 'C')
        service_mock.get_testcases.return_value = [testcase]
        manager.create_test_cases(
            test_cases=[testcase],
            force=True,
        )
        service_mock.get_testcases.assert_not_called()
        service_mock.remove_testcases.assert_called_with(
            RootFolder('A') / 'B' / 'C',
        )
        service_mock.create_testcases.assert_called_with(
            RootFolder('A') / 'B' / 'C',
            [testcase]
        )
    service_mock.close.assert_called_once()


class InvalidUploadTestCase(unittest.TestCase):

    def test_raises_error_if_duplicated_files_provided_for_one_test_case(self):
        service_mock: Service = MagicMock()
        with Manager(service_mock) as manager:
            testcase = ModelTestCase(name='TC 1', description='Descr 1', folder=RootFolder('A') / 'B' / 'C')
            with self.assertRaises(ValueError) as context:
                manager.attach_files_to_testcases(
                    attachments={
                        testcase: [Path("test1.txt"), Path("test2.txt"), Path("test1.txt")]
                    }
                )
            self.assertEqual("duplicated files in attachments: ['test1.txt']", str(context.exception))

    def test_no_error_if_all_paths_are_unique(self):
        service_mock: Service = MagicMock()
        with Manager(service_mock) as manager:
            testcase = ModelTestCase(name='TC 1', description='Descr 1', folder=RootFolder('A') / 'B' / 'C')
            attachments = {
                testcase: [Path("test1.txt"), Path("test2.txt")]
            }
            manager.attach_files_to_testcases(
                attachments=attachments
            )
            service_mock.attache_files_to_testcases.assert_called_with(
                attachments
            )
