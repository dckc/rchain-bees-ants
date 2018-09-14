"""social_coding_sync -- sync users, issues, endorsements from github

Usage:
  social_coding_sync [options] issues_fetch
  social_coding_sync [options] issues_insert
  social_coding_sync [options] users_fetch
  social_coding_sync [options] users_insert
  social_coding_sync [options] reactions_get
  social_coding_sync [options] trust_seed
  social_coding_sync [options] trust_unseed
  social_coding_sync [options] trusted
  social_coding_sync [options] trust_view
  social_coding_sync [options] db_bak

Options:
  --config=FILE     config file with github_repo.read_token
                    and _databse.db_url
                    [default: ../conf.ini]
  --seed=NAMES      login names (comma separated) of trust seed
                    [default: dckc,deannald,PatrickM727]
  --good_nodes=XS   qty of good nodes for each rating (comma separated)
                    [default: 60,30,20]
  --view=FILE       filename for social network visualization
                    [default: ,states.js]
  --cache=DIR       directory for query results [default: cache]
  --bak-dir=DIR     directory for database dumps [default: bak]
  --voter=NAME      test voter for logging [default: dckc]

.. note: This line separates usage notes above from design notes below.

    >>> io = MockIO()
    >>> run = lambda cmd: main(cmd.split(), io.cwd, io.now, io.run,
    ...                        io.build_opener, io.create_engine,
    ...                        io.NamedTemporaryFile)
    >>> from pprint import pprint

    >>> run('script.py issues_fetch')
    >>> pprint(json.loads(io.fs['./cache/issues.json']))
    [{'repository': {'issues': {'nodes': [{'number': 123,
                                           'state': 'OPEN',
                                           'title': 'Bad breath',
                                           'updatedAt': '2001-01-01'}]}}}]
"""

from cgi import parse_qs, escape
from configparser import SafeConfigParser
from contextlib import contextmanager
from datetime import timedelta
from io import BytesIO, StringIO
from math import ceil
from shutil import copyfileobj
from string import Template
from urllib.request import Request
import gzip
import json
import logging

from docopt import docopt
import pandas as pd
import pkg_resources as pkg
import sqlalchemy as sqla

import net_flow

log = logging.getLogger(__name__)
USAGE = __doc__.split('\n..', 1)[0]

PLAIN = [('Content-Type', 'text/plain')]
HTML8 = [('Content-Type', 'text/html; charset=utf-8')]
JSON = [('Content-Type', 'application/json')]


def main(argv, cwd, now, run, build_opener, create_engine, NamedTemporaryFile):
    log.debug('argv: %s', argv)
    opt = docopt(USAGE, argv=argv[1:])
    log.debug('opt: %s', opt)

    def cache_open(filename, mode, what):
        path = cwd / opt['--cache'] / filename
        log.info('%s %s to %s',
                 'Writing' if mode == 'w' else 'Reading',
                 what, path)
        return path.open(mode=mode)

    io = IO(create_engine, build_opener, NamedTemporaryFile, cwd / opt['--config'])

    if opt['issues_fetch']:
        Issues(io.opener(), io.tok()).fetch_to_cache(cache_open)

    elif opt['issues_insert']:
        Issues.sync_from_cache(cache_open, io.db())

    elif opt['users_fetch']:
        Collaborators(io.opener(), io.tok()).fetch_to_cache(cache_open)

    elif opt['users_insert']:
        Collaborators.sync_from_cache(cache_open, io.db())

    elif opt['reactions_get']:
        rs = Reactions(io.opener(), io.tok())
        info = rs.fetch(dest=cwd / opt['--cache'] / 'reactions.json')
        log.info('%d reactions saved to %s',
                 len(info['repository']['issues']['nodes']), opt['--cache'])

    elif opt['trust_seed']:
        log.info('using cache %s to get saved reactions', opt['--cache'])
        with cache_open('reactions.json', mode='r', what='reactions') as fp:
            reaction_info = json.load(fp)
        reactions = Reactions.normalize(reaction_info)
        TrustCert.seed_from_reactions(reactions, io.db())

    elif opt['trust_unseed']:
        log.info('using cache %s to get saved reactions', opt['--cache'])
        with cache_open('reactions.json', mode='r', what='reactions') as fp:
            reaction_info = json.load(fp)
        reactions = Reactions.normalize(reaction_info)
        TrustCert.unseed_from_reactions(reactions, io.db())

    elif opt['trusted']:
        seed, good_nodes = TrustCert.doc_params(opt)
        trusted = TrustCert.update_results(io.db(), seed, good_nodes)
        by_rating = trusted.groupby('rating')[['login']].count()
        log.info('trust count by rating:\n%s', by_rating)

    elif opt['trust_view']:
        certs = TrustCert.get_certs(io.db())
        seed, good_nodes = TrustCert.doc_params(opt)
        info = TrustCert.viz(certs, seed, good_nodes)
        with (cwd / opt['--view']).open('w') as fp:
            json.dump(info, fp, indent=2)

    elif opt['db_bak']:
        with io.bak_file(now, cwd / opt['--bak-dir']) as dest:
            io.db_bak(run, dest)


