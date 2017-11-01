import logging
logging.basicConfig(level = logging.INFO,format = '%(asctime)s %(message)s',
datefmt = '%d/%m/%Y %H:%M:%S',
filename = 'log/recommender.log')

logger = logging.getLogger(__name__)
logger.info('-' * 120)
logger.info('Script {} started'.format('recommender'))


from sklearn.metrics.pairwise import cosine_similarity
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from gensim.models import word2vec
from collections import Counter
from sklearn.preprocessing import MinMaxScaler
import numpy as np


from database import *
from utils import flatten

all_genres = np.array([
    'action', 'adventure', 'animation', 'comedy', 'crime', 'documentary', 'drama', 'family',\
    'fantasy', 'history', 'horror', 'music', 'mystery','romance', 'science fiction', 'thriller', 'war', 'western'])

sw = set(stopwords.words('english'))

def lowercase(x):
    if str(x) != 'nan' and x is not None:
        return x.lower()
    else:
        return None
    
def tokenization(kw_string):
    ''' Tokenization of keywords '''
    if isinstance(kw_string, float) or kw_string is None: 
        return None
    new_str = ''
    for s in kw_string.split('|'):
        arr = [w for w in word_tokenize(s) if w not in sw and w != '\'' and w != '\'s']
        for word in arr:
            new_str += word
            new_str += '|'
    kw_list = new_str.split('|')
    kw_list.remove('')
    return '|'.join(kw_list) 

def movies_preproc(movie):
    movie['kwords'] = tokenization(lowercase(movie['kwords']))
    movie['genres'] = lowercase(movie['genres'])
    movie['actors'] = lowercase(movie['actors'])
    return movie

def form_kwords_sentences(input_movies, model):
    unknown = []
    for index, kwords in enumerate(input_movies):
        for kword in kwords:
            if kword not in model.wv.vocab and kword != '':
                unknown.append(index)

    kwords_sentences = []
    for index in set(unknown):
        kwords_sentences.append(input_movies[index])
    return kwords_sentences

def compute_tf(kwords):
    tf_text = Counter(kwords)
    for key in tf_text:
        tf_text[key] = tf_text[key]/float(len(kwords))
    return dict(tf_text)

def compute_idf(word, corpus):
     return np.log10(len(corpus)/sum([1 for i in corpus if word in i])) 
    
def kwords2vec(kwords, all_input_kwords, model):
    '''
        Evaluation of vector of the movie by averaging 
        all words vectors and multiplying it with TF-IDF score of word 
        in the corpus of all keywords
        
        input: kwords = ['love', 'spring']
        returns np.vector of shape 300
    '''
    tf_of_kwords = compute_tf(kwords)
    movie_vector = []
    for word in kwords:
        try:
            word_vector = model.wv.word_vec(word) * tf_of_kwords[word] * compute_idf(word, all_input_kwords)
        except KeyError:
            logger.info('Keywords model passed the world on KW {}'.format(word))
            continue
        movie_vector.append(word_vector) # состоит из векторов слов * tf-idf
    movie_vector = np.array(movie_vector)
    return np.average(np.transpose(movie_vector), axis = 1)

def genres2vec(input_genres):
    genres_vector = np.zeros(len(all_genres))
    for genre in all_genres:
        for input_genre in input_genres.split('|'):
            if input_genre in all_genres:
                genres_vector[np.where(all_genres == input_genre)[0][0]] = 1
    return genres_vector

def jaccard_similarity(query, document):
    intersection = set(query).intersection(set(document))
    union = set(query).union(set(document))
    return len(intersection)/len(union)

flatten = lambda l: [item for sublist in l for item in sublist]

def get_movie_dict(tmdb_id):
    movie = Movie.query.filter_by(tmdb_id = tmdb_id).first()
    m = dict(kwords = movie.kwords, genres = movie.genres, actors = movie.actors)
    return m



