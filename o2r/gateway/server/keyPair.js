/** keyPair -- ed25519 signing keys as Capper persistent objects

key parts (publicKey, privateKey) are persisted in hex, which
should integrate nicely with rho:pubkey:ed25519:xxxxx.

 */

// ref https://nodejs.org/api/util.html#util_custom_inspection_functions_on_objects
// ack: https://stackoverflow.com/a/46870568
const inspect = require('util').inspect;

const sign = require('tweetnacl').sign;  // ocap discpline: "hiding" keyPair

// TODO: Buffer() is deprecated.
const b2h = bytes => Buffer.from(bytes).toString('hex');
const h2b = hex => Buffer.from(hex, 'hex');
const t2b = text => Buffer.from(text);

const def = obj => Object.freeze(obj);  // cf. ocap design note


module.exports.appFactory = appFactory;
function appFactory({ randomBytes }) /*: CapperApp */ {
    return def({ keyPair: keyPair });

    function keyPair(context){
	let state = context.state ? context.state : null /* state.X throws until init() */;

	function init(label) {
	    const key = sign.keyPair.fromSeed(randomBytes(32));

	    state = context.state;
	    state.label = label;
	    state.publicKey = b2h(key.publicKey);
	    state.secretKey = b2h(key.secretKey);
	}

	const toString = () => `<keyPair ${state.label}: ${state.publicKey.substring(0, 12)}...>`;
	const signBytes = bytes => sign.detached(bytes, privateKey());

	return def({
	    init, toString, signBytes,
	    signBytesHex: bytes => b2h(signBytes(bytes)),
	    signText: text => signBytes(t2b(text)),
	    signTextHex: text => b2h(signBytes(t2b(text))),
	    publicKey: () => state.publicKey,
	    label: () => state.label,
	    [inspect.custom]: toString
	});

	function privateKey() {
	    return sign.keyPair.fromSecretKey(h2b(state.secretKey)).secretKey;
	}
    }
}


// TODO: adopt community testing norms
function unitTest() {
    const cases = [
	// https://developer.rchain.coop/tutorial/#verify
	{
	    label: 'RChain tutorial verify example',
	    seedHex: 'f6664a95992958bbfeb7e6f50bbca2aa7bfd015aec79820caf362a3c874e9247',
	    pubKeyHex: '288755c48c3951f89c5f0ffe885088dc0970fd935bc12adfdd81f81bb63d6219',
	    messageHex: "a6da46a1dc7ed715d4cd6472a736249a4d11142d160dbef9f20ae493de908c4e",
	    sigHex: 'd0a909078ce8b8706a641b07a0d4fe2108064813ce42009f108f89c2a3f4864aa1a510d6dfccad3b62cd610db0bfe82bcecb08d813997fa7df14972f56017e0b'
	},
	{
	    label: 'trust metric 2018-07-29T02:00:21.259Z',
	    seedHex: '9217509f61d80a69627daad29796774d1b65d06e70762aa114e9aa534c0d76bb',
	    pubKeyHex: '90685cf270025cddab375b3de595e9b87548c5f05f9e5bf17502d7cfcb7259f7',
	    messageHex: '2abc02a201b8020a132a071a056d657267654a0800000000000000000a182a0c1a0a74727573745f636572744a0800000000000000000afc010a4d0a190a172a0b1a09636572745f74696d654a08000000000000000012262a1a1a18323031382d30372d32395430313a34343a34352e3132385a4a0800000000000000002a0800000000000000000a330a160a142a081a06726174696e674a080000000000000000120f2a031a01314a0800000000000000002a0800000000000000000a350a170a152a091a077375626a6563744a08000000000000000012102a041a0261314a0800000000000000002a0800000000000000000a350a150a132a071a05766f7465724a08000000000000000012122a061a0464636b634a0800000000000000002a0800000000000000004a0800000000000000001a0800000000000000004a080000000000000000',
	    sigHex: '6018f96443adbe15ded23957b14be634b8708c80042fd6e9f882f75c3f227dc876d5f2026964483c3ee8b2913f7473d9f8827f32a0281eb1717af053f1f4c90e'
	}
    ];

    assertEqual('turn toByteArray',
		'2abc02a201b8020a132a071a056d657267654a0800000000000000000a182a0c1a0a74727573745f636572744a0800000000000000000afc010a4d0a190a172a0b1a09636572745f74696d654a08000000000000000012262a1a1a18323031382d30372d32395430323a30303a32312e3235395a4a0800000000000000002a0800000000000000000a330a160a142a081a06726174696e674a080000000000000000120f2a031a01314a0800000000000000002a0800000000000000000a350a170a152a091a077375626a6563744a08000000000000000012102a041a0261314a0800000000000000002a0800000000000000000a350a150a132a071a05766f7465724a08000000000000000012122a061a0464636b634a0800000000000000002a0800000000000000004a0800000000000000001a0800000000000000004a080000000000000000',
		'2abc02a201b8020a132a071a056d657267654a0800000000000000000a182a0c1a0a74727573745f636572744a0800000000000000000afc010a350a150a132a071a05766f7465724a08000000000000000012122a061a0464636b634a0800000000000000002a0800000000000000000a350a170a152a091a077375626a6563744a08000000000000000012102a041a0261314a0800000000000000002a0800000000000000000a330a160a142a081a06726174696e674a080000000000000000120f2a031a01314a0800000000000000002a0800000000000000000a4d0a190a172a0b1a09636572745f74696d654a08000000000000000012262a1a1a18323031382d30372d32395430323a30303a32312e3235395a4a0800000000000000002a0800000000000000004a0800000000000000001a0800000000000000004a080000000000000000');
    for (let test of cases) {
	const kpApp = appFactory({
	    randomBytes: () => h2b(test.seedHex)
	});

	const context1 = { state: {} };
	const pair1 = kpApp.keyPair(context1);
	pair1.init(test.label);
	assertEqual('public key:', test.pubKeyHex, pair1.publicKey());

	const message = h2b(test.messageHex);
	const sigHex = pair1.signBytesHex(message);
	assertEqual('signature:', test.sigHex, sigHex);
    }

    // ISSUE: TODO: adopt community testing norms
    function assertEqual(label, expected, actual) {
	if (expected == actual) {
	    console.log('==>', label, 'OK');
	} else {
	    console.error('!!!', label, 'expected', expected, 'got', actual);
	}
    }
}

function integrationTest({ randomBytes }) {
    const kpApp = appFactory({ randomBytes });

    const context1 = { state: {} };
    const pair1 = kpApp.keyPair(context1);
    pair1.init('k1');
    console.log('inspect keyPair:', pair1);
    console.log('keyPair.toString():', pair1.toString());
    console.log('public key:', pair1.publicKey());
    console.log('signature:', pair1.signTextHex('hello world'));
}


if (require.main == module) {
    unitTest();
    // ocap: Import powerful references only when invoked as a main module.
    integrationTest(
	{
	    randomBytes: require('crypto').randomBytes
	});
}
