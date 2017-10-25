#!/bin/sh -e
/usr/bin/jinja2 -D USE_AWS=$USE_AWS -D SG_STATS_PREFIX=$SG_STATS_PREFIX stats-config.js.j2 > stats-config.js
cat stats-config.js
/usr/local/bin/node stats.js stats-config.js
