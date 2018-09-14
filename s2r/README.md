# s2r -- Replicate SQL updates to RChain

**Work in Progress**

## TODO

 - Sign data when we put it on the chain.
 - Figure out how to fully propose blocks, not just deploy code.


## Usage

Once access to the mysql binlog and RChain is set up (see `INSTALL.md`),
start the service and watch it replicate mysql events by deploying
rholang send events:

```
RCHAIN_BINLOG_PASSWORD=... node server.js 
...
{ type: 'INSERT', table: 'budget_vote', rows: 1 }
@@rows: [ { after: 
     { pay_period: 2018-07-01T05:00:00.000Z,
       issue_num: 199,
       voter: 'dckc',
       amount: 425,
       vote_time: 2018-08-05T01:19:05.000Z,
       weight: null },
    before: undefined } ]
@@TODO: sign the voting event
@@rho: @[`https://rewards.rchain.coop`, "budget_vote"]!("INSERT", [@"after"!(@"amount"!(425) | @"issue_num"!(199) | @"pay_period"!("2018-07-01T05:00:00.000Z") | @"vote_time"!("2018-08-05T01:19:05.000Z") | @"voter"!("dckc") | @"weight"!(Nil))])
@@doDeploy result: { success: true, message: 'Success!' }
```

In your rnode log, you should see:

```
20:19:05.205 [grpc-default-executor-1] INFO  c.rchain.casper.MultiParentCasper$ - CASPER: Received Deploy #1533431945199 -- @{[``https://rewards.rcha...
```

Then you can `rnode propose` as usual and see:

```
20:25:07.112 [grpc-default-executor-0] INFO  c.rchain.casper.util.comm.CommUtil$ - CASPER: Beginning send of Block #2 (da4d99f728...) -- Sender ID 1d034ef5e7... -- M Parent Hash 24edc327a4... -- Contents d9f84c498b... to peers...
20:25:07.135 [repl-io-45] INFO  c.rchain.casper.util.comm.CommUtil$ - CASPER: Sent da4d99f728... to peers
20:25:07.135 [repl-io-45] INFO  c.rchain.casper.MultiParentCasper$ - CASPER: Added da4d99f728...
20:25:07.138 [repl-io-45] INFO  c.rchain.casper.MultiParentCasper$ - CASPER: New fork-choice tip is block da4d99f728....
20:25:08.218 [grpc-default-executor-3] INFO  c.rchain.casper.util.comm.CommUtil$ - CASPER: Received block da4d99f728... again.
```
