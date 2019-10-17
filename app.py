import os
import time

from flask import Flask, make_response, jsonify
from flask_cors import CORS
from flask_pymongo import PyMongo
from flask_restplus import Api, Resource, abort

from config import DAI_CONVERTER_ADDRESS, BNT_ADDRESS, EVENT_CONVERSION, w3, BLOCKS_PER_DAY, DAI_ADDRESS
from contracts import BancorConverter, ERC20
from utils import get_logs

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
        found = mongo.db.tokens.find_one({'token': token}, {'_id': False})
        if found is None:
            abort(make_response(jsonify({'error': 'Token {} not found'.format(token)}), 404))
        return found


@namespace.route('/roi/<string:token>')
class Roi(Resource, DateParserMixin, TokenExistsMixin):
    @rest_api.doc(parser=parser)
    def get(self, token):
        self.ensure_token_exists(token)
        start_date, end_date = self.parse_date()
        roi = list(mongo.db.history.find({'token': token, 'timestamp': {'$lte': end_date, '$gte': start_date}},
                                         {'_id': False, 'timestamp': True, 'gm_change': True, 'price': True}))

        return {
            'roi': roi
        }


@namespace.route('/providers/<string:token>')
class Providers(Resource, TokenExistsMixin):
    def get(self, token):
        self.ensure_token_exists(token)
        providers = list(mongo.db.providers.find({'token': token}, {'_id': False, 'token': False}))

        return {
            'providers': providers,
            'total': sum(p['bnt'] for p in providers)
        }


@namespace.route('/volume')
class Volume(Resource, DateParserMixin):
    @rest_api.doc(parser=parser)
    def get(self):
        start_date, end_date = self.parse_date()
        volume = list(mongo.db.history.find({'timestamp': {'$lte': end_date, '$gte': start_date}, 'volume': {'$gt': 0}},
                                            {'_id': False, 'token': True, 'volume': True, 'timestamp': True}))
        return {
            'volume': volume
        }


@namespace.route('/volume/<string:token>')
class VolumeByToken(Resource, DateParserMixin, TokenExistsMixin):
    @rest_api.doc(parser=parser)
    def get(self, token):
        self.ensure_token_exists(token)
        start_date, end_date = self.parse_date()
        volume = list(mongo.db.history.find(
            {
                'timestamp': {'$lte': end_date, '$gte': start_date},
                'volume': {'$gt': 0},
                'token': token
            },
            {
                '_id': False,
                'token': True,
                'volume': True,
                'timestamp': True
            }
        ))
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

        liquidity = list(mongo.db.history.find({'timestamp': {'$lte': end_date, '$gte': start_date}},
                                               {'_id': False, 'token': True, 'timestamp': True, 'bnt': True}))

        return {
            'liquidity': liquidity
        }


@namespace.route('/liquidity/<string:token>')
class LiquidityByToken(Resource, DateParserMixin, TokenExistsMixin):
    @rest_api.doc(parser=parser)
    def get(self, token):
        self.ensure_token_exists(token)
        start_date, end_date = self.parse_date()

        liquidity = list(mongo.db.history.find({'token': token, 'timestamp': {'$lte': end_date, '$gte': start_date}},
                                               {'_id': False, 'token': True, 'timestamp': True, 'bnt': True}))

        return {
            'liquidity': liquidity
        }


@namespace.route('/info/<string:token>')
class InfoByToken(Resource, TokenExistsMixin):
    def get(self, token):
        token_info = self.ensure_token_exists(token)
        converter_addr = token_info['converter']
        converter = BancorConverter(converter_addr)
        dai_converter = BancorConverter(DAI_CONVERTER_ADDRESS)
        bnt_balance = converter.token_balance(BNT_ADDRESS)
        token_address = converter.token_address()
        token_decimals = ERC20(token_address).decimals()
        token_balance = converter.token_balance(token_address)
        token_price_in_bnt = bnt_balance / token_balance / 10 ** (18 - token_decimals)
        dai_price_in_bnt = dai_converter.price(DAI_ADDRESS)
        token_price_in_dai = token_price_in_bnt / dai_price_in_bnt

        current_block = w3.eth.blockNumber
        logs = get_logs(converter_addr, [EVENT_CONVERSION], current_block - BLOCKS_PER_DAY, current_block)
        volume = 0
        for log in logs:
            event = converter.parse_event('Conversion', log)
            if event['args']['_fromToken'] == BNT_ADDRESS:
                volume += event['args']['_amount']
            else:
                volume += event['args']['_return'] + event['args']['_conversionFee']

        return {
            'bnt_balance': bnt_balance / 10 ** 18,
            'token_balance': token_balance / 10 ** token_decimals,
            'token_price_in_bnt': token_price_in_bnt,
            'token_price_in_usd': token_price_in_dai,
            '24h_volume_in_bnt': volume / 10 ** 18,
            '24h_volume_in_usd': volume / 10 ** 18 / dai_price_in_bnt
        }
