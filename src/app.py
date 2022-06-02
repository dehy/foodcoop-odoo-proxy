from flask import Flask, request, Response
import requests
import os
import json
import jwt
# from jwt import PyJWKClient
from patches import PyJWKClient

app = Flask(__name__)

jwks_client = PyJWKClient(
    f"{os.environ['OIDC_ISSUER']}/oauth/jwks.json")

authenticate_data = {
    "params": {
        "db": "PROD",
        "login": "login@supercoop.fr",
        "password": "MeGaP@ssWd"
    }
}

authenticate_response = requests.post(
    f"{os.environ['ODOO_ENDPOINT']}/web/session/authenticate",
    headers={"Host": "odoo.supercoop.fr", "Content-Type": "application/json"},
    data=json.dumps(authenticate_data)
)


@app.route("/web/<path:subpath>", methods=['POST'])
def forward_request(subpath):
    headers = dict(request.headers)
    jwt_token = headers['X-Auth-Token']
    assert_token_is_valid(jwt_token)

    return

    payload = request.get_data(cache=False)

    app.logger.debug(headers)
    app.logger.debug(payload)

    odoo_response = requests.post(
        f"{os.environ['ODOO_ENDPOINT']}/web/{subpath}",
        headers=headers,
        data=payload
    )

    app.logger.debug(odoo_response.request)
    app.logger.debug(odoo_response.content)
    app.logger.debug(odoo_response.status_code)
    app.logger.debug(odoo_response.headers)

    response = Response(
        response=odoo_response.content,
        status=odoo_response.status_code,
        headers=odoo_response.headers
    )

    return response


def assert_token_is_valid(token):
    app.logger.debug('assert_token_is_valid')
    signing_key = jwks_client.get_signing_key_from_jwt(token)
    app.logger.debug(signing_key)
    app.logger.debug(token)
    jwt.decode(
        token,
        signing_key.key,
        issuer="toto",
        # issuer="os.environ['OIDC_ISSUER']",
        algorithms=['RS256'],
        options={"require": ["exp", "iss", "aud", "iat"]}
    )