class WSGI_App(object):
    template = '''
        <h1>Sync</h1>
        <h2>Users from GitHub</h2>
        <form action='user' method='post'>
        <input type='submit' value='Update Users' />
        </form>
        <h2>Issues from GitHub</h2>
        <form action='issue' method='post'>
        <input type='submit' value='Update Issues' />
        </form>
        <h2>Trust Ratings</h2>
        <a href='../trust_net_viz.html'>social network viz</a>
        <form action='trust_cert' method='post'>
        <input type='submit' value='Update Trust Ratings' />
        </form>
        <h2>Database Dump</h2>
        <p><em>Allow 30 seconds or so for a response.</em></p>
        <p><strong>Dumps may be pruned after 15 minutes.</strong></p>
        <form action='db_dump' method='post'>
        <input type='submit' value='Dump DB' />
        </form>
        '''

    def __init__(self, config_path, now, run, build_opener, mktemp,
                 create_engine):
        io = IO(create_engine, build_opener, mktemp, config_path)
        self.__io = io

        def db_bak():
            with io.bak_file(now, config_path.parent / 'bak') as dest:
                return io.db_bak(run, dest)

        self.__db_bak = db_bak

    def __call__(self, environ, start_response):
        [path, method] = [environ.get(n)
                          for n in ['PATH_INFO', 'REQUEST_METHOD']]
        if method == 'GET':
            if path == '/user':
                login = parse_qs(environ['QUERY_STRING']).get('login')
                if not login:
                    return self.form(start_response)
                return self.my_work(login[0], start_response)
            elif path in ('/issue', '/trust_cert'):
                return self.form(start_response)
            elif path == '/trust_net':
                return self.trust_net(start_response)
        elif method == 'POST':
            if path == '/user':
                return self.sync(Collaborators, start_response)
            elif path == '/issue':
                return self.sync(Issues, start_response)
            elif path == '/trust_cert':
                params = self._post_params(environ)
                return self.cert_recalc(start_response, params)
            elif path == '/db_dump':
                return self.db_dump(start_response)
        start_response('404 not found', PLAIN)
        return [('cannot find %r' % path).encode('utf-8')]

    def form(self, start_response):
        start_response('200 OK', HTML8)
        return [self.template.encode('utf-8')]

    def sync(self, cls, start_response):
        io = self.__io
        data = cls(io.opener(), io.tok()).sync_data(io.db())
        start_response('200 ok', PLAIN)
        return [('%d records' % len(data)).encode('utf-8')]

    def db_dump(self, start_response):
        dest = self.__db_bak()
        mb = 1024 * 1024
        size_mb = round(dest.stat().st_size * 1.0 / mb, 2)
        start_response('200 ok', HTML8)
        return [('<p>db dump result: <a href="/%s">%s</a> %s Mb</p>' %
                 (dest, dest.name, size_mb)).encode('utf-8')]

    def cert_recalc(self, start_response, params):
        seed, good_nodes = TrustCert.doc_params()
        ratings = TrustCert.update_results(self.__io.db(), seed, good_nodes)
        start_response('200 ok', PLAIN)
        return [('%d records' % len(ratings)).encode('utf-8')]

    def _post_params(self, environ):
        try:
            request_body_size = int(environ.get('CONTENT_LENGTH', 0))
        except (ValueError):
            request_body_size = 0

        request_body = environ['wsgi.input'].read(request_body_size)
        return parse_qs(request_body)

    def trust_net(self, start_response):
        certs = TrustCert.get_certs(self.__io.db())
        seed, good_nodes = TrustCert.doc_params()
        net = TrustCert.viz(certs, seed, good_nodes)
        start_response('200 OK', JSON)
        return [json.dumps(net, indent=2).encode('utf-8')]

    def my_work(self, login, start_response):
        io = self.__io
        worker = Collaborators(io.opener(), io.tok())
        work = worker.my_work(login)
        pg_parts = worker.fmt_work(work)
        start_response('200 OK', HTML8)
        return pg_parts


