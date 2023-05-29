import sqlite3
from sqlite3 import Error

def create_connection():
    conn = None;
    try:
        #conn = sqlite3.connect(':memory:')  # create a database in RAM
        # for a persistent database use the following line
        conn = sqlite3.connect('vip.db')
        print(f'successful connection with sqlite version {sqlite3.version}')
    except Error as e:
        print(e)
    
    if conn:
        return conn
    return None

def create_table(conn):
    try:
        sql_create_table = """CREATE TABLE IF NOT EXISTS vip (
                                    steam_id integer PRIMARY KEY,
                                    minutes integer
                                );"""
        c = conn.cursor()
        c.execute(sql_create_table)
    except Error as e:
        print(e)

#setup
c = create_connection()
create_table(c)