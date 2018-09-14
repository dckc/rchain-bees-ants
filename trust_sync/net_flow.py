#!/usr/bin/env python
""" net_flow.py:        Network Maximum Flow Graph.
        Copyright (C) 2001 Luke Kenneth Casson Leighton <lkcl@samba-tng.org>
        revised 2010 by Dan Connolly <http://www.w3.org/People/Connolly/>

    This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program; if not, write to the Free Software
    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA


        This is an almost line-for-line translation of the original c code,
        net_flow.c:
        Copyright (C) 1999-2000 Raph Levien <raph@acm.org>

        Usage:

        f = NetFlow()
        f.add_edge(item1, item2)
        f.add_edge(class1, item2)
        f.add_edge(..., ...)
        ...

        capacity_list = [NNNN, NNN, NN, NN, N, N, N]
        mf1 = f.max_flow_extract(supersink, capacity_list)
        mf2 = f.max_flow_extract(supersink2, capacity_list)
        ...

        note: items (nodes) are stored in a dictionary.  therefore,
        [just in case you're new to python] you can therefore evaluate
        anything.  names, strings, unicode, numbers, tuples, complex
        numbers, classes - whatever you like.  python is cool.

        TODO: look at Raph's paper, get the formula for the recommended
        capacity calculations (which are based on the number of nodes)
        and use that as the default for if capacity_list is None

"""

TWEAK = 1
FALSE = 0 #@@ change to python True/False keywords?
TRUE = 1


class Debug:
    """     why on earth this isn't a base-class in python,
        i do _not_ know.  *sigh*
    """
    def __init__(self):
        self.debug_level = 0
        self.warnings = []

    def set_debuglevel(self, level):
        self.debug_level = level

    def get_debuglevel(self):
        return self.debug_level

    def debug(self, str, level=1):
        if level <= self.debug_level:
            print(str)

    def warning(self, str):
        self.warnings.append(str)

    def add_warnings(self, war):
        self.warnings += war

    def get_warnings(self):
        return self.warnings