class Recommender():
    def __init__(self, tmdb_idx, table_name, column_name, user_id):
        self.tmdb_idx = tmdb_idx # input user movies
        self.model = word2vec.Word2Vec.load('models/keywords.model')
        self.collected_input_info = []
        self.collected_premieres_info = []
        self.label_no_movies = False
        self.table_name = table_name
        self.column_name = column_name
        self.user_id = user_id
        
    def tmdb_input_info(self):
        for tmdb_id in self.tmdb_idx:
            m = get_movie_dict(tmdb_id)
            self.collected_input_info.append(m)

    def form_characteristics(self): 
        premieres = [(movie.tmdb_fk_id, movie.vkino_id) for movie in Vkino.query.filter(Vkino.tmdb_fk_id != None , Vkino.is_actual == 1).all()]
        premieres = [tup for tup in premieres if tup[0] not in self.tmdb_idx] # не рекоммендовать то что во входных данных
        seen = set()
        premieres = [item for item in premieres if item[0] not in seen and not seen.add(item[0])] # выкинуть повторения (мовою оригіналу)

        user_previous_recs = [rec.id for rec in Recommendation.query.filter_by(user_id = self.user_id).all()]

        user_previous_rec_movies = []
        for rec_id in user_previous_recs:
            ids_of_movies = [mv_rec.movie_id for mv_rec in MovieRecommendation.query.filter_by(recommendation_id = rec_id).all()]
            user_previous_rec_movies.append(ids_of_movies)

        user_previous_rec_movies = set(flatten(user_previous_rec_movies))   

        premieres = [tup for tup in premieres if tup[1] not in user_previous_rec_movies]

        if not premieres:
            return []

        for premiere in premieres:
            m = get_movie_dict(premiere[0])
            m['pk_id'] = premiere[1]
            self.collected_premieres_info.append(m)
            
        if not self.collected_input_info:
            self.label_no_movies = True
            return 
        
        
        self.collected_input_info = list(map(lambda x: movies_preproc(x), self.collected_input_info))
        self.collected_premieres_info = list(map(lambda x: movies_preproc(x), self.collected_premieres_info)) 
        
        # if model needs to be retrained
        kwords_sentences = []
        _vocab = self.model.wv.vocab
        input_kwords = [movie['kwords'].split('|') for movie in self.collected_input_info]
        premieres_kwords = [movie['kwords'].split('|') for movie in self.collected_premieres_info]
        kwords_sentences = form_kwords_sentences(input_kwords, self.model) + form_kwords_sentences(premieres_kwords, self.model)
        if not(not kwords_sentences):
            self.model.build_vocab(kwords_sentences, update = True)
            self.model.save('models/keywords.model')
            logger.info('Keywords model retrained and saved.')
            
        input_actors = '|'.join(flatten([movie['actors'].split('|') for movie in self.collected_input_info]))
        kw_context = flatten(input_kwords) + flatten(premieres_kwords)
        
        
        for movie in self.collected_input_info:
            movie['kwords_vector'] = kwords2vec(movie['kwords'].split('|'), kw_context, self.model)
            movie['genres_vector'] = genres2vec(movie['genres'])
                 
        for movie in self.collected_premieres_info:
            movie['kwords_vector'] = kwords2vec(movie['kwords'].split('|'), kw_context, self.model)
            movie['genres_vector'] = genres2vec(movie['genres'])
             
        for movie in self.collected_premieres_info:
            movie['actor_weight'] = jaccard_similarity(movie['actors'].split('|'), input_actors.split('|'))
        
    def get_recommendations(self):
        num_of_rec = 3
        if not self.label_no_movies:
            result = []
            user_kw_vector = np.average(np.transpose(np.array([movie['kwords_vector'] for movie in self.collected_input_info])), axis = 1)
            user_genres_vector = np.average(np.transpose(np.array([movie['genres_vector'] for movie in self.collected_input_info])), axis = 1)
            for movie in self.collected_premieres_info:
                kw_sim = cosine_similarity(user_kw_vector.reshape(1, -1), movie['kwords_vector'].reshape(1, -1))
                genres_sim = cosine_similarity(user_genres_vector.reshape(1, -1), movie['genres_vector'].reshape(1, -1))
                movie['kw_sim'] = kw_sim[0][0]
                movie['genres_sim'] = genres_sim[0][0]

            all_actor_weights = [r['actor_weight'] for r in self.collected_premieres_info]
            avg_vec_sim = [(r['kw_sim'] + r['genres_sim'])/2 for r in self.collected_premieres_info]
            scaler = MinMaxScaler(feature_range = (min(avg_vec_sim), max(avg_vec_sim)))
            all_actor_weights = list(list(scaler.fit_transform(np.array(all_actor_weights).reshape(1, -1)))[0])

            for movie, actor_weight in zip(self.collected_premieres_info, all_actor_weights):
                movie['relevance'] = (movie['kw_sim'] + movie['genres_sim']) / 2 + actor_weight
                if movie['relevance'] < 0.35: 
                    continue
                else:
                    result.append(movie)
            result = list(reversed(sorted(result, key = lambda x: x['relevance'])))
        else:
            result = []
            
        logger.info('Result formed and returned.')

        return result
