# RChain Distribute Budgeting and Rewards (rchain-dbr)

The [RChain Cooperative](https://rchain.coop) is developing a
decentralized, economically sustainable public compute infrastructure.
As part of its efforts toward coordination at scale, it runs a [bounty
program][rb] with distributed budgeting and rewards. This `rchain-dbr`
code powers the web site where budgets and rewards are decided.

[rb]: https://github.com/rchain/bounties

copyright (c) 2018 by by [Dan Connolly
(dckc)](http://www.madmode.com/) and collaborators.

license: GPL 2 (inherited from xataface)

## Features and use cases

See

  - [Getting Involved in the RChain Bounty Program][p1804]  
    presented Spring 2018 at the RChain Developer Conference in Boulder, CO
	- [video](https://www.youtube.com/watch?v=HsQTDNEIbjs&t=1s)
  - [Usable Web app prototype for RAM distributed budgeting and reward
system #260][260]

[p1804]: https://docs.google.com/presentation/d/1B2Vu8o3ACwruY6HY1ayXRQ4qkNKsMy4hdbOdxrCHI2o/edit#slide=id.p
[260]: https://github.com/rchain/bounties/issues/260

## Design notes: toward node.js and RChain from LAMP

see CONTRIBUTING.md, o2r/README.md


## Installation and Configuration

see INSTALL.md


## Contents

 - `o2r` - OAuth to RChain gateway
 - `index.php` - CRUD web UI (xataface app)
   - `conf.ini.example`, `conf/ApplicationDelegate.php`
   - `tables/` - per-table, field tweaks
   - `actions.ini` - discord verification etc.
   - `xataface_template/modules/Auth/XDB/XDB.php` - OAuth integration
     - `lib/`
	   - _ISSUE: move XDB.php to lib? rename lib?_
     - `composer.json` - OAuth libraries
       - `composer_download.php`, `composer.lock`
   - `templates/` - logo, fine print
   - `Web.config` - tell ASP.net to hide Xataface config files
 - `dbr_schema/` - core database schema: budget votes, reward votes, etc.
 - `trust_sync/` - sync, trust metric
 - `deploy_tasks/` - toward automated deployment with ansible, systemd
