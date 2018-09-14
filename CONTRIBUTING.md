# Design and development of rchain-dbr

Please excuse the use of PHP; I try to use alternatives below for new
development.


## CRUD powered by xataface, LAMP

Most of the web CRUD UI is built with [xataface][], which lets us
create some SQL tables and write:

```
[tables]
github_users=Users
issue=Issue
...
```

and voila, xataface makes a full CRUD application, with searching and
sorting. For this (and because I have years of experience using it in
[hh-office][]), I am willing to hold my nose and use PHP.

Customizing field widgets, relationships, permissions, and templates
is a little extra work, but it's all quite straightforward.

[xataface]: http://www.xataface.com/
[hh-office]: https://bitbucket.org/DanC/hh-office


## Sync powered by python, sqlalchemy, and pandas

Some auxiliary functions such as sync with github and computing the
trust metric are written in python with sqlalchemy and pandas.
See `social_coding_sync.py`.

[Rholang]: https://developer.rchain.coop/


## Porting the trust metric to Rholang with node.js and Capper

To put certifications such as "I (dckc) certify Bob at journeyer
level" on RChain, `package.json` and `server.js` and such are the
start of a node.js/Express web UI that integrates with RChain nodes
via the [CasperMessage.proto][cp] gRPC protocol.

As in the PHP code, we use OAuth2 to authenticate discord and github
users and we (aim to) use the **member** discord role to verify RChain coop
membership. A May 2017 [simple guide to discord oauth2][orlov] shows that this
is a well-trodden path.

Then we (aim to) represent votes as rholang terms such as `["dckc",
"bob", 2, "deadbeef"]` where 2 is journeyer level and "deadbeef" is a
signature using a key held by this gateway. An on-chain rholang contract
can check such signatures, much like [BasicWallet.rho][bw] as
seen in the [Genesis Block Demo][gbd] of July 11.

To extend persistence and object capability security to off-chain
secrets and configuration, `server.js` is built using [Capper][],
which supports ocap discipline and object persistence in
node.js/Express applications with [webkeys][].

[cp]: https://github.com/rchain/rchain/blob/dev/models/src/main/protobuf/CasperMessage.proto
[bw]: https://github.com/rchain/rchain/blob/dev/casper/src/main/rholang/BasicWallet.rho
[gbd]: https://www.youtube.com/watch?v=WzAdfjwgaQs#t=9m28s
[Capper]: https://github.com/dckc/Capper
[webkeys]: http://waterken.sourceforge.net/web-key/
[orlov]: https://medium.com/@orels1/using-discord-oauth2-a-simple-guide-and-an-example-nodejs-app-71a9e032770


## Object capability (ocap) discipline

In order to supporting robust composition and cooperation without
vulnerability, all JavaScript and python code in this project should
adhere to [object capability discipline][ocap]. (_This discipline is
built-in to Rholang. As to PHP, abandon hope all ye who enter._)

  - **Memory safety and encapsulation**
    - There is no way to get a reference to an object except by
      creating one or being given one at creation or via a message; no
      casting integers to pointers, for example. _JavaScript is safe
      in this way._

      From outside an object, there is no way to access the internal
      state of the object without the object's consent (where consent
      is expressed by responding to messages). _We use `Object.freeze`
      and closures rather than properties on `this` to achieve this.
	  In python, we're experimenting with conventions._

  - **Primitive effects only via references**
    - The only way an object can affect the world outside itself is
      via references to other objects. All primitives for interacting
      with the external world are embodied by primitive objects and
      **anything globally accessible is immutable data**. There must be
      no `open(filename)` function in the global namespace, nor may
      such a function be imported. _It takes some discipline to use
      modules in node.js and python in this way.  We use a convention
      of only accessing ambient authority inside `if (require.main ==
      module) { ... }`._

ISSUE: gloss powerful reference, ambient authority

ISSUE: note integration testing idioms

[ocap]: http://erights.org/elib/capability/ode/ode-capabilities.html
