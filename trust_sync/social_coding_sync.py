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

Options:
  --config=FILE     config file with github_repo.read_token
                    and _databse.db_url
                    [default: conf.ini]
  --seed=NAMES      login names (comma separated) of trust seed
                    [default: dckc,Jake-Gillberg,kitblake]
  --good_nodes=XS   qty of good nodes for each rating (comma separated)
                    [default: 45,25,15]
  --view=FILE       filename for social network visualization
                    [default: ,states.js]
  --cache=DIR       directory for query results [default: cache]
  --voter=NAME      test voter for logging [default: dckc]

.. note: This line separates usage notes above from design notes below.

    >>> io = MockIO()
    >>> run = lambda cmd: main(cmd.split(),
    ...                        io.cwd, io.build_opener, io.create_engine)
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
from io import BytesIO, StringIO
from math import ceil
from string import Template
from urllib.request import Request
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


def main(argv, cwd, build_opener, create_engine):
    log.debug('argv: %s', argv)
    opt = docopt(USAGE, argv=argv[1:])
    log.debug('opt: %s', opt)

    def cache_open(filename, mode, what):
        path = cwd / opt['--cache'] / filename
        log.info('%s %s to %s',
                 'Writing' if mode == 'w' else 'Reading',
                 what, path)
        return path.open(mode=mode)

    io = IO(create_engine, build_opener, cwd / opt['--config'])

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
        states = TrustCert.viz(io.db())
        with (cwd / opt['--view']).open('w') as fp:
            json.dump(states, fp, indent=2)


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
        '''

    def __init__(self, create_engine, build_opener, config_path):
        self.__io = IO(create_engine, build_opener, config_path)

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
        net = TrustCert.viz(self.__io.db())
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
    def __init__(self, create_engine, build_opener, config_path):
        self.__config_path = config_path
        self.__create_engine = create_engine
        self.__build_opener = build_opener
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

    @classmethod
    def update_results(cls, dbr, seed, good_nodes):
        trusted = pd.concat([
            cls.trust_flow(dbr, seed, good_nodes[rating - 1], rating).reset_index()
            for rating in TrustCert.ratings])
        trusted = trusted.groupby('login').max()
        trusted = trusted.sort_index()
        trusted = trusted[trusted.index != '<superseed>']
        trusted.to_sql('authorities', if_exists='replace', con=dbr,
                       dtype=noblob(trusted))
        return trusted

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
    def trust_flow(cls, dbr, seed, good_qty,
                   rating=1, max_level=4):
        g = net_flow.NetFlow()

        last_cert = pd.read_sql('''
            select subject, max(cert_time) last_cert_time
            from {table}
            where rating >= {rating}
            group by subject
        '''.format(table=cls.table, rating=rating), dbr).set_index('subject')

        edges = pd.read_sql('''
            select distinct voter, subject
            from {table}
            where rating >= {rating}
        '''.format(table=cls.table, rating=rating), dbr)
        for _, e in edges.iterrows():
            g.add_edge(e.voter, e.subject)

        superseed = "<superseed>"
        for s in seed:
            g.add_edge(superseed, s)

        # "The capacity of the seed should be equal to
        # the number of good servers in the network,
        # and the capacity of each successive level should be
        # the previous level's capacity divided by the average outdegree."
        out_degree = pd.read_sql('''
            select avg(out_degree) avg from (
              select voter, count(*) out_degree
              from {table}
              where rating >= {rating}
              group by voter
            ) by_voter
        '''.format(table=cls.table, rating=rating), dbr).iloc[0]

        capacities = [ceil(good_qty / out_degree.avg ** level)
                      for level in range(max_level + 1)]
        flow = g.max_flow_extract(superseed, capacities)
        ok = pd.DataFrame([
            dict(login=login)
            for login, value in flow.items()
            if login != 'superseed' and value > 0
        ]
        ).set_index('login')
        ok['rating'] = rating
        return ok.merge(last_cert,
                        left_index=True, right_index=True, how='left')

    @classmethod
    def viz(cls, dbr):
        users = pd.read_sql(
            '''
            select login, convert(verified_coop, char) member_snowflake
                 , coalesce(rating, -1) as rating, rating_label, weight, sig
            from user_flair u
            order by u.login
            ''', dbr)
        nodes = [dict(u, id=ix,
                      rating=None if u.rating < 0 else u.rating)
                 for ix, u in users.iterrows()]
        certs = pd.read_sql(
            'select voter, subject, coalesce(rating, -1) rating from trust_cert', dbr)
        users.index.name = 'id'
        byLogin = users.reset_index().set_index('login')
        certs['from_'] = byLogin.loc[certs.voter].id.values
        certs['to_'] = byLogin.loc[certs.subject].id.values
        edges = [{'from': c.from_, 'to': c.to_,
                  'rating': c.rating if c.rating >= 0 else None }
                 for _, c in certs.iterrows()]
        return {
            "nodes": nodes,
            "edges": edges
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

        [github_repo]
        read_token: SEKRET
        '''.split('\n')
    ])

    fs = {
        './conf.ini': config
    }

    def __init__(self, path='.', web_ua=False):
        self.path = path
        self.web_ua = web_ua

    @property
    def cwd(self):
        return MockIO('.')

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
        from sys import argv
        from urllib.request import build_opener
        from pathlib import Path
        from sqlalchemy import create_engine

        logging.basicConfig(level=logging.INFO)
        main(argv, cwd=Path('.'),
             build_opener=build_opener,
             create_engine=create_engine)

    _script()
