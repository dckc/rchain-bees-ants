function makeSocialNetwork(makeXHR) {
    function fetch() {
        return new Promise(function (resolve, reject) {
            const xhr = makeXHR();
            xhr.open("GET", "/aux/trust_net");
            xhr.onload = function () {
                if (this.status >= 200 && this.status < 300) {
                    resolve(JSON.parse(xhr.response));
                } else {
                    reject({
                        status: this.status,
                        message: xhr.statusText
                    });
                }
            };
            xhr.onerror = function () {
                reject({
                    status: this.status,
                    message: xhr.statusText
                });
            };
            xhr.send();
        });
    }


    // colors get darker like karate belts
    const colors = [
        '#f0f0f0', // "white belt"
        'khaki', // apprentice
        'orange', // journeyer
        'darkgray' // master
    ];

    function nodes(net) {
        return net.nodes.map(
            n => ({
                id: n.login,
                color: {
                    background: colors[n.rating] || '#f0f0f0',
                    border: 'black'
                },
                label: n.login,
            })
        );
    }

    function drawCerts(net, container) {
        const edges = net.certs.map(
            e => ({
                'from': e.voter,
                'to': e.subject,
                arrows: 'to',
                color: {color: colors[e.rating]},
            })
        );
        render(nodes(net), edges, container);
    }

    function drawFlow(net, rating, container) {
        const { who, why } = net.flow[rating - 1];
        const seed = { id: '<superseed>', label: '<superseed>' };
        const logins = who.map(n => n.login);

        const edges = why.map(
            e => ({
                'from': e.voter,
                'to': e.subject,
                label: e.flow.toString(),
                arrows: 'to',
                color: {color: colors[rating]},
            })
        );
        render(nodes(net).filter(n => logins.includes(n.id)).concat([seed]),
               edges, container);
    }

    function render(nodes, edges, container) {
        var network = new vis.Network(
            container,
            {
                nodes: new vis.DataSet(nodes),
                edges: new vis.DataSet(edges)
            },
            {
                interaction: {
                    navigationButtons: true,
                    keyboard: true
                }
            });
    }

    return Object.freeze({ fetch, drawCerts, drawFlow });
}
