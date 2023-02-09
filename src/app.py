from flask import Flask, request, make_response
import requests
import os
import json
import jwt
from datetime import datetime
from urllib.parse import urlparse
import sentry_sdk
# from http.cookies import SimpleCookie

# from jwt import PyJWKClient
from patches import PyJWKClient

# TODO check environment

app = Flask(__name__)
app.config.from_prefixed_env()
app.logger.level = 10 if app.config['DEBUG'] else 50

if not app.config['DEBUG']:
    sentry_sdk.init(
        dsn=os.environ['SENTRY_DSN'],

        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for performance monitoring.
        # We recommend adjusting this value in production.
        traces_sample_rate=1.0,
    )

odoo_cookie = None
odoo_host = urlparse(os.environ['ODOO_ENDPOINT']).hostname

jwks_client = PyJWKClient(f"{os.environ['OIDC_ISSUER']}/oauth/jwks.json")

authenticate_data = {
    "params": {
        "db": os.environ["ODOO_DB"],
        "login": os.environ["ODOO_USERNAME"],
        "password": os.environ["ODOO_PASSWORD"],
    }
}


def refresh_odoo_cookie():
    global odoo_cookie, odoo_host

    odoo_cookie = None
    app.logger.info("  + Refreshing cookie")
    response = requests.post(
        f"{os.environ['ODOO_ENDPOINT']}/web/session/authenticate",
        headers={"Host": odoo_host, "Content-Type": "application/json"},
        data=json.dumps(authenticate_data),
    )

    print(response.json())
    if response.json()['result']['uid'] is None:
        app.logger.critical("!! Cannot authenticate")
        raise Exception(f"!! Cannot authenticate: {response.json()}")

    odoo_cookie = response.headers["set-cookie"]
    app.logger.debug("   New cookie:" + odoo_cookie)


@ app.route("/", methods=["GET"])
def index():
    return "Hello FoodCoop Proxy"


@ app.route("/web/<path:subpath>", methods=["POST"])
def forward_request(subpath):
    global odoo_cookie

    if (odoo_cookie is None):
        refresh_odoo_cookie()

    r_params = request.get_json()['params']
    app.logger.info("==> Received new request")
    app.logger.debug(f"   - method: {r_params['method']}")
    app.logger.debug(f"   - model:  {r_params['model']}")

    odoo_host = urlparse(os.environ['ODOO_ENDPOINT']).hostname
    headers = dict(request.headers)
    headers['Host'] = odoo_host
    headers['cookie'] = odoo_cookie
    
    try:
        jwt_token = headers["X-Auth-Token"]
        # remove X-Auth-Token from headers before proxying the request to odoo
        headers.pop("X-Auth-Token")
    except KeyError:
        app.logger.error("!! Missing X-Auth-Token in headers")

    try:
        assert_token_is_valid(jwt_token)
    except Exception as e:
        return make_response({"error": e}, 401)

    payload = request.get_data(cache=False)

    # TODO verifier ici si c'est un post ou get ou...
    app.logger.info("  > Forwarding request to Odoo")
    odoo_response = requests.post(
        f"{os.environ['ODOO_ENDPOINT']}/web/{subpath}",
        headers=headers,
        data=payload
    )

    json_response = odoo_response.json()
    app.logger.info("  < Got response from Odoo")
    if ('error' in json_response and json_response['error']['code'] == 100):
        raise Exception("Odoo session expired")

    response = make_response(odoo_response.content)
    response.headers['Content-Type'] = odoo_response.headers['Content-Type']
    response.status = odoo_response.status_code

    app.logger.info("<== Sending back response")
    return response


def assert_token_is_valid(token):
    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        decoded = jwt.decode(
            token,
            signing_key.key,
            issuer=os.environ['OIDC_ISSUER'],
            algorithms=["RS256"],
            audience=os.environ['OIDC_VALID_AUDIENCES'].split(','),
            options={"require": ["exp", "iss", "aud", "iat"]},
            verify_signature=True,
        )

        app.logger.info("  ✅ Token is valid")
        app.logger.info(f"  ℹ️ User is {decoded.get('name')} <{decoded.get('email')}>")
        app.logger.info(f"  ⏱️ The token is still valid until {datetime.fromtimestamp(decoded.get('exp'))} UTC")

        return True
    except Exception as e:
        app.logger.error("⛔️ Token is invalid!")
        sentry_sdk.capture_exception(e)
        raise e
