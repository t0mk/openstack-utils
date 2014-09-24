#!/usr/bin/env python

# much faster alternative to "nova list" it needs the cache in place.
# See build_cache.py for how to set up the cache building

import json
import build_cache
import os
import sys

cache_file = build_cache.INSTANCES_CACHE_FILE % os.environ['OS_TENANT_NAME']

def main(args_list):
    with open(cache_file, 'r') as f:
        for l in f:
            fields = l.strip().split(' ', 2)
            print fields[0], json.loads(fields[2])['floating'][0], fields[1]

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))


