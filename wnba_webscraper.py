import grequests
import pandas as pd
import sqlite3

class WNBAScraper():
    def __init__(self, start_date, end_date):
        self.start_date = str(start_date)
        self.end_date = str(end_date)
        dates = [d for d in pd.date_range(self.start_date, self.end_date).strftime('%Y%m%d').tolist() if d[4:6] in ('05', '06', '07', '08', '09', '10')]

        base_headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'en-US,en;q=0.9',
            'if-modified-since': 'Wed, 29 Apr 2026 01:13:20 GMT',
            'priority': 'u=1, i',
            'sec-ch-ua': '"Google Chrome";v="147", "Not.A/Brand";v="8", "Chromium";v="147"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36',
        }

        base_params = {
            '_xhr': 'pageContent',
            'refetchShell': 'false',
            'offset': '-07:00',
        }

            
        reqs = [
            grequests.get(
                url=f'https://www.espn.com/wnba/schedule/_/date/{date}',
                params={**base_params, 'original': f'date={date}', 'date': date},
                headers={**base_headers, 'referer': f'https://www.espn.com/wnba/schedule/_/date/{date}'}
            )
            for date in dates
        ]

        responses = grequests.map(reqs)


        ## game data
        rows = []
        last_date = None
        for response in responses:
            if response.status_code != 200:
                continue


            data = response.json()
            
            dates = pd.Series(data['events'].keys())
            


            for date in dates:
                if last_date is not None and pd.to_datetime(date) <= pd.to_datetime(last_date):
                    continue

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

            last_date = dates.iloc[-1]


        self.game_data = pd.DataFrame(rows)


        self.game_ids = pd.unique(self.game_data[self.game_data['completed']]['game_id'])


        


        game_data_headers = {
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

        game_data_base_params = {
            'region': 'us',
            'lang': 'en',
            'contentorigin': 'espn',
            'features': 'ng',
        }



        params_list = [
            {**game_data_base_params, 'event': game_id}
            for game_id in self.game_ids
        ]


        url = 'https://site.web.api.espn.com/apis/site/v2/sports/basketball/wnba/summary'

        reqs = (grequests.get(url,
                            headers = game_data_headers, 
                            params = game_params) for game_params in params_list)

        self.game_data_responses = grequests.map(reqs)

    def game_meta_data(self):
        return self.game_data

    def player_box_scores(self):
        responses = self.game_data_responses
        player_box_score_rows = []
        
        
        for response in responses:
            if (response.status_code != 200) or (response is None):
                continue

        for i in range(len(responses)):
            data = responses[i].json()


            if not data['header']['competitions'][0]['status']['type']['completed']:
                continue

            players_boxscore = data['boxscore']['players']
            game_info = data['header']



            for j in range(len(players_boxscore)):
                team = players_boxscore[j]['team']['displayName']
                game_id = game_info['id']

                statistics = players_boxscore[j]['statistics'][0]['athletes']
                for k in range(len(statistics)):   
                    athlete = statistics[k]['athlete']
                    stats = statistics[k]['stats']
                    metadata = statistics[k]
                

                    if stats:
                        try:
                            fg_made, fg_attempted = stats[2].split('-')
                        except:
                            print(game_id)

                        try:
                            threes_made, threes_attempted = stats[3].split('-')
                        except:
                            print(game_id)
                        try:
                            free_throws_made, free_throws_attempted = stats[4].split('-')
                        except:
                            print(game_id)

                
                    if not stats:
                        stats = pd.Series(pd.NA, index = range(14))
                        fg_made, fg_attempted = pd.NA, pd.NA
                        threes_made, threes_attempted = pd.NA, pd.NA
                        free_throws_made, free_throws_attempted = pd.NA, pd.NA



                    
                    try:
                        reason = metadata['reason']
                    except KeyError:
                        reason = pd.NA

                    try:
                        ejected = metadata['ejected']
                    except KeyError:
                        ejected = pd.NA
                        


                    player_box_score_rows.append({
                        'game_id': game_id,
                        'player': athlete['displayName'],
                        'player_team': team,
                        'player_id': athlete['id'],
                        'player_guid': athlete['guid'],
                        'player_position': athlete['position']['displayName'],
                        'player_active': bool(metadata['active']),
                        'player_starter': bool(metadata['starter']),
                        'player_did_not_play': bool(metadata['didNotPlay']),
                        'reason': reason,
                        'ejected': bool(ejected),
                        'minutes': stats[0],
                        'points': stats[1],
                        'field_goals_made': fg_made,
                        'field_goals_attempted': fg_attempted,
                        'threes_made': threes_made,
                        'threes_attempted': threes_attempted,
                        'free_throws_made': free_throws_made,
                        'free_throws_attempted': free_throws_attempted,
                        'rebounds': stats[5],
                        'assists': stats[6],
                        'turnovers': stats[7],
                        'steals': stats[8],
                        'blocks': stats[9],
                        'offensive_rebounds': stats[10],
                        'defensive_rebounds': stats[11],
                        'fouls': stats[12],
                        'plus_minus': stats[13]
                    })



        player_box_scores_df = pd.DataFrame(player_box_score_rows)
        

        ## correct dtypes
        int_cols = ['game_id',
                    'player_id', 
                    'minutes', 
                    'points', 
                    'field_goals_made', 
                    'field_goals_attempted', 
                     'threes_made', 
                     'threes_attempted', 
                     'free_throws_made', 
                     'free_throws_attempted', 
                     'rebounds', 
                     'assists', 
                     'turnovers', 
                     'steals', 
                     'blocks', 
                     'offensive_rebounds', 
                     'defensive_rebounds', 
                     'fouls', 
                     'plus_minus']
        
        player_box_scores_df[int_cols] = player_box_scores_df[int_cols].apply(pd.to_numeric, errors = 'coerce').astype('Int64')


        ## pk
        player_box_scores_df['player_game_id'] = player_box_scores_df['game_id'].astype(str) + '-' + player_box_scores_df['player']
        player_box_scores_df = player_box_scores_df.set_index('player_game_id')


        return player_box_scores_df

    def team_box_scores(self):
        responses = self.game_data_responses
        team_box_score_rows = []
        
        for response in responses:
            if (response.status_code != 200) or (response is None):
                continue

        for i in range(len(responses)):
            data = responses[i].json()

            if not data['header']['competitions'][0]['status']['type']['completed']:
                continue

            team_box_score = data['boxscore']['teams']
            game_data = data['header']

            for j in range(len(team_box_score)):
                team_name = team_box_score[j]['team']['displayName']
                team_id = team_box_score[j]['team']['id']


                home_away = team_box_score[j]['homeAway']


                stats = team_box_score[j]['statistics']

                fg_made, fg_attempted = stats[0]['displayValue'].split('-')
                threes_made, threes_attempted = stats[2]['displayValue'].split('-')
                free_throws_made, free_throws_attempted = stats[4]['displayValue'].split('-')


                team_box_score_rows.append({
                    'game_id': game_data['id'],
                    'team_name': team_name,
                    'team_id': team_id,
                    'fg_made': fg_made,
                    'fg_attempted': fg_attempted,
                    'fg_pct': stats[1]['displayValue'],
                    'threes_made': threes_made,
                    'threes_attempted': threes_attempted,
                    'threes_pct': stats[3]['displayValue'],
                    'free_throws_made': free_throws_made,
                    'free_throws_attempted': free_throws_attempted,
                    'free_throws_pct': stats[5]['displayValue'],
                    'total_rebounds': stats[6]['displayValue'],
                    'offensive_rebounds': stats[7]['displayValue'],
                    'defensive_rebounds': stats[8]['displayValue'],
                    'assists': stats[9]['displayValue'],
                    'steals': stats[10]['displayValue'],
                    'blocks': stats[11]['displayValue'],
                    'turnovers': stats[12]['displayValue'],
                    'team_turnovers': stats[13]['displayValue'],
                    'total_turnovers': stats[14]['displayValue'],
                    'technical_fouls': stats[15]['displayValue'],
                    'total_technical_fouls': stats[16]['displayValue'],
                    'flagrant_fouls': stats[17]['displayValue'],
                    'turnover_points': stats[18]['displayValue'],
                    'fastbreak_points': stats[19]['displayValue'],
                    'points_in_paint': stats[20]['displayValue'],
                    'fouls': stats[21]['displayValue'],
                    'largest_lead': stats[22]['displayValue'],
                    'home_away': home_away
                })


        team_box_scores_df = pd.DataFrame(team_box_score_rows)

        int_cols = ['game_id', 
                    'team_id', 
                    'fg_made', 
                    'fg_attempted',
                    'threes_made', 
                    'threes_attempted',
                    'free_throws_made', 
                    'free_throws_attempted',
                    'total_rebounds', 
                    'offensive_rebounds', 
                    'defensive_rebounds',
                    'assists', 
                    'steals', 
                    'blocks', 
                    'turnovers', 
                    'team_turnovers',
                    'total_turnovers', 
                    'technical_fouls', 
                    'total_technical_fouls',
                    'flagrant_fouls',
                    'turnover_points', 
                    'fastbreak_points',
                    'points_in_paint', 
                    'fouls', 'largest_lead']

        team_box_scores_df[int_cols] = team_box_scores_df[int_cols].apply(pd.to_numeric, errors = 'coerce').astype('Int64')

        float_cols = [
            'free_throws_pct', 
            'threes_pct', 
            'fg_pct'
        ]
        team_box_scores_df[float_cols] = team_box_scores_df[float_cols].apply(pd.to_numeric, errors = 'coerce').astype('Float64')


        ## pk
        team_box_scores_df['team_game_id'] = team_box_scores_df['game_id'].astype(str)  + '-' + team_box_scores_df['team_name']
        team_box_scores_df = team_box_scores_df.set_index('team_game_id')

        return team_box_scores_df

    def pbp(self):
        responses = self.game_data_responses
        rows = []
        for response in responses:
            if (response is None) or (response.status_code != 200):
                continue

            
            data = response.json()
            if not data['header']['competitions'][0]['status']['type']['completed']:
                continue


            pbp = data['entities']['plays']
            game_id = response.json()['header']['id']

            for play_number, play_id in enumerate(pbp):
                play = pbp[play_id]
                play_type = pbp[play_id]['type']
                
                
                subtype, subtype_id = pd.NA, pd.NA

                if play_type.get('category'):
                    subtype = pbp[play_id]['type']['category']['slug']
                    subtype_id = pbp[play_id]['type']['category']['id']

                scorer, assister = pd.NA, pd.NA
                if play.get('participants'):
                    for participant in play['participants']:
                        role = participant['type']
                        key = participant['athlete']['$key']

                        if role == 'scorer':
                            scorer = key

                        elif role == 'assister':
                            assister = key

                rows.append({
                    'game_id': game_id,
                    'play_number': play_number, 
                    'play_id': play_id,  
                    'team_id': play['team']['$key'],
                    'scorer': scorer, 
                    'assister': assister,
                    'text': play['text'], 
                    'type': play_type['slug'], 
                    'type_id': play_type['id'],
                    'subtype': subtype, 
                    'subtype_id': subtype_id,
                    'home_score': play['homeScore'], 
                    'away_score': play['awayScore'], 
                    'score_value': play['scoreValue'], 
                    'scoring_play': play['scoringPlay'], 
                    'points_attempted': play['pointsAttempted'], 
                    'shooting_play': play['shootingPlay'],
                    'period': play['period']['number'], 
                    'seconds_remaining_quarter': play['clock']['value'],
                    'clock_display': play['clock']['displayValue'], 
                    'coord_x': play['coordinate']['x'], 
                    'coord_y': play['coordinate']['y'], 
                    'wallclock': pd.to_datetime(play['wallclock'])
                })


        pbp_df = pd.DataFrame(rows)

        int_cols = ['game_id', 
                    'play_number', 
                    'play_id', 
                    'team_id', 
                    'scorer', 
                    'assister', 
                    'type_id', 
                    'subtype_id', 
                    'home_score', 
                    'away_score', 
                    'score_value', 
                    'points_attempted', 
                    'period', 
                    'coord_x', 
                    'coord_y']
        
        float_cols = ['seconds_remaining_quarter']

        pbp_df[int_cols] = pbp_df[int_cols].apply(pd.to_numeric, errors = 'coerce').astype('Int64')
        pbp_df[float_cols] = pbp_df[float_cols].apply(pd.to_numeric, errors = 'coerce').astype('Float64')


        ## set pk
        pbp_df = pbp_df.set_index('play_id')
        return pbp_df

    def db_writer(self, db_path, unique_keys, tables):
        conn = sqlite3.connect(db_path)
        for table_name, df in tables.items():
            df.to_sql(name = table_name, con = conn, if_exists = 'append')
            conn.execute(f'''
                        delete from {table_name}
                        where rowid not in (
                            select min(rowid)
                            from {table_name}
                            group by {unique_keys[table_name]}
                            )
                        ''')
        conn.commit()
        conn.close()
