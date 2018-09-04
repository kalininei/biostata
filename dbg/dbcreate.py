import sqlite3

dbname = "test.db"


connection = sqlite3.connect(dbname)
cursor = connection.cursor()

# data table list
cursor.execute("""
    CREATE TABLE _DATA_TABLES_ (
        name TEXT PRIMARY KEY,
        comment TEXT)
""")
pst = [
        ("tab1", "some comment"),
        ("tab2", "some comment"),
]
cursor.executemany("""
    INSERT INTO _DATA_TABLES_ (name, comment) VALUES (?, ?)
""", pst)

cursor.execute("SELECT * from _DATA_TABLES_")
print(cursor.fetchall())


# dictionary list
cursor.execute("""
    CREATE TABLE _DICTIONARIES_ (
        name TEXT PRIMARY KEY,
        type TEXT NOT NULL,
        comment TEXT
    )
""")
pst = [
    ("biochar type", "ENUM", None),
    ("fertilizer", "BOOL", None),
    ("has biochar", "BOOL", None),
    ("dict_ABC", "ENUM", None),
    ("dict_yesno", "BOOL", None),
    ("dict_truefalse", "BOOL", None),
    ("dict_01", "BOOL", None)
]

cursor.executemany("""
    INSERT INTO _DICTIONARIES_ (name, type, comment)
        VALUES (?,?,?)
""", pst)

# data types descriptions
# biochar type
cursor.execute("""
    CREATE TABLE "_DICTIONARY biochar type" (
        key INTEGER PRIMARY KEY,
        value TEXT UNIQUE,
        comment TEXT
    )
""")
pst = [
    (0, "no", "no biochar"),
    (1, "b4p", "biochar 400C, powder"),
    (2, "b5p", "biochar 500C, powder"),
    (3, "b4g", "biochar 400C, granular"),
    (4, "b5g", "biochar 500C, granular"),
]
cursor.executemany("""
    INSERT INTO "_DICTIONARY biochar type" (key, value, comment) VALUES (?,?,?)
""", pst)

# fertilizer
cursor.execute("""
    CREATE TABLE "_DICTIONARY fertilizer"(
        key INTEGER PRIMARY KEY,
        value TEXT UNIQUE,
        comment TEXT
    )
""")
pst = [
    (0, "noF", None),
    (1, "F", None)
]
cursor.executemany("""
    INSERT INTO "_DICTIONARY fertilizer"(key, value, comment) VALUES (?,?,?)
""", pst)

# has biochar
cursor.execute("""
    CREATE TABLE "_DICTIONARY has biochar"(
        key INTEGER PRIMARY KEY,
        value TEXT UNIQUE,
        comment TEXT
    )
""")
pst = [
    (0, "noB", None),
    (1, "B", None)
]
cursor.executemany("""
    INSERT INTO "_DICTIONARY has biochar"(key, value, comment) VALUES (?,?,?)
""", pst)

# 1/0
cursor.execute("""
    CREATE TABLE "_DICTIONARY dict_01"(
        key INTEGER PRIMARY KEY,
        value TEXT UNIQUE,
        comment TEXT
    )
""")
pst = [
    (0, "0"),
    (1, "1")
]
cursor.executemany("""
    INSERT INTO "_DICTIONARY dict_01"(key, value) VALUES (?,?)
""", pst)

# yes/no
cursor.execute("""
    CREATE TABLE "_DICTIONARY dict_yesno"(
        key INTEGER PRIMARY KEY,
        value TEXT UNIQUE,
        comment TEXT
    )
""")
pst = [
    (0, "no"),
    (1, "yes")
]
cursor.executemany("""
    INSERT INTO "_DICTIONARY dict_yesno"(key, value) VALUES (?,?)
""", pst)

# true/false
cursor.execute("""
    CREATE TABLE "_DICTIONARY dict_truefalse"(
        key INTEGER PRIMARY KEY,
        value TEXT UNIQUE,
        comment TEXT
    )
""")
pst = [
    (0, "false"),
    (1, "true")
]
cursor.executemany("""
    INSERT INTO "_DICTIONARY dict_truefalse"(key, value) VALUES (?,?)
""", pst)

