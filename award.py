#todo award vip to seeders
import os
import requests
import schedule
import time
import json
import sqlite3
from sqlite3 import Error
#from setup_db import create_connection

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

def give_points(conn, id):
    try:
        c = conn.cursor()
        # If the id doesn't exist, create it and set hours to 5
        c.execute('''
            INSERT OR IGNORE INTO vip (steam_id, minutes) VALUES (?, 5);
        ''', (id,))

        # Whether the id pre-existed or was just inserted, add 5 to hours
        c.execute('''
            UPDATE vip SET minutes = minutes + 5 WHERE steam_id = ?;
        ''', (id,))

        conn.commit()

    except Error as e:
        print(e)

def seeding(data):
    if len(data['result']) < 50:
        return True
    return False


def select_all_tasks(conn):
    cur = conn.cursor()
    cur.execute("SELECT * FROM vip")

    rows = cur.fetchall()
    return rows

def job(c):
    session_id = os.getenv('SESSIONID', '0')

    cookies = {'sessionid': session_id}
    response = requests.get('http://server.deemos.club/api/get_players_fast',cookies=cookies)
    data = response.json()

    players = len(data['result'])

    if(seeding(data)):
        for player in data['result']:
            # print(player['steam_id_64'])
            give_points(c,player['steam_id_64'])

    # print(select_all_tasks(c))
        c.commit()
        print("Logged seeders")
    else:
        print("Server has more than 50 players")


#setup
c = create_connection()
job(c)
schedule.every(10).seconds.do(job,c)

while True:
    schedule.run_pending()
    time.sleep(1)