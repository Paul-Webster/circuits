#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Shadow Auth Demo

An example of a Circuits Component that requires users authenticate
against /etc/passwd or /etc/shadow before letting them into the web site.
"""

from os import path
from crypt import crypt
from socket import gethostname
from re import compile as compile_regex

from circuits import handler, Component
from circuits.web import _httpauth, Server, Controller
from circuits.web.errors import HTTPError, Unauthorized


def check_auth(user, password):
    salt_pattern = compile_regex(r"\$.*\$.*\$")
    passwd = "/etc/shadow" if path.exists("/etc/shadow") else "/etc/passwd"

    with open(passwd, "r") as f:
        rows = (line.strip().split(":") for line in f)
        records = [row for row in rows if row[0] == user]

    hash = records and records[0][1]
    salt = salt_pattern.match(hash).group()

    return crypt(password, salt) == hash


class PasswdAuth(Component):

    channel = "web"

    def init(self, realm=None):
        self.realm = realm or gethostname()

    @handler("request", filter=True, priority=1.0)
    def _on_request(self, request, response):
        if "authorization" in request.headers:
            ah = _httpauth.parseAuthorization(request.headers["authorization"])
            if ah is None:
                return HTTPError(request, response, 400)

            username, password = ah["username"], ah["password"]

            if check_auth(username, password):
                request.login = username
                return

        response.headers["WWW-Authenticate"] = _httpauth.basicAuth(self.realm)

        return Unauthorized(request, response)


class Root(Controller):

    def index(self):
        return "Hello, {0:s}".format(self.request.login)

app = Server(("0.0.0.0", 8000))
PasswdAuth().register(app)
Root().register(app)
app.run()
