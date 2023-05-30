#todo award vip to seeders
import os
import requests
import schedule
import time
import json
import sqlite3
from sqlite3 import Error
#from setup_db import create_connection
import logging
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_connection():
    conn = None;
    try:
        #conn = sqlite3.connect(':memory:')  # create a database in RAM
        # for a persistent database use the following line
        conn = sqlite3.connect('vip.db')
        logger.info(f'successful connection with sqlite version %s',{sqlite3.version})
    except Error as e:
        logger.info('%s',e)
    
    if conn:
        return conn
    return None

def give_points(conn, id):
    c = conn.cursor()
    try:
        today = time.strftime('%Y-%m-%d', time.gmtime())

        # Check if the player already has 20 minutes today
        c.execute("SELECT minutes, last_updated_day FROM vip WHERE steam_id = ?", (id,))
        result = c.fetchone()
        if result is not None and result[1] == today and result[0] >= 20:
            return

        # If the id doesn't exist, create it and set minutes to 5
        # If the id exists but last_updated_day is not today, reset minutes to 5 and set last_updated_day to today
        c.execute('''
            INSERT INTO vip (steam_id, minutes, last_updated_day)
            VALUES (?, 5, ?)
            ON CONFLICT (steam_id) DO UPDATE SET minutes = (CASE WHEN last_updated_day = ? THEN minutes + 5 ELSE 5 END), last_updated_day = ?;
        ''', (id, today, today, today))

        conn.commit()

    except Error as e:
        logger.info('%s',e)

def seeding(data):
    if len(data['result']) < 2:
        return True
    return False


def select_all_tasks(conn):
    cur = conn.cursor()
    cur.execute("SELECT * FROM vip")

    rows = cur.fetchall()
    return rows

def add_vip(steam_id, player_name, expiration_timestamp):
    session_id = os.getenv('SESSIONID', '0')
    cookies = {'sessionid': session_id}
    params = {'steam_64_id': steam_id, 'name': player_name, 'expiration': expiration_timestamp}
    try:
        logger.info(f'vip added!!!')
        logger.info(' %s',steam_id)
        logger.info(' %s',expiration_timestamp)
        response = requests.get('http://server.deemos.club/api/do_add_vip', cookies=cookies, params=params)
        response.raise_for_status()  # Raise an exception if the response was unsuccessful
    except requests.exceptions.RequestException as err:
        print ("An error occurred: ", err)
    else:
        # Check response status contents
        data = response.json()
        if data['failed'] != False:
            logger.info(f'Error in API response:', data)
            
def job(conn):
    c = conn.cursor()
    session_id = os.getenv('SESSIONID', '0')
    cookies = {'sessionid': session_id}
    try:
        response = requests.get('http://server.deemos.club/api/get_players_fast', cookies=cookies)
        response.raise_for_status()  # Raise an exception if the response was unsuccessful
    except requests.exceptions.RequestException as err:
        print ("An error occurred: ", err)
    else:
        # Check response status contents
        data = response.json()
        if data['failed'] != False:
            logger.info(f'Error in API response:  %s', data)
            return  # Skip the rest of the function if there was an error

    players = len(data['result'])

    for player in data['result']:
        logger.info('%s',player['name'])
        # Give points to player
        give_points(conn, player['steam_id_64'])

        # Check if player has accumulated 20 minutes and seeding is False
        c.execute("SELECT minutes, successfully_seeded FROM vip WHERE steam_id = ?", (player['steam_id_64'],))
        
        result = c.fetchone()
        if result is not None and result[0] >= 20 and not seeding(data) and result[1] == 0:
            # Update successfully_seeded
            c.execute('''
                UPDATE vip SET successfully_seeded = 1 WHERE steam_id = ?;
            ''', (player['steam_id_64'],))

            # Update successful_seeding_days
            c.execute('''
                UPDATE vip SET successful_seeding_days = successful_seeding_days + 1 WHERE steam_id = ?;
            ''', (player['steam_id_64'],))

            # Add VIP for 1 day
            current_time = time.time()
            add_vip(player['steam_id_64'], player['name'], int(current_time + (1 * 24 * 60 * 60)))  # 1 day in seconds)
            logger.info(f'One Day VIP added for  %s',player['name'])

        # Check if player has successfully seeded for 7 days in the last 30 days
        c.execute("SELECT successful_seeding_days FROM vip WHERE steam_id = ?", (player['steam_id_64'],))
        
        result = c.fetchone()
        if result is not None and result[0] >= 7:
            # Add VIP for 30 days
            current_time = time.time()
            add_vip(player['steam_id_64'], player['name'], int(current_time + (30 * 24 * 60 * 60)))  # 30 days in seconds
            logger.info(f'One Month VIP added for  %s',player['name'])


    conn.commit()
    logger.info(f'ran job %s',time.time()) 

conn = create_connection()

job(conn)
schedule.every(10).seconds.do(job,conn)

while True:
    schedule.run_pending()
    time.sleep(1)
