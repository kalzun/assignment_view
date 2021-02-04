import pytest
from dataclasses import dataclass
from pathlib import Path
import app.group_sorter as group_sorter
from ..group_sorter import (
    find_group,
    get_path_file_of_student,
    unzip_file,
    copy_files_to_folder,
    get_submission_name,
    get_newest_file,
    build_group_overview,
)

group4 = {
    "tiw012",
    "day014",
    "bbr044",
    "jda047",
    "mfl049",
    "duj015",
    "hkl018",
    "skn016",
    "qix014",
    "kkr038",
    "hni030",
    "pso026",
    "lsv008",
    "ltv010",
    "cve020",
    "geq014",
    "foe011",
}


@pytest.mark.skip(reason="Refactored to a new copy method")
def test_find_one_group():
    group4 = {
        "tiw012",
        "day014",
        "bbr044",
        "jda047",
        "mfl049",
        "duj015",
        "hkl018",
        "skn016",
        "qix014",
        "kkr038",
        "hni030",
        "pso026",
        "lsv008",
        "ltv010",
        "cve020",
        "geq014",
        "foe011",
    }
    assert find_group(4) == group4
    # build_group_overview()


@pytest.mark.skip(reason="Refactored to a new copy method")
def test_get_path_file_of_student():
    studentcode = "kog002"
    assert studentcode in get_path_file_of_student(studentcode).name


@pytest.mark.skip(reason="Skipping due to I/O operations")
def test_unzipping_and_sorting():
    fn = "1599122728_293__INFO132-Temaoppgave_1_submissions.zip"
    assert unzip_file(fn) == False


@pytest.mark.skip(reason="Refactored to a new copy method")
def test_copy_a_group_of_files():
    assert copy_files_to_folder(group4) == False


@pytest.mark.skip(reason="Refactored to a new copy method")
def test_get_subname():
    fn = "1599122728_293__INFO132-Temaoppgave_1_submissions.zip"
    assert get_submission_name(fn) == "Temaoppgave_1"


@pytest.mark.skip(reason="Refactored to a new copy method")
def test_get_subname_course_not_found():
    fn = "1599122728_293__INFO282-Temaoppgave_1_submissions.zip"
    assert get_submission_name(fn) == fn.rstrip(".zip")


@pytest.mark.skip(reason="Refactored to a new copy method")
def test_get_subname_submission_not_found():
    fn = "1599122728_293__INFO282-Temaoppgave_1.zip"
    assert get_submission_name(fn) == fn.rstrip(".zip")


@pytest.mark.skip(reason="Refactored to a new copy method")
def test_get_zips():
    assert len(get_zips()) == 1


@pytest.mark.skip(reason="Refactored to a new copy method")
def test_two_digits_group():
    """
    Group 1 cannot get overloaded with people from group 10, 11..
    """
    group4 = {
        "tiw012",
        "day014",
        "bbr044",
        "jda047",
        "mfl049",
        "duj015",
        "hkl018",
        "skn016",
        "qix014",
        "kkr038",
        "hni030",
        "pso026",
        "lsv008",
        "ltv010",
        "cve020",
        "geq014",
        "foe011",
    }
    assert find_group(4) == group4


@pytest.mark.skip(reason="Refactored to a new copy method")
def test_handins_with_no_studentcode():
    assert get_path_file_of_student("duq013") == False


def test_get_submission_name():
    # '1599224423_837__DATA110-Temaoppgave_1_submissions.zip'
    assert (
        get_submission_name("1599224423_837__DATA110-Temaoppgave_1_submissions.zip")
        == "Temaoppgave_1"
    )


def test_get_submission_name_different_course(monkeypatch):
    # '1599224423_837__INFO132-Temaoppgave_1_submissions.zip'
    monkeypatch.setitem(group_sorter.CONFIG, "COURSECODE", "INFO132")
    assert (
        get_submission_name("1599224423_837__INFO132-Temaoppgave_1_submissions.zip")
        == "Temaoppgave_1"
    )


@pytest.mark.xfail
def test_get_submission_name_no_match():
    # '1599224423_837__INFO132-Temaoppgave_1_submissions.zip'
    assert get_submission_name("-Temaoppgave_1_submissions.zip") == "Temaoppgave_1"


@dataclass
class MockPath:
    suffix: str = ".zip"
    st_mtime: float = 1
    name: str = "woaw"

    def stat(self):
        return self


class MockPathIterable:
    items = [MockPath(".zip", 2, "noes"), MockPath(st_mtime=3, name="yes")]

    def __getitem__(self, index):
        return self.items[index]


def test_newest_file(monkeypatch):
    # Monkeypatching for the fun of it, and teaching!
    # Patching iterdir-method, to return a mock list of mockpaths

    def mock_iterdir(*args):
        return MockPathIterable()

    monkeypatch.setattr(Path, "iterdir", mock_iterdir)

    from_folder = Path("zips")
    assert get_newest_file(from_folder) == "yes"


def test_build_group_overview(monkeypatch):
    def mock_find_group(*args):
        # A set of Studentcodes
        return set((1, 2))

    monkeypatch.setitem(group_sorter.CONFIG, "N_OF_GROUPS", 4)
    monkeypatch.setattr(group_sorter.Groups, "all", {})
    monkeypatch.setattr(group_sorter, "find_group", mock_find_group)

    # assert group_sorter.GROUPS == {0: {1,2}, 1: {1, 2}, 2: {1, 2}, 3: {1, 2}, 4: {1, 2}}
    assert build_group_overview() == {1: {1, 2}, 2: {1, 2}, 3: {1, 2}, 4: {1, 2}}

def test_build_group_overview_two_groups(monkeypatch):
    def mock_find_group(*args):
        # A set of Studentcodes
        if args[0] == 2:
            return set((3, 4))
        else:
            return set((1, 2))

    monkeypatch.setitem(group_sorter.CONFIG, "N_OF_GROUPS", 2)
    monkeypatch.setattr(group_sorter.Groups, "all", {})
    monkeypatch.setattr(group_sorter, "find_group", mock_find_group)

    assert build_group_overview() == {1: {1, 2}, 2: {3, 4}}

def test_build_group_overview_realcodes(monkeypatch):
    def mock_find_group(*args):
        # A set of Studentcodes
        if args[0] == 2:
            return set((3, 4))
        else:
            return set(('mir010','mir010', 'mir011'))

    monkeypatch.setitem(group_sorter.CONFIG, "N_OF_GROUPS", 2)
    monkeypatch.setattr(group_sorter.Groups, "all", {})
    monkeypatch.setattr(group_sorter, "find_group", mock_find_group)

    assert build_group_overview() == {1: {'mir010', 'mir011'}, 2: {3, 4}}



