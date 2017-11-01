import logging
logging.basicConfig(
    level = logging.INFO,
    format = '%(asctime)s %(message)s',
    datefmt = '%d/%m/%Y %H:%M:%S',
    filename = 'log/premieres_update.log'
)
logger = logging.getLogger(__name__)


import argparse
parser = argparse.ArgumentParser(description='Parse input string')
parser.add_argument('string', help='Input String', nargs='+')
args = parser.parse_args()
AGENT_NAME = args.string[0]
logger.info('Script started for update {} started'.format(AGENT_NAME))


from datetime import datetime
from bs4 import BeautifulSoup
import re
import requests
from requests.auth import HTTPBasicAuth
import time


from database import *
from utils import API_KEY, BASE_PATH, AGENTS_URL_DATA, SEARCH_PATH, agents_cleaning_data, flatten



def get(method, language = 'en', special_details = ''):
    link = BASE_PATH.format(method, special_details, API_KEY, language)
    r = requests.get(url = link)
    return r.json(), int(r.headers['X-RateLimit-Remaining'])

def collect_info(tmdb_id):
    ''' Collecting data about premiere movie on tmdb by tmdb_id 
        (title, poster, budget, runtime, genres, keywords, director, novel author, actors)
    '''
    title, limit = get(str(tmdb_id), language = 'ru')
    # if 'status_code' in title and title['status_code'] == 34:
    
    title = title['title']
    
    response, limit = get(str(tmdb_id)) # info
    
    poster_path = response['poster_path']
    budget = response['budget']
    runtime = response['runtime']
    genres = '|'.join([genre['name'] for genre in response['genres']]).lower()
        
    kwords, limit = get(str(tmdb_id), special_details = '/keywords')
    kwords = '|'.join([kword['name'] for kword in kwords['keywords']]).lower()
    
    
    credits, limit = get(str(tmdb_id), special_details = '/credits')
    director = '|'.join([item['name'] for item in credits['crew'] if item['job'] == 'Director'][:NUM_OF_PEOPLE])
    novel = '|'.join([item['name'] for item in credits['crew'] if item['job'] == 'Novel'][:NUM_OF_PEOPLE])
    actors = '|'.join([item['name'] for item in credits['cast']][:NUM_OF_PEOPLE])
    
    result = dict(
        poster_path = poster_path,
        director = director,
        novel = novel,
        actors = actors,
        budget = budget,
        runtime = runtime,
        genres = genres,
        kwords = kwords,
        title = title
    )    
    return result


error_movies = []
not_found = []
not_matched = []
not_matched_at_all = []

def search(queries):
    '''queries = [query_ukr, query_en]'''
    results = []
    limit = ''
    for query in queries:
        if query != '':
            response = requests.get(SEARCH_PATH.format(query, API_KEY))
            if response.status_code == 200:
                result = response.json()['results']
                limit = int(response.headers['X-RateLimit-Remaining']) 
            else:
                result = []
        else:
            result = []
        results.append(result)
    return results, limit


def get_data_for_search(agent_name, movies_to_add, auth):
    '''
        Search data on agent_name website for matching movies 
        with tmdb
        returns [id_,name,nameoriginal,year],
    '''
    movies_to_add_data = []
    for premiere in movies_to_add:
        id_ = int(premiere.find('id').text) if premiere.find('id') is not None else int(premiere.attrs['id'])
        name = premiere.find('namealt').text.lower() if auth else premiere.find('name').text.lower()
        name = re.sub(agents_cleaning_data[agent_name]['name_age_pattern'], '', name)
        nameoriginal = premiere.find('nameoriginal').text.lower()
        year = premiere.find('year').text if premiere.find('year') is not None else ''
        for w in agents_cleaning_data[agent_name]['words_to_drop']:
            name = re.sub(w, '', name).strip()
            nameoriginal = re.sub(w, '', nameoriginal).strip()
        if name != '':
            if year != '':
                movies_to_add_data.append([id_, name, nameoriginal,year])
            else:
                movies_to_add_data.append([id_, name, nameoriginal])
        
    return movies_to_add_data


