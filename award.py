#todo award vip to seeders
import requests
import schedule
import time
import json
import sqlite3
from sqlite3 import Error
from setup_db import create_connection

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

        # c.commit()

    except Error as e:
        print(e)

def seeding():
    return True

def select_all_tasks(conn):
    cur = conn.cursor()
    cur.execute("SELECT * FROM vip")

    rows = cur.fetchall()
    return rows

def job(c):
    # response = requests.get('http://api.example.com/data')
    # data = response.json()
    # this should be replaced by the API call
    with open('players.json') as f:
        data = json.load(f)

    if(seeding):
        for player in data['result']:
            print(player['steam_id_64'])
            give_points(c,player['steam_id_64'])

    print(select_all_tasks(c))

#setup
c = create_connection()
schedule.every(5).seconds.do(job,c)

while True:
    schedule.run_pending()
    time.sleep(1)