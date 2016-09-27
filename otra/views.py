import datetime

from flask import jsonify, request
import pymongo.errors
import jwt

from . import app, db
from . import pwhash
from . import mailing


CONFIRM_USER_TOKEN = 'ne'
LOGIN_TOKEN = 'lo'
RESET_TOKEN = 're'
ADDRESS_CHANGE_TOKEN = 'ad'


@app.route('/')
def index():
    return jsonify(msg='This is a great api.')


@app.route('/<tenant>/users/<user_id>', methods=['GET'])
def get_user(tenant, user_id):
    if tenant not in app.config['TENANTS']:
        return jsonify(msg='Unknown tenant'), 404

    u = db.users.find_one({'ten': tenant, 'uid': user_id})
    if u is None:
        return jsonify(state='unknown', msg='Unknown user'), 404

    return jsonify(state=u['state'])


@app.route('/<tenant>/users/', methods=['POST'])
def add_user(tenant):
    if tenant not in app.config['TENANTS']:
        return jsonify(msg='Unknown tenant'), 404

    # TODO: Is password secure enough? Is the username reasonable?
    # TODO: What if the write failed because it was a duplicate user id?

    j = request.get_json(force=True)
    try:
        db.users.insert_one({
            'ten': tenant,
            'uid': j['username'],
            'pw': pwhash.generate(j['password']),
            'state': 'new',
            'started': datetime.datetime.utcnow(),
            'old_addr': [j['username']],
        })
    except pymongo.errors.DuplicateKeyError:
        return jsonify(msg='Username is already taken'), 400

    token_content = {
        'p': CONFIRM_USER_TOKEN,
        't': tenant,
        'uid': j['username'],
        'iat': datetime.datetime.utcnow(),
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=5),
    }
    token = jwt.encode(token_content, app.config['JWT_TOKEN_SECRET'],
                       algorithm='HS256')
    mailing.send_confirm_new_user_message(tenant, j['username'], token)
    return jsonify(ok=True)


@app.route('/<tenant>/confirmation/<code>')
def get_code(tenant, code):
    if tenant not in app.config['TENANTS']:
        return jsonify(msg='Unknown tenant'), 404

    # TODO: throttle invalid tokens from an ip address?
    try:
        content = jwt.decode(code, app.config['JWT_TOKEN_SECRET'])
    except jwt.InvalidTokenError:
        return jsonify(valid=False), 404

    if content.get('t') != tenant or content.get('p') != CONFIRM_USER_TOKEN:
        return jsonify(valid=False), 404

    user = db.users.find_one({
        'ten': tenant,
        'uid': content['uid'],
        'state': 'new'
    })
    if user:
        return jsonify(valid=True, username=content['uid'])

    return jsonify(valid=False), 404


@app.route('/<tenant>/confirmation/<code>', methods=['POST'])
def post_code(tenant, code):
    if tenant not in app.config['TENANTS']:
        return jsonify(msg='Unknown tenant'), 404

    # TODO: throttle invalid tokens from an ip address?
    try:
        content = jwt.decode(code, app.config['JWT_TOKEN_SECRET'])
    except jwt.InvalidTokenError:
        return jsonify(confirmed=False), 404

    if content.get('t') != tenant or content.get('p') != CONFIRM_USER_TOKEN:
        return jsonify(confirmed=False), 404

    result = db.users.update_one(
        {'ten': tenant, 'uid': content['uid'], 'state': 'new'},
        {'$set': {'state': 'confirmed'}})
    if result.modified_count:
        return jsonify(confirmed=True, username=content['uid'])

    return jsonify(confirmed=False), 404


@app.route('/<tenant>/auth/', methods=['POST'])
def post_auth(tenant):
    if tenant not in app.config['TENANTS']:
        return jsonify(valid=False, msg='Unknown tenant'), 404

    # TODO: Throttle attempts by user
    # TODO: Throttle attempts by ip?
    # TODO: Track the generation of pw
    j = request.get_json(force=True)
    user = db.users.find_one({'ten': tenant, 'uid': j['username']})
    valid = pwhash.check(user['pw'], j['password'])

    if not valid:
        return jsonify(valid=False, msg='Invalid credentials'), 400

    token_content = {
        'p': LOGIN_TOKEN,
        't': tenant,
        'uid': user['uid'],
        'iat': datetime.datetime.utcnow(),
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=5),
    }
    token = jwt.encode(token_content, app.config['JWT_TOKEN_SECRET'],
                       algorithm='HS256')
    return jsonify(valid=True, token=token)


@app.route('/<tenant>/auth/<token>')
def get_auth(tenant, token):
    if tenant not in app.config['TENANTS']:
        return jsonify(msg='Unknown tenant'), 404

    try:
        content = jwt.decode(token, app.config['JWT_TOKEN_SECRET'])
    except:
        return jsonify(valid=False), 404

    if content.get('t') != tenant or content.get('p') != LOGIN_TOKEN:
        return jsonify(valid=False), 404

    return jsonify(valid=True, uid=content['uid'])


