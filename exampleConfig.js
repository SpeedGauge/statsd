/*

Required Variables:

  port:             StatsD listening port [default: 8125]

Graphite Required Variables:

(Leave these unset to avoid sending stats to Graphite.
 Set debug flag and leave these unset to run in 'dry' debug mode -
 useful for testing statsd clients without a Graphite server.)

  graphiteHost:     hostname or IP of Graphite server
  graphitePort:     port of Graphite server

Optional Variables:

  debug:            debug flag [default: false]
  debugInterval:    interval to print debug information [ms, default: 10000]
  dumpMessages:     log all incoming messages
  flushInterval:    interval (in ms) to flush to Graphite
  percentThreshold: for time information, calculate the Nth percentile
                    [%, default: 90]

  statsPrefix:      prefix for stats in graphite (eg, with statsPrefix:"foo",
                    metric "bar" will become "foo.bar" in graphite). can also
                    be any expression resolving to a string.
*/
{
  graphitePort: 2003
, graphiteHost: "graphite.host.com"
, port: 8125
}
