function sessionUI(session, clock, $) {
    const ui = {
	user: $('#user'),
	session: $('#session'),
	cert_time: $('#cert_time'),
	subject: $('#subject'),
	rating: $('#rating'),
	certify: $('#certify'),
	results: $('#results'),
	recordKey: $('#recordKey'),
	takeTurnTerm: $('#takeTurnTerm'),
	turnSig: $('#turnSig'),
    };

    const sessionInfo = Bacon.fromPromise(session.post('info'));
    sessionInfo.onValue(si => {
	const user = si.userProfile,
	      dob_str = user.detail.created_at,
	      dob = dob_str ? new Date(dob_str) : null,
	      since = dob ? ` since ${dob.getFullYear()}-${dob.getMonth() + 1}` : null,
	      accountDetail = user.username + since;
	ui.user.text(user.displayName)
	    .attr('title', accountDetail)
	    .attr('href', user.url);

	ui.session.text(`login: ${ new Date(si.created).toISOString() }`);

	showCertTime(clock());
    });

    function showCertTime(t) {
	ui.cert_time.val(t.toISOString().substring(0, "yyyy-MM-ddThh:mm".length));
    }

    Bacon.fromPromise(session.post('select', 'users')).onValue(peers => {
	ui.subject.html('');
	peers.forEach(who => ui.subject.append(
	    $('<option>', { value: who.username,
			    html: `${who.username}: ${who.displayName}`
			  })));
    });

    // issue: session.merge(...) => session.post('merge', ...)
    const certifyStart = ui.certify.asEventStream('click').log('certify click');
    const certifyRecord = certifyStart
	      .zip(sessionInfo)
	      .map(([_e, si]) => ({
		  voter: si.userProfile.username,
		  subject: ui.subject.val(),
		  rating: ui.rating.val(),
		  cert_time: clock()
	      })).log('record');
    certifyRecord.onValue(record => {
	showCertTime(record.cert_time);
    });
    const certifySend = certifyRecord
	      .flatMap(record => Bacon.fromPromise(session.post('merge', 'trust_cert', record)));
    const certifyReply = certifySend.merge(certifySend.mapError(err => null)).log('reply');
    certifyStart.awaiting(certifyReply).log('awaiting@@')
	.onValue(loading => {
	ui.certify.attr('disabled', loading);

	if (loading) {
	    ui.results.hide();
	}
    });

    // ISSUE: certifyReply.onError(err => ...)
    certifyReply.onValue(r => {
	ui.recordKey.val(JSON.stringify(r.recordKey));
	ui.takeTurnTerm.val(r.takeTurnTerm);
	ui.turnSig.val(r.turnSig);
	ui.results.show();
    });
}


const def = obj => Object.freeze(obj);

function mockSession({ clock }) {
    const db = {
	// ISSUE: dbr_tables.sql calls it github_users, with login
	users: {
	    key: ['username'],
	    // JSON-stringified key cols -> record
	    records: {
		'["a1"]': { username: 'a1', displayName: 'Angela' },
		'["b2"]': { username: 'b2', displayName: 'Bob' },
		'["c3"]': { username: 'c3', displayName: 'Charlie' },
		'["d4"]': { username: 'd4', displayName: 'Darlene' },
	    }
	},
	trust_cert: {
	    key: ['voter', 'subject'],
	    records: {}
	}
    };

    return def({ info, select, merge });

    function info() {
	const min = 1000 * 60;
	return Promise.resolve({
	    created: new Date(clock().valueOf() - 15 * min),
	    userProfile: {
		username: "dckc", displayName: "Dan Connolly",
		url: 'https://github.com/dckc',
		detail: {
		    createdAt: new Date(2009, 9, 1)
		}
	    }
	});
    }

    function select(tablename) {
	const table = db[tablename];
	if (!table) {
	    return Promise.reject('unknown table: ' + tablename);
	}

	return Promise.resolve(Object.values(table.records));
    }

    function merge(tablename, record) {
	const table = db[tablename];
	if (!table) {
	    return Promise.reject('unknown table: ' + tablename);
	}
	const key = table.key.map(field => record[field]);
	table.records[JSON.stringify(key)] = record;
	return Promise.resolve(key);
    }
}