class IO(object):
    def __init__(self, create_engine, build_opener, mktemp, config_path):
        self.__config_path = config_path
        self.__create_engine = create_engine
        self.__build_opener = build_opener
        self.__mktemp = mktemp
        self.__config = None

    @property
    def _cp(self):
        if self.__config:
            return self.__config

        path = self.__config_path
        log.info('config: %s', path)
        with path.open('r') as txt_in:
            cp = headless_config(txt_in, str(path))
        self.__config = cp
        return cp

    def db(self):
        url = self._cp.get('_database', 'db_url')
        url = url.strip('"')  # PHP needs ""s for %(interp)s
        return self.__create_engine(url)

    @contextmanager
    def _db_defaults(self):
        with self.__mktemp(mode='w') as defaults_file:
            defaults = self._db_password_config()
            defaults.write(defaults_file)
            defaults_file.flush()
            yield defaults_file

    def _db_password_config(self):
        """Wrap DB password in mysql style configuration.

        Suppose we have the usual configuration:

        >>> io = MockIO.makeIO()

        Then we can get a mysql style configuration:

        >>> defaults = io._db_password_config()

        This is what it looks like:

        >>> from io import StringIO
        >>> buf = StringIO()
        >>> defaults.write(buf)
        >>> print(buf.getvalue(), end='')
        [client]
        password = sekret
        <BLANKLINE>

        """
        password = self._cp.get('_database', 'password')
        defaults = SafeConfigParser()
        defaults['client'] = {}
        defaults['client']['password'] = password
        return defaults

    def bak_file(self, now, storage):
        if not storage.exists():
            storage.mkdir()
        t = now()
        self._prune(storage, t)
        return (storage / str(t)).with_suffix('.sql')

    @classmethod
    def _prune(self, storage, t,
               threshold=15):
        cutoff = t - timedelta(seconds=threshold * 60)
        for old_dump in storage.glob('*.sql'):
            if old_dump.name < str(cutoff):
                log.info('removing dump older than %s: %s', cutoff, old_dump)
                old_dump.unlink()

    mysqldump = 'mysqldump'

    def db_bak(self, run, dest):
        url = sqla.engine.url.make_url(self._cp.get('_database', 'db_url').strip('"'))
        if dest.exists():
            raise IOError('backup destination exists: %s' % dest)

        # Tell mysqldump to get password from config file:
        # https://stackoverflow.com/a/6861458
        # http://dev.mysql.com/doc/refman/5.1/en/password-security-user.html
        with self._db_defaults() as defaults:
            cmd = [self.mysqldump, '--defaults-file=' + defaults.name,
                   '--host=%s' % url.host, '--port=%s' % url.port, '--compress',
                   '--user=%s' % url.username, '-r', str(dest), url.database]
            log.info('backing up %s to: %s', url.database, dest)
            log.debug('%s', cmd)
            run(cmd, input=url.password.encode('utf-8'))

        dest_gz = dest.with_suffix('.sql.gz')
        log.info('compressing to %s', dest_gz)
        with dest.open('rb') as f_in:
            with gzip.GzipFile(fileobj=dest_gz.open('wb'), mode='wb') as f_out:
                copyfileobj(f_in, f_out)
        dest.unlink()
        return dest_gz

    def tok(self):
        return self._cp.get('github_repo', 'read_token')

    def opener(self):
        return self.__build_opener()


def headless_config(fp, fname):
    txt = '[root]\r\n' + fp.read()
    cp = SafeConfigParser()
    cp.read_string(txt, fname)
    return cp


