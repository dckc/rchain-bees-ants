
# coding: utf-8

# In[1]:

import pandas as pd
dict(pandas=pd.__version__)


# In[302]:

dbr_xls = pd.read_excel('/home/connolly/Downloads/Pub Member Budget Allocation-Spending.xlsx',
                        sheetname=['Budget 201801', 'Rewards 201801'])


# In[303]:

issue = dbr_xls['Budget 201801'].iloc[3:, [0, 2, 9]]
issue.columns = ['num', 'title', 'status']
issue = issue[~issue.num.isnull()]
issue.num = issue.num.astype(int)
issue.set_index('num', inplace=True)
issue['repo'] = 'rchain/Members'
issue.head()


# In[307]:

budget_vote = dbr_xls['Budget 201801'].iloc[3:]
budget_vote.columns.values[0] = 'issue_num'
budget_vote = budget_vote.rename({})
budget_vote.set_index(u'issue_num', inplace=True)
budget_vote = budget_vote.iloc[:, 11:-2]

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

budget_vote = stack(budget_vote, ['amount', 'voter', 'tally'])
budget_vote = budget_vote[~budget_vote.amount.isnull() &
                          ~budget_vote.voter.isnull()]
budget_vote = budget_vote.reset_index()
budget_vote = budget_vote[budget_vote.voter != '#ERROR!']
budget_vote.issue_num = budget_vote.issue_num.astype(int)

budget_vote = budget_vote.set_index(['issue_num', 'voter']).drop('tally', axis=1).sort_index()
budget_vote.head(15)


# In[308]:

reward_vote = dbr_xls['Rewards 201801']  # .iloc[2:]
reward_vote.columns = reward_vote.iloc[1]
reward_vote = reward_vote.rename(columns={'Github Issues': 'issue_num'})
reward_vote = reward_vote.iloc[2:]

# reward_vote.issue_num.unique()

def a1(letter):
    return ord(letter) - ord('A')

def reward_norm(df):
    out = []
    # print "columns:", len(df.columns), df.columns.values[a1('Q'):]
    for issue_num in df.issue_num.dropna().unique():
        # print "issue num:", issue_num
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
                #print "@@votes:", votes
                out.append(votes)
    return pd.concat(out)

reward_vote = reward_norm(reward_vote).set_index(['issue_num', 'voter', 'worker']).sort_index()
reward_vote.head()


# In[309]:

ok = reward_vote.portion.apply(lambda x: isinstance(x, (float, int)))
reward_vote[~ok]


# In[310]:

reward_vote = reward_vote[ok]
reward_vote['percent'] = (reward_vote.portion * 100).astype(int)
reward_vote = reward_vote.drop('portion', axis=1)
reward_vote.head(30)


# In[179]:

import sqlalchemy as sqla


# In[454]:

import json

def theDatabase():
    url = json.load(open("ram-dbr-db-access.json"))["url"]
    return sqla.create_engine(url)

dbr = theDatabase()
pd.read_sql('select 1', dbr)


# In[418]:

from sys import stderr

import json
from urllib2 import Request

GH_ENDPOINT = 'https://api.github.com/graphql'


class QuerySvc(object):
    def __init__(self, urlopener, token):
        self.__urlopener = urlopener
        self.__token = token
  
    def runQ(self, query, variables={}):
        options = {
            'method' : 'post',
            
            }
        req = Request(
            GH_ENDPOINT,
            data=json.dumps({ 'query': query, 'variables': variables }),
            headers={
                "Authorization": "bearer " + self.__token
            })
        print >>stderr, "post", req
        response = self.__urlopener.open(req)
        if response.getcode() != 200:
            raise response
        body = json.loads(response.read().decode('utf-8'))
        if body.get('errors'):
            raise IOError(body['errors'])
        return body['data']


def theQuerySvc():
    from urllib2 import build_opener
    from json import load
    repoRd = load(open('ram-dbr-access-token.json'))['token']
    return QuerySvc(build_opener(), repoRd)


repoRd = theQuerySvc()
repoRd.runQ('query { viewer { login }}')


# In[379]:

