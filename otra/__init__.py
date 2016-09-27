from flask import Flask
import pymongo
from .reverseproxy import ReverseProxied

__version__ = '0.0.1'

app = Flask(__name__)
app.wsgi_app = ReverseProxied(app.wsgi_app)
app.config.from_envvar('OTRA_SETTINGS')

mongo = pymongo.MongoClient(app.config['MONGO_URL'])
db_name = pymongo.uri_parser.parse_uri(app.config['MONGO_URL']).get('database')
db = mongo[db_name]

from . import views
