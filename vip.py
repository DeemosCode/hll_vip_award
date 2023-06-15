import os
import time
import requests
import schedule
import calendar
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


def calculate_expiration_date(player_doc):
    # Fetch the player document
    dates_seeded_successfully = player_doc['dates_seeded_successfully']

    # Count successful days in current calendar month
    successful_days_current_month = sum(1 for date in dates_seeded_successfully if date.month == datetime.utcnow().month and date.year == datetime.utcnow().year)

    #initializing variable
    is_end_of_month = False

    if successful_days_current_month >= 7 or (player_doc['geforce_now']==True):
        # If player has been successful for 7 or more days this month, set expiration to the end of the current month
        current_year = datetime.utcnow().year
        current_month = datetime.utcnow().month
        last_day_of_month = calendar.monthrange(current_year, current_month)[1]  # Get the last day of the current month
        expiration_date = datetime(current_year, current_month, last_day_of_month, 23, 59, 59).isoformat()  # Set the expiration to the end of the current month
        is_end_of_month = True
    else:
        # Otherwise, set expiration to 24 hours in the future
        expiration_timestamp = time.time() + (24 * 60 * 60)
        expiration_date = datetime.utcfromtimestamp(expiration_timestamp).isoformat()

    return (expiration_date, is_end_of_month)


def award_vip(steam_id_64, player_name):
    # Fetch the document for this player
    player_doc = vip.find_one({'steam_id_64': steam_id_64})
    date_calc_result = calculate_expiration_date(player_doc)
    has_vip_this_month = date_calc_result[1]
    expiration_date = date_calc_result[0]

    # Convert dates_seeded_successfully to dates only (no time) for comparison
    dates_seeded_successfully_only = [date.date() for date in player_doc['dates_seeded_successfully']]

    # If today's date is already in dates_seeded_successfully, return early
    if datetime.utcnow().date() in dates_seeded_successfully_only:
        return
    
    current_month = datetime.utcnow().month
    current_year = datetime.utcnow().year

    # Check if player has vip this month
    if has_vip_this_month:
        # Count days player played war or training in current calendar month
        days_played_war_this_month = sum(1 for date in player_doc['dates_played_war'] if date.month == current_month and date.year == current_year)
        days_played_training_this_month = sum(1 for date in player_doc['dates_played_training'] if date.month == current_month and date.year == current_year)

        # If player played war or training 3 or more days this month, set level to 'deemocrat'
        if ((days_played_war_this_month + days_played_training_this_month) >= 3):
            vip.update_one(
                {'steam_id_64': steam_id_64},
                {
                    '$set': {'level': 'deemocrat'}  # Set 'level' to 'deemocrat'
                }
            )
            print(f"PROMOTION TO DEEMOCRAT for {player_doc['name']}")

    # Update the document
    params = {'steam_id_64': steam_id_64, 'name': player_name, 'expiration': expiration_date}
    vip.update_one(
        {'steam_id_64': steam_id_64},
        {
            '$push': {'dates_seeded_successfully': datetime.utcnow()}  # Add the current date and time to 'dates_seeded_successfully'
        }
    )

    # try to make the api call    
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
                        'name': player_name,
                        'minutes_today': interval_in_minutes-2,
                        'pending_award': False,
                        'steam_id_64': steam_id_64,
                        'dates_seeded_successfully': [],
                        'dates_played_war' : [],
                        'dates_played_training' : [],
                        'geforce_now': False,
                        'level': 'recruit',
                        'vip_this_month':False,
                    })
                    break
                    doc = vip.find_one({'steam_id_64': steam_id_64})  # Fetch the document to use below

                # Check award condition
                if (no_of_players >= 50 and doc['minutes_today'] >= minutes_requirement_if_success) or (doc['minutes_today'] >= minutes_requirement_if_failure):

                    # Make external API call
                    award_vip(steam_id_64,player_name)

    print(f"Ran job - No of players : {no_of_players}")    

schedule.every(interval_in_minutes).minutes.do(job)

# Keep the script running.
while True:
    schedule.run_pending()
    time.sleep(1)
