#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""usage: gIMble query                  -z FILE -b [-u <INT> -i <INT> -h|--help]
                                            
    Options:
        -h --help                                   show this
        -z, --zarr_file FILE                        ZARR datastore
        -b, --blocks                                Writes BED file of Blocks
        -u, --max_multiallelic <INT>                Max multiallelics per block [default: 2]
        -i, --max_missing <INT>                     Max missing per block [default: 2]

"""

from timeit import default_timer as timer
from docopt import docopt
import lib.gimble

class ParameterObj(lib.gimble.RunObj):
    '''Sanitises command line arguments and stores parameters.'''

    def __init__(self, params, args):
        super().__init__(params)
        self.zstore = self._get_path(args['--zarr_file'])
        self.blocks = args['--blocks']
        self.block_max_multiallelic = int(args['--max_multiallelic'])
        self.block_max_missing = int(args['--max_missing'])

def main(params):
    try:
        start_time = timer()
        args = docopt(__doc__)
        parameterObj = ParameterObj(params, args)
        store = lib.gimble.load_store(parameterObj)
        #print(store.tree())
        store.write_block_bed(parameterObj)
        print("[*] Total runtime: %.3fs" % (timer() - start_time))
    except KeyboardInterrupt:
        print("\n[X] Interrupted by user after %s seconds!\n" % (timer() - start_time))
        exit(-1)