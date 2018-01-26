import time
import os
import stat
import subprocess
from datetime import datetime
import hashlib

from chalice import Chalice
import boto3
from botocore.exceptions import ClientError
from chalice import NotFoundError

app = Chalice(app_name='aws_lambda_test')

S3 = boto3.client('s3', region_name='eu-central-1')
BUCKET = 'bulyatestlambda'
HOST = 'https://s3.eu-central-1.amazonaws.com/{}/'.format(BUCKET)


app.debug = True


@app.route('/')
def index():
    return {'hello': 'world'}


@app.route('/name/{name}')
def print_name(name):
    return {'hello': '{}'.format(name)}


OBJECTS = {
}


@app.route('/htmltopdf', methods=['GET'])
def htmltopdf():
    request = app.current_request
    url = request.query_params.get('url', None)
    if url is None:
        return {'status': 'bad', 'message': 'no url'}

    cmd = os.path.abspath(os.path.join(os.path.dirname(__file__), 'wkhtmltopdf2'))

    output = subprocess.check_output([cmd, url, '-'])
    now = datetime.now()
    h = hashlib.sha256()
    key = '{year}/{month}/{day}/{hr}/{min}/{sec}/{h}.pdf'.format(
        year=now.year, month=now.month, day=now.day, hr=now.hour, min=now.minute, sec=now.second, h=h.hexdigest()
    )
    S3.put_object(Body=output, Bucket=BUCKET, Key=key, ACL='public-read')
    return {'status': 'ok', 'url': HOST + key}


@app.route('/objects/{key}', methods=['GET', 'PUT'])
def myobject(key):
    request = app.current_request
    if request.method == 'PUT':
        OBJECTS[key] = request.json_bodyc
    elif request.method == 'GET':
        try:
            return {key: OBJECTS[key]}
        except KeyError:
            raise NotFoundError(key)


@app.route('/sleep')
def sleep():
    seconds_to_sleep = 10
    time.sleep(seconds_to_sleep)
    return {'sleeped': '{} secs'.format(seconds_to_sleep)}


@app.route('/find-bin')
def find_bin():
    result = {}
    result['current'] = os.listdir(os.curdir)
    result['0'] = os.path.dirname(__file__)
    result['1'] = os.path.abspath(os.path.join(os.path.dirname(__file__), 'wkhtmltopdf2'))
    result['2'] = oct(
        stat.S_IMODE(os.lstat(os.path.abspath(os.path.join(os.path.dirname(__file__), 'wkhtmltopdf2'))).st_mode)
    )

    return {'current_dir': result}


def optimize(f):
    optimize_process = subprocess.Popen(
        '/usr/local/bin/cjpeg',
        # './cjpeg0' ???
        stdin=f,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    return optimize_process.stdout


@app.route('/s3/process/{key}', methods=['GET'])
def s3objects(key):
    request = app.current_request
    try:
        response = S3.get_object(Bucket=BUCKET, Key=key)
    except ClientError as e:
        raise NotFoundError(key)
    optimized_key = 'optimized-{}'.format(key)
    S3.upload_fileobj(optimize(response['Body']), BUCKET, optimized_key)
    return {'optimized_key': optimized_key}

# The view function above will return {"hello": "world"}
# whenever you make an HTTP GET request to '/'.
#
# Here are a few more examples:
#
# @app.route('/hello/{name}')
# def hello_name(name):
#    # '/hello/james' -> {"hello": "james"}
#    return {'hello': name}
#
# @app.route('/users', methods=['POST'])
# def create_user():
#     # This is the JSON body the user sent in their POST request.
#     user_as_json = app.json_body
#     # Suppose we had some 'db' object that we used to
#     # read/write from our database.
#     # user_id = db.create_user(user_as_json)
#     return {'user_id': user_id}
#
# See the README documentation for more examples.
#