def search_on_tmdb(list_to_search, auth):
    '''
        returns 5 lists:
        search_results
        premieres_idx,
        main_premieres_titles, 
        orig_premieres_titles, 
        premieres_years
    '''
    
    search_results = []
    premieres_idx = [m[0] for m in list_to_search]
    main_premieres_titles = [m[1] for m in list_to_search]
    orig_premieres_titles = [m[2] for m in list_to_search]
    premieres_years = [m[3] for m in list_to_search] if auth else []
    logger.info('Searching movies on tmdb.')
    try:
        for movie in list_to_search:
            try:
                res, limit = search([movie[1], movie[2]])
                search_results.append(res)
                if limit is str:
                    continue
                if limit is not str and (limit <= 2): 
                    time.sleep(TMDB_TIME_LIMIT)
            except Exception as ex:
                template = "An exception in search cycle of type {0} occurred. Arguments:\n{1!r}"
                message = template.format(type(ex).__name__, ex.args)
                logger.exception(message)
                error_movies.append(movie[0])
                logger.info('{} was added to error movies and in db will be with no tmdb value.'.format(movie[0]))
                continue
                
    except Exception as ex:
        template = "An exception of type {0} occurred. Arguments:\n{1!r}"
        message = template.format(type(ex).__name__, ex.args)
        logger.exception(message)
    
    return search_results, premieres_idx, main_premieres_titles, orig_premieres_titles, premieres_years


def matching(search_results, premieres_idx, main_premieres_titles, orig_premieres_titles, premieres_years):
    ''' Cleaning search results and matching agent movies with tmdb movies '''
    idx = []
    for main_title, orig_title, pk_id, year, results in zip(main_premieres_titles, orig_premieres_titles,premieres_idx, premieres_years, search_results):
        try:
            if not results[0] and not results[1]:
                not_found.append(pk_id)
                logger.info('{} was added to not_found movies and in db will be with no tmdb value.'.format(pk_id))
                continue
            elif len(results[0]) == 1:
                idx.append([results[0][0]['id'], pk_id])
                continue
            elif len(results[0]) > 1 and len(results[1]) != 0:
                idx_1 = [item['id'] for item in results[0]]
                idx_2 = [item['id'] for item in results[1]]
                common = list(set(idx_1) & set(idx_2))
                if len(common) == 1:
                    idx.append([common[0], pk_id])
                    continue
                else:
                    main_results_by_date = [elem for elem in results[0] if elem['id'] in common]
                    main_results_by_date = [result for result in results[0] if result['release_date'].split('-')[0] == year]
                
                    if len(main_results_by_date) == 1:
                        idx.append([main_results_by_date[0]['id'], pk_id])
                        continue
                    try:
                        main_results_by_date = list(sorted(main_results_by_date, key = lambda x: x['release_date'], reverse = True))[0]
                        id = main_results_by_date['id']
                        idx.append([id, pk_id])
                        continue 
                    except:
                        pass # оно должно найтись дальше
            elif len(results[0]) == 0:
                if len(results[1]) == 1:
                    idx.append([results[1][0]['id'],pk_id])
                    continue
                else:
                    if year != '' and int(year) > 1975: # просто потому что
                        en_results_by_date = [result for result in results[1] if result['release_date'].split('-')[0] == year]
                        if len(en_results_by_date) == 1:
                            idx.append([en_results_by_date[0]['id'],pk_id])
                            continue
                        else:
                            for m in en_results_by_date:
                                if len(m['original_title'].lower()) == len(orig_title):
                                    idx.append([m['id'], pk_id])
                                    break
                        continue
                    else:
                        en_results_by_date = list(sorted(results[1], key = lambda x: x['release_date'], reverse = True))[0]
                        id = en_results_by_date['id']
                        idx.append([id, pk_id])
            elif len(results[1]) == 0:
                if len(results[0]) == 1:
                    idx.append([results[0][0]['id'],pk_id])
                    continue
                else:
                    if year != '' and int(year) > 1975: # ?????
                        main_results_by_date = [result for result in results[0] if result['release_date'].split('-')[0] == year]
                        if len(main_results_by_date) == 1:
                            idx.append([main_results_by_date[0]['id'],pk_id])
                            continue
                        else:
                            for m in main_results_by_date:
                                if len(m['original_title'].lower()) == len(orig_title):
                                    idx.append([m['id'], pk_id])
                                    break
                        continue
                    else:
                        main_results_by_date = list(sorted(results[0], key = lambda x: x['release_date'], reverse = True))[0]
                        id = main_results_by_date['id']
                        idx.append([id, pk_id])
            else:
                not_matched_at_all.append(pk_id)
                logger.info('{} was added to not_matched_at_all movies and in db will be with no tmdb value.'.format(pk_id))
        except Exception as ex:
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            not_matched.append(pk_id)
            logger.exception(message)
            logger.info('{} was added to not_matched movies and in db will be with no tmdb value.'.format(pk_id))
            continue   
    
    return idx



