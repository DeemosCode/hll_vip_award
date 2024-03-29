#     HLL rcon vip award
#     Copyright (C) 2023 Nikolaos Katzakis

#     This program is free software: you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.

#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.

#     You should have received a copy of the GNU General Public License
#     along with this program.  If not, see <https://www.gnu.org/licenses/>.


import os
import time
import json
import requests
import schedule
import calendar
from pymongo import MongoClient
from datetime import datetime,timedelta
import logging
from systemd import journal
from dotenv import load_dotenv
load_dotenv()

MONGO_CONNECTION_STRING = os.getenv('MONGO_CONNECTION_STRING')
SESSION_ID = os.getenv('SESSIONID', '0')

log = logging.getLogger('vip')
log.addHandler(journal.JournaldLogHandler())
log.setLevel(logging.INFO)

# Set up the MongoDB client
client = MongoClient(MONGO_CONNECTION_STRING)  # Connect to your MongoDB
db = client.deemos 
vip = db.members
    
# Set interval
INTERVAL_IN_MINUTES = 5
MINUTES_REQUIREMENT_IF_SUCCESS = 15
MINUTES_REQUIREMENT_IF_FAILURE = 120
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1119199023602073610/nmqzDMXyWjPI0GLd5x-U4QPLbLHVCd17ecHAkQKs0JzBVeZcfPqlMeRkdLSsLH-HpDrG"
WAR='war'
TRAINING='training'
SEED='seed'
MISC='misc'
cookies = {'sessionid': SESSION_ID}


def post_to_discord(content):
    data = {"content": content}
    response = requests.post(DISCORD_WEBHOOK_URL, json=data)

    if response.status_code != 204:
        print(f"Failed to send message to Discord: {response.text}")

def count_days_of_type(participation_type,player_document):
    current_year = datetime.utcnow().year
    current_month = datetime.utcnow().month
    if (player_document['participation'] is not None):
        return sum(1 for rec in player_document['participation'] if rec[1] == participation_type and rec[0].month == current_month and rec[0].year == current_year)

def count_participation_last_30_days(player_document):
    # Get the current date/time
    current_date = datetime.utcnow()

    # Calculate the date 30 days ago
    date_30_days_ago = current_date - timedelta(days=30)

    if (player_document['participation'] is not None):
        return sum(1 for rec in player_document['participation'] if rec[0] >= date_30_days_ago)


def fetch_days_of_type_in_current_month(participation_type, player_document):
    current_year = datetime.utcnow().year
    current_month = datetime.utcnow().month
    dates_list = []
    if player_document['participation'] is not None:
        for rec in player_document['participation']:
            if rec[1] == participation_type and rec[0].month == current_month and rec[0].year == current_year:
                dates_list.append(rec[0].date())
    return dates_list


def calculate_expiration_date(player_doc):
    # Fetch the participation records
    participation_records = player_doc['participation']

    # Fetch dates from participation records for 'seed' type in the current calendar month
    current_year = datetime.utcnow().year
    current_month = datetime.utcnow().month
    dates_seeded_successfully = [datetime(rec[0]) for rec in participation_records if rec[1] == "seed" and datetime(rec[0]).year == current_year and datetime(rec[0]).month == current_month]

    # Count successful days in current calendar month
    successful_days_current_month = len(dates_seeded_successfully)

    # Initializing variable
    has_vip_until_end_of_month = False

    if successful_days_current_month >= 7:
        # If player has been successful for 7 or more days this month, set expiration to the end of the current month
        last_day_of_month = calendar.monthrange(current_year, current_month)[1]  # Get the last day of the current month
        expiration_date = datetime(current_year, current_month, last_day_of_month, 23, 59, 59).isoformat()  # Set the expiration to the end of the current month
        has_vip_until_end_of_month = True
    else:
        # Otherwise, set expiration to 24 hours in the future
        expiration_timestamp = time.time() + (24 * 60 * 60)
        expiration_date = datetime.utcfromtimestamp(expiration_timestamp).isoformat()

    return (expiration_date, has_vip_until_end_of_month)


def check_and_demote_aspiring():
    # Fetch all players
    all_players = vip.find({})
    current_month = datetime.utcnow().month
    current_year = datetime.utcnow().year
    
    # Iterate through all players and perform tasks
    for player in all_players:
        discord_id = player['discord_id']

        # If player played war or training 3 or more days this month, set level to 'deemocrat'
        if (count_participation_last_30_days(player)) == 0:
            # vip.update_one(
            #     {'discord_id': discord_id},
            #     {
            #         '$set': {'level': 'none'}  # Demote to nothing
            #     }
            # )
            print(f"Loss of recruit status for {player['discord_id']}")
            post_to_discord(f"Loss of Recruit status for {player['discord_id']}")

    print("Checked for recruit demotions")




