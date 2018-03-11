r'''dbr_norm1 - normalize budget, reward spreadsheets

..

Usage:
  dbr_norm1 [options] save_sheets <xlsx>
  dbr_norm1 [options] normalize
  dbr_norm1 [options] insert

Options:
  <xlsx>               the big spreadsheet in .xls format
                       e.g. 'Pub Member Budget Allocation-Spending.xlsx'
  --pay-period=YYYYMM  pay period in YYYYMM format [default: 201801]
  --data-dir=DIR       where to save CSV, pkl files [default: sheets]
  --db-access=FILE     where to find access credentials
                       [default: ram-dbr-db-access.json]


'''

import json
import logging

from docopt import docopt
import pandas as pd
from sqlalchemy import types as sql_types  # ISSUE: aimbient?

log = logging.getLogger(__name__)


def main(argv, cwd, create_engine):
    log.debug('pandas version: %s', pd.__version__)
    log.debug('argv: %s', argv)
    opt = docopt(__doc__.split('..\n', 1)[1], argv=argv[1:])
    log.debug('opt: %s', opt)

    yyyymm = opt['--pay-period']

    data_cache = DataCache(cwd / opt['--data-dir'])

    if opt['save_sheets']:
        big = BigSheet.read_xlsx(cwd / opt['<xlsx>'], yyyymm)
        big.to_cache(data_cache)
    elif opt['normalize']:
        BigSheet.normalize(data_cache, yyyymm)
    elif opt['insert']:
        with (cwd / opt['--db-access']).open('r') as txt_in:
            url = json.load(txt_in)["url"]
        dbr = create_engine(url)

        with dbr.connect() as con:
            BigSheet.insert(con, data_cache)


class DataCache(object):
    def __init__(self, data_dir):
        self.__data_dir = data_dir

    def save_sheets(self, info):
        for fname, data in info:
            with (self.__data_dir / fname).open('wb') as out:
                logging.info('saving %s...', fname)
                data.to_pickle(out)

    def read(self, names):
        logging.info('reading...')
        sheets = []
        for fname in names:
            with (self.__data_dir / fname).open('rb') as bfp:
                sheets.append(pd.read_pickle(bfp))
        return sheets


