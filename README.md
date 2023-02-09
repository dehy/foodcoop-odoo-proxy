# Foodcoop Mobile App Proxy

## Purpose

Odoo 9, still used by many French foodcoops, lacks API authentication through API Key or JWT and requires using a local
account. This little app acts as a reverse-proxy. It receives JWT authenticated requests, check authentication, and
forwards the request using to the Odoo instance, using a technical account.

## How-to

1. Copy `src/.env.dist` to `src/.env` and change values accordingly.
2. Start the project with Docker: `docker compose up`