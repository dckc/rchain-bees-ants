See https://github.com/rchain/Members/issues/260

## Installation and Configuration

At a high level:

  1. Create OAuth apps in github, discord.
  2. Initialize a mysql database from `dbr_tables.sql` etc.
  3. Install software dependencies.
  4. Fill in `conf.ini` from `conf.ini.template`.

Detailed, executable instructions are in `playbook.yml` following
[ansible][] conventions. Use `ansible-playbook -i inventory.yml playbook.yml`
once you have `inventory.yml` set up appropriately:

```
all:
  hosts:
    SSH_HOST
  vars:
    ansible_user: SSH_USER
    ansible_ssh_pass: ...
    db_host: ...
    db_name: ...
    db_user: ...
    db_password: ...
    gh_client_id: ...
    gh_client_secret: ...
```

You may need to set other ansible vars such as
`ansible_python_interpreter: /usr/local/bin/python2`.

When creating your github OAuth app, the callback URL should
correspond to `github_auth_callback.php`.

[xataface]: http://www.xataface.com/
[ansible]: https://www.ansible.com/

  
## TODO

  - voter_gh: don't let user choose; use their login credentials
  - you can only edit your own votes
    - new votes obsolete old votes?
    - ah: [history logging](http://xataface.com/documentation/how-to/history-howto)
  - reporting epoch: 201712 vs 201801
  - import persons, issues from github repo
    - sync/update
    - bootstrap: [import filters](http://xataface.com/documentation/how-to/import_filters)
    - The Right Way: use graphql
  - money datatype: is integer dollars good enough?
  - [dashboard](http://xataface.com/wiki/Creating_a_Dashboard)

### Beyond PHP

Please excuse the use of PHP; [Rholang][] isn't here yet. :-)

[Rholang]: https://developer.rchain.coop/