class BigSheet(object):
    denorm_names = ['budget.pkl', 'reward.pkl']
    norm_names = ['issue.pkl', 'reward_vote.pkl', 'budget_vote.pkl']

    def __init__(self, yyyymm, budget_sheet, rewards_sheet):
        self.yyyymm = yyyymm
        self.budget_sheet = budget_sheet
        self.rewards_sheet = rewards_sheet

    @classmethod
    def sheet_names(cls, yyyymm):
        return ['Budget ' + yyyymm, 'Rewards ' + yyyymm]

    @classmethod
    def read_xlsx(cls, xlsx, yyyymm):
        (budget_pp, rewards_pp) = cls.sheet_names(yyyymm)
        with xlsx.open('rb') as fp:
            logging.info('reading %s...', xlsx)
            xls = pd.read_excel(
                fp, sheet_name=[budget_pp, rewards_pp])
        logging.info('sheets: %s', xls.keys())
        return cls(yyyymm, xls[budget_pp], xls[rewards_pp])

    def to_cache(self, cache):
        cache.save_sheets([
            ('budget.pkl', self.budget_sheet),
            ('reward.pkl', self.rewards_sheet)
        ])

    def issues(self,
               hd_rows=3,
               num_title_status=[0, 2, 9],
               repo='rchain/Members'):
        log.info('normalizing issues...')
        issue = self.budget_sheet.iloc[hd_rows:, num_title_status]
        issue.columns = ['num', 'title', 'status']
        issue = issue[~issue.num.isnull()]
        issue.num = issue.num.astype(int)
        issue.set_index('num', inplace=True)
        issue['repo'] = repo
        # issue = issue.drop('status', axis=1)
        log.info('issues:\n%s', issue.head())
        return issue

    def budget_votes(self, yyyymm):
        log.info('normalizing budget votes...')
        budget_vote = self.budget_sheet.iloc[3:]
        budget_vote.columns.values[0] = 'issue_num'
        budget_vote = budget_vote.rename({})
        budget_vote.set_index(u'issue_num', inplace=True)
        budget_vote = budget_vote.iloc[:, 11:-2]

        budget_vote = stack(budget_vote, ['amount', 'voter', 'tally'])
        budget_vote = budget_vote[~budget_vote.amount.isnull() &
                                  ~budget_vote.voter.isnull()]
        budget_vote = budget_vote.reset_index()
        budget_vote = budget_vote[budget_vote.voter != '#ERROR!']
        budget_vote.issue_num = budget_vote.issue_num.astype(int)

        budget_vote = budget_vote.set_index(['issue_num', 'voter']).drop(
            'tally', axis=1).sort_index()

        pay_period_start = pd.to_datetime(yyyymm + '01')
        budget_vote['pay_period'] = pay_period_start
        budget_vote = budget_vote.reset_index().set_index(
            ['pay_period', 'issue_num', 'voter']).sort_index()

        x = budget_vote
        if any(x.index.duplicated()):
            log.warn('dup budget votes!\n%s', x[x.index.duplicated()])
            budget_vote = x[~x.index.duplicated()]

        log.info('budget votes:\n%s', budget_vote.head(15))
        return budget_vote

    def reward_votes(self, yyyymm):
        log.info('normalizing reward votes...')
        reward_vote = self.rewards_sheet
        reward_vote.columns = reward_vote.iloc[1]
        reward_vote = reward_vote.rename(
            columns={'Github Issues': 'issue_num'})
        reward_vote = reward_vote.iloc[2:]

        reward_vote = self._reward_norm(reward_vote).set_index(
            ['issue_num', 'voter', 'worker']).sort_index()

        ok = reward_vote.portion.apply(lambda x: isinstance(x, (float, int)))
        if any(~ok):
            log.warn('oops!\n%s', reward_vote[~ok])
            reward_vote = reward_vote[ok]
        reward_vote['percent'] = (reward_vote.portion * 100).astype(int)
        reward_vote = reward_vote.drop('portion', axis=1)

        pay_period_start = pd.to_datetime(yyyymm + '01')
        reward_vote['pay_period'] = pay_period_start

        reward_vote = reward_vote.reset_index().set_index(
            ['pay_period', 'issue_num', 'voter', 'worker']).sort_index()

        dups = reward_vote.index.duplicated()
        if any(dups):
            log.warn('reward_vote: DUPS!\n%s', reward_vote[dups])
            reward_vote = reward_vote[~dups]
        log.info('reward votes:\n%s', reward_vote.head(30))
        return reward_vote

    @classmethod
    def _reward_norm(cls, df):
        out = []
        # print "columns:", len(df.columns), df.columns.values[a1('Q'):]
        for issue_num in df.issue_num.dropna().unique():
            log.debug('issue num: %s', issue_num)
            ea_issue = df[(df.issue_num == issue_num)]
            for vote_ix in range(a1('Q'), len(df.columns), 3):
                # print "vote cols:", df.columns.values[vote_ix:vote_ix + 3]
                votes = ea_issue.iloc[1:, [a1('C'), a1('M'), vote_ix]].dropna()
                votes.columns.values[2] = 'portion'
                votes = votes.rename(columns={'Member': 'worker'})
                votes = votes[votes.portion != 0]
                # print "voter:", ea_issue.iloc[0, vote_ix + 1]
                if len(votes) > 0:
                    votes['voter'] = ea_issue.iloc[0, vote_ix + 1]
                    votes = votes[~votes.voter.isnull()]  ##@@FIXME?
                    # print "@@votes:", votes
                    out.append(votes)
        return pd.concat(out)

    @classmethod
    def normalize(cls, data_cache, yyyymm):
        [budget, reward] = data_cache.read(BigSheet.denorm_names)
        big = BigSheet(yyyymm, budget, reward)
        issues = big.issues()
        budget_votes = big.budget_votes(yyyymm)
        reward_votes = big.reward_votes(yyyymm)
        data_cache.save_sheets([
            ('issue.pkl', issues),
            ('reward_vote.pkl', reward_votes),
            ('budget_vote.pkl', budget_votes),
        ])

    @classmethod
    def only_known_users(cls, df, login, name_cols):
        ix_cols = df.index.names
        df = df.reset_index()
        for nc in name_cols:
            ok = df[nc].isin(login)
            if any(~ok):
                log.warn('unkonwn %s:\n%s', nc, df[~ok])
            df = df[ok]
        return df.set_index(ix_cols)

    @classmethod
    def insert(cls, con, data_cache):
        dfs = DataCache.read(cls.norm_names)
        [issues, reward_votes, budget_votes] = dfs

        users = pd.read_sql('select login from github_users', con=con)

        budget_votes = cls.only_known_users(
            budget_votes, users.login, ['voter'])
        reward_votes = cls.only_known_users(
            reward_votes, users.login, ['voter', 'worker'])
        table_info = [
            ('issue', issues),
            ('reward_vote', reward_votes),
            ('budget_vote', budget_votes),
        ]
        # delete in reverse order
        for table_name, _ in reversed(table_info):
            log.info('delete from %s...', table_name)
            con.execute('delete from ' + table_name)  # ISSUE: truncate?

        for table_name, data in table_info:
            log.info('insert %d into %s...', len(data), table_name)
            data.to_sql(
                table_name, con=con, if_exists='append')


def stack(df, cols):
    col_ix = 0
    out = None
    while col_ix + len(cols) < len(df.columns):
        slice = df.iloc[:, col_ix:col_ix + len(cols)]
        slice.columns = cols
        if out is None:
            out = slice
        else:
            out = out.append(slice)
        col_ix += len(cols)
    return out


def a1(letter):
    return ord(letter) - ord('A')


def noblob(df,
           pad=4):
    df = df.reset_index()
    return {col: sql_types.String(length=pad + df[col].str.len().max())
            for col, t in zip(df.columns.values, df.dtypes)
            if t.kind == 'O'}


