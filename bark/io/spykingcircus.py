import argparse
import bark
import h5py
import numpy as np
import os
import pandas
import sys

SC_GRADES_DICT = {1.0: 'O',
                  2.0: 'E',
                  3.0: 'D',
                  4.0: 'C',
                  5.0: 'B',
                  6.0: 'A'}

def get_sc_path(entry_fn, dataset, sc_suffix, sc_filename):
    sc_dir = os.path.splitext(dataset)[0]
    if sc_suffix is None:
        sc_suffix = ''
    else:
        sc_suffix = '-' + sc_suffix
    fn = sc_dir + '.spyc.' + sc_filename + sc_suffix + '.hdf5'
    return os.path.join(entry_fn, sc_dir, fn)

def extract_sc(entry_fn, dataset, sc_suffix, out_fn):
    sr = bark.read_metadata(os.path.join(entry_fn, dataset))['sampling_rate']
    # determine file names
    results_path = get_sc_path(entry_fn, dataset, sc_suffix, 'result')
    templates_path = get_sc_path(entry_fn, dataset, sc_suffix, 'templates')
    # extract times and amplitudes
    with h5py.File(results_path) as rf:
        cluster_indices = {name: np.array(indices).astype(float) / sr for name,indices in rf['spiketimes'].items()}
        cluster_amplitudes = {name: np.array(amplitudes)
                              for name,amplitudes in rf['amplitudes'].items()}
        cluster_names = sorted(cluster_indices.keys(), key=lambda x: int(x[5:]))
        zipped = []
        for n in cluster_names:
            zipped.extend([(n, idx[0], amp[0])
                           for idx,amp in zip(cluster_indices[n], cluster_amplitudes[n])])
        zipped.sort(key=lambda x: x[1]) # sort by time
    # extract grades
    with h5py.File(templates_path) as tf:
        cluster_grades = [SC_GRADES_DICT[tag[0]] for tag in tf['tagged']]
        cluster_grades = {n: cluster_grades[idx] for idx,n in enumerate(cluster_names)}
    # write times and amplitudes to event dataset
    attrs = {'columns': {'start': {'units': 's'},
                         'template_name': {'units': None},
                         'amplitude': {'units': None}},
             'datatype': 1001,
             'sampling_rate': sr,
             'templates': {name: {'score': score} for name,score in cluster_grades.items()}}
    return bark.write_events(os.path.join(entry_fn, out_fn),
                             pandas.DataFrame({'start': [event[1] for event in zipped],
                                               'template_name': [event[0] for event in zipped],
                                               'amplitude': [event[2] for event in zipped]}),
                             **attrs)

def _parse_args(raw_args):
    desc = 'Extract Spyking Circus spike-sorting info into a Bark-readable form.'
    epi = 'Assumes standard Spyking Circus naming conventions for output files.\n'
    epi += 'Currently only supports extraction of spike times, amplitudes, and quality tags.'
    parser = argparse.ArgumentParser(description=desc, epilog=epi)
    dflt = 'sc_template_times.csv'
    parser.add_argument('-o', '--out', help='output filename (default: {})'.format(dflt), default=dflt)
    parser.add_argument('-s', '--suffix', help='Spyking Circus suffix (if applicable)')
    parser.add_argument('entry', help='Bark entry path')
    parser.add_argument('dataset', help='sampled dataset name to generate Spyking Circus filenames')
    return parser.parse_args(raw_args)

def _main():
    parsed_args = _parse_args(sys.argv[1:])
    _ = extract_sc(parsed_args.entry, parsed_args.dataset, parsed_args.suffix, parsed_args.out)

if __name__ == '__main__':
    _main()