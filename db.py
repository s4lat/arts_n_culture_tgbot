import sqlite3

class DB:
	def __init__(self, db):
		self.db = db

	def getArt(self, token):
		conn, c = self.__connect()
		c.execute("SELECT * FROM arts WHERE token=?", (token,))
		art = c.fetchone()

		conn.commit()
		conn.close()
		return art

	def addArt(self, token):
		conn, c = self.__connect()
		c.execute("INSERT INTO arts(token) VALUES (?)", (token, ))
		conn.commit()
		conn.close()

	def __connect(self):
		conn = sqlite3.connect(self.db, timeout=10)
		c = conn.cursor()
		return conn, c