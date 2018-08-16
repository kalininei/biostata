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
    ("S", "sample day", 1, "INTEGER", "days"),
    ("H", "sample hour", 1, "INTEGER", "h"),
    ("F", "fertilizer", 1, "BOOLEAN", None),
    ("r1", "result 1", 0, "REAL", "m"),
    ("r2", "result 2", 0, "REAL", "m"),
    ("r3", "result 3", 0, "REAL", "h"),
]
cursor.executemany("""
    INSERT INTO _DATA_TYPES_ (shortname, name, iscategory, type, dim)
        VALUES (?,?,?,?,?)
""", pst)

# data types descriptions
cursor.execute("""
    CREATE TABLE "_DATA_TYPE biochar type" (
        value INTEGER PRIMARY KEY AUTOINCREMENT,
        shortname TEXT UNIQUE,
        name TEXT UNIQUE
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
    INSERT INTO "_DATA_TYPE biochar type" (shortname, name) VALUES (?,?)
""", pst)

cursor.execute("""
    CREATE TABLE "_DATA_TYPE fertilizer"(
        value INTEGER PRIMARY KEY AUTOINCREMENT,
        shortname TEXT UNIQUE,
        name TEXT UNIQUE
    )
""")

pst = [
    (0, "noF", "no fertilizer"),
    (1, "F", "with fertilizer")
]
cursor.executemany("""
    INSERT INTO "_DATA_TYPE fertilizer"(value, shortname, name) VALUES (?,?,?)
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
    (1, 2, 5, 1, 1.51, 2.22, 1.3),
    (1, 1, 5, 1, 2.23, 2.23, 2.5),
    (3, 2, 5, 1, 0.24, 2.12, 1.2),
    (2, 1, 3, 0, 3.42, 0.11, 2.2),
    (1, 2, 5, 0, 0.41, 1.12, 1.1),
    (2, 1, 5, 0, 2.22, 0.22, 2.2),
]
cursor.executemany("""
    INSERT INTO tab1 ("biochar type", "sample day", "sample hour",
                      "fertilizer", "result 1", "result 2", "result 3")
    VALUES (?,?,?,?,?,?,?)
""", pst)

connection.commit()
connection.close()
