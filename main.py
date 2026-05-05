import grequests
import requests
import pandas as pd
import numpy as np
import sqlite3
import json



headers = {
    'accept': 'application/json, text/plain, */*',
    'accept-language': 'en-US,en;q=0.9',
    'if-modified-since': 'Wed, 29 Apr 2026 01:13:20 GMT',
    'priority': 'u=1, i',
    'referer': 'https://www.espn.com/wnba/schedule/_/date/20250502',
    'sec-ch-ua': '"Google Chrome";v="147", "Not.A/Brand";v="8", "Chromium";v="147"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"macOS"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36',
}

params = {
    '_xhr': 'pageContent',
    'refetchShell': 'false',
    'offset': '-07:00',
    'original': 'date=20250502',
    'date': '20250502',
}

response = requests.get('https://www.espn.com/wnba/schedule/_/date/20250502', params=params, headers=headers)

#with open('file.json', 'w') as f:
#    f.write(json.dumps(response.json()))






data = response.json()


## game meta data
dates = pd.Series(data['events'].keys())


rows = []
for date in dates:
    for event in data['events'][date]:
        competitors = event['competitors']

        if competitors[0]['isHome']:
            home = competitors[0]
            away = competitors[1]

        else:
            home = competitors[1]
            away = competitors[0]


        rows.append({
            'game_date': pd.to_datetime(event['date']),
            'game_id': int(event['id']), 
            'season': int(event['season']['year']), 
            'season_type': event['season']['slug'],
            'home_team': home['name'], 
            'home_id': int(home['id']),
            'away_team': away['name'], 
            'away_id': int(away['id']),
            'home_score': int(home['score']), 
            'away_score': int(away['score']), 
            'neutral_site': bool(event['neutralSite']), 
            'completed': bool(event['completed'])
        })


pd.DataFrame(rows)



## box scores

headers = {
    'accept': '*/*',
    'accept-language': 'en-US,en;q=0.9',
    'origin': 'https://www.espn.com',
    'priority': 'u=1, i',
    'referer': 'https://www.espn.com/',
    'sec-ch-ua': '"Google Chrome";v="147", "Not.A/Brand";v="8", "Chromium";v="147"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"macOS"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-site',
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36',
}

params = {
    'region': 'us',
    'lang': 'en',
    'contentorigin': 'espn',
    'event': '401761558',
    'features': 'ng',
}

response = requests.get(
    'https://site.web.api.espn.com/apis/site/v2/sports/basketball/wnba/summary',
    params=params,
    headers=headers,
)

data = response.json()
players_boxscore = data['boxscore']['players']



player_box_score_rows = []
for i in range(len(players_boxscore)):
    team = players_boxscore[i]['team']['displayName']

    statistics = players_boxscore[i]['statistics'][0]['athletes']
    for j in range(len(statistics)):   

        athlete = statistics[j]['athlete']
        stats = statistics[j]['stats']
        metadata = statistics[j]
    

        if stats:
            fg_made, fg_missed = stats[2].split('-')
    
        if not stats:
            stats = pd.Series(pd.NA, index = range(14))
            fg_made, fg_missed = pd.NA, pd.NA
            


        fg_made, fg_attempted = stats[2].split('-')
        player_box_score_rows.append({
            'player': athlete['displayName'], 
            'player_team': team,
            'player_id': athlete['id'], 
            'player_guid': athlete['guid'], 
            'player_position': athlete['position']['displayName'], 
            'player_active': metadata['active'], 
            'player_starter': metadata['starter'],
            'player_did_not_play': metadata['didNotPlay'], 
            'reason': metadata['reason'], 
            'ejected': metadata['ejected'], 
            'minutes': stats[0], 
            'points': stats[1], 
            'field_goals_made': fg_made, 
            'field_goals_attempted': fg_attempted
        })

print(pd.DataFrame(player_box_score_rows))