class NetFlowPriv(Debug):
    """     This class represents edges' view of the nodes
    """

    def __init__(self, succs):
        self.node_sink = {} # 1 if there is flow from this node to the supersink
        self.node_flow = {} # total flow through the node

        self.capacity = None # capacity of each node

        self.__init_graph(succs)

        Debug.__init__(self)

    def __init_graph(self, nf):
        """Initialize edge-oriented structures from node-oriented structures.
        """

        nodes = list(nf.succs.keys())
        qn = len(nodes)

        self.node_sink = dict.fromkeys(nodes, 0)
        self.node_flow = dict.fromkeys(nodes, 0)

        self.node_in_edges = dict([(n, []) for n in nodes])
        self.node_out_edges = dict([(n, []) for n in nodes])

        self.edge_src = []
        self.edge_dst = []
        self.edge_flow = []

        for src in nodes:

            for dst in nf.succs[src]:

                if src == dst: # exclude all node self-references
                    continue

                e = len(self.edge_src)

                self.node_out_edges[src].append(e)
                self.node_in_edges[dst].append(e)

                self.edge_src.append(src)
                self.edge_dst.append(dst)

        self.edge_flow = [0] * len(self.edge_src)

    def from_tree(self, pred_list, node_names):
        """ from_tree: Set up flows in graph based on tree assignment.

            @self: The #NetFlowPriv context.
            @pred_list: The tree assignment, in predecessor form.
            @node_names: list of node names
        """

        for node in node_names:

            last = -1

            if pred_list[node] == -1:
                continue

            self.node_sink[node] = 1
            ix = node

            while ix != last:

                # increment node flow
                next = pred_list[ix]
                self.node_flow[ix] += 1

                if ix != next:

                    # find edge from next to ix and increment edge flow
                    for edge in self.node_in_edges[ix]:

                        if self.edge_src[edge] == next:
                            self.edge_flow[edge] += 1
                            break

                last = ix
                ix = next

    def sanity_check_tree(self, seed, pred, node_list):

        result = 0

        caps = {}
        for node in node_list:
            cap = self.capacity[node]
            if cap < 0:
                cap = 0
            caps[node] = cap

        for node in node_list:
            if pred[node] != -1:
                n = node
                last = -1

                while n != last:
                    caps[n] -= 1
                    last = n
                    n = pred[n]

        for node in node_list:
            if caps[node] < 0:
                cap = self.capacity[node]
                if cap < 0:
                    cap = 0
                self.debug("Node %d flow %d over capacity %d" % \
                    (node, cap - caps[node], cap))
                result = -1

        return result

    def tweak_flow(self):
        """     tweaks the flow.  ??
        """
        for i in list(self.node_flow.keys()):

            self.node_flow[i] -= self.node_sink[i]
            self.capacity[i] -= 1

    def augment(self, seed, node_list):
        """Find a unit augmenting path to the flow.

        :param seed: source of flow
        :param node_list: nodes in the network

        "Each node x is split into two nodes, x- and x+. For a node x
        with capacity c, an edge is added from x- to x+ with capacity
        c - 1. For each edge from s to t in the original graph, we add
        an infinite capacity edge from s+ to t- in the new
        graph. Finally, from each node x, we add a unit capacity edge
        from x- to the supersink node."
        -- http://www.advogato.org/trust-metric.html

        :returns: TRUE iff an augmenting path exists.
        """
        visited_in = {}
        visited_out = {}
        queue = []
        queue_dir = []
        pred = []
        result = 0

        for i in node_list:
            visited_in[i] = FALSE
            visited_out[i] = FALSE

        # visit seed-in
        queue.append(seed)
        queue_dir.append(FALSE)
        pred.append(0)
        visited_in[seed] = TRUE

        self.debug("augment")

        q_beg = 0
        while q_beg < len(queue):

            node = queue[q_beg]
            node_dir = queue_dir[q_beg]

            self.debug("visit node %s " % node,)
            if node_dir:
                self.debug('o')
            else:
                self.debug('i')

            if (node_dir != TWEAK) and self.node_sink[node] == 0:

                # found a path to the supersink, now actually augment
                self.debug("augment:")

                self.node_sink[node] = 1
                q_ptr = q_beg
                while q_ptr != 0:

                    node_dir = queue_dir[q_ptr]
                    q_ptr = pred[q_ptr]
                    pred_node = queue[q_ptr]

                    if node_dir:
                        self.debug(" %si->%so:" % (str(pred_node), str(node)),)
                    else:
                        self.debug(" %so->%si:" % (str(pred_node), str(node)),)
                    if pred_node == node:

                        if node_dir:
                            # edge from in to out

                            self.debug(" %s += 1" % str(node))
                            self.node_flow[node] += 1

                        else:
                            # edge from out to in (ie reversing)

                            self.debug(" %s -= 1" % str(node))
                            self.node_flow[node] -= 1

                    else:
                        if not node_dir:

                            # find the edge from pred_node to node and
                            #   increment flow
                            edges = self.node_in_edges[node]

                            for edge in edges:
                                if self.edge_src[edge] == pred_node:
                                    self.debug(" (%so->%si) += 1" % \
                                            (str(pred_node), str(node)),)
                                    self.edge_flow[edge] += 1

                                    break

                        else:

                            # find the edge from node to pred_node and
                            # decrement flow
                            edges = self.node_out_edges[node]

                            for edge in edges:
                                if self.edge_dst[edge] == pred_node:
                                    self.debug(" (%so->%si) -= 1" % \
                                            (str(node), str(pred_node)),)
                                    self.edge_flow[edge] -= 1

                                    break

                        node = pred_node
                self.debug("")
                result = TRUE
                break

            else:
                # have not found supersink, trace edges from current node
                if (not node_dir) and \
                    (self.node_flow[node] < self.capacity[node]) \
                    and not visited_out[node]:

                    queue.append(node)
                    queue_dir.append(TRUE)
                    pred.append(q_beg)
                    visited_out[node] = TRUE
                    self.debug("add %so to queue (from %si)" % \
                        (str(node), str(node)))

                elif node_dir and (self.node_flow[node] > 0) and \
                    not visited_in[node]:

                    # backwards flow from out to in residual graph
                    queue.append(node)
                    queue_dir.append(FALSE)
                    pred.append(q_beg)
                    visited_in[node] = TRUE
                    self.debug("add %si to queue (from %so)" % \
                        (str(node), str(node)))

                # now, follow the incident edges (in original graph)
                if node_dir:

                    # outgoing edges
                    edges = self.node_out_edges[node]

                    for edge in edges:
                        dst = self.edge_dst[edge]

                        if not visited_in[dst]:

                            queue.append(dst)
                            queue_dir.append(FALSE)
                            pred.append(q_beg)
                            self.debug("add %si to queue" % str(dst))
                            visited_in[dst] = TRUE
                else:

                    # ingoing edges
                    edges = self.node_in_edges[node]

                    for edge in edges:
                        src = self.edge_src[edge]

                        if (not visited_out[src]) and self.edge_flow[edge] > 0:

                            queue.append(src)
                            queue_dir.append(TRUE)
                            pred.append(q_beg)
                            self.debug("add %so to queue" % src)
                            visited_out[src] = TRUE

            q_beg += 1

        # you wouldn't believe how much memory python uses up
        # on a 10,000-edge graph if you don't delete these...
        del queue
        del queue_dir
        del pred

        return result

    def sanity_check(self, seed, node_list):
        """ sanity_check: Check that flow
            satisfies constraints.
            @self: The #NetFlow context.
            @seed: The seed.
            @node_list: List of node names

            Checks that:
            + For all in nodes other than seed,
              the sum of inedge flow is equal to
              supersink flow plus node flow.
            + For all out nodes, the sum of outedge
              flow is equal to node flow.
            + All flows are nonnegative.
            + All supersink flows are either 0 or 1.
            + All node flows are
              less-than-or-equal-to the capacity.

            Return value: 0 if ok.
        """
        result = 0

        for e in self.edge_flow:
            if e < 0:
                self.warning("Negative edge flow")
                result = -1

        for n in node_list:

            if self.node_sink[n] < 0 or self.node_sink[n] > 1:
                self.warning("Node %s flow %d to sink\n" % \
                         (str(n), self.node_sink[n]))
                result = -1

            if self.node_flow[n] < 0:
                self.warning("Negative node %s flow %d\n" % \
                         (str(n), self.node_flow[n]))
                result = -1

            cap = self.capacity[n]
            if cap < 0:
                cap = 0
            if self.node_flow[n] > cap:

                self.warning("Node %s flow %d over capacity %d\n" % \
                         (str(n), self.node_flow[n], self.capacity[n]))
                result = -1

            if n != seed:

                in_edges = self.node_in_edges[n]
                flow = 0
                for e in in_edges:
                    if self.edge_dst[e] != n:
                        self.warning("Edge/node data structure inconsistency\n")
                        result = -1

                    flow += self.edge_flow[e]

                if flow != self.node_flow[n] + self.node_sink[n]:

                    self.warning("Flow inconsistency, node %sin\n" % str(n))
                    result = -1

            out_edges = self.node_out_edges[n]
            flow = 0
            for e in out_edges:
                if self.edge_src[e] != n:
                    self.warning("Edge/node data structure inconsistency\n")
                    result = -1
                flow += self.edge_flow[e]

            if flow != self.node_flow[n]:
                self.warning("Flow inconsistency, node %sout, node_flow = %d, sum of flow is %d\n" % \
                          (str(n), self.node_flow[n], flow))
                result = -1

        return result

    def max_flow(self, seed, pred_list, node_list):
        """Compute a maximum flow.

        :param seed: source of flow
        :param pred_list: see assign_tree()
        :node_list: nodes in the network (why is this needed?)

        Updates node_flow and node_sink using augment().
        """

        self.sanity_check_tree(seed, pred_list, node_list)
        # if enabled, start from tree flow rather than zero
        self.from_tree(pred_list, node_list)

        del pred_list

        if TWEAK:
            self.tweak_flow()

        self.sanity_check(seed, node_list)

        n_aug = 0
        while self.augment(seed, node_list):
            n_aug += 1
            if n_aug % 100 == 0:
                self.debug("%d augmentations" % n_aug)

        self.debug("total flow %d with %d augmentations" % \
                (self.node_flow[seed], n_aug))

        self.sanity_check(seed, node_list)

    def extract(self):
        """Determine which nodes were accepted.

        :returns: a mapping from nodes to 1 or 0
                  depending on whether the node is
                  accepted.
        """

        return self.node_sink.copy()


