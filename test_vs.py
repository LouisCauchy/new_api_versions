import warnings
warnings.filterwarnings('ignore')

from database import Movie
a = Movie.query.filter_by(tmdb_id = 597).first()

print(a)