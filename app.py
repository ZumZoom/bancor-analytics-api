import os
import time

from flask import Flask, make_response, jsonify
from flask_cors import CORS
from flask_pymongo import PyMongo
from flask_restplus import Api, Resource, abort

flask_app = Flask(__name__)
cors = CORS(flask_app)
rest_api = Api(app=flask_app)
namespace = rest_api.namespace('api/v1', description='Main APIs')

flask_app.config['MONGO_URI'] = os.environ['MONGODB_URI']
mongo = PyMongo(flask_app)

SEC_PER_WEEK = 60 * 60 * 24 * 7

parser = rest_api.parser()
parser.add_argument(
    'start_date', type=int, help='Start date timestamp. Default value = one week before current server time')
parser.add_argument(
    'end_date', type=int, help='End date timestamp. Default value = current server time')


class DateParserMixin:
    def parse_date(self):
        args = parser.parse_args()
        start_date = args['start_date']
        if start_date is None:
            start_date = int(time.time() - SEC_PER_WEEK)
        end_date = args['end_date']
        if end_date is None:
            end_date = int(time.time())

        return start_date, end_date


class TokenExistsMixin:
    def ensure_token_exists(self, token):
        found = mongo.db.tokens.find_one({'token': token})
        if found is None:
            abort(make_response(jsonify({'error': 'Token {} not found'.format(token)}), 404))


@namespace.route('/roi/<string:token>')
class Roi(Resource, DateParserMixin, TokenExistsMixin):
    @rest_api.doc(parser=parser)
    def get(self, token):
        self.ensure_token_exists(token)
        start_date, end_date = self.parse_date()
        roi = list(mongo.db.roi.find({'token': token, 'timestamp': {'$lte': end_date, '$gte': start_date}},
                                     {'_id': False, 'token': False}))

        return {
            'roi': roi
        }


@namespace.route('/providers/<string:token>')
class Providers(Resource):
    def get(self, token):
        self.ensure_token_exists(token)
        providers = list(mongo.db.providers.find({'token': token}, {'_id': False, 'token': False}))

        return {
            'providers': providers,
            'total': sum(p['bnt'] for p in providers)
        }


@namespace.route('/total_volume')
class TotalVolume(Resource, DateParserMixin):
    @rest_api.doc(parser=parser)
    def get(self):
        start_date, end_date = self.parse_date()
        volume = list(mongo.db.roi.find({'timestamp': {'$lte': end_date, '$gte': start_date}},
                                        {'_id': False, 'gm_change': False, 'price': False}))
        return {
            'volume': volume
        }


@namespace.route('/tokens')
class Tokens(Resource):
    def get(self):
        tokens = list(r['token'] for r in mongo.db.tokens.find({}, {'_id': False}))

        return {
            'tokens': tokens
        }


@namespace.route('/liquidity')
class Liquidity(Resource, DateParserMixin):
    @rest_api.doc(parser=parser)
    def get(self):
        start_date, end_date = self.parse_date()

        liquidity = list(mongo.db.liquidity.find({'timestamp': {'$lte': end_date, '$gte': start_date}},
                                                 {'_id': False}))

        return {
            'liquidity': liquidity
        }


@namespace.route('/liquidity/<string:token>')
class LiquidityByToken(Resource, DateParserMixin, TokenExistsMixin):
    @rest_api.doc(parser=parser)
    def get(self, token):
        self.ensure_token_exists(token)
        start_date, end_date = self.parse_date()

        liquidity = list(mongo.db.liquidity.find({'token': token, 'timestamp': {'$lte': end_date, '$gte': start_date}},
                                                 {'_id': False}))

        return {
            'liquidity': liquidity
        }