class NetFlow(Debug):
    """A NetFlow computes maximum flow through a network.
    """

    def __init__(self):

        self.succs = {} # dict by node of list of successors
        self.paths_to_sink = {} #

        Debug.__init__(self)

    def add_edge(self, src, dst):
        """Add an edge from src to dst and ensure both nodes are included.
        """

        self.succs.setdefault(src, []).append(dst)
        self.succs.setdefault(dst, [])

    def depth_capacities(self, seed, caps):
        """Compute capacities based on distance from seed.

        :returns: c, a where c is a mapping from nodes to capacities where
                  c[n] = caps[min(distance(seed, n), len(caps)-1)]
                  and a is average capacity
        """

        n_nodes = len(self.succs)
        assert n_nodes > 0, "no edges!"

        capacity = dict.fromkeys(list(self.succs.keys()), -1)

        cap_sum = 0

        iter_num = 0
        for level_nodes in breadth_first_search(seed, self.succs):
            if iter_num < len(caps):
                cap = caps[iter_num]

            for node in level_nodes:
                capacity[node] = cap
                cap_sum += cap

        return capacity, cap_sum / n_nodes

    def assign_tree(self, seed, caps, priv):
        """Do greedy assignment of capacity to nodes.

        :returns: a predecessor represenation of the tree.

        >>> def _t(edges, caps):
        ...    nf = NetFlow()
        ...    for v1, v2 in edges:
        ...        nf.add_edge(v1, v2)
        ...    return nf.assign_tree(1, caps, NetFlowPriv(nf))

        In this case, there's capacity for everybody:

        >>> _t([(1, 2), (1, 3), (3, 5), (2, 3)], [20, 10, 5, 1])
        {1: 1, 2: 1, 3: 1, 5: 3}

        But here there's only capacity for 1 and 2:
        >>> _t([(1, 2), (1, 3), (3, 5), (2, 3)], [2, 1])
        {1: 1, 2: 1, 3: -1, 5: -1}

        Edge case, just to check:
        >>> _t([(1, 1)], [10])
        {1: 1}
        """
        n_nodes = len(self.succs)

        assert priv.capacity is None, "capacity previously initialised!"
        priv.capacity, self.avg_capacity = self.depth_capacities(seed, caps)

        pred = {}
        children = {}
        resid_cap = {}
        start_assign = [0] * len(caps)
        child_ix = [0] * len(caps)

        for i in list(self.succs.keys()):
            resid_cap[i] = priv.capacity[i]
            pred[i] = -1
            children[i] = []

        pred[seed] = seed
        resid_cap[seed] -= 1

        for level in range(len(caps)):

            cur_assign = 0
            cur_node = seed
            cur_depth = 0
            cap = resid_cap[seed]
            child_ix[cur_depth] = 0
            start_assign[0] = cur_assign

            while 1:

                if cur_depth == level:

                    # add children of cur_node to tree, respecting capacity
                    # constraint
                    succ = self.succs[cur_node]

                    children[cur_node] = []

                    for j_ix in succ:
                        if cap <= 0:
                            break
                        if pred[j_ix] == -1:
                            pred[j_ix] = cur_node

                            children[cur_node].append(j_ix)
                            resid_cap[j_ix] -= 1
                            cur_assign += 1
                            cap -= 1

                    resid_cap[cur_node] = cap

                    if level == 0:
                        break

                    # traverse up the stack
                    while cur_depth > 0:

                        cur_depth -= 1
                        cur_node = pred[cur_node]
                        resid_cap[cur_node] -= cur_assign - start_assign[cur_depth]

                        start_assign[cur_depth] = cur_assign
                        cap = resid_cap[cur_node]
                        if child_ix[cur_depth] < len(children[cur_node]):
                            break

                    if cur_depth == 0 and child_ix[0] == len(children[cur_node]):
                        break

                else:

                    # not at the bottom level, go to next
                    if child_ix[cur_depth] < len(children[cur_node]):

                        cur_node = children[cur_node][child_ix[cur_depth]]
                        if cap > resid_cap[cur_node]:
                            cap = resid_cap[cur_node]
                        else:
                            resid_cap[cur_node] = cap
                        child_ix[cur_depth] += 1
                        cur_depth += 1
                        child_ix[cur_depth] = 0
                        start_assign[cur_depth] = cur_assign

                    else:

                        # no children remaining at this level, up one
                        if cur_depth == 0:
                            break
                        cur_depth -= 1
                        cur_node = pred[cur_node]
                        resid_cap[cur_node] -= cur_assign - start_assign[cur_depth]

                        start_assign[cur_depth] = cur_assign
                        cap = resid_cap[cur_node]

        return pred

    def max_flow(self, seed, caps):
        """Compute a maximum flow.

        :param seed: source of flow
        :param caps: per-depth (from seed) list of capacities

        :returns: a NetFlowPriv including the results; see NetFlowPriv.max_flow
        """

        priv = NetFlowPriv(self)
        priv.set_debuglevel(self.get_debuglevel())

        pred_list = self.assign_tree(seed, caps, priv)
        node_list = list(self.succs.keys())

        priv.max_flow(seed, pred_list, node_list)

        return priv

    def max_flow_extract(self, seed, caps):
        """     performs and extracts a maximum flow network flow.

            returns a dictionary with the node
            names as keys and the values as 0 to
            indicate no flow reached that node
            and 1 to indicate that it did.
        """

        priv = self.max_flow(seed, caps)
        u_flow = priv.extract()
        self.add_warnings(priv.get_warnings())

        del priv

        # print all warnings, just for fun
        warnings = self.get_warnings()
        if len(warnings) > 0:
            for w in warnings:
                print(w)

        return u_flow