class QuerySvc(object):
    endpoint = 'https://api.github.com/graphql'
    query = "query { viewer { login } }"

    def __init__(self, urlopener, token):
        self.__urlopener = urlopener
        self.__token = token

    def runQ(self, query, variables={}):
        req = Request(
            self.endpoint,
            data=json.dumps({'query': query,
                             'variables': variables}).encode('utf-8'),
            headers={
                "Authorization": "bearer " + self.__token
            })
        log.info("query -> %s", self.endpoint)
        response = self.__urlopener.open(req)
        if response.getcode() != 200:
            raise response
        body = json.loads(response.read().decode('utf-8'))
        if body.get('errors'):
            raise IOError(body['errors'])
        return body['data']

    def _page_q(self, cursor):
        maybeParens = lambda s: '(' + s + ')' if s else ''
        fmtParams = lambda params: ', '.join(
            part
            for k, (val, ty) in params.items()
            for part in ([('$' + k + ':' + ty)] if val else []))
        paramInfo = dict(cursor=[cursor, 'String!'])
        variables = {k: v for (k, [v, _t]) in paramInfo.items()}
        return variables, (
            self.query
            .replace('PARAMETERS', maybeParens(fmtParams(paramInfo)))
            .replace('CURSOR', ' after: $cursor' if cursor else ''))

    def fetch_pages(self):
        pageInfo = {'endCursor': None}
        pages = []
        while 1:
            variables, query = self._page_q(pageInfo['endCursor'])
            info = self.runQ(query, variables)
            pageInfo = Obj(info).repository[self.connection].pageInfo
            log.info('pageInfo: %s', pageInfo)
            pages.append(info)
            if not pageInfo.get('hasNextPage', False):
                return pages

    def fetch(self, dest=None):
        info = self.runQ(self.query)
        if dest:
            with dest.open('w') as data_fp:
                json.dump(info, data_fp)
        return info

    @classmethod
    def db_sync(cls, db, data, table):
        log.info('db_sync cols: %s', data.dtypes)
        cols = ', '.join(data.columns.values)
        params = ', '.join(
            ('%%(%s)s' % name) for name in data.columns)
        assignments = ', '.join(
            ('%s = values(%s)' % (name, name) for name in data.columns))
        sql = '''
        insert into %(table)s (%(cols)s)
        values (%(params)s)
        on duplicate key update
        %(assignments)s
        ''' % dict(cols=cols, params=params,
                   assignments=assignments, table=table)
        log.info('db_sync SQL: %s', sql)
        records = data.to_dict(orient='records')
        with db.begin() as trx:
            trx.execute(sql, records)

    def fetch_to_cache(self, cache_open):
        info = self.fetch_pages()
        with cache_open(
                self.cache_filename, mode='w',
                what='%d pages of %s' % (len(info), self.connection)) as fp:
            json.dump(info, fp)

    @classmethod
    def sync_from_cache(cls, cache_open, dbr):
        with cache_open(cls.cache_filename, mode='r',
                        what=cls.connection + ' pages') as fp:
            pages = json.load(fp)
        cls.db_sync(dbr, cls.data(pages), cls.table)

    def sync_data(self, dbr):
        pages = self.fetch_pages()
        data = self.data(pages)
        self.db_sync(dbr, self.data(pages), self.table)
        return data


class Obj(dict):
    '''
    >>> x = Obj(dict(a={'b': 3}))
    >>> x.a.b
    3
    >>> x.a.oops
    {}
    '''
    def __getitem__(self, n):
        x = self.get(n, {})
        if isinstance(x, dict):
            return Obj(x)
        return x

    def __getattr__(self, n):
        return self[n]


class Reactions(QuerySvc):
    query = pkg.resource_string(__name__, 'reactions.graphql').decode('utf-8')

    endorsements = ['HEART', 'HOORAY', 'LAUGH', 'THUMBS_UP']

    @classmethod
    def normalize(cls, info):
        log.info('dict to df...')
        reactions = pd.DataFrame([
            dict(user=reaction['user']['login'],
                 # issue_num=issue['number'],
                 # content=reaction['content'],
                 author=comment['author']['login'],
                 createdAt=comment['createdAt'])
            for issue in info['repository']['issues']['nodes']
            for comment in issue['comments']['nodes']
            for reaction in comment['reactions']['nodes']
            if reaction['content'] in cls.endorsements
        ])
        reactions.createdAt = pd.to_datetime(reactions.createdAt)
        return reactions


