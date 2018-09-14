#!/usr/bin/python3

from wsgiref.util import shift_path_info
import logging

import social_coding_sync as socsync

log = logging.getLogger(__name__)

HTML = [('Content-Type', 'text/html')]


def build_app():
    from datetime import datetime
    from pathlib import Path
    from subprocess import run
    from tempfile import NamedTemporaryFile
    from traceback import format_exc  # ISSUE: ambient
    from urllib.request import build_opener

    from sqlalchemy import create_engine

    _configure_logging()
    app = socsync.WSGI_App(
        Path('../conf.ini'),
        datetime.now, run, build_opener, NamedTemporaryFile,
        create_engine)
    wrap = error_middleware(format_exc, app)
    return wrap


OOPS = '''
<h1>Oops!</h1>

<p>An error has been logged.</p>

<p>Please report the problem to
<a href=
"https://discordapp.com/channels/375365542359465989/418562733727023114"
>#bounties</a>
 in RChain-pub discord.</p>
'''


def error_middleware(format_exc, app):
    def err_app(env, start_response):
        shift_path_info(env)  # strip /aux
        try:
            return app(env, start_response)
        except Exception as oops:  # noqa
            log.error('app failed:', exc_info=oops)
            start_response('500 internal error', HTML)
            return [OOPS.encode('utf-8')]

    return err_app


def _configure_logging():
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(levelname)s: %(message)s')
    log.debug('logging configured')


# ISSUE: ambient
application = build_app()
