from dataclasses import dataclass, field
from datetime import date


@dataclass(unsafe_hash=True, frozen=True)
class TestCase:
    name: str
    folder: 'Folder'
    description: str = field(default='')

    def __post_init__(self):
        object.__setattr__(self, 'name', self.name.strip())
        if self.description is not None:
            object.__setattr__(self, 'description', self.description.strip())


@dataclass(unsafe_hash=True, frozen=True)
class Requirement:
    name: str
    folder: 'Folder'
    description: str = field(default='')

    def __post_init__(self):
        object.__setattr__(self, 'name', self.name.strip())
        if self.description is not None:
            object.__setattr__(self, 'description', self.description.strip())


@dataclass(unsafe_hash=True, frozen=True)
class Cycle:
    name: str
    start_date: date
    end_date: date

    def __post_init__(self):
        object.__setattr__(self, 'name', self.name.strip())
        if self.start_date > self.end_date:
            raise Exception(f'start date {self.start_date} must be less or equal to end date {self.end_date}')


@dataclass
class ExecutionStatus:
    id: str
    name: str


@dataclass(unsafe_hash=True, frozen=True)
class Folder:
    name: str
    parent: 'Folder' = field(default=None)

    def __post_init__(self):
        object.__setattr__(self, 'name', self.name.strip())

    def __truediv__(self, other: str) -> 'Folder':
        return Folder(name=other, parent=self)


@dataclass(init=False, unsafe_hash=True, frozen=True)
class RootFolder(Folder):
    name: str

    def __init__(self, name: str):
        super(RootFolder, self).__init__(name.strip(), None)


@dataclass(unsafe_hash=True, frozen=True)
class AttachedFile:
    id: str
    name: str
