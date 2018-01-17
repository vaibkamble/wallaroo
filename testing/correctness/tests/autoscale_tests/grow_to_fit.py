# Copyright 2017 The Wallaroo Authors.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
#  implied. See the License for the specific language governing
#  permissions and limitations under the License.


# import requisite components for integration test
from integration import (add_runner,
                         ex_validate,
                         get_port_values,
                         iter_generator,
                         Metrics,
                         MetricsParser,
                         Reader,
                         Runner,
                         RunnerChecker,
                         RunnerReadyChecker,
                         Sender,
                         setup_resilience_path,
                         Sink,
                         SinkAwaitValue,
                         start_runners,
                         TimeoutError)

from collections import Counter
from itertools import cycle
from string import lowercase
from struct import pack, unpack
import re
import time


fmt = '>I2sQ'
def decode(bs):
    return unpack(fmt, bs)[1:3]


def pre_process(decoded):
    totals = {}
    for c, v in decoded:
        totals[c] = v
    return totals


def process(data):
    decoded = []
    for d in data:
        decoded.append(decode(d))
    return pre_process(decoded)


def validate(raw_data, expected):
    data = process(raw_data)
    assert(data == expected)


def test_autoscale_grow_pony_by_1():
    command = 'alphabet'
    _test_autoscale_grow(command, join_count=1, cycles=12)


#def test_autoscale_grow_machida_by_1():
#    command = 'machida --application-module alphabet'
#    _test_autoscale_grow(command, join_count=1)


#def test_autoscale_grow_pony_by_4():
#    command = 'alphabet'
#    _test_autoscale_grow(command, join_count=5, cycles=3)


#def test_autoscale_grow_machida_by_4():
#    command = 'machida --application-module alphabet'
#    _test_autoscale_grow(command, join_count=4)


def send_shrink_cmd(host, port, names=[], count=1):
    # Trigger log rotation with external message
    cmd_external_trigger = ('external_sender --external {}:{} --type shrink '
                            '--message {}'
                            .format(host, port,
                                    ','.join(names) if names else count))

    success, stdout, retcode, cmd = ex_validate(cmd_external_trigger)
    try:
        assert(success)
    except AssertionError:
        raise AssertionError('External shrink trigger failed with '
                             'the error:\n{}'.format(stdout))


def phase_validate_output(runners, sink, expected):
    # Validate captured output
    try:
        validate(sink.data, expected)
    except AssertionError:
        outputs = [(r.name, r.get_output()) for r in runners]
        outputs = '\n===\n'.join(('\n---\n'.join(t) for t in outputs))
        raise AssertionError('Validation failed on expected output. '
                             'Worker outputs are included below:'
                             '\n===\n{}'.format(outputs))


def edge_changes(duration, totals, metrics_ts):
    """
    Construct a sequence of high-to-low and low-to-high edge changes
    representing a switch from non-zero to zero total values and vice versa.
    """
    # the first switch is low-to-high by definition (if totals is not empty)
    switches = []
    if not totals:
        return switches
    switches.append((totals[0][0], 'up'))
    for ts, tot in totals[1:]:
        if ts - switches[-1][0] > duration:
            if switches[-1][1] == 'up':
                # add a 'down' switch after the last switch
                switches.append((switches[-1][0] + duration, 'down'))
                # add an 'up' switch at the current ts
                switches.append((ts, 'up'))
    # Since the last switch is always up, we can always add a 'down' in the
    # ts that follows it if enough time has elapsed
#    if metrics_ts > switches[-1][0] + duration:
#        print 'adding down to the end because {} > {} + {}'.format(metrics_ts, switches[-1][0], duration)
#        switches.append((switches[-1][0] + duration, 'down'))
    print 'last ts in totals: ', switches[-1][0]
    return switches