def write(true_tmdb_idx, db_name, column_name, movie_status, logger = None):
    for tmdbid, pkid in true_tmdb_idx:
        movie = Movie.query.filter_by(tmdb_id = 4568).first()
        if movie is None:
            new_movie_data = collect_info(tmdbid)
            logger.info('Adding movie {} to movies...'.format(tmdbid))
            logger.info('Started collecting info...')
            logger.info('Collected')
            new_movie = Movie(datetime.now(), datetime.now(), tmdbid, new_movie_data['poster_path'], new_movie_data['director'],new_movie_data['novel'], new_movie_data['actors'],new_movie_data['budget'],new_movie_data['genres'],new_movie_data['kwords'],new_movie_data['runtime'],new_movie_data['title'])
            try:   
                db.session.add(new_movie)
                db.session.commit()
            except Exception as e:
                if type(e).__name__ == 'IntegrityError':
                    db.session.rollback()
                    logger.error('IntegrityError')
                    continue
            finally:
                logger.info('Added {} to db.'.format(tmdbid))
        else:
            logger.info('Movie {} is in db, continuing.'.format(tmdbid))
            
    logger.info('Updating {} table...'.format(db_name))
    
    for tmdbid, pkid in true_tmdb_idx:
        if db_name == 'vkino_movies':
            new_movie = Vkino(pkid, tmdbid, movie_status)
            try:   
                db.session.add(new_movie)
                db.session.commit()
            except Exception as e:
                if type(e).__name__ == 'IntegrityError':
                    db.session.rollback()
                    logger.error('IntegrityError')
                    continue
            finally:
                logger.info('Added {} to db.'.format(tmdbid))
                
                
                
                
