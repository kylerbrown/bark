# original by KJB

import bark
import numpy as np
import pandas as pd
import os.path


def create_data(guifolder, sampling_rate):
    times = np.load(os.path.join(guifolder, 'spike_times.npy')) / sampling_rate
    amplitude = np.load(os.path.join(guifolder, 'amplitudes.npy'))
    name = np.load(os.path.join(guifolder, 'spike_clusters.npy'))
    positions = np.load(os.path.join(guifolder, 'channel_positions.npy')
                        )  # not used? might be needed for missing channels
    data = pd.DataFrame({'name': name, 'start': times, 'amplitude': amplitude})
    return data


def create_metadata(guifolder):
    cluster_groups = pd.read_csv(
        os.path.join(guifolder, 'cluster_groups.csv'),
        sep='\t')
    templates = np.load(guifolder + '/templates.npy')
    channel = np.argmax(np.argmax(np.abs(templates), 1), 1)
    template_dict = {int(name): {'score': cluster_groups.group[i],
                                 'center_channel': int(channel[i])}
                     for i, name in enumerate(cluster_groups.cluster_id)}
    attrs = {'columns': {'start': {'units': 's'},
                         'name': {'units': None},
                         'amplitude': {'units': None}},
             'datatype': 1001,
             'templates': template_dict,
             'filetype': 'csv',
             'creator': 'phy', }
    return attrs


def main():
    import argparse
    p = argparse.ArgumentParser(description='''
    Convert Spyking Circus PHY GUI output to Bark event dataset.
    ''')
    p.add_argument('phydir', help='directory containing PHY GUI output files')
    p.add_argument('out', help='name of output event dataset')
    p.add_argument('-r',
                   '--rate',
                   required=True,
                   type=float,
                   help='sampling rate of original data')
    args = p.parse_args()
    data = create_data(args.phydir, args.rate)
    attrs = create_metadata(args.phydir)
    bark.write_events(args.out, data, **attrs)


if __name__ == '__main__':
    main()