def parse_metrics(metrics):
    # parse metrics data and validate worker has shifted from 1 to 2
    # workers
    mp = MetricsParser()
    mp.load_string_list(metrics.data)
    metrics_ts = time.time()
    print 'metrics_ts:', metrics_ts
    mp.parse()
    # Now confirm that there are computations in each worker's metrics
    app_key = mp.data.keys()[0]  # 'metrics:Alphabet Popularity Contest'
    names = mp.data[app_key].keys()  # this includes 'initializer'
    # For each worker, get a metrics duration value, and a list of
    # (end_ts, node_ingress_egress totals) pairs
    wm = {k: {'total': {}, 'duration': 0} for k in names}
    for w in names:
        for t in mp.data[app_key][w]:
            if (t[0] == 'metrics' and
                t[1]['metric_category'] == 'node-ingress-egress'):
                    wm[w]['duration'] = t[1]['duration'] / 1e9
                    t_key = t[1]['end_ts'] / 1e9
                    wm[w]['total'][t_key] = (
                        wm[w]['total'].get(t_key, 0) + t[1]['total'])
            elif w in ['worker4', 'worker5']:
                print w, t[0]
                if len(t) > 1:
                    print t[1:]
                print

    # Sort the totals
    for w in wm.keys():
        wm[w]['total'] = sorted(wm[w]['total'].items(), key=lambda x: x[0])

    # Get sequence of edge changes
    switches = {}
    for w in wm.keys():
        try:
            print 'constructing edge graph for {}'.format(w)
            switches[w] = edge_changes(wm[w]['duration'], wm[w]['total'],
                                       metrics_ts)
        except Exception as err:
            print 'KeyError in wm[{}]: {}'.format(w, wm[w])
            raise err
    return switches


def phase_validate_metrics(runners, metrics, joined=[], left=[]):
    # Verify there is at least one entry for a computation with a nonzero
    # total value
    wm = parse_metrics(metrics)
    print 'joined', joined
    print 'left', left
    print 'worker_metrics'
    print '==='
    for w in wm:
        print w
        print '---'
        print wm[w]
        print '='
    print
    for w in joined:
        try:
            assert(wm[w][-1][1] == 'up')
        except AssertionError:
            outputs = [(r.name, r.get_output()) for r in runners]
            outputs = '\n===\n'.join(('\n---\n'.join(t) for t in outputs))
            raise AssertionError('{} does not appear to have joined! '
                                 'Worker outputs are included below:'
                                 '\n===\n{}'.format(w, outputs))
    for w in left:
        try:
            assert(wm[w][-1][1] == 'down')
        except AssertionError:
            outputs = [(r.name, r.get_output()) for r in runners]
            outputs = '\n===\n'.join(('\n---\n'.join(t) for t in outputs))
            raise AssertionError('{} does not appear to have left! '
                                 'Worker outputs are included below:'
                                 '\n===\n{}'.format(w, outputs))


