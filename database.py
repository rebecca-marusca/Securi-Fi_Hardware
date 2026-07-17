import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'securi-fi.db')

def start_connection():
	conn = sqlite3.connect(DB_PATH)
	# cu row factory il putem folosi si ca si dictionary, nu numai tuple
	conn.row_factory = sqlite3.Row
	return conn

def init_db():
	conn = start_connection()
	c = conn.cursor()

	# cam tot ce tine de info-ul dat de esp-uri
	# vedeti ca sql nu are bool, deci pt orice true / false trebuie transformat in int 1 / 0
	c.execute('''CREATE TABLE IF NOT EXISTS events (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		home_id TEXT,
		node_id TEXT,
		timestamp TEXT,
		movement INTEGER,
		state TEXT,
		is_warning INTEGER
	)''')

	# ce tine de users
	c.execute('''CREATE TABLE IF NOT EXISTS fcm_tokens (
		user_id TEXT PRIMARY KEY,
		token TEXT
	)''')

	# ce tine de casa ta
	c.execute('''CREATE TABLE IF NOT EXISTS system_state (
		home_id TEXT PRIMARY KEY,
		armed INTEGER DEFAULT 0
	)''')

	conn.commit()
	conn.close()
	print("Database ready :D")


# Setters:
def set_event(home_id, node_id, timestamp, movement, state, is_warning):
	conn = start_connection()
	c = conn.cursor()

	# (id, home_id, node_id, timestamp, movement, state, is_warning) -> ca sa nu modificam id e null
	c.execute("INSERT INTO events VALUES (NULL,?,?,?,?,?,?)", (home_id, node_id, timestamp, movement, state, is_warning))
	conn.commit()
	conn.close()

def set_armed(home_id, armed: bool):
	conn = start_connection()
	c = conn.cursor()

	c.execute("INSERT OR REPLACE INTO system_state VALUES (?,?)", (home_id, int(armed)))
	conn.commit()
	conn.close()

def set_fcm_token(user_id, token):
	conn = start_connection()
	c = conn.cursor()

	c.execute("INSERT OR REPLACE INTO fcm_tokens VALUES (?,?)", (user_id, token))
	conn.commit()
	conn.close()


# Getters:
def get_history(home_id, limit=100):
	conn = start_connection()
	c = conn.cursor()

	data = c.execute("SELECT * FROM events WHERE home_id=? ORDER BY timestamp DESC LIMIT ?", (home_id, limit)).fetchall()
	conn.close()

	# noi vrem de fapt o lista cu package-urile din history, care sunt dict ca e mai usor de lucrat cu ele decat cu tuple
	return [dict(d) for d in data]

def get_armed(home_id):
	conn = start_connection()
	c = conn.cursor()

	row = c.execute("SELECT armed FROM system_state WHERE home_id=?", (home_id,)).fetchone()
	conn.close()

	if row:
		return bool(row["armed"])
	else:
		return False

def get_fcm_token(user_id):
	conn = start_connection()
	c = conn.cursor()

	row = c.execute("SELECT token FROM fcm_tokens WHERE user_id=?", (user_id,)).fetchone()
	conn.close()

	if row:
		return row["token"]
	else:
		return None