class Issues(QuerySvc):
    query = pkg.resource_string(__name__, 'issues.graphql').decode('utf-8')
    connection = 'issues'
    table = 'issue'
    cache_filename = 'issues.json'

    @classmethod
    def data(cls, pages,
             repo='rchain/bounties'):
        df = pd.DataFrame([
            dict(num=node['number'],
                 title=node['title'],
                 labels=json.dumps([
                     label['name']
                     for label in node.get('labels', {}).get('nodes', [])
                     ]),
                 createdAt=node['createdAt'],
                 updatedAt=node['updatedAt'],
                 state=node['state'],
                 repo=repo)
            for page in pages
            for node in page['repository']['issues']['nodes']
        ])
        # df['updatedAt'] = pd.to_datetime(df.updatedAt)
        when = df.updatedAt.str.replace('T', ' ').str.replace('Z', '')
        df['updatedAt'] = when
        when = df.createdAt.str.replace('T', ' ').str.replace('Z', '')
        df['createdAt'] = when
        return df


class Collaborators(QuerySvc):
    query = pkg.resource_string(__name__,
                                'collaborators.graphql').decode('utf-8')
    q_work = pkg.resource_string(__name__,
                                'my_work.graphql').decode('utf-8')
    tpl_work = pkg.resource_string(__name__,
                                   'my_work.html').decode('utf-8')
    connection = 'collaborators'
    table = 'github_users'
    cache_filename = 'users.json'

    @classmethod
    def data(self, pages):
        df = pd.DataFrame(
            [dict(edge['node'],
                  permission=edge['permission'],
                  followers=edge['node']['followers']['totalCount'])
             for page in pages
             for edge in page['repository']['collaborators']['edges']],
            columns=['login', 'followers', 'name', 'location', 'email',
                     'bio', 'websiteUrl', 'avatarUrl', 'permission',
                     'createdAt'])
        # df = df.set_index('login')
        # df.createdAt = pd.to_datetime(df.createdAt)
        df = df.fillna(value='')
        df.createdAt = df.createdAt.str.replace('T', ' ').str.replace('Z', '')
        return df

    def my_work(self, login):
        return self.runQ(self.q_work, {'login': login})

    @classmethod
    def fmt_work(cls, work):
        parts = []
        comments = work['user']['issueComments']['nodes']
        comments = reversed(sorted(
            comments,
            key=lambda c: (c['issue']['number'],
                           c['createdAt'])))
        for c in comments:
            c.update({'issue_' + k: v for k, v in c['issue'].items()})
            c = {k: escape(str(v)) for k, v in c.items()}
            section = Template(cls.tpl_work).substitute(c)
            #section = '<pre>@@' + str(c.keys()) + '</pre>'
            parts.append(section.encode('utf-8'))
        return parts


