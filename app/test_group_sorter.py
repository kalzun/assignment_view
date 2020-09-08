import pytest
import group_sorter

group4 = {'tiw012', 'day014', 'bbr044', 'jda047', 'mfl049', 'duj015', 'hkl018', 'skn016', 'qix014', 'kkr038', 'hni030', 'pso026', 'lsv008', 'ltv010', 'cve020', 'geq014', 'foe011'}

@pytest.mark.skip(reason="Refactored to a new copy method")
def test_find_one_group():
    group4 = {'tiw012', 'day014', 'bbr044', 'jda047', 'mfl049', 'duj015', 'hkl018', 'skn016', 'qix014', 'kkr038', 'hni030', 'pso026', 'lsv008', 'ltv010', 'cve020', 'geq014', 'foe011'}
    assert group_sorter.find_group(4) == group4
    # group_sorter.build_group_overview() 

@pytest.mark.skip(reason="Refactored to a new copy method")
def test_get_path_file_of_student():
    studentcode = 'kog002'
    assert studentcode in group_sorter.get_path_file_of_student(studentcode).name

@pytest.mark.skip(reason="Skipping due to I/O operations")
def test_unzipping_and_sorting():
    fn = '1599122728_293__INFO132-Temaoppgave_1_submissions.zip'
    assert group_sorter.unzip_file(fn) == False

@pytest.mark.skip(reason="Refactored to a new copy method")
def test_copy_a_group_of_files():
    assert group_sorter.copy_files_to_folder(group4) == False

def test_get_subname():
    fn = '1599122728_293__INFO132-Temaoppgave_1_submissions.zip'
    assert group_sorter.get_submission_name(fn) == 'Temaoppgave_1'

def test_get_subname_course_not_found():
    fn = '1599122728_293__INFO282-Temaoppgave_1_submissions.zip'
    assert group_sorter.get_submission_name(fn) == fn.rstrip('.zip')

def test_get_subname_submission_not_found():
    fn = '1599122728_293__INFO282-Temaoppgave_1.zip'
    assert group_sorter.get_submission_name(fn) == fn.rstrip('.zip')

def test_get_zips():
    assert len(group_sorter.get_zips()) == 1

def test_two_digits_group():
    '''
    Group 1 cannot get overloaded with people from group 10, 11..
    '''
    group4 = {'tiw012', 'day014', 'bbr044', 'jda047', 'mfl049', 'duj015', 'hkl018', 'skn016', 'qix014', 'kkr038', 'hni030', 'pso026', 'lsv008', 'ltv010', 'cve020', 'geq014', 'foe011'}
    assert group_sorter.find_group(4) == group4


def test_handins_with_no_studentcode():
    assert group_sorter.get_path_file_of_student('duq013') == False
