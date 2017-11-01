import logging
logging.basicConfig(
    level = logging.INFO,
    format = '%(asctime)s %(message)s',
   datefmt = '%d/%m/%Y %H:%M:%S',
    filename = 'log/app.log'
)

logger = logging.getLogger(__name__)
logger.info('-' * 120)
logger.info('{} started'.format('app'))
print('1')
import os
import time
from datetime import datetime
from recommender import Recommender 
from flask import request, jsonify, Response 
from flask import  abort, render_template_string, send_from_directory

from database import *


def get_user_movies(user_id): 
    tickets = Ticket.query.filter_by(user_id = user_id).all()
    user_movies = [ticket.movie_id for ticket in tickets]
    return user_movies

@app.errorhandler(403)
def accessKeyRequired(not_in_db = False):
    code = 403
    if not_in_db:
        description = '403 Forbidden. Unknown access key.\n'
        logger.error(description)
    else:
        description = '403 Forbidden. Specify Access Key.\n'
        logger.error(description)
    return description, code

@app.errorhandler(400)
def badRequest(user = False, data = ''):
    code = 400
    if user:
        description = '400 Bad Request. Unknown user.\n'
        logger.error(description)
    else:
        description = '400 Bad Request. Wrong input.\n'
        logger.error(description)
    if data != '':
        description = data
    return description, code

@app.route('/')
def f():
    return 'It works'

@app.route('/tickets', methods=['POST'])
def tickets():
    if request.method == 'POST':
        data = request.get_json()
    try:
        access_key = str(data['access_key'])
    except:
        return accessKeyRequired()
    
    agent = Agent.query.filter_by(access_key = access_key).first() 
    if agent is None: return accessKeyRequired(not_in_db = True)
    
    try:
        agent_user_id = str(data['user_id'])  
    except:
        return badRequest()
    
    if type(data['movies']) is not list:
        return badRequest()
    else:
        input_movies = set(data['movies'])    
    
    user = User.query.filter_by(agent_user_id = agent_user_id, agent_id = agent.id).first() 
    new_user = False if user is not None else True
    print(new_user)    
    if new_user:
        email = str(data['email']) if 'email' in data else None
        username = str(data['username']) if 'username' in data else None
        
        user = User(datetime.now(), datetime.now(), agent_user_id, agent.id, username, email)
        db.session.add(user)
        db.session.commit()
    
    prev_user_movies = Ticket.query.filter_by(user_id = user.id).all()
    if prev_user_movies is not None: 
        user_movies = set([ticket.movie_id for ticket in Ticket.query.filter_by(user_id = user.id).all()])
        movies_to_add = input_movies - user_movies
    else:
         movies_to_add = input_movies
    if not movies_to_add and bool(user_movies):
        return 'All tickets already in db\n'
    
    for movie in movies_to_add:
        ticket = Ticket(user.id, movie, datetime.now(), datetime.now())
        print(movie)
        db.session.add(ticket)
        db.session.commit()
    return 'Ok\n'

@app.route('/recommendations', methods = ['GET'])
def recommendations():
    print('2')
   # print(request.args)
    data = request.args
    try:
        access_key = str(dict(data)['access_key'][0])
    except:
        return accessKeyRequired()
    
    agent = Agent.query.filter_by(access_key = access_key).first() 
    if agent is None: return accessKeyRequired(not_in_db = True)
    try:
        agent_user_id = str(data['user_id'])
    except:
        return badRequest()
    
    user = User.query.filter_by(agent_user_id = agent_user_id, agent_id = agent.id).first()
    if user is None: return badRequest(user = True)
    
    user_movies = get_user_movies(user.id)
    logger.info(user_movies)
    print(user_movies) 
    if not user_movies: return 'User has no movies'#, Response(403) jsonify([])
    
    if not Recommendation.query.filter_by(user_id = user.id).all():
        print('No recommendations before')
    else:
        print('Some movies were recommender before')
        prev_rec_dates = []
        for rec in Recommendation.query.filter_by(user_id = user.id).all():
            prev_rec_dates.append((datetime.now() - rec.created_at).total_seconds() / 3600)
        last_rec_date = min(prev_rec_dates)
        print(last_rec_date)
        if last_rec_date <= 24:
            print('Latest recommendation was today. Return empty list')
            return jsonify(recommendations = [])
    
    if agent.agent_name == 'vkino':
        user_tmdb_movies = []
        for movie in user_movies:
            tmdbid = Vkino.query.filter_by(vkino_id = movie).first().tmdb_fk_id
            if tmdbid is None:
                continue
            else:
                user_tmdb_movies.append(tmdbid)
    if not user_tmdb_movies:
        return jsonify(recommendations = [])
    print(user_tmdb_movies)
    min_num_of_recs = 3

    rs = Recommender(user_tmdb_movies, agent.agent_name + '_movies', agent.agent_name + '_id', user.id)
    rs.tmdb_input_info()
    rs.form_characteristics()
    result = rs.get_recommendations()
    #print(result[0])
    if not result:
        return jsonify(recommendations = result)
    
    agent_premiere_idx = [movie['pk_id'] for movie in result[:min_num_of_recs]]
    print(agent_premiere_idx)
    if type(agent_premiere_idx) is list:
        r = Recommendation(user.id, agent.id, datetime.now())
        db.session.add(r)
        db.session.commit()
        for movie in agent_premiere_idx:
            mr = MovieRecommendation(r.id, movie, datetime.now())
            db.session.add(mr)
            db.session.commit()
            
    return jsonify(recommendations = agent_premiere_idx, recommendation_id = r.id)


from flask import url_for
@app.route('/')
def index():
    return '<img src=' + url_for('static') + '>' 



app.wsgi_app = ProxyFix(app.wsgi_app)
port = int(os.getenv('PORT', 5000))

if __name__ == "__main__":
    app.run(
        host = '127.0.0.1',
        port = port
    )
