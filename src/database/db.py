import mysql.connector
from mysql.connector import Error


class Database:
    def __init__(self, host, user, password, database):
        self.config = {
            "host": host,
            "user": user,
            "password": password,
            "database": database
        }
        self.connection = None
        self.cursor = None
        self.connect()

    def connect(self):
        """(Re)connect to the database"""
        try:
            self.connection = mysql.connector.connect(**self.config)
            self.cursor = self.connection.cursor(dictionary=True)
            print("✅ Database connected successfully")
        except Error as err:
            print(err)
            self.connection = None
            self.cursor = None

    def ensure_connection(self):
        """Make sure the connection is alive"""
        if self.connection is None or not self.connection.is_connected():
            self.connect()

    def execute_query(self, query, params=None, fetch=False):
        """Execute a query (SELECT if fetch=True)"""
        try:
            self.ensure_connection()
            self.cursor.execute(query, params)

            if fetch:
                return self.cursor.fetchall()

            self.connection.commit()
        except Error as err:
            print(err)
            return None
