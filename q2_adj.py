"""q2_adj -- adjustments to fix Q2 reporting

Usage:
  q2_adj [options] import-invoices
  q2_adj [options] import-invoice-summary
  q2_adj [options] make-claims-table

Options:
  --claims=FILE     Claims tab [default: cache/Declarations - Claims.csv]
  --summary=FILE    Invoice summary [default: cache/import_invoice_summary.csv]
  --pay-period=YM   Pay period to work on [default: 201805]
  --config=FILE     config file with github_repo.read_token
                    and _databse.db_url
                    [default: conf.ini]
  --invoices=DIR    directory (tree) of .pdf invoices [default: cache]

"""

from sys import stderr
from datetime import datetime
import re

from docopt import docopt
import pandas as pd

from social_coding_sync import IO


def main(argv, cwd, run, create_engine):
    cli = docopt(__doc__, argv=argv[1:])
    _log(cli)
    pay_period = datetime.strptime(cli['--pay-period'] + '01', '%Y%m%d')
    _log((pay_period, pay_period.strftime('%b')))
    io = IO(create_engine, build_opener, cwd / cli['--config'])
    if cli['import-invoice-summary']:
        import_invoice_summary(pay_period, str(cwd / cli['--summary']), io.db())
    elif cli['make-claims-table']:
        make_claims_table(pd.read_csv(str(cwd / cli['--claims'])),
                          pay_period.strftime('%b'), io.db())
    elif cli['import-invoices']:
        data = read_invoices(pay_period,
                             cwd / cli['--invoices'],
                             mkConvert(run))
        _log('inserting %d records into invoice_rewards' % len(data))
        data.reset_index().to_sql('invoice_rewards', io.db(),
                                  index=False, if_exists='replace')


def _log(x):
    print(x, file=stderr)


def build_opener(*args):
    raise IOError('not allowed')


def make_claims_table(claims, month, db):
    pp_claims = claims[claims.Month == month]
    pp_claims = pp_claims[['Total in USD', 'Month', 'GithubName']]
    _log(pp_claims.head())
    pp_claims.to_sql('claims_' + month, db)


def import_invoice_summary(pay_period, rd, db):
    data = pd.read_csv(rd,
                       parse_dates=['pay_period'])
    data = data[data.pay_period == pay_period]
    _log(data.columns)
    _log(data.head(2))
    data.to_sql('import_invoice_summary', db,
                if_exists='replace', index=False)


def read_invoices(pay_period, rd, pdftotxt):
    invoices = rd.glob('**/*.pdf')
    out = None
    for inv in invoices:
        _log(str(inv))
        txt = pdftotxt(inv)
        cols, detail, subtot = parse_rewards(txt.open().readlines())
        rewards = pd.DataFrame.from_records(detail, columns=cols)
        if len(rewards) > 0:
            if rewards.reward_usd.sum() != subtot:
                raise ValueError()
            rewards['pay_period'] = pay_period
            _log(rewards.groupby(['pay_period', 'worker'])[['reward_usd']].sum())
            rewards = rewards.set_index(['pay_period', 'worker', 'issue_num'])
            # _log(rewards)
            if out is None:
                out = rewards
            else:
                out = out.append(rewards)
    return out


def parse_rewards(lines):
    github_id = None
    detail_cols = []
    detail = []
    subtot = None

    money = lambda txt: float(txt.replace(',', ''))  # noqa
    desc = lambda txt: txt.strip()  # noqa

    styles = [
        (r'Issue Number\s+Description\s+USD\s*',
         r'(\d+)\s+(.{65})\s+\(?\$\s*([\d\.,]+)\)?',
         ['issue_num', 'title', 'reward_usd'],
         [int, desc, money]),
        (r'Issue #\s+Description\s+# Votes\s+Budget\s+% Reward\s+USD\s*',
         r'(\d+)\s+(.{53})\s+(\d+)\s+\(?\$\s*([\d\.,]+)\)?\s+'
         '(\d+\.\d+) %\s+\(?\$\s*([\d\.,]+)\)?',
         ['issue_num', 'title', 'vote_qty',
          'budget_usd', 'percent_avg', 'reward_usd'],
         [int, desc, int,
          money, float, money])
    ]

    for line in lines:
        if github_id is None:
            hd = line.strip()[:18].strip()
            if hd == 'GitHub ID':
                github_id = line.strip()[20:50].strip()
        elif not detail_cols:
            for hd_pat, detail_pat, cols, col_types in styles:
                if re.search(hd_pat, line):
                    detail_cols = cols
                    # _log(detail_cols)
                    break
        elif line.strip().startswith('Add rows above') or line.strip() == '':
            pass
        elif line.strip().startswith('Subtotal of Issues'):
            subtot = money(line.strip().split('($')[1].strip()[:-1])
            # _log(('subtot:', subtot))
            break
        else:
            m = re.search(detail_pat, line)
            if m:
                values = [f(txt) for f, txt in zip(col_types, m.groups())]
                record = dict(dict(zip(detail_cols, values)),
                              worker=github_id)
                # _log(record)
                detail.append(record)
            else:
                _log(line + 'MISMATCH: ' + detail_pat)

    return (detail_cols + ['worker']), detail, subtot


def mkConvert(run):
    def convert(pdf):
        txt = pdf.with_suffix('.txt')
        run(['pdftotext', '-layout', str(pdf), str(txt)])
        return txt

    return convert


if __name__ == '__main__':
    def _script():
        from sys import argv
        from pathlib import Path
        from subprocess import run
        from sqlalchemy import create_engine

        main(argv[:], cwd=Path('.'), run=run,
             create_engine=create_engine)

    _script()
