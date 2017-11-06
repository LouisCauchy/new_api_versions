import requests
import json
import csv
import os
from requests.auth import HTTPBasicAuth
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader
import sys
from io import BytesIO
import urllib
import re
import argparse

import PIL
from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw 

parser = argparse.ArgumentParser(description='Parse input string')
parser.add_argument('string', help = 'Input filename or filepath', nargs='+')
args = parser.parse_args()
FILE_NAME = args.string[0]


SOURCE_URL = 'https://api.movieterra.com'
POSTERS_FOLDER = 'static' # путь, где должно лежать финальное фото 
TEMPLATES_PATH = 'templates'
TEMPLATE_NAME = 'vkino_template.html'
ESPUTNIK_USER = ''
ESPUTNIK_PASSWORD = ''
SUBJECT = 'Вам сподобається'
PLAIN_TEXT = 'Вам сподобається'


# https://api.vkino.com.ua/posters/97/9741e5eb09d4c92a2c746103e82b6b6de4ab30fa.jpg - posters/97
 
email_api_method = 'https://esputnik.com/api/v1/message/email'

VKINO_LOGIN = ''
VKINO_PASSWORD = ''
ACCESS_KEY = 'FCRpHzn8PugrkdWEHStNQDZh'    
    
BASE_FONT_PATH = "fonts/arialbd.ttf"
NUMBER_FONT_PATH = "fonts/ariblk.ttf"
    
MOVIE_METADATA_URL = 'http://api.vkino.com.ua/catalog-cinema/shows/{}.xml'    
CREATE_USER_URL = 'https://api.movieterra.com/tickets'
GET_RECOMMENDATIONS_URL = 'https://api.movieterra.com/recommendations?user_id={}&access_key={}'    
 
    
headers = {'User-Agent': 'curl/7.52.1', 'Accept' : 'application/json', 'Content-Type' : 'application/json'}

max_plot_len = 314
num_of_movies = []
months = {
    "01": "січня",
    "02": "лютого",
    "03": "березня",
    "04": "квітня",
    "05" : "травня",
    "06": "червня",
    "07":"липня",
    "08":"серпня",
    "09":"вересня",
    "10":"жовтня",
    "11":"листопада",
    "12": "грудня"   
}

TEMPLATE_ENVIRONMENT = Environment(autoescape = False, loader = FileSystemLoader(TEMPLATES_PATH), trim_blocks = False)

def render_template(template_filename, context):
    return TEMPLATE_ENVIRONMENT.get_template(template_filename).render(context)

def create_poster(img_poster, month, day, filename):
    max_poster_width  = 615
    max_poster_height = 230

    maxsize = (max_poster_width, max_poster_height)

    wpercent = (max_poster_width / float(img_poster.size[0]))
    hsize = int((float(img_poster.size[1]) * float(wpercent)))

    img_poster = img_poster.resize((max_poster_width, hsize), Image.ANTIALIAS)

    font_base_size = 12
    font_bigger_size = 22
    font_base = ImageFont.truetype(font = BASE_FONT_PATH, size = font_base_size)
    font_number = ImageFont.truetype(font = NUMBER_FONT_PATH, size = font_bigger_size)
    box_width = 78
    box_height = 65

    box_coordinates = (505, 0)
    padding_top = 7
    
    box_color = "rgb(255, 164, 57)"
    month = month.upper()

    day_padding_left = 10 if len(day) == 1 else 5
    month_padding_left = 12 if len(month) <= 7 else 0
    
    source_img = img_poster.convert("RGBA")

    box_img = Image.new('RGBA', (box_width, box_height), box_color)

    source_img.paste(box_img, box_coordinates)
    draw = ImageDraw.Draw(source_img)    
    draw.text((box_coordinates[0] + 7, padding_top), "ПРЕМ'ЄРА", font = font_base)
    draw.text((box_coordinates[0] + 20 + day_padding_left, 2 * padding_top + font_base_size / 2), day, font = font_number) 
    draw.text((box_coordinates[0] + month_padding_left, 2.5 * padding_top + font_base_size + font_bigger_size), month, font = font_base)
    draw.polygon([(box_coordinates[0], box_height), (box_coordinates[0]+box_width/2, box_width), (box_coordinates[0]+box_width, box_height)], fill = (255, 164, 57))
    button_img = Image.open('{}/buy-ticket.jpg'.format(POSTERS_FOLDER))
    source_img.paste(button_img, (20, 290))
    source_img.save('{}/'.format(POSTERS_FOLDER) + filename)
                                                                                                                                                                                                                                                                                         

