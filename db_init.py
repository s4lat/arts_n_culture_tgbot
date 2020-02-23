import sqlite3, cfg

name = cfg.DB_NAME
conn = sqlite3.connect(name)

c = conn.cursor()
c.execute(
""" CREATE TABLE IF NOT EXISTS arts (
	id integer PRIMARY KEY AUTOINCREMENT,
	token text NOT NULL UNIQUE
);""")