class TrustCert(object):
    table = 'trust_cert'

    ratings = [1, 2, 3]
    superseed = '<superseed>'

    @classmethod
    def update_results(cls, dbr, seed, good_nodes):
        certs = cls.get_certs(dbr)
        trusted = cls.trust_ratings(certs, seed, good_nodes)

        last_cert = certs.groupby('subject')[['cert_time']].max()
        trusted = trusted.merge(last_cert,
                                left_index=True, right_index=True, how='left')
        trusted.to_sql('authorities', if_exists='replace', con=dbr,
                       dtype=noblob(trusted))
        return trusted

    @classmethod
    def get_certs(cls, dbr):
        return pd.read_sql('''
            select voter, subject, rating, cert_time
            from {table}
        '''.format(table=cls.table), dbr)

    @classmethod
    def _certs_from_reactions(cls, reactions, users):
        certs = reactions.reset_index().rename(columns={
            'user': 'voter',
            'author': 'subject',
            'createdAt': 'cert_time'})
        certs = certs.groupby(['voter', 'subject'])[['cert_time']].max()
        certs['rating'] = 1
        certs = certs.reset_index()
        log.info('dckc certs:\n%s',
                 certs[certs.voter == 'dckc'])
        log.info('to_sql...')
        ok = certs.voter.isin(users.login) & certs.subject.isin(users.login)
        if not all(ok):
            log.warn('bad users:\n%s', certs[~ok])
            certs = certs[ok]
        return certs.set_index(['voter', 'subject'])

    @classmethod
    def seed_from_reactions(cls, reactions, dbr):
        users = pd.read_sql('select * from github_users', con=dbr)
        certs = cls._certs_from_reactions(reactions, users)
        dbr.execute('delete from %s' % cls.table)
        certs.to_sql(cls.table, con=dbr, if_exists='append',
                     dtype=noblob(certs))
        log.info('%d rows inserted into %s:\n%s',
                 len(certs), cls.table, certs.head())
        return certs

    @classmethod
    def unseed_from_reactions(cls, reactions, dbr):
        users = pd.read_sql('select * from github_users', con=dbr)
        log.info('%d in github_users table', len(users))
        certs_inferred = cls._certs_from_reactions(reactions, users)
        log.info("%d certs inferred from cached reactions",
                 len(certs_inferred))
        certs_on_file = pd.read_sql(
            'select voter, subject, rating, cert_time from trust_cert', dbr)
        certs_on_file = certs_on_file.set_index(['voter', 'subject'])
        log.info("%d in trust_certs table", len(certs_on_file))
        certs_both = intersection(certs_inferred, certs_on_file)
        log.info("%d in common:\n%s\n...",
                 len(certs_both), certs_both.head())

        certs_both.to_sql('tmp_cert', dbr, if_exists='replace')
        [before] = dbr.execute('select count(*) from trust_cert').fetchone()
        dbr.execute('''
            delete tc from trust_cert tc
            inner join tmp_cert tmp
              on tc.voter     = tmp.voter
             and tc.subject   = tmp.subject
             and tc.cert_time = tmp.cert_time
             and tc.rating    = tmp.rating
        ''')
        [after] = dbr.execute('select count(*) from trust_cert').fetchone()
        dbr.execute('drop table tmp_cert')
        log.info('%d rows before - %d after = %d trust_cert rows removed',
                 before, after, before - after)

    @classmethod
    def doc_params(cls, opt=None):
        if opt is None:
            opt = docopt(USAGE, argv=['trusted'])
        seed = opt['--seed'].split(',')
        good_nodes = [int(c) for c in opt['--good_nodes'].split(',')]
        return seed, good_nodes

    @classmethod
    def trust_ratings(cls, certs, seed, good_nodes):
        """Compute trust ratings.

        >>> certs = MockIO.certs()
        >>> seed = certs.voter[:2]
        >>> TrustCert.trust_ratings(certs, seed, [18, 9, 5])
        ... # doctest: +NORMALIZE_WHITESPACE
                 rating
        login
        aunt-q        3
        aunt-x        1
        aunt-y        1
        col-d         2
        col-p         1
        col-x         1
        judge-p       3
        judge-x       3
        judge-z       2
        mr-d          1
        mr-p          2
        mr-x          1
        mr-y          3
        mr-z          2
        ms-d          2
        ms-q          1
        ms-z          1
        """
        def trusted_at(rating):
            edges = certs[certs.rating >= rating]
            who, _why = cls.net_flow(edges, seed, good_nodes[rating - 1])
            who['rating'] = rating
            return who

        trusted = pd.concat([
            trusted_at(rating)
            for rating in cls.ratings])
        trusted = trusted.groupby('login').max()
        trusted = trusted.sort_index()
        trusted = trusted[trusted.index != cls.superseed]
        return trusted

    @classmethod
    def net_flow(cls, certs, seed, good_qty):
        '''Evaluate trust metric for one rating.

        @param certs: DataFrame with .voter, .subject
        @param seed: trust seed voters
        @param good_qty: targe number of trusted subjects

        In a community of people, suppose some of them have certified
        each other with trust ratings:

        >>> certs = MockIO.certs()
        >>> certs.head(3)
           rating subject    voter
        0       2    mr-z  judge-x
        1       2    mr-p  judge-p
        2       2  aunt-p    col-p
        >>> sorted(certs.rating.unique())
        [1, 2, 3]

        And suppose a couple of them are the trusted seed and about
        30% are to be trusted at journeyer level:

        >>> seed = certs.voter[:2]
        >>> target = len(certs.voter.unique()) * .30

        Who does the trust metric pick?

        >>> who, why = TrustCert.net_flow(certs, seed, target)
        >>> len(who), target
        (9, 8.7)
        >>> who
                 login
        0  <superseed>
        1       aunt-q
        2       aunt-x
        3        col-d
        4      judge-p
        5      judge-x
        6         mr-p
        7         mr-y
        8         mr-z

        >>> why
        ... # doctest: +NORMALIZE_WHITESPACE
                             flow
        voter       subject
        <superseed> judge-p     4
                    judge-x     4
        judge-p     aunt-q      1
                    aunt-x      1
                    mr-p        1
        judge-x     col-d       1
                    mr-y        1
                    mr-z        1

        Which are the 60% to be trusted at apprentice level?

        >>> target = len(certs.voter.unique()) * .6
        >>> who, why = TrustCert.net_flow(certs, certs.voter[:3], target)
        >>> len(who), target
        (18, 17.4)
        >>> who.head(5)
                 login
        0  <superseed>
        1       aunt-p
        2       aunt-q
        3       aunt-x
        4       aunt-y

        '''
        g = net_flow.NetFlow()

        for _, e in certs.iterrows():
            g.add_edge(e.voter, e.subject)

        for s in seed:
            g.add_edge(cls.superseed, s)

        detail = g.max_flow(cls.superseed, cls._capacities(certs, good_qty))
        who = pd.DataFrame([
            dict(login=login)
            for login, value in sorted(detail.extract().items())
            if login != cls.superseed and value > 0
        ])
        why = pd.DataFrame(dict(
            voter=detail.edge_src,
            subject=detail.edge_dst,
            flow=detail.edge_flow))
        why = why[why.flow > 0].set_index(['voter', 'subject'])
        return who, why.sort_index()

    @classmethod
    def _capacities(self, certs, good_qty,
                    max_level=10):
        """
        "The capacity of the seed should be equal to
        the number of good servers in the network,
        and the capacity of each successive level should be
        the previous level's capacity divided by the average outdegree."
        """
        out_degree = certs.groupby('voter')[['subject']].count()
        out_avg = out_degree.subject.mean()
        return [ceil(good_qty / out_avg ** level)
                for level in range(max_level + 1)]

    @classmethod
    def viz(cls, certs, seed, good_nodes):
        """Format trust metric info for visualization.

        >>> certs = MockIO.certs()
        >>> seed = certs.voter[:2]
        >>> info = TrustCert.viz(certs, seed, [18, 9, 5])
        >>> import pprint
        >>> pprint.pprint(info)
        ... # doctest: +ELLIPSIS +NORMALIZE_WHITESPACE
        {'flow': [(1,
                   [{'index': 0, 'login': '<superseed>'},
                    {'index': 1, 'login': 'aunt-q'},
                    {'index': 2, 'login': 'aunt-x'},
                    ...
                    {'index': 17, 'login': 'ms-z'}],
                   [{'flow': 10, 'subject': 'judge-p', 'voter': '<superseed>'},
                    {'flow': 7, 'subject': 'judge-x', 'voter': '<superseed>'},
                    {'flow': 1, 'subject': 'aunt-q', 'voter': 'judge-p'},
                    ...
                    {'flow': 1, 'subject': 'ms-q', 'voter': 'mr-z'}]),
                  (2,
                   ...
                    {'flow': 1, 'subject': 'mr-z', 'voter': 'judge-x'}]),
                  (3,
                   [{'index': 0, 'login': '<superseed>'},
                    {'index': 1, 'login': 'aunt-q'},
                    {'index': 2, 'login': 'judge-p'},
                    {'index': 3, 'login': 'judge-x'},
                    {'index': 4, 'login': 'mr-y'}],
                   [{'flow': 1, 'subject': 'judge-p', 'voter': '<superseed>'},
                    {'flow': 3, 'subject': 'judge-x', 'voter': '<superseed>'},
                    {'flow': 2, 'subject': 'mr-y', 'voter': 'judge-x'},
                    {'flow': 1, 'subject': 'aunt-q', 'voter': 'mr-y'}])],
         'nodes': [{'login': 'aunt-q', 'rating': 3},
                   {'login': 'aunt-x', 'rating': 1},
                   {'login': 'aunt-y', 'rating': 1},
                   ...
                   {'login': 'ms-z', 'rating': 1}]}

        Check that it's JSON-serializable:

        >>> import json
        >>> _ = json.dumps(info)
        """
        trusted = cls.trust_ratings(certs, seed, good_nodes)
        flow = [
            (rating, who, why)
            for rating in cls.ratings
            for edges in [certs[certs.rating >= rating]]
            for (who, why) in [
                    cls.net_flow(edges, seed, good_nodes[rating - 1])]
        ]

        def plain(df):
            return df.reset_index().to_dict('records')

        return {
            "nodes": plain(trusted),
            # ISSUE: last_cert is not JSON serializable
            "certs": plain(certs[['voter', 'subject', 'rating']]),
            "flow": [
                {"rating": rating, "who": plain(who), "why": plain(why)}
                for rating, who, why in flow
            ]
        }


