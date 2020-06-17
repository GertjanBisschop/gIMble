#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""usage: gIMble simulate                  -m FILE [-c FILE] 
                                            [-b INT] [-r INT]
                                            [-t INT] [-h|--help]
                                            [-o STR] [-z --zarr_store]
                                            
    Options:
        -h --help                                   show this
        -m, --model_file FILE                       Model file to analyse
        -c, --config_file FILE                      Config file with parameters (if not present, empty config file is created)
        -P, --precision INT                         Floating point precision of probabilities [default: 25]
        -b, --blocks INT                            Number of blocks per window
        -r, --replicates INT                        Number of replicates per parametercombo
        -t, --threads INT                           Threads [default: 1]
        -o, --out_prefix <STR>                      Prefix for output files
        -z, --zarr_store <STR>                      Name of zarr store (output)
        
"""
import pathlib
import oyaml as yaml
import collections
from timeit import default_timer as timer
from docopt import docopt
import sys, os
from lib.gimble import RunObj
import lib.simulate
import numpy as np

"""
test command:
gIMble simulate -m 
./gIMble model -s A,B -p 2 -n 1,1 -m 'A>B' -j 'A,B' -o output/test
./gIMble model -s A,B -p 2 -n 2,1 -j 'A,B' -o output/test

./gIMble simulate -m output/s_A_B.p2.n_1_1.m_AtoB.j_A_B.model.tsv
./gIMble simulate -m output/test.model.tsv

./gIMble simulate -m output/s_A_B.p2.n_1_1.m_AtoB.j_A_B.model.tsv -c /Users/s1854903/git/gIMble/output/s_A_B.p2.n_1_1.m_AtoB.j_A_B.model.config.yaml
./gIMble simulate -m output/test.model.tsv -c output/test.model.config.yaml -o output/sims_test
"""


class ParameterObj(RunObj):
    """Sanitises command line arguments and stores parameters."""

    def __init__(self, params, args):
        super().__init__(params)
        # self.zstore = self._get_path(args["--zarr_file"])
        self.model_file = self._get_path(args["--model_file"])
        self.config_file = self._get_path(args["--config_file"])
        self.threads = self._get_int(args["--threads"])
        self._config = self._get_or_write_config(args["--blocks"], args["--replicates"])
        self.data_type = self._get_datatype(
            [args["--blocks"]]
        )  # adapt to simulations.py
        self.outprefix = args["--out_prefix"] if args["--out_prefix"] else os.getcwd()
        self.zarr_store = (
            args["--zarr_store"] if args["--zarr_store"] else "simulations.zarr"
        )

    def _get_datatype(self, args):
        # needs to be adapted for simulation.py
        if not any(args):
            return None
        elif args[0]:
            return "blocks"
        elif args[1]:
            return "windows"
        else:
            sys.exit("[X] This should not have happend.")

    def _get_or_write_config(self, blocks, replicates):
        if self.config_file is None:
            print("[-] No config file found.")
            print("[+] Generating config file for model %r" % self.model_file)
            """for now we use the following dict until columns are fixed in gimble model"""
            if blocks is None:
                blocks = 1
            if replicates is None:
                replicates = 1
            config = {
                "version": self._VERSION,
                "model": self.model_file,
                # "random_seed": 12345,
                "precision": 25,
                "blocks": int(blocks),
                "blocklength": 1000,
                "replicates": int(replicates),
                #'k_max': collections.defaultdict(dict),
                "parameters": collections.defaultdict(dict),
                "boundaries": collections.defaultdict(list),
            }
            (pop_configs, columns) = self._parse_model_file()
            config["ploidy"] = int(pop_configs["ploidy"])
            config["parameters"]["sample_size_A"] = pop_configs["A"]
            config["parameters"]["sample_size_B"] = pop_configs["B"]
            config["parameters"]["theta"] = "FLOAT"
            for column in columns:
                if column.startswith("C_") or column.startswith("M_"):
                    config["parameters"][column] = "FLOAT"
            config["parameters"]["T"] = "FLOAT"
            for parameter in config["parameters"]:
                if parameter not in ["sample_size_A", "sample_size_B"]:
                    config["boundaries"][parameter] = ["MIN", "MAX", "STEPSIZE"]
            config_file = pathlib.Path(self.model_file).with_suffix(".config.yaml")
            yaml.add_representer(
                collections.defaultdict, yaml.representer.Representer.represent_dict
            )
            with open(config_file, "w") as fh:
                yaml.dump(config, fh)
            print("[+] Wrote file %r" % str(config_file))
            sys.exit(
                "[X] Please specify parameters in config file %r" % str(config_file)
            )
        else:
            print("[+] Reading config %r" % self.config_file)
            config_raw = yaml.safe_load(open(self.config_file, "r"))
            config = {}
            for k, v in config_raw.items():
                if k == "version":
                    config[k] = v
                elif k == "model":
                    config[k] = v
                elif isinstance(v, str):
                    sys.exit(
                        "[X] Config file error: %r should be a number (not %r)."
                        % (k, v)
                    )
                elif k == "parameters":
                    config["parameters"] = {}
                    for v_k, v_v in config_raw[k].items():
                        if isinstance(v_v, str):  # parameter not set
                            if any(
                                [
                                    isinstance(bound, str)
                                    for bound in config_raw["boundaries"][v_k]
                                ]
                            ):
                                sys.exit(
                                    "[X] Config file error: set parameter or boundaries for %r (not %r)."
                                    % (v_k, v_v)
                                )
                            else:
                                config["parameters"][v_k] = config_raw["boundaries"][
                                    v_k
                                ]
                        else:
                            config[k][v_k] = [
                                v_v,
                            ]
                elif k == "boundaries":
                    pass
                else:
                    config[k] = v
            for k, name in zip([blocks, replicates], ["blocks", "replicates"]):
                if k:
                    config[name] = int(k)
            (pop_configs, columns) = self._parse_model_file()
            assert (
                config["parameters"]["sample_size_A"][0] == pop_configs["A"]
                and config["parameters"]["sample_size_B"][0] == pop_configs["B"]
            ), "sample size does not match model sample size"
            return config

    def _parse_model_file(self):
        """# model = s_A_B.p2.n_1_1.m_AtoB.j_A_B"""
        with open(self.model_file) as fh:
            first_line = fh.readline().rstrip()
            columns = first_line.split()
            second_line = fh.readline().rstrip().split()
            A, B = second_line[3].split(";")
            pop_configs = {}
            for pop, name in zip([A, B], ["A", "B"]):
                pop = pop.lstrip(f"{name}=[").rstrip("]")
                unique_el, count_el = np.unique(pop.split(","), return_counts=True)
                pop_configs[name] = len(unique_el)
            pop_configs["ploidy"] = count_el[0]
            return (pop_configs, columns)

    def simulate(self):
        replicate = lib.simulate.run_sim(self)
        lib.simulate.get_genotypes(self, replicate)


def main(params):
    try:
        start_time = timer()
        args = docopt(__doc__)
        # log = lib.log.get_logger(params)
        parameterObj = ParameterObj(params, args)
        lib.simulate.run_sim(parameterObj)

        print("[*] Total runtime: %.3fs" % (timer() - start_time))
    except KeyboardInterrupt:
        print("\n[X] Interrupted by user after %s seconds!\n" % (timer() - start_time))
        exit(-1)
