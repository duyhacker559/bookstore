try:
	import pymysql

	pymysql.install_as_MySQLdb()
except Exception:
	# Keep startup resilient for non-MySQL environments.
	pass
