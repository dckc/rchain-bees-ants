## Dependencies: mysql-events, rchain-api


As is traditional, start with:

```
npm install
```

## Create an account authorized to get replication logs

Use `node server.js --help` for full usage and options.

The options (with defaults) for connecting to mysql are:

```
 --host HOST     mysql connection host [default: 127.0.0.1]
 --port PORT     mysql connection port [default: 3506]
 --user USER     mysql connection user [default: rchain_binlog]
 --passkey VAR   environment variable for mysql password
                 [default: RCHAIN_BINLOG_PASSWORD]
```

To create the account, log in to the mysql server as the administrative user and ...

```
mysql> create user 'U1'@'localhost' identified by '...';
Query OK, 0 rows affected (0.02 sec)

mysql> GRANT REPLICATION SLAVE, REPLICATION CLIENT, SELECT ON *.* TO 'U1'@'localhost';
Query OK, 0 rows affected (0.00 sec)
```

## Configure binary logging for xataface in mysql

Symptoms: `ER_NO_BINARY_LOGGING: You are not using binary logging`

Solution: put `rchain_binlog.cnf` in `/etc/mysql/mysql.conf.d` on the
mysql server host and `service restart mysql`.


## Connecting to RChain

The options (and defaults) for connecting to a node are:

```
 --grpc-host H   RChain node host [default: localhost]
 --grpc-port P   RChain node port [default: 40401]
```

As discussed in [User guide for running RNode][rnode], there are a
number of options for running RNode.

One way that is known to work on Ubuntu 16.04 and as of rchain dev Aug
2 `7c3500a3892` is:


```
$ git clone https://github.com/rchain/rchain
$ cd rchain
$ git checkout dev
$ sbt clean rholang/bnfc:generate casper/test:compile node/debian:packageBin
$ sudo apt install ./node/target/rnode_0.5.3_all.deb

$ boot=rnode://c61769b39d368cbcbc9499634e030386c79d5b02@52.119.8.108:40400
$ vsk=...ask around...
$ rnode run --no-upnp --bootstrap $boot --validator-private-key $vsk
```

[rnode]: https://rchain.atlassian.net/wiki/spaces/CORE/pages/428376065/User+guide+for+running+RNode