q_collaborators = '''
query PARAMETERS {
  repository(owner:"rchain", name:"Members") {
    collaborators(first:100 CURSOR) {
      totalCount
      pageInfo {
        endCursor,
        hasNextPage      
      }
      edges {
        permission
        node {
          login
          createdAt
          avatarUrl
          bio
          name
          email
          location
          websiteUrl
          followers {
            totalCount
          }
        }
      }
    }
  }
}
'''

def usersPage(svc, cursor=None):
    maybeParens = lambda s: ('(%s)' % s) if s else ''
    flatMap = lambda a, f: [item for x in a for item in f(x)]
    fmtParams = lambda params: ', '.join([
            '$' + k + ':' + t
            for (k, (v, t)) in params.items()
            if v])
    query = (q_collaborators
        .replace('PARAMETERS', maybeParens(fmtParams({'cursor': [cursor, 'String!']})))
        .replace('CURSOR', ' after: $cursor' if cursor else '')
             )
    #print >>stderr, 'runQ cursor:', cursor
    #print >>stderr, query
    return svc.runQ(query, {'cursor': cursor})


def allUserPages(githubSvc):
    pageInfo = {'endCursor': None}

    out = []
    while 1:
        userInfo = usersPage(githubSvc, pageInfo.get('endCursor'))['repository']['collaborators']
        import pprint
        # print >>stderr, "@@", pprint.pformat(userInfo)
        out.extend(userInfo['edges'])
        pageInfo = userInfo['pageInfo']
        print >>stderr, pageInfo
        if not pageInfo.get('hasNextPage'):
            break
    return out

ram_user_info = allUserPages(repoRd)
ram_user_info[:3]


# In[381]:

ram_users = pd.DataFrame(
    [dict(edge['node'], permission=edge['permission'], followers=edge['node']['followers']['totalCount'])
     for edge in ram_user_info],
    columns=['login', 'followers', 'name', 'location', 'email', 'bio', 'websiteUrl', 'avatarUrl', 'permission', 'createdAt'])
ram_users = ram_users.set_index('login')
ram_users.createdAt = pd.to_datetime(ram_users.createdAt)
ram_users.sort_values(['permission', 'followers'], ascending=[True, False]).head()


# In[387]:

def noblob(df,
           pad=4):
    df = df.reset_index()
    return {col: sqla.types.String(length=pad + df[col].str.len().max())
            for col, t in zip(df.columns.values, df.dtypes)
            if t.kind == 'O'}


with dbr.connect() as con:
    con.execute('delete from github_users')
    ram_users.to_sql('github_users', con=dbr, if_exists='replace',
                     dtype=noblob(ram_users))
    con.execute('ALTER TABLE `github_users` ADD PRIMARY KEY (`login`);')


# In[388]:

dbr.execute('delete from issue')
issue.drop('status', axis=1).to_sql('issue', con=dbr, if_exists='append')


# In[322]:

budget_vote['pay_period'] = pd.to_datetime('2018-01-01')
budget_vote = budget_vote.reset_index()
budget_vote.head()


# In[392]:

budget_vote[~budget_vote.voter.isin(ram_users.index)]


# In[402]:

x = budget_vote.set_index(['pay_period', 'issue_num', 'voter']).sort_index()
budget_vote = x[~x.index.duplicated()].reset_index()


# In[403]:

dbr.execute('truncate table budget_vote')
budget_vote[budget_vote.voter.isin(ram_users.index)].to_sql('budget_vote', con=dbr, if_exists='append', index=False)


# In[326]:

reward_vote['pay_period'] = pd.to_datetime('2018-01-01')
#reward_vote = reward_vote.reset_index()
reward_vote.head()


# In[394]:

reward_vote[~(reward_vote.voter.isin(ram_users.index) &
            reward_vote.worker.isin(ram_users.index) &
            (reward_vote.percent > 0))
           ]


# In[410]:

x = reward_vote.groupby(['pay_period', 'issue_num', 'voter'])
x = x[['percent']].sum()
x[x.percent > 100]


# In[414]:

x = reward_vote.set_index(['pay_period', 'issue_num', 'voter', 'worker']).sort_index()
x[x.index.duplicated()]


# In[415]:

reward_vote = x[~x.index.duplicated()].reset_index()


# In[416]:

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