def breadth_first_search(root, succs):
    """
    >>> dag = {1: [2, 3], 2: [4, 5], 3: [6, 7], 4: [2, 6]}
    >>> levels = breadth_first_search(1, dag)
    >>> levels.next()
    [1]
    >>> levels.next()
    [2, 3]
    >>> levels.next()
    [4, 5, 6, 7]
    """
    seen = set()

    node_list = [root]
    beg_nl = 0
    end_nl = 1

    while end_nl > beg_nl:
        yield node_list[beg_nl:end_nl]

        new_end_nl = end_nl

        j = beg_nl

        while j < end_nl:
            ix = node_list[j]
            for succ in succs[ix]:
                if succ not in seen:
                    seen.add(succ)
                    if new_end_nl == len(node_list):
                        node_list.append(succ)
                    else:
                        node_list[new_end_nl] = succ
                    new_end_nl += 1
            j += 1

        beg_nl = end_nl
        end_nl = new_end_nl


def test():

    from pprint import pprint

    # large test of max flow.
    #
    # notes.
    #
    # this test is to double-check that if you have a large
    # group of nodes that are interlinked to each other, and
    # another group that is interlinked to itself and the first
    # group, that none of the second group gets any flow.
    #
    # it's also quite a good test of the amount of
    # time / memory this takes up (about 1k per node).
    # try 100,000: it's fun!

    from random import randint

    f = NetFlow()
    f.add_edge("-", 0)
    len = 10000
    for i in range(len):
        f.add_edge(randint(0, len/4), randint(0, len/4))
        f.add_edge(randint(len/4+1, len/2), randint(0, len/2))

    e = f.max_flow_extract("-", [800, 200, 50, 12, 4, 2, 1])

    for x in list(e.keys()):
        if type(x) == type(0) and x > (len/4) and e[x] != 0:
            raise "untrusted group (%d->%d) linked to trusted (0->%d)\n"

    print("random test passed ok")
    print()

    # pretty test of max flow.
    #
    # notes.
    #
    # mary and bob like each other, but the seeds aren't
    # interested in mary and bob, so they don't show up
    # in the max flow diagram.
    #
    # fleas ad infinitum is so far down from the seeds that
    # despite being linked, no flow reaches it: the
    # available capacity, which is limited in this test to
    # 7 degrees away from the supersink ("-") _anyway_,
    # is all used up.
    #
    # 1: -, 2: seed, 3: heather, 4: rob,
    # 5: fleas, 6: lit-f, 7: less-f - whoops! 8: fad.
    # yeah, that's right.  the capacity chain is only 7-long
    # so anything beyond 7 degrees from the supersink isn't
    # included.  cool.

    # the second test is what heather likes, and heather's likes'
    # likes, and heather's likes' likes' likes... etc., up to
    # 7 degrees.  which is why fleas ad infinitum _is_ shown
    # in the flow, this time.  cool.

    f = NetFlow()
    f.set_debuglevel(1)
    f.add_edge("-", "seed")
    f.add_edge("-", "seed2")
    f.add_edge("seed", "heather")
    f.add_edge("seed2", "heather")
    f.add_edge("seed", 55)
    f.add_edge("seed", "luke")
    f.add_edge(55, 10)
    f.add_edge(10, "luke")
    f.add_edge("luke", "heather")
    f.add_edge("heather", "luke")
    f.add_edge("heather", "flat-faced cat")
    f.add_edge("flat-faced cat", "heather")
    f.add_edge("luke", "flat-faced cat")
    f.add_edge("heather", "mo the mad orange pony")
    f.add_edge("heather", "robbie the old crock pony")
    f.add_edge("robbie the old crock pony", "fleas")
    f.add_edge("fleas", "little fleas")
    f.add_edge("little fleas", "lesser fleas")
    f.add_edge("lesser fleas", "fleas ad infinitum")

    f.add_edge("bob", "heather")
    f.add_edge("bob", "mary")
    f.add_edge("mary", "bob")

    print("pretty node graph (yes, the numbers 55 and 10 are nodes):")
    pprint(f.succs)
    print()

    e = f.max_flow_extract("-", [800, 200, 50, 12, 4, 2, 1])
    print("supersink as seed - avg_capacity:", f.avg_capacity)
    pprint(e)
    print()

    e = f.max_flow_extract("heather", [800, 200, 50, 12, 4, 2, 1])
    print("heather as seed - avg_capacity:", f.avg_capacity)
    pprint(e)
    print()

if __name__ == '__main__':
    test()
