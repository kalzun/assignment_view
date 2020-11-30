import pytest
from pathlib import Path
from ..group_sorter import find_group, get_path_file_of_student, unzip_file, copy_files_to_folder, get_submission_name, get_newest_file

group4 = {'tiw012', 'day014', 'bbr044', 'jda047', 'mfl049', 'duj015', 'hkl018', 'skn016', 'qix014', 'kkr038', 'hni030', 'pso026', 'lsv008', 'ltv010', 'cve020', 'geq014', 'foe011'}

@pytest.mark.skip(reason="Refactored to a new copy method")
def test_find_one_group():
    group4 = {'tiw012', 'day014', 'bbr044', 'jda047', 'mfl049', 'duj015', 'hkl018', 'skn016', 'qix014', 'kkr038', 'hni030', 'pso026', 'lsv008', 'ltv010', 'cve020', 'geq014', 'foe011'}
    assert find_group(4) == group4
    # build_group_overview() 

@pytest.mark.skip(reason="Refactored to a new copy method")
def test_get_path_file_of_student():
    studentcode = 'kog002'
    assert studentcode in get_path_file_of_student(studentcode).name

@pytest.mark.skip(reason="Skipping due to I/O operations")
def test_unzipping_and_sorting():
    fn = '1599122728_293__INFO132-Temaoppgave_1_submissions.zip'
    assert unzip_file(fn) == False

@pytest.mark.skip(reason="Refactored to a new copy method")
def test_copy_a_group_of_files():
    assert copy_files_to_folder(group4) == False


@pytest.mark.skip(reason="Refactored to a new copy method")
def test_get_subname():
    fn = '1599122728_293__INFO132-Temaoppgave_1_submissions.zip'
    assert get_submission_name(fn) == 'Temaoppgave_1'

@pytest.mark.skip(reason="Refactored to a new copy method")
def test_get_subname_course_not_found():
    fn = '1599122728_293__INFO282-Temaoppgave_1_submissions.zip'
    assert get_submission_name(fn) == fn.rstrip('.zip')

@pytest.mark.skip(reason="Refactored to a new copy method")
def test_get_subname_submission_not_found():
    fn = '1599122728_293__INFO282-Temaoppgave_1.zip'
    assert get_submission_name(fn) == fn.rstrip('.zip')

@pytest.mark.skip(reason="Refactored to a new copy method")
def test_get_zips():
    assert len(get_zips()) == 1

@pytest.mark.skip(reason="Refactored to a new copy method")
def test_two_digits_group():
    '''
    Group 1 cannot get overloaded with people from group 10, 11..
    '''
    group4 = {'tiw012', 'day014', 'bbr044', 'jda047', 'mfl049', 'duj015', 'hkl018', 'skn016', 'qix014', 'kkr038', 'hni030', 'pso026', 'lsv008', 'ltv010', 'cve020', 'geq014', 'foe011'}
    assert find_group(4) == group4


@pytest.mark.skip(reason="Refactored to a new copy method")
def test_handins_with_no_studentcode():
    assert get_path_file_of_student('duq013') == False


def test_newest_file():
    from_folder = Path('zips')
    assert get_newest_file(from_folder) == 'some'
