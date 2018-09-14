const usage = `
Replicate MySql events in RChain

Usage:
  server.js [options]

Options:
 --rewards URL   URL of budget and rewards app
                 [default: https://rewards.rchain.coop]
 --grpc-host H   RChain node host [default: localhost]
 --grpc-port P   RChain node port [default: 40401]
 --host HOST     mysql connection host [default: 127.0.0.1]
 --port PORT     mysql connection port [default: 3506]
 --user USER     mysql connection user [default: rchain_binlog]
 --passkey VAR   environment variable for mysql password
                 [default: RCHAIN_BINLOG_PASSWORD]
 --help          show usage help
`;

const MySQLEvents = require('@rodrigogs/mysql-events');
const docopt = require('docopt').docopt;
const rchainAPI = require('rchain-api'),
      RSON = rchainAPI.RSON;

function main(argv, env, { createConnection, grpc, clock }) {
    const cli = docopt(usage, { argv: argv.slice(2) });
    const rchain = rchainAPI.clientFactory({ grpc, clock })
	      .casperClient({ host: cli['--grpc-host'], port: parseInt(cli['--grpc-port']) });

    const acctInfo = { user: cli['--user'],
		       host: cli['--host'], port: parseInt(cli['--port']) };
    const mysql = createConnection(Object.assign({ password: env[cli['--passkey']] }, acctInfo));

    subscribe(mysql, rchain, cli['--rewards'])
	.then(() => console.log('Waiting for database events from...', acctInfo))
	.catch(console.error);
}

async function subscribe(connection, rchain, rewards) {
    const instance = new MySQLEvents(connection, {
	startAtEnd: true,
	excludedSchemas: {
	    mysql: true,
	},
    });

    await instance.start();

    const logVote = (event) => {
	console.log({type: event.type, table: event.table, rows: event.affectedRows.length });
	console.log('@@rows:', event.affectedRows);
	const rho = d => RSON.stringify(RSON.fromData(jsonData(d)));
	const msg = `${rho(event.type)}, ${rho(event.affectedRows)}`;
	const send = `@[\`${rewards}\`, ${rho(event.table)}]!(${msg})`;
	console.log('@@TODO: sign the voting event');
	console.log('@@rho:', send);
	rchain.doDeploy(send)
	    .then(d => console.log('@@doDeploy result:', d));
    };

    ['budget_vote', 'reward_vote'].forEach(t => {
	instance.addTrigger({
	    name: t,
	    expression: `xataface.${t}`,
	    statement: MySQLEvents.STATEMENTS.ALL,
	    onEvent: logVote,
	});
    });

    instance.on(MySQLEvents.EVENTS.CONNECTION_ERROR, console.error);
    instance.on(MySQLEvents.EVENTS.ZONGJI_ERROR, console.error);

    return instance;
};


/**
 * Prepare data for JSON serialization.
 *
 * Replace dates using toISOString and prune undefined properties.
 */
function jsonData(obj) {
    return recur(obj);

    function recur(x) {
	if (typeof x !== 'object' || x == null) {
	    return x;
	} else if (x instanceof Date) {
	    return x.toISOString();
	} else if (x instanceof Array) {
	    return x.map(recur);
	} else {
	    return Object.keys(x).reduce((acc, prop) => {
		if (x[prop] !== undefined) {
		    acc[prop] = recur(x[prop]);
		}
		return acc;
	    }, {});
	}
    }
}

function logged(x) {
    console.log('@@', x);
    return x;
}



if (require.main == module) {
    // Import primitive effects only when invoked as main module.
    //
    // TODO: document Object capability discipline in CONTRIBUTING.md.
    main(process.argv, process.env,
         {
	     createConnection: require('mysql').createConnection,
	     grpc: require('grpc'),
	     clock: () => new Date(),
	 });
}
