from typing import List
from jwt.exceptions import PyJWKClientError
from jwt.api_jwk import PyJWK
from jwt import PyJWKClient as oldPyJWKClient


class PyJWKClient(oldPyJWKClient):
    def get_signing_keys(self, refresh: bool = False) -> List[PyJWK]:
        jwk_set = self.get_jwk_set(refresh)
        signing_keys = [
            jwk_set_key
            for jwk_set_key in jwk_set.keys
            if jwk_set_key.public_key_use in ["sig", None]
        ]

        if not signing_keys:
            raise PyJWKClientError("The JWKS endpoint did not contain any signing keys")

        return signing_keys