class Update():
    def __init__(self, agent_name):
        self.agent_name = agent_name
        self.db_name = agent_name + '_movies'
        self.column_name = agent_name + '_id'
    
    def check_updates(self):
        logger.info('-' * 120)
        logger.info('Checking premieres for updates...')
        
        actual_movies = Vkino.query.filter_by(is_actual = 1).all()
        current_premieres_ids = set([movie.vkino_id for movie in actual_movies])
        
        movies_url = AGENTS_URL_DATA[self.agent_name]['url']
        auth = AGENTS_URL_DATA[self.agent_name]['auth']
        actual_indicator = AGENTS_URL_DATA[self.agent_name]['actual_indicator']
        premieres_xml = []
        premieres_movie_metadata = []
        
        if auth is None:
            soup = requests.get(movies_url).text
            soup = BeautifulSoup(soup, 'lxml')
            for path in AGENTS_URL_DATA[self.agent_name]['path']:
                premieres_xml.append(soup.select(path))
            premieres_xml = flatten(flatten(premieres_xml))    
            for premiere in premieres_xml:
                if premiere.find(AGENTS_URL_DATA[self.agent_name]['actual_indicator']):
                    premieres_movie_metadata.append(premiere)
            new_premieres_movies_ids = set([int(movie.id.text) for movie in premieres_movie_metadata])
        else:
            soup = requests.get(movies_url, auth = HTTPBasicAuth(auth['login'], auth['password'])).text
            soup = BeautifulSoup(soup, 'lxml')
            for path in AGENTS_URL_DATA[self.agent_name]['path']:
                premieres_xml.append([show for show in soup.select(path)[0].contents]) 
            premieres_movie_metadata = flatten(premieres_xml)
            
            new_premieres_movies_ids = set([int(movie.attrs['id']) for movie in premieres_movie_metadata])
            
            
        if len(current_premieres_ids - new_premieres_movies_ids) > 0:
            removed = tuple(current_premieres_ids - new_premieres_movies_ids)
            logger.info('There were removed {} movies'.format(removed))
            for item in removed:
                removed_item = Vkino.query.filter_by(vkino_id = item).first()
                removed_item.is_actual = 0
                db.session.commit()
            logger.info('All removed status were updated to 0')
        
        
        if len(new_premieres_movies_ids - current_premieres_ids) > 0:
            added = tuple(new_premieres_movies_ids - current_premieres_ids)
            logger.info('There were added {} movies to premieres'.format(added))
            list_to_add = []
            # если оно есть в бд но временно его убрали
            for movie in added:
                added_item = Vkino.query.filter_by(vkino_id = movie).first()
                if added_item is None:
                    list_to_add.append(movie)
                else:
                    added_item.is_actual = 1
                    db.session.commit()
                logger.info('Updated status for movie {}'.format(movie))
                        
            if not list_to_add:
                logger.info('Ok. Just updated status.')
                return 'Ok. Just updated status.\n'            
            
                    
            to_add = [premiere for premiere in premieres_movie_metadata
                      if ('id' in premiere.attrs and int(premiere.attrs['id']) in list_to_add)
                      or (premiere.id is not None and int(premiere.id.text) in list_to_add)]
            
            premieres_search_metadata = get_data_for_search(self.agent_name,to_add,auth)
            
            search_results, premieres_idx, main_premieres_titles, orig_premieres_titles, premieres_years = search_on_tmdb(premieres_search_metadata,auth)
            logger.info('Got search results')
            
            true_tmdb_idx = matching(search_results, premieres_idx, main_premieres_titles, orig_premieres_titles, premieres_years)    
            
            logger.info('Search results cleaned. {} from {}'.format(len(true_tmdb_idx),len(premieres_search_metadata)))
            
            if not (not true_tmdb_idx):
                write(true_tmdb_idx, self.db_name, self.column_name, 1, logger)
            else:
                logger.info('There was no info about new premieres.')
                logger.info(list_to_add)
            
        if len(current_premieres_ids - new_premieres_movies_ids) == 0:
            logger.info('No changes.')

        none_movies = not_found + error_movies + not_matched + not_matched_at_all

        for movie in none_movies:
            row = tuple([movie, None, 0])
            not_matched_movie = Vkino(movie, None, 0)
            try:
                db.session.add(not_matched_movie)
                db.session.commit()
            except Exception as e:
                if type(e).__name__ == 'IntegrityError':
                    db.session.rollback()
                    logger.error('IntegrityError')
                    continue
                else:
                    db.session.rollback()
                    raise
            finally:
                logger.info('Inserted {}.'.format(movie))
        logger.info('-' * 120)    
        return 'Ok'  
    
    
agent_db_update = Update(AGENT_NAME)
agent_db_update.check_updates()