import os
import time
import requests
import schedule
from pymongo import MongoClient
from datetime import datetime
from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv
load_dotenv()

# Set up the MongoDB client
client = MongoClient('mongodb://127.0.0.1:27017/')  # Connect to your MongoDB
db = client.deemos 
vip = db.vip  # Access the 'vip' collection

# Get the session_id
session_id = os.getenv('SESSIONID', '0')

# Set interval
interval_in_minutes = 5
minutes_requirement_if_success = 15
minutes_requirement_if_failure = 120


def calculate_expiration_date(steam_id_64, minutes_requirement):
    # Fetch the player document
    player_doc = vip.find_one({'steam_id_64': steam_id_64})
    successful_dates = player_doc['successful_dates']

    # Count successful days in current calendar month
    successful_days_current_month = sum(1 for date in successful_dates if date.month == datetime.utcnow().month and date.year == datetime.utcnow().year)

    if successful_days_current_month >= 7:
        # If player has been successful for 7 or more days this month, set expiration to 30 days in the future
        expiration_timestamp = time.time() + (30 * 24 * 60 * 60)
    else:
        # Otherwise, set expiration to 24 hours in the future, minus the minutes requirement
        expiration_timestamp = time.time() + (24 * 60 * 60 - minutes_requirement)

    expiration_date = datetime.utcfromtimestamp(expiration_timestamp).isoformat()
    return expiration_date


def award_vip(steam_id_64, player_name, expiration_date):
    # Fetch the document for this player
    player_doc = vip.find_one({'steam_id_64': steam_id_64})

    # Convert successful_dates to dates only (no time) for comparison
    successful_dates_only = [date.date() for date in player_doc['successful_dates']]

    # If today's date is already in successful_dates, return early
    if datetime.utcnow().date() in successful_dates_only:
        return

    # Update the document
    params = {'steam_id_64': steam_id_64, 'name': player_name, 'expiration': expiration_date}
    vip.update_one(
        {'steam_id_64': steam_id_64},
        {
            '$push': {'successful_dates': datetime.utcnow()}  # Add the current date and time to 'successful_dates'
        }
    )
    try:
        response = requests.get('http://server.deemos.club/api/do_add_vip', cookies=cookies, params=params)
        response.raise_for_status()
        vip.update_one(
            {'steam_id_64': steam_id_64},
            {
                '$set': {'pending_award': False}, # reset 'pending_award'
            }
        )
        print(f"VIP Awarded to {steam_id_64} {player_name} {datetime.utcnow()}")
    except requests.exceptions.RequestException as err:
        print(f"An error occurred while adding VIP status: {err}")
        # save it to try again later
        vip.update_one(
            {'steam_id_64': steam_id_64},
            {
                '$set': {'pending_award': True}, # Set 'pending_award' to true
            }
        )

def job():
    no_of_players=0
    cookies = {'sessionid': session_id}
     # Check for players with pending_award: true and make API call for each
    pending_award_players = vip.find({'pending_award': True})
    for player in pending_award_players:
        steam_id_64 = player['steam_id_64']
        player_name = player['name']
        expiration_date = datetime.utcfromtimestamp(time.time() + (24 * 60 * 60 - minutes_requirement_if_success)).isoformat()
        award_vip(steam_id_64,player_name,expiration_date)
        
    try:
        response = requests.get('http://server.deemos.club/api/get_players_fast', cookies=cookies)
        response.raise_for_status()  # Raise an exception if the response was unsuccessful
    except requests.exceptions.RequestException as err:
        print ("An error occurred: ", err)
    else:
        data = response.json()
        no_of_players= len(data['result'])
        if data['failed'] != False:
            print(f'Error in API response: {data}')
        else:
            for player in data['result']:
                steam_id_64 = player['steam_id_64']
                player_name = player['name']

                # Find the document for this player
                doc = vip.find_one({'steam_id_64': steam_id_64})

                if doc:
                    # Update the document
                    vip.update_one(
                        {'steam_id_64': steam_id_64},
                        {'$inc': {'minutes_today': interval_in_minutes}}  # Increment the 'minutes_today' field by interval
                    )
                    doc = vip.find_one({'steam_id_64': steam_id_64})  # Fetch the document again to get updated 'minutes_today'
                else:
                    # Create a new document for this player
                    vip.insert_one({
                        'discord_id': '',
                        'minutes_today': interval_in_minutes,
                        'successful_dates': [],
                        'pending_award': False,
                        'steam_id_64': steam_id_64
                    })
                    doc = vip.find_one({'steam_id_64': steam_id_64})  # Fetch the document to use below

                # Check award condition
                if (no_of_players >= 50 and doc['minutes_today'] >= minutes_requirement_if_success) or (doc['minutes_today'] >= minutes_requirement_if_failure):

                    # Make external API call
                    expiration_timestamp = time.time() + (24 * 60 * 60 - minutes_requirement_if_success)  # 24 hours in the future
                    expiration_date = datetime.utcfromtimestamp(expiration_timestamp).isoformat()
                    award_vip(steam_id_64,player_name,expiration_date)

    print(f"Ran job - No of players : {no_of_players}")    

schedule.every(interval_in_minutes).minutes.do(job)

# Keep the script running.
while True:
    schedule.run_pending()
    time.sleep(1)
