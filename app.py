from flask import Flask
from flask_cors import CORS
from flask_restplus import Api, Resource

flask_app = Flask(__name__)
cors = CORS(flask_app)
app = Api(app=flask_app)
namespace = app.namespace('api/v1', description='Main APIs')


@namespace.route('/hello')
class Test(Resource):
    def get(self):
        return "Hello world!"