def check_and_promote_deemocrat():
    # Fetch all players
    all_players = vip.find({})
    current_month = datetime.utcnow().month
    current_year = datetime.utcnow().year
    
    # Iterate through all players and perform tasks
    for player in all_players:
        steam_id_64 = player['steam_id_64']

        # If player played war or training 3 or more days this month, set level to 'deemocrat'
        if (len(player['participation'])) >= 5:
            vip.update_one(
                {'steam_id_64': steam_id_64},
                {
                    '$set': {'level': 'deemocrat'}  # Set 'level' to 'deemocrat'
                }
            )
            print(f"PROMOTION TO DEEMOCRAT for {player['discord_id']}")
            post_to_discord(f"PROMOTION TO DEEMOCRAT for {player['discord_id']}")

    print("Checked for deemocrat promotions")

def award_vip(steam_id_64, player_name):
    # Fetch the document for this player
    player_doc = vip.find_one({'steam_id_64': steam_id_64})
    
    # calculate how until when the VIP will be valid
    date_calc_result = calculate_expiration_date(player_doc)
    has_vip_this_month = date_calc_result[1]
    expiration_date = date_calc_result[0]

    # If today's date is already in dates_seeded_successfully, return early
    if datetime.utcnow().date() in fetch_days_of_type_in_current_month(SEED, player_doc):
        return

    # parameters for http request
    # check cookies
    params = {'steam_id_64': steam_id_64, 'name': player_name, 'expiration': expiration_date}
    
    # try to make the api call    
    try:
        response = requests.get('http://server.deemos.club/api/do_add_vip', cookies=cookies, params=params)
        response.raise_for_status()
        vip.update_one(
            {'steam_id_64': steam_id_64},
            {
                '$set': {'pending_award': False}, # reset 'pending_award'
                '$push': {'participation': [datetime.utcnow(), SEED]}  # Add the current date and time to 'participation' with 'seed' as participation type
            }
        )
        print(f"VIP Awarded to {steam_id_64} {player_name}")
    except requests.exceptions.RequestException as err:
        print(f"An error occurred while adding VIP status: {err}")
        # save it to try again later
        vip.update_one(
            {'steam_id_64': steam_id_64},
            {
                '$set': {'pending_award': True}, # Set 'pending_award' to true
            }
        )

def award_pending():
     # Check for players with pending_award: true and make API call for each
    pending_award_players = vip.find({'pending_award': True})
    for player in pending_award_players:
        steam_id_64 = player['steam_id_64']
        player_name = player['name']
        award_vip(steam_id_64,player_name)

def reset_minutes_today():
    all_players = vip.find({})
    for player in all_players:
        steam_id_64 = player['steam_id_64']
        vip.update_one(
            {'steam_id_64': steam_id_64},
            {
                '$set': {'minutes_today': 0}  # Reset 'minutes_today' to 0
            }
        )
    print("Reset minutes_today for all players")

def job():
    no_of_players=0
    cookies = {'sessionid': SESSION_ID}
        
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
                    # Convert dates_seeded_successfully to dates only (no time) for comparison
                    dates_seeded_successfully_only = fetch_days_of_type_in_current_month(SEED,doc)

                    # If today's date is already in dates_seeded_successfully, return early
                    if datetime.utcnow().date() in dates_seeded_successfully_only:
                        return
                    # add minutes to that player
                    vip.update_one(
                        {'steam_id_64': steam_id_64},
                        {'$inc': {'minutes_today': INTERVAL_IN_MINUTES}}  # Increment the 'minutes_today' field by interval
                    )
                    doc = vip.find_one({'steam_id_64': steam_id_64})  # Fetch the document again to get updated 'minutes_today'
                else:
                    # Create a new document for this player
                    vip.insert_one({
                        'discord_id': '',
                        'name': player_name,
                        'minutes_today': INTERVAL_IN_MINUTES,
                        'pending_award': False,
                        'steam_id_64': steam_id_64,
                        'participation': [],
                        'geforce_now': False,
                        'level': 'recruit',
                        'vip_this_month':False,
                    })
                    doc = vip.find_one({'steam_id_64': steam_id_64})  # Fetch the document to use below

                # Check award condition
                if (no_of_players >= 50 and doc['minutes_today'] >= MINUTES_REQUIREMENT_IF_SUCCESS) or (doc['minutes_today'] >= MINUTES_REQUIREMENT_IF_FAILURE):
                    print(f"vip attempt to award to {player_name}")
                    # Make external API call
                    # award_vip(steam_id_64,player_name)

    if(no_of_players!=0):
        print(f"Ran job - No of players : {no_of_players}")

# schedule.every(INTERVAL_IN_MINUTES).minutes.do(job)
# schedule.every(1).hours.do(check_and_promote_deemocrat)
# # schedule.every(1).hours.do(check_and_demote_aspiring)
# schedule.every().day.at("07:00").do(reset_minutes_today)  # Reset 'minutes_today' to 0 every day at 7AM
# job()
# # Keep the script running.
# while True:
#     schedule.run_pending()
#     time.sleep(1)

check_and_demote_aspiring()