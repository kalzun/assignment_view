import sqlite3

import pytest


@pytest.fixture
def session_test():
    connection = sqlite3.connect(":memory:")
    db_session = connection.cursor()
    yield db_session
    connection.close()


@pytest.fixture
def setup_test_db(session_test):
    session_test.execute(
        """CREATE TABLE numbers
                          (number text, existing boolean)"""
    )
    session_test.execute('INSERT INTO numbers VALUES ("321", 1)')
    session_test.connection.commit()


@pytest.mark.usefixtures("setup_test_db")
def test_get(session_test):
    assert session_test.execute("SELECT * FROM numbers").fetchall() == [("321", 1)]


@pytest.fixture
def session_cache():
    connection = sqlite3.connect(":memory:")
    db_session = connection.cursor()
    yield db_session
    connection.close()


@pytest.fixture
def setup_small_db(session_cache):
    session_cache.execute(
        """CREATE TABLE small
        (latest_fetch INTEGER)"""
    )

    session_cache.connection.commit()
    session_cache.execute("INSERT submissions VALUES(submission_id=:sub", {"sub": 123})
    session_cache.connection

    assert 23 == session_cache.execute("SELECT * from submissions").fetchall()


@pytest.fixture
def setup_db(session_cache):
    """Setup db as done in canvas api
    three tables (attachments, info, submissions)
    """
    session_cache.execute(
        """CREATE TABLE info
        (latest_fetch INTEGER)"""
    )

    # Table for submissions -
    session_cache.execute(
        """CREATE TABLE submissions
        (submission_id INTEGER,
        assignment_id INTEGER,
        assignment_name TEXT,
        grader_id INTEGER,
        current_grade TEXT,
        current_grader TEXT,
        group_nr INTEGER,
        sis_user_id TEXT,
        user_name TEXT,
        user_id INTEGER
        )"""
    )

    # Another table for attachments - for multiple attachments
    session_cache.execute(
        """CREATE TABLE attachments
        (displayname TEXT,
        filename TEXT,
        modified_at REAL,
        code BLOB,
        submission_id INTEGER,
        FOREIGN KEY(submission_id) REFERENCES submissions(submission_id)
        )"""
    )
    session_cache.connection.commit()
    # Insert into submissions
    submission = {
        "submission_id": 123,
        "assignment_id": 456,
        "assignment_name": "Temaoppgave 1",
        "grader_id": 999,
        "current_grade": "complete",
        "current_grader": "Black Knight",
        "group_nr": 1,
        "sis_user_id": "mir111",
        "user_name": "Brian Cohen",
        "user_id": 444555,
    }

    session_cache.execute(
        """
        INSERT INTO submissions VALUES (
        :submission_id,
        :assignment_id,
        :assignment_name,
        :grader_id,
        :current_grade,
        :current_grader,
        :group_nr,
        :sis_user_id,
        :user_name,
        :user_id)""",
        submission,
    )
    session_cache.connection.commit()


#### ONLY DB TESTS: ###


@pytest.mark.skip("After refactoring, needs update")
@pytest.mark.usefixtures("setup_db")
def test_basic(session_cache):

    submission = {
        "submission_id": 123,
        "assignment_id": 456,
        "assignment_name": "Temaoppgave 1",
        "grader_id": 999,
        "current_grade": "complete",
        "current_grader": "Black Knight",
        "group_nr": 1,
        "sis_user_id": "mir111",
        "user_name": "Brian Cohen",
        "user_id": 444555,
    }

    assert session_cache.execute("SELECT * FROM submissions").fetchall() == values


@pytest.mark.skip("After refactoring, needs update")
@pytest.mark.usefixtures("setup_db")
def test_basic_two(session_cache):
    values = [
        (
            1,
            "mir101",
            123,
            "Temaoppgave_1",
            4040,
            "Landrok Kire",
            431,
            "complete",
            "Saerdna Kire",
            "1243_mir101.py",
            "12341_mir101.py",
            "https://mitt.uib.no/files/3086939/download?download_frd=1&verifier=OD3PPfKOhdoWH6a81wUem5kzTrDEr",
        )
    ]
    assert session_cache.execute("SELECT * FROM cache").fetchall() == values


@pytest.mark.skip("After refactoring, needs update")
@pytest.mark.usefixtures("setup_db")
def test_dict_values_store(session_cache):
    specific_data = {
        "group": int("2"),
        "sis_user_id": "rim101",
        "assignment_id": int("321"),
        "assignment_name": "Temaoppgave_1",
        "user_id": int("123"),
        "user_name": "Larsen_Erik",
        "grader_id": int("333"),
        "current_grade": "complete",
        "current_grader": "Fritz_Larsen",
        "filename": "rim101_t2.py",
        "display_name": "rim101_t2.py",
        "url": "https://mitt.uib.no/files/3086939/download?download_frd=1&verifier=OD3PPfKOhdoWH6a81wUem5kzTrDErL3",
    }
    print([tuple(elem for elem in (specific_data.values()))])

    session_cache.executemany(
        """
        INSERT INTO cache VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        [tuple(elem for elem in (specific_data.values()))],
    )
    session_cache.connection.commit()
    assert (
        session_cache.execute("SELECT * FROM cache").fetchall()
        == specific_data.values()
    )


@pytest.mark.skip("After refactoring, needs update")
@pytest.mark.usefixtures("setup_db")
def test_list_tuples_sql(session_cache):
    all_rows = []
    all_rows.append(
        (
            int("2"),
            "rim101",
            int("321"),
            "Temaoppgave_1",
            int("123"),
            "Larsen_Erik",
            int("333"),
            "complete",
            "Fritz_Larsen",
            "rim101_t2.py",
            "rim101_t2.py",
            "https://mitt.uib.no/files/3086939/download?download_frd=1&verifier=OD3PPfKOhdoWH6a81wUem5kzTrDErL3",
        )
    )
    print(all_rows)

    session_cache.executemany(
        """
        INSERT INTO cache VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        all_rows,
    )
    session_cache.connection.commit()
    assert session_cache.execute("SELECT * FROM cache").fetchall() == all_rows


@pytest.mark.skip("copied from canvas")
def test_select():
    with closing(sqlite3.connect(DB)) as conn:
        with closing(conn.cursor()) as cursor:
            result = cursor.execute("SELECT * FROM info").fetchone()
            print(result[0])


@pytest.mark.skip("copied from canvas")
def test_inserts():
    with closing(sqlite3.connect(DB)) as conn:
        with closing(conn.cursor()) as cursor:
            resp = req.get(
                "https://mitt.uib.no/files/3140327/download?download_frd=1&verifier=1Tvm0lGJPA3upziJK5kZpxsYIbXvKWkRH6brdm5i",
                headers=headers,
            )
            breakpoint()
            print(type(resp))
            logger.debug(resp)

            values = [
                (
                    1,
                    "mir101",
                    123,
                    "Temaoppgave_1",
                    4040,
                    "Landrok Kire",
                    431,
                    "complete",
                    "Saerdna Kire",
                    "1243_mir101.py",
                    "12341_mir101.py",
                    resp.text,
                )
            ]
            cursor.executemany(
                """
                INSERT INTO cache VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                values,
            )
            rows = cursor.execute("SELECT * FROM cache").fetchall()
            print(rows)
