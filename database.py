import warnings
warnings.filterwarnings('ignore')

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://ai:Machine_Learning128@192.168.0.112/movies_development?charset=utf8'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class Agent(db.Model):
    __tablename__ = 'agents'
    
    id = db.Column(db.Integer, primary_key=True)
    agent_name = db.Column(db.String(255))
    access_key = db.Column(db.String(255))
    created_at = db.Column(db.DateTime)

    def __init__(self, agent_name, access_key, created_at):
        self.agent_name = agent_name
        self.access_key = access_key
        self.created_at = created_at

    def __repr__(self):
        return '<Agent %r>' % self.agent_name

class Movie(db.Model):
    
    __tablename__ = 'movies'
    
    id = db.Column(db.Integer, primary_key = True)
    created_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime)
    tmdb_id = db.Column(db.Integer)
    poster_path = db.Column(db.String(255))
    director = db.Column(db.String(255))
    novel = db.Column(db.String(255))
    actors = db.Column(db.String(255))
    budget = db.Column(db.Integer)
    genres = db.Column(db.String(255))
    kwords = db.Column(db.Text)
    runtime = db.Column(db.Integer)
    title = db.Column(db.String(255))

    def __init__(self, created_at, updated_at, tmdb_id, poster_path, \
                 director, novel,actors,budget,genres,kwords,runtime, title):
        self.created_at = created_at 
        self.updated_at = updated_at
        self.tmdb_id = tmdb_id
        self.poster_path = poster_path
        self.director = director
        self.novel = novel
        self.actors = actors
        self.novel = novel
        self.actors = actors
        self.budget = budget
        self.genres = genres
        self.kwords = kwords
        self.runtime = runtime
        self.title = title
        
    def __repr__(self):
        return '<Movie %r>' % self.title
    
class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key = True)
    created_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime)
    agent_user_id = db.Column(db.Text)
    agent_id = db.Column(db.Integer)
    name = db.Column(db.String(255))
    email = db.Column(db.String(255))
    
    def __init__(self, created_at, updated_at, agent_user_id, agent_id, name, email):
        self.created_at = created_at
        self.updated_at = updated_at
        self.agent_user_id = agent_user_id
        self.agent_id = agent_id
        self.name = name
        self.email = email
        
    def __repr__(self):
        return '<User ' + self.agent_user_id + ' '+ str(self.agent_id) + '>'


    
class Recommendation(db.Model):
    
    __tablename__ = 'recommendations'
    
    id = db.Column(db.Integer, primary_key = True)
    created_at = db.Column(db.DateTime)
    user_id = db.Column(db.Integer)
    agent_id = db.Column(db.Integer)

    def __init__(self, user_id, agent_id, created_at):
        self.user_id = user_id
        self.agent_id = agent_id
        self.created_at = created_at
    
    def __repr__(self):
        return '<Recommendation %r>' % self.user_id + ' ' + str(self.agent_id)
    

class MovieRecommendation(db.Model):
    
    __tablename__ = 'movies_recommendations';
    
    id = db.Column(db.Integer, primary_key = True)
    recommendation_id = db.Column(db.Integer)
    movie_id = db.Column(db.Integer)
    created_at = db.Column(db.DateTime)
    
    def __init__(self, recommendation_id, movie_id, created_at):
        self.recommendation_id = recommendation_id
        self.movie_id = movie_id
        self.created_at = created_at

class Ticket(db.Model):
   
    __tablename__ = 'tickets'
    
    id = db.Column(db.Integer, primary_key = True)
    user_id = db.Column(db.Integer)
    movie_id = db.Column(db.Integer)
    created_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime)
    
    def __init__(self, user_id, movie_id, created_at, updated_at):
        self.user_id = user_id
        self.movie_id = movie_id
        self.created_at = created_at
        self.updated_at = updated_at
        

class Vkino(db.Model):

    __tablename__ = 'vkino_movies'
    
    id = db.Column(db.Integer, primary_key = True)
    vkino_id = db.Column(db.Integer)
    tmdb_fk_id = db.Column(db.Integer)
    is_actual = db.Column(db.Boolean)
    
    def __init__(self, vkino_id, tmdb_fk_id, is_actual):
        self.vkino_id = vkino_id
        self.tmdb_fk_id = tmdb_fk_id
        self.is_actual = is_actual
    
    
class PlanetaKino(db.Model):
    __tablename__ = 'planetakino_movies'
    
    id = db.Column(db.Integer, primary_key = True)
    planetakino_id = db.Column(db.Integer)
    tmdb_fk_id = db.Column(db.Integer)
    is_actual = db.Column(db.Boolean)
    def __init__(self, planetakino_id, tmdb_fk_id, is_actual):
        self.vkino_id = vkino_id
        self.tmdb_fk_id = tmdb_fk_id
        self.is_actual = is_actual