def other():
    # In[308]:


    # In[179]:

    # In[454]:

    if 0:
        con.execute('delete from github_users')
        ram_users.to_sql('github_users', con=dbr, if_exists='replace',
                         dtype=noblob(ram_users))
        con.execute('ALTER TABLE `github_users` ADD PRIMARY KEY (`login`);')


def to_sql(dbr, issues, budget_votes, yyyymm):

    with dbr.connect() as con:

        log.info('insert %d issues...', len(issues))
        con.execute('delete from issue')
        issues.drop('status', axis=1).to_sql(
            'issue', con=con, if_exists='append')


def other():
    # In[326]:


    dbr.execute('truncate table reward_vote')
    reward_vote[reward_vote.voter.isin(ram_users.index) &
                reward_vote.worker.isin(ram_users.index)
               ].to_sql('reward_vote', con=dbr, if_exists='append', index=False)


    # ## Suggesting rewards based on reactions

    # In[434]:

    reactions_q = '''
    {
      repository(owner: "rchain", name: "Members") {
        issues(first: 100, orderBy: {field: UPDATED_AT, direction: DESC}) {
          nodes {
            number
            title
            updatedAt
            comments(last: 50) {
              nodes {
                createdAt
                author {
                  login
                }
                reactions(last: 50) {
                  nodes {
                    content
                    user {
                      login
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
    '''
    reactions = repoRd.runQ(reactions_q)
    len(reactions['repository']['issues']['nodes'])


    # In[517]:

    voter = 'dckc'

    voter_reactions = pd.DataFrame([
            dict(issue_num=issue['number'],
                 # title=issue['title'],
                 worker=comment['author']['login'],
                 createdAt=comment['createdAt'],
                 #content=reaction['content'],
                 voter=reaction['user']['login']
                )
            for issue in reactions['repository']['issues']['nodes']
            for comment in issue['comments']['nodes']
            for reaction in comment['reactions']['nodes']
            if reaction['content'] in ['HEART', 'HOORAY', 'LAUGH', 'THUMBS_UP']
        ]).set_index(['voter', 'issue_num', 'worker']).sort_index()
    voter_reactions[voter_reactions.index.get_level_values(0) == voter]


    # In[451]:

    reward_suggestions = voter_reactions.index.difference(
      reward_vote.set_index(['voter', 'issue_num', 'worker']).index
    )
    pd.DataFrame(index=reward_suggestions)


    # ## Advogato style trust metric
    # 
    # http://advogato.p2b.tv/trust-metric.html

    # In[521]:

    edges = voter_reactions.reset_index()[['voter', 'worker']].sort_values(['voter', 'worker']).drop_duplicates()

    edges.head()


    # In[537]:

    import socialsim.net_flow as net_flow

    # capacities = [800, 200, 50, 12, 4, 2, 1] # fom net_flow.py
    capacities = [100, 50, 12, 4, 2, 1] # fom net_flow.py
    g = net_flow.NetFlow()

    for _, e in edges.iterrows():
        g.add_edge(e.voter, e.worker)

    seed = ['lapin7', 'kitblake', u'jimscarver']
    superseed = "superseed"
    for s in seed:
        g.add_edge(superseed, s)

    g.max_flow_extract(superseed, capacities)


    # In[ ]:




    # ## Authenticating Coop Members via Discord's OAuth 2 API
    # 
    # https://discordapp.com/developers/docs/topics/oauth2
    # https://discordapp.com/developers/docs/reference
    # 
    # https://requests-oauthlib.readthedocs.io/en/latest/oauth2_workflow.html#backend-application-flow
    # 

    # In[506]:

    import json
    from oauthlib.oauth2 import BackendApplicationClient
    from requests_oauthlib import OAuth2Session

    def discord_access(scope=['identify', 'guilds', 'connections']):
        from pathlib import Path
        with Path('discord_api_key.json').open() as fp:
            creds = json.load(fp)
        client_id, client_secret = creds['id'], creds['secret']
        client = BackendApplicationClient(client_id=creds['id'])
        oauth = OAuth2Session(client=client, scope=scope)
        token = oauth.fetch_token(token_url='https://discordapp.com/api/oauth2/token',
                                  scope=scope,
                                  client_id=client_id,
                                  client_secret=client_secret)
        return creds, client, oauth, token

    _creds, discord_client, discord_session, discord_token = discord_access()
    discord_token['scope']


    # In[507]:

    import requests

    authz = {'Authorization': '{ty} {tok}'.format(ty=discord_token['token_type'],
                                tok=discord_token['access_token'])}
    x = requests.get('https://discordapp.com/api/v6/users/@me',
                 headers=authz)
    x.json()


    # In[508]:

    requests.get('https://discordapp.com/api/v6/users/@me/connections',
                 headers=authz).json()


    # In[505]:

    requests.get('https://discordapp.com/api/v6/guilds/{id}'.format(id='375365542359465989'),
                 headers=authz).json()

if __name__ == '__main__':
    def _script():
        from sys import argv, stderr
        from os import environ
        from pathlib import Path
        from sqlalchemy import create_engine

        logging.basicConfig(level=logging.DEBUG,
                            stream=stderr,
                            datefmt='%02H:%02M:%02S')
        main(argv, cwd=Path('.'),
             create_engine=create_engine)

    _script()
