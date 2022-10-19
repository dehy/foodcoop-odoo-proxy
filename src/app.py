from flask import Flask, request, make_response
import requests
import os
import json
import jwt
# from http.cookies import SimpleCookie

# from jwt import PyJWKClient
from patches import PyJWKClient

app = Flask(__name__)

odoo_cookie = None

jwks_client = PyJWKClient(f"{os.environ['OIDC_ISSUER']}/oauth/jwks.json")

authenticate_data = {
    "params": {
        "db": "PROD",
        "login": os.environ["ODOO_USERNAME"],
        "password": os.environ["ODOO_PASSWORD"],
    }
}


def refresh_odoo_cookie():
    global odoo_cookie
    try:
        if odoo_cookie is None:
            # TODO or expired ?
            # print(f"{os.environ['ODOO_ENDPOINT']}/web/session/authenticate")
            response = requests.post(
                f"{os.environ['ODOO_ENDPOINT']}/web/session/authenticate",
                headers={"Host": "odoo.supercoop.fr",
                         "Content-Type": "application/json"},
                data=json.dumps(authenticate_data),
            )
            # print(response.headers["set-cookie"])
            # print('\n')
            #  odoo_cookie = SimpleCookie()
            #  odoo_cookie.load(response.headers["set-cookie"])
            odoo_cookie = response.headers["set-cookie"]
            # print(odoo_cookie)
            # print('\n')
            # print(odoo_cookie["session_id"]["expires"])

            # print('\nresponse.headers["set-cookie"]:\n')
            # print(response.headers["set-cookie"])

            # response = requests.get(
            #     f"{os.environ['ODOO_ENDPOINT']}/web?ids=8256&fields=name,barcode,qty_available,lst_price,uom_id,weight_net,volume,product_tmpl_id&model=product.product",
            #     headers={"Host": "odoo.supercoop.fr",
            #              "Content-Type": "application/json"},
            #     # data=json.dumps(authenticate_data)
            # )
            # # print(request.url)
            # print(response)
            # print(response.headers)
            # print(response.content)
            # odoo_cookie = response.headers["set-cookie"]
            print("set odoo cookie OK")
        else:
            print("odoo_cookie=")
            print(odoo_cookie)
            print("\n")
    except Exception as e:
        print(e)  # print error


@ app.route("/", methods=["GET"])
def index():
    print("GET hello world")
    refresh_odoo_cookie()
    headers = dict(request.headers)
    try:
        jwt_token = headers["X-Auth-Token"]
        assert_token_is_valid(jwt_token)
    except KeyError:
        app.logger.debug("X-Auth-Token key missing in headers")
    return "hello FoodCoop Proxy"


@ app.route("/web/<path:subpath>", methods=["POST"])
def forward_request(subpath):
    global odoo_cookie
    refresh_odoo_cookie()
    print("RECEIVE NEW PROXY subpath="+subpath)
    # print("request.headers="+json.dumps(dict(request.headers)))
    # print("request.data="+request.data.decode())
    print()
    headers = dict(request.headers)
    headers['Host'] = f"{os.environ['ODOO_HOST']}"
    headers['cookie'] = odoo_cookie
    # headers['Content-Type'] = 'application/json'
    # headers.pop('Content-Length')
    # headers.pop('Accept')
    # headers.pop('X-Forwarded-For')
    # headers.pop('X-Forwarded-Proto')

    # print(headers)
    try:
        jwt_token = headers["X-Auth-Token"]
        # remove X-Auth-Token from headers before proxying the request to odoo
        headers.pop("X-Auth-Token")

    except KeyError:
        app.logger.debug("X-Auth-Token key missing in headers")
    res = assert_token_is_valid(jwt_token)
    if (not res):
        response = make_response({"error": res})
    if (res):

        payload = request.get_data(cache=False)

        # app.logger.debug(headers)
        # app.logger.debug(payload)

        # verifier ici si c'est un post ou get ou...
        odoo_response = requests.post(
            f"{os.environ['ODOO_ENDPOINT']}/web/{subpath}",
            headers=headers,
            data=payload
        )

        print("\nSEND REQUEST PROXY\n")

        # app.logger.debug(odoo_response.request.headers)
        # app.logger.debug(odoo_response.request.url)
        # app.logger.debug(odoo_response.request.body)
        app.logger.debug(odoo_response.content)
        app.logger.debug(odoo_response.status_code)
        app.logger.debug(odoo_response.headers)

        # remove cookies from headers before sending back request
        # headers = dict(odoo_response.headers)
        # app.logger.debug(headers)
        # odoo_response.headers.pop("Set-Cookie")
        # app.logger.debug(odoo_response.headers)

        response = make_response(odoo_response.content)
        response.headers['Content-Type'] = odoo_response.headers['Content-Type']
        response.status = odoo_response.status_code
        # response = Response(
        #     response=odoo_response.content,
        #     status=odoo_response.status_code,
        #     headers=headers,
        # )
        print("\nSUCCESS SEND BACK REQUEST\n")
        print(response.get_data())
        # return jsonify(odoo_response.content.decode())
        return response
    else:
        return("token invalid")


def assert_token_is_valid(token):
    # app.logger.debug("assert_token_is_valid")
    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        # app.logger.debug(signing_key)
        # app.logger.debug(token)
        decoded = jwt.decode(
            token,
            signing_key.key,
            # issuer="toto",
            issuer=os.environ['OIDC_ISSUER'],
            algorithms=["RS256"],
            audience=os.environ['OIDC_AUDIENCE_APP_MOBILE'],
            options={"require": ["exp", "iss", "aud", "iat"]},
        )
        print(decoded)
        return True
    except Exception as e:
        print(e)
        return e