@app.route('/<tenant>/users/<user_id>/password', methods=['POST'])
def post_new_password(tenant, user_id):
    if tenant not in app.config['TENANTS']:
        return jsonify(msg='Unknown tenant'), 404

    j = request.get_json(force=True)

    user = db.users.find_one({'ten': tenant, 'uid': user_id})
    valid = pwhash.check(user['pw'], j['old'])
    if not valid:
        return jsonify(valid=False), 400

    result = db.users.update_one(
        {'ten': tenant, 'uid': user_id},
        {'$set': {'pw': pwhash.generate(j['new'])}})
    if not result.matched_count:
        app.logger.warn('Failed to modify password for %s', user_id)
        return jsonify(valid=False), 500

    return jsonify(valid=True)


@app.route('/<tenant>/password-resets/', methods=['POST'])
def start_reset(tenant):
    if tenant not in app.config['TENANTS']:
        return jsonify(msg='Unknown tenant'), 404

    j = request.get_json(force=True)

    user = db.users.find_one({'ten': tenant, 'uid': j['username']})
    if not user:
        return jsonify(valid=False, msg='Unknown user'), 400

    token_content = {
        'p': RESET_TOKEN,
        't': tenant,
        'uid': user['uid'],
        'iat': datetime.datetime.utcnow(),
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=3),
    }
    token = jwt.encode(token_content, app.config['JWT_TOKEN_SECRET'],
                       algorithm='HS256')
    mailing.send_password_reset_message(tenant, user['uid'], token)
    return jsonify(valid=True)


@app.route('/<tenant>/password-resets/<token>')
def get_reset(tenant, token):
    if tenant not in app.config['TENANTS']:
        return jsonify(msg='Unknown tenant'), 404

    # TODO: Throttle the bad requests?
    try:
        content = jwt.decode(token, app.config['JWT_TOKEN_SECRET'])
    except:
        return jsonify(valid=False), 404

    if content.get('t') != tenant or content.get('p') != RESET_TOKEN:
        return jsonify(valid=False), 404

    return jsonify(valid=True, uid=content['uid'])


@app.route('/<tenant>/password-resets/<token>', methods=['POST'])
def post_reset(tenant, token):
    if tenant not in app.config['TENANTS']:
        return jsonify(msg='Unknown tenant'), 404

    j = request.get_json(force=True)

    # TODO: Throttle the bad requests?
    try:
        content = jwt.decode(token, app.config['JWT_TOKEN_SECRET'])
    except:
        return jsonify(valid=False), 404

    if content.get('t') != tenant or content.get('p') != RESET_TOKEN:
        return jsonify(valid=False, uid=content['uid'])

    result = db.users.update_one(
        {'ten': tenant, 'uid': content['uid']},
        {'$set': {'pw': pwhash.generate(j['password'])}})

    if not result.matched_count:
        app.logger.warn('Failed to modify password for %s', content['uid'])
        return jsonify(valid=False), 500

    # TODO: Can we change someone else's password by changing our user ids?
    return jsonify(valid=True)


@app.route('/<tenant>/address-changes/', methods=['POST'])
def start_address_change(tenant):
    if tenant not in app.config['TENANTS']:
        return jsonify(msg='Unknown tenant'), 404

    j = request.get_json(force=True)
    user = db.users.find_one({'ten': tenant, 'uid': j['old']})
    valid = pwhash.check(user['pw'], j['password'])

    if not valid:
        return jsonify(valid=False, msg='Invalid credentials'), 400

    # TODO: validate format of new uid

    token_content = {
        'p': ADDRESS_CHANGE_TOKEN,
        't': tenant,
        'uid': user['uid'],
        'nid': j['new'],
        'iat': datetime.datetime.utcnow(),
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=5),
    }
    token = jwt.encode(token_content, app.config['JWT_TOKEN_SECRET'],
                       algorithm='HS256')
    mailing.send_address_change_message(tenant, user['uid'], token)
    return jsonify(valid=True)


@app.route('/<tenant>/address-changes/<token>', methods=['POST'])
def post_address_change(tenant, token):
    if tenant not in app.config['TENANTS']:
        return jsonify(msg='Unknown tenant'), 404

    # TODO: throttle invalid tokens from an ip address?
    try:
        content = jwt.decode(token, app.config['JWT_TOKEN_SECRET'])
    except jwt.InvalidTokenError:
        return jsonify(confirmed=False), 404

    if content.get('t') != tenant or content.get('p') != ADDRESS_CHANGE_TOKEN:
        return jsonify(confirmed=False), 404

    new_address = content['nid']
    result = db.users.update_one(
        {'ten': tenant, 'uid': content['uid']},
        {
            '$set': {'uid': new_address},
            '$addToSet': {'old_addr': new_address},
        })
    if result.matched_count:
        return jsonify(confirmed=True, username=content['nid'])

    return jsonify(confirmed=False), 404


# TODO: Use public/private keys for the JWT tokens. Publish the public keys so
#       they can be verified externally by client apps. This should reduce
#       bandwidth needs and improve client app performance.
# TODO: Alert on hacking attempts
