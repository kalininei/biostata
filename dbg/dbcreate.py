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


# categories list
cursor.execute("""
    CREATE TABLE _DATA_TYPES_ (
        name TEXT PRIMARY KEY,
        shortname TEXT,
        iscategory INTEGER NOT NULL,
        type TEXT NOT NULL,
        dim TEXT,
        comment TEXT
    )
""")
pst = [
    ("Tp", "biochar type", 1, "ENUM", None),
    ("D", "sample day", 1, "INTEGER", "days"),
    ("H", "sample hour", 1, "INTEGER", "h"),
    ("F", "fertilizer", 1, "BOOLEAN", None),
    ("r1", "result 1", 0, "REAL", "m"),
    ("r2", "result 2", 0, "REAL", "m"),
    ("r3", "result 3", 0, "REAL", "h"),
    ("b", "has biochar", 1, "BOOLEAN", None),
    ("T", "bc temp", 1, "INTEGER", "C"),
    ("r", "repl", 1, "INTEGER", None),
]
cursor.executemany("""
    INSERT INTO _DATA_TYPES_ (shortname, name, iscategory, type, dim)
        VALUES (?,?,?,?,?)
""", pst)

# data types descriptions
cursor.execute("""
    CREATE TABLE "_DATA_TYPE biochar type" (
        value INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        comments TEXT
    )
""")

pst = [
    ("no", "no biochar"),
    ("b4p", "biochar 400C, powder"),
    ("b5p", "biochar 500C, powder"),
    ("b4g", "biochar 400C, granular"),
    ("b5g", "biochar 500C, granular"),
]
cursor.executemany("""
    INSERT INTO "_DATA_TYPE biochar type" (name, comments) VALUES (?,?)
""", pst)

cursor.execute("""
    CREATE TABLE "_DATA_TYPE fertilizer"(
        value INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        comments TEXT
    )
""")

pst = [
    (0, "noF", "no fertilizer"),
    (1, "F", "with fertilizer")
]
cursor.executemany("""
    INSERT INTO "_DATA_TYPE fertilizer"(value, name, comments) VALUES (?,?,?)
""", pst)

cursor.execute("""
    CREATE TABLE "_DATA_TYPE has biochar"(
        value INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        comments TEXT
    )
""")

pst = [
    (0, "B", ""),
    (1, "noB", "")
]
cursor.executemany("""
    INSERT INTO "_DATA_TYPE has biochar"(value, name, comments) VALUES (?,?,?)
""", pst)

# data table
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
    (2, 1, 2, 0, 0.22, 0.72, 1.2),
    (1, 2, 5, 1, 1.01, 2.32, 2.3),
    (2, 1, 3, 0, 0.12, 3.32, 1.2),
    (1, 3, 5, 1, 1.51, 2.22, 1.3),
    (1, 4, 5, 1, 2.23, 2.23, 2.5),
    (3, 2, 5, 1, 0.24, 2.12, 1.2),
    (2, 5, 3, 0, 3.42, 0.11, 2.2),
    (1, 2, 5, 0, 0.41, 1.12, 1.1),
    (2, 1, 3, 0, 0.22, 1.22, 2.8),
    (2, 1, 5, 0, 2.22, 0.22, 2.2),
]
cursor.executemany("""
    INSERT INTO tab1 ("biochar type", "sample day", "sample hour",
                      "fertilizer", "result 1", "result 2", "result 3")
    VALUES (?,?,?,?,?,?,?)
""", pst)

# data table
cursor.execute("""
    CREATE TABLE tab2 (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        "has biochar" INTEGER,
        "bc temp" INTEGER,
        "fertilizer" INTEGER,
        "repl" INTEGER,
        "result 1" REAL,
        "result 2" REAL)
    """)

pst = [
    (0, 300, 0, 1, 0.12, 4.3),
    (0, 400, 0, 1, 1.01, 3.2),
    (0, 400, 0, 2, 1.21, 3.4),
    (0, 400, 0, 3, 0.98, 3.1),
    (0, 500, 0, 1, 2.12, 4.6),
    (0, 600, 1, 1, 1.22, 2.5),
    (0, 600, 1, 2, 1.54, 2.3),
    (0, 600, 1, 3, 1.09, 2.2),
    (1, 300, 0, 1, 2.03, 7.6),
    (1, 400, 0, 1, 0.95, 8.0),
    (1, 500, 0, 1, 1.14, 4.3),
    (1, 600, 1, 1, 1.17, 1.1),
    (1, 600, 1, 2, 1.04, 1.3),
    (1, 600, 1, 3, 1.00, 1.0),
]
cursor.executemany("""
    INSERT INTO tab2 ("has biochar", "bc temp", "fertilizer",
                      "repl", "result 1", "result 2")
    VALUES (?,?,?,?,?,?)
""", pst)

connection.commit()
connection.close()