# abc
cursor.execute("""
    CREATE TABLE "_DICTIONARY dict_ABC"(
        key INTEGER PRIMARY KEY,
        value TEXT UNIQUE,
        comment TEXT
    )
""")
pst = [(i, a) for i, a in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ")]
cursor.executemany("""
    INSERT INTO "_DICTIONARY dict_ABC"(key, value) VALUES (?,?)
""", pst)


# data table
cursor.execute("""
    CREATE TABLE "_COLINFO tab1"(
        colname TEXT PRIMARY KEY,
        type TEXT,
        dict TEXT,
        colgroup TEXT,
        dim TEXT,
        shortname TEXT UNIQUE)
    """)
pst = [
    ("biochar type", "ENUM", "biochar type", None, None, "Tp"),
    ("sample day", "INT", None, None, None, "sD"),
    ("sample hour", "INT", None, None, None, "sH"),
    ("fertilizer", "BOOL", "fertilizer", None, None, "F"),
    ("result 1", "REAL", None, None, "m", "r1"),
    ("result 2", "REAL", None, None, "kg", "r2"),
    ("result 3", "REAL", None, None, "m/s", "r3")]
cursor.executemany("""
    INSERT INTO "_COLINFO tab1"(colname, type, dict, colgroup, dim, shortname)
        VALUES (?,?,?,?,?,?)
""", pst)

cursor.execute("""
    CREATE TABLE tab1 (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        "biochar type" INTEGER,
        "sample day" INTEGER,
        "sample hour" INTEGER,
        "fertilizer" INTEGER,
        "result 1" REAL,
        "result 2" REAL,
        "result 3" REAL)
    """)

pst = [
    (0, 1, 2, 0, 0.22, 0.72, 1.2),
    (1, 2, 5, 1, 1.01, 2.32, 2.3),
    (2, 1, 5, 0, 0.12, 3.32, 1.2),
    (1, 3, 5, 1, 1.51, 2.22, 1.3),
    (1, 4, 5, 1, 2.23, 2.23, 2.5),
    (3, 2, 5, 1, 0.24, 2.12, 1.2),
    (2, 5, 3, 0, 3.42, 0.11, 2.2),
    (1, 2, 5, 0, 0.41, 1.12, 1.1),
    (4, 1, 3, 0, 0.22, 1.22, 2.8),
    (2, 1, 5, 0, 2.22, 0.22, 2.2),
]
cursor.executemany("""
    INSERT INTO tab1 ("biochar type", "sample day", "sample hour",
                      "fertilizer", "result 1", "result 2", "result 3")
    VALUES (?,?,?,?,?,?,?)
""", pst)

# data table
cursor.execute("""
    CREATE TABLE "_COLINFO tab2"(
        colname TEXT PRIMARY KEY,
        type TEXT,
        dict TEXT,
        colgroup TEXT,
        dim TEXT,
        shortname TEXT UNIQUE)
    """)
pst = [
    ("has biochar", "BOOL", "has biochar", None, None, "B"),
    ("biochar type", "ENUM", "biochar type", None, None, "Tp"),
    ("bc temp", "INT", None, None, None, "T"),
    ("fertilizer", "BOOL", "fertilizer", None, None, "F"),
    ("repl", "INT", None, None, "m", None),
    ("result 1", "REAL", None, None, "kg", "r1"),
    ("result 2", "REAL", None, None, "m3", "r2")]
cursor.executemany("""
    INSERT INTO "_COLINFO tab2"(colname, type, dict, colgroup, dim, shortname)
        VALUES (?,?,?,?,?,?)
""", pst)

cursor.execute("""
    CREATE TABLE tab2 (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        "has biochar" INTEGER,
        "biochar type" INTEGER,
        "bc temp" INTEGER,
        "fertilizer" INTEGER,
        "repl" INTEGER,
        "result 1" REAL,
        "result 2" REAL)
    """)

pst = [
    (0, 0, 300, 0, 1, 0.12, 4.3),
    (0, 0, 400, 0, 1, 1.01, 3.2),
    (0, 0, 400, 0, 2, 1.21, 3.4),
    (0, 0, 400, 0, 3, 0.98, 3.1),
    (0, 0, 500, 0, 1, 2.12, 4.6),
    (0, 0, 600, 1, 1, 1.22, 2.5),
    (0, 0, 600, 1, 2, 1.54, 2.3),
    (0, 0, 600, 1, 3, 1.09, 2.2),
    (1, 2, 300, 0, 1, 2.03, 7.6),
    (1, 2, 400, 0, 1, 0.95, 8.0),
    (1, 2, 500, 0, 1, 1.14, 4.3),
    (1, 2, 600, 1, 1, 1.17, 1.1),
    (1, 2, 600, 1, 2, 1.04, 1.3),
    (1, 2, 600, 1, 3, 1.00, 1.0),
]
cursor.executemany("""
    INSERT INTO tab2 ("has biochar", "biochar type", "bc temp", "fertilizer",
                      "repl", "result 1", "result 2")
    VALUES (?,?,?,?,?,?,?)
""", pst)

connection.commit()
connection.close()