def noblob(df,
           pad=4):
    """no blobs; use string types instead

    Pandas defaults string fields to clobs to be safe,
    but the resulting performance is abysmal.
    """
    df = df.reset_index()
    return {col: sqla.types.String(length=pad + df[col].str.len().max())
            for col, t in zip(df.columns.values, df.dtypes)
            if t.kind == 'O'}


def intersection(d1, d2):
    d1 = d1.reset_index()
    d2 = d2.reset_index()
    return d1.merge(d2, how='inner')


class MockIO(object):
    config = '\n'.join([
        line.strip() for line in
        '''
        [_database]
        db_url: sqlite:///
        password: sekret

        [github_repo]
        read_token: SEKRET
        '''.split('\n')
    ])

    fs = {
        './../conf.ini': config
    }

    def __init__(self, path='.', web_ua=False):
        self.path = path
        self.web_ua = web_ua
        self._ran = []

    @classmethod
    def makeIO(cls):
        it = cls()
        return IO(it.create_engine, it.build_opener,
                  it.NamedTemporaryFile, it / '../conf.ini')

    @property
    def cwd(self):
        return MockIO('.')

    def now(self):
        from datetime import datetime
        return datetime(2001, 1, 1, 1, 2, 3)

    def run(self, *argv):
        self._ran.append(argv)

    def __truediv__(self, other):
        from posixpath import join
        return MockIO(join(self.path, other))

    def open(self, mode='r'):
        if mode == 'r':
            return StringIO(self.fs[self.path])
        elif mode == 'w':
            def done(value):
                self.fs[self.path] = value
            return MockFP(done)
        else:
            raise IOError(mode)

    def build_opener(self):
        return MockWeb()

    def create_engine(self, db_url):
        from sqlalchemy import create_engine
        return create_engine('sqlite:///')

    @contextmanager
    def NamedTemporaryFile(self, mode='wb'):
        yield self / 'tempfile1'

    @classmethod
    def certs(cls,
              size_factor=5):
        import numpy as np
        who = pd.Series([
            pfx + sufx
            for pfx in ['mr-', 'ms-', 'judge-', 'col-', 'aunt-']
            for sufx in ['x', 'y', 'z', 'p', 'd', 'q']
        ])
        qty = len(who) * size_factor
        np.random.seed(0)
        certs = pd.DataFrame(dict(
            voter=np.random.choice(who, qty),
            subject=np.random.choice(who, qty),
            rating=np.random.choice([1, 2, 3], qty)))
        return certs


