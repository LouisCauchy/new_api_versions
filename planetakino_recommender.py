import warnings
warnings.filterwarnings('ignore')

import logging
logging.basicConfig(
    level = logging.INFO,
    format = '%(asctime)s %(message)s',
    datefmt = '%d/%m/%Y %H:%M:%S',
    filename = 'log/planetakino_recommender.log'
)
logger = logging.getLogger(__name__)

import argparse

from database import *
from recommender import Recommender

parser = argparse.ArgumentParser()
parser.add_argument('-l', '--list', nargs = '+', help = '<Required> Set flag', required = True)
args = parser.parse_args()

tmdb_ids = [int(x) for x in args.list]
logger.info('-' * 120)
logger.info('{} movies as input'.format(tmdb_ids))

rs = Recommender(tmdb_ids,  'planetakino_movies', 'planetakino_id', None)
rs.tmdb_input_info()
rs.form_characteristics()
result = rs.get_recommendations()
logger.info('Number of recommendations: {}'.format(len(result)))
agent_premiere_idx = [movie['pk_id'] for movie in result]
logger.info('Recommendations: {}'.format(agent_premiere_idx))
print(agent_premiere_idx[:3])