class Mailer():
    
    def __init__(self, user_id,movies, email = None):
        self.user_id = user_id
        self.email = email
        self.movies = movies
        self.movies_to_recommend = []
        self.recommendation_id = ''

    def create_user(self):
        body = dict(access_key =  ACCESS_KEY, user_id = self.user_id, email = self.email, movies = self.movies)
        response = requests.post(CREATE_USER_URL, data = json.dumps(body), headers = headers)
        return response.status_code
    
    def get_recommendations(self):
        response_body = requests.get(GET_RECOMMENDATIONS_URL.format(self.user_id, ACCESS_KEY))
        self.movies_to_recommend = response_body.json()    
        self.movies_to_recommend = self.movies_to_recommend['recommendations']
        if not (not self.movies_to_recommend):
            self.recommendation_id = response_body.json()['recommendation_id']
            return True
        else:# ему не набралось рекоммендаций, просто пропускаем
            return False
        
    def form_characteristics(self):
        table_items = []
        for movie in self.movies_to_recommend:
            movie_metadata_response = BeautifulSoup(requests.get(
                MOVIE_METADATA_URL.format(movie), 
                auth = HTTPBasicAuth(VKINO_LOGIN, VKINO_PASSWORD)
            ).text, 'lxml')
            runtime = movie_metadata_response.runningtime.text
            if runtime != '':
                hours = round(int(runtime) / 60)
                minutes = round(int(runtime) / 60 - hours, 2)
                if hours == 1:
                    fin = 'а'
                else:
                    fin = 'и'
            else:
                hours = ''
                fin = ''   
                
            name = movie_metadata_response.namealt.text
            releasedate = movie_metadata_response.releasedate.text 
            
            if releasedate != '':
                day = releasedate.split('-')[2][1] if releasedate.split('-')[2][0] == '0' else releasedate.split('-')[2]
                month = months[releasedate.split('-')[1]]
                releasedate_final = dict(day = day, month = month)
            else:
                releasedate_final = dict(day = '', month = '')
            
            vkino_poster_url = movie_metadata_response.posterwide.url.text
            with urllib.request.urlopen(vkino_poster_url) as url:
                poster_file = BytesIO(url.read())
                
            img_poster = Image.open(poster_file)

            filename =  str(name) + '_' + str(self.recommendation_id)
            filename = re.sub(' ','',filename.lower())
            filename = re.sub("([\(\[]).*?([\)\]])", '' ,filename)
            filename = re.sub('-','',(str(hash(filename))))
            filename = filename + '.png'
            
            create_poster(img_poster, releasedate_final['month'], releasedate_final['day'], filename)
            final_poster_url = '{}/{}/'.format(SOURCE_URL, POSTERS_FOLDER) + filename
            movie_dict = dict(
                name = name,
                nameorig = movie_metadata_response.nameoriginal.text, 
                genres = movie_metadata_response.genrealt.text,
                runtime = str(hours) + ' годин{} '.format(fin) + str(minutes).split('.')[1] + ' хвилин',
                country = movie_metadata_response.countryalt.text,
                actors = movie_metadata_response.starringalt.text,
                director = movie_metadata_response.directoralt.text,
                agelimit = movie_metadata_response.agelimit.text + '+',
                plot = movie_metadata_response.plotalt.text[:max_plot_len] + '...',
                poster_url = movie_metadata_response.poster.url.text,
                poster_wide_url = final_poster_url,
                movie_url = 'https://vkino.ua/ua/show/{}'.format(movie) + '#showtimes',
                trailer_url = 'https://vkino.ua/ua/show/{}'.format(movie) + '?autoplay-video=on'# movie_url + '?autoplay-video=on
            )
            
            table_items.append(movie_dict)
            
            context = dict(table_items = table_items)
            
            # for index, d in enumerate(table_items):
            #     context['movie_'+str(index+1)] = d

        html = render_template(TEMPLATE_NAME, context)
        return html

    def send_email(self, html,email):
        json_value = {
            'from': ESPUTNIK_USER,'subject' : SUBJECT,'htmlText' : html,'plainText' : PLAIN_TEXT,
            'emails' : [email]
        }
        resp = requests.post(url = email_api_method, auth = HTTPBasicAuth(ESPUTNIK_USER, ESPUTNIK_PASSWORD), json = json_value)
        return resp

def main(filename):
    users = []
    file = open(filename, 'r')
    reader = csv.reader(file)
    for user in reader:
        users.append(user)
    file.close()
    for user in users:
        user_id = user[0]
        email = user[1]

        user_movies = user[2:]
        if len(user_movies) == 1 and ',' in user_movies[0]:
            movies = [int(m) for m in user_movies[0].split(',')]
        else:
            movies = [int(m) for m in user[2:] if m != '']

        user_mail = Mailer(user_id,movies)
        created = user_mail.create_user()
        if created == 200:
            rec_status = user_mail.get_recommendations()
            if rec_status:
                html = user_mail.form_characteristics()
                resp = user_mail.send_email(html,email)
                print(resp)
            else:
                print('Nothing to recommend')
                continue

if __name__ == "__main__":
    main(FILE_NAME)