class MockFP(StringIO):
    def __init__(self, done):
        StringIO.__init__(self)
        self.done = done

    def close(self):
        self.done(self.getvalue())


class MockWeb(object):
    def open(self, req):
        url, method = req.full_url, req.get_method()
        if (method, url) == ('POST', 'https://api.github.com/graphql'):
            # req.data
            ans = {
                'data': {
                    'repository': {
                        'issues': {
                            'nodes': [
                                {
                                    'title': 'Bad breath',
                                    'number': 123,
                                    'updatedAt': '2001-01-01',
                                    'state': 'OPEN'
                                }
                            ]
                        }
                    }
                }
            }
            return MockResponse(json.dumps(ans).encode('utf-8'))
        raise NotImplementedError(req.full_url)


class MockResponse(BytesIO):
    def getcode(self):
        return 200


if __name__ == '__main__':
    def _script():
        from datetime import datetime
        from pathlib import Path
        from subprocess import run
        from sys import argv
        from tempfile import NamedTemporaryFile
        from urllib.request import build_opener

        from sqlalchemy import create_engine

        logging.basicConfig(level=logging.INFO)
        main(argv, cwd=Path('.'), run=run, now=datetime.now,
             build_opener=build_opener,
             NamedTemporaryFile=NamedTemporaryFile,
             create_engine=create_engine)

    _script()