def _test_autoscale_grow(command, join_count=1, cycles=1):
    host = '127.0.0.1'
    sources = 1
    workers = 1
    joiners = join_count
    res_dir = '/tmp/res-data'
    base = 1000
    expect = base + (2000 * cycles)
    sender_timeout = expect/200 + 10

    setup_resilience_path(res_dir)

    runners = []
    try:
        # Create sink, metrics, reader, sender
        sink = Sink(host)
        metrics = Metrics(host)
        lowercase2 = [a + b for a in lowercase for b in lowercase]
        char_gen = cycle(lowercase2)
        chars = [next(char_gen) for i in range(expect)]
        expected = Counter(chars)

        reader = Reader(iter_generator(chars,
                                        lambda s: pack('>2sI', s, 1)))

        await_values = [pack('>I2sQ', 10, c, v) for c, v in
                        expected.items()]

        # Start sink and metrics, and get their connection info
        sink.start()
        sink_host, sink_port = sink.get_connection_info()
        outputs = '{}:{}'.format(sink_host, sink_port)

        metrics.start()
        metrics_host, metrics_port = metrics.get_connection_info()
        time.sleep(0.05)

        num_ports = sources + 3 + (2 * (workers - 1))
        ports = get_port_values(num=num_ports, host=host)
        (input_ports, (control_port, data_port, external_port),
         worker_ports) = (ports[:sources],
                          ports[sources:sources+3],
                          zip(ports[-(2*(workers-1)):][::2],
                              ports[-(2*(workers-1)):][1::2]))
        inputs = ','.join(['{}:{}'.format(host, p) for p in
                           input_ports])

        start_runners(runners, command, host, inputs, outputs,
                      metrics_port, control_port, external_port, data_port,
                      res_dir, workers, worker_ports)

        # Wait for first runner (initializer) to report application ready
        runner_ready_checker = RunnerReadyChecker(runners, timeout=30)
        runner_ready_checker.start()
        runner_ready_checker.join()
        if runner_ready_checker.error:
            raise runner_ready_checker.error

        # start sender
        sender = Sender(host, input_ports[0], reader, batch_size=10,
                        interval=0.05)
        sender.start()

        # Perform grow cycles
        start_from_i = 0
        for cyc in range(cycles):
            joined = []
                # create a new worker and have it join
            new_ports = get_port_values(num=(joiners * 2), host=host,
                                        base_port=25000)
            joiner_ports = zip(new_ports[::2], new_ports[1::2])
            for i in range(joiners):
                add_runner(runners, command, host, inputs, outputs,
                           metrics_port,
                           control_port, external_port, data_port, res_dir,
                           joiners, *joiner_ports[i])
                joined.append(runners[-1])

            patterns_i = ([re.escape(r'***Worker {} attempting to join the '
                                     r'cluster. Sent necessary information.***'
                                     .format(r.name)) for r in joined]
                          +
                          [re.escape(r'Migrating partitions to {}'.format(
                              r.name)) for r in joined]
                          +
                          [re.escape(r'--All new workers have acked migration '
                                     r'batch complete'),
                           re.escape(r'~~~Resuming message processing.~~~')])
            patterns_j = [re.escape(r'***Successfully joined cluster!***'),
                          re.escape(r'~~~Resuming message processing.~~~')]

            # Wait for runner to complete a joining
            join_checkers = []
            join_checkers.append(RunnerChecker(runners[0], patterns_i,
                                               timeout=30,
                                               start_from=start_from_i))
            for runner in joined:
                join_checkers.append(RunnerChecker(runner, patterns_j,
                                                   timeout=30))
            for jc in join_checkers:
                jc.start()
            for jc in join_checkers:
                jc.join()
                if jc.error:
                    print('RunnerChecker error for Join check on {}'
                          .format(jc.runner_name))
                    print jc.error

                    outputs = [(r.name, r.get_output()) for r in runners]
                    outputs = '\n===\n'.join(('\n---\n'.join(t) for t in outputs))
                    raise TimeoutError(
                        'Worker {} join timed out in {} '
                        'seconds. The cluster had the following outputs:\n===\n{}'
                        .format(jc.runner_name, jc.timeout, outputs))

            start_from_i = runners[0].tell()
            # wait for there to be metrics for the worker
            time.sleep(8.25)

            # validate new worker joined via metrics
            try:
                phase_validate_metrics(runners, metrics, joined=[r.name for r in
                                                                 joined])
            except Exception as err:
                print 'error validating [{}] have joined'.format([r.name for r in joined])
                print 'their outputs are included below:'
                for r in [runners[0]] + joined:
                    print '==='
                    print r.name
                    print '---'
                    print r.get_output()
                print
                raise err

        # wait until sender completes (~10 seconds)
        sender.join(sender_timeout)
        if sender.error:
            raise sender.error
        if sender.is_alive():
            sender.stop()
            raise TimeoutError('Sender did not complete in the expected '
                               'period')

        # Wait one full metrics period to ensure we get all the metrics
        time.sleep(4.25)

        # Use Sink value to determine when to stop runners and sink
        stopper = SinkAwaitValue(sink, await_values, 30)
        stopper.start()
        stopper.join()
        if stopper.error:
            print 'sink.data', len(sink.data)
            print 'await_values', len(await_values)
            raise stopper.error

        # stop application workers
        for r in runners:
            r.stop()

        # Stop sink
        sink.stop()

        # Stop metrics
        metrics.stop()

        # validate all workers left via metrics
        #phase_validate_metrics(runners, metrics,
        #                       left=set((r.name for r in runners)))

        # validate output
        phase_validate_output(runners, sink, expected)

    finally:
        for r in runners:
            r.stop()
