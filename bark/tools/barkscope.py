import subprocess
import os.path
from xml.etree.ElementTree import Element, SubElement, ElementTree
from bark import read_metadata

#readable dtypes and their bit depth
DTYPES = {'int16':'16',
        '<i2':'16',
        'int32': '32',
        '<i4':'32',
        'int64':'64',
        '<i8':'64'}

def meta_to_neuroscope_xml(meta):
    '''
    Converts a metatdata dictionary of attributes
    into a neuroscope xml file

    required keys:
    dtype
    sampling_rate
    n_channels
    '''
    assert meta['dtype'] in DTYPES
    parameters = Element('parameters')
    parameters.set('version', '1.0')
    parameters.set('creator', 'bark-0.2')
    acq = SubElement(parameters, 'acquisitionSystem')
    SubElement(acq, 'nBits').text = DTYPES[meta['dtype']]
    SubElement(acq, 'nChannels').text = str(len(meta['columns']))
    SubElement(acq, 'samplingRate').text = str(meta['sampling_rate'])
    SubElement(acq, 'voltageRange').text = '20'
    SubElement(acq, 'amplification').text = '1000'
    SubElement(acq, 'offset').text = '0'
    fp = SubElement(parameters, 'fieldPotentials')
    SubElement(fp, 'lfpSamplingRate').text = '1250'
    anatdes = SubElement(parameters, 'anatomicalDescription')
    chngrp = SubElement(anatdes, 'channelGroup')
    grp = SubElement(chngrp, 'group')
    for i in range(meta['n_channels']):
            channel = SubElement(grp, 'channel')
            channel.set('skip', '0')
            channel.text = str(i)
    SubElement(parameters, 'spikeDetection')
    neuroscope = SubElement(parameters, 'neuroscope')
    neuroscope.set('version', '2.0.0')
    misc = SubElement(neuroscope, 'miscellaneous')
    SubElement(misc, 'screenGain').text = '2.0'
    SubElement(misc, 'traceBackgroundImage')
    vid = SubElement(neuroscope, 'video')
    SubElement(vid, 'rotate').text = '0'
    SubElement(vid, 'flip').text = '0'
    SubElement(vid, 'videoImage')
    SubElement(vid, 'positionsBackground').text = '0'
    spikes = SubElement(neuroscope, 'spikes')
    SubElement(spikes, 'nSamples').text = '32'
    SubElement(spikes, 'peakSampleIndex').text = '16'
    channels = SubElement(neuroscope, 'channels')
    for i in range(meta['n_channels']):
        channelcolors = SubElement(channels, 'channelColors')
        SubElement(channelcolors, 'channel').text = str(i)
        SubElement(channelcolors, 'color').text = '#0080ff'
        SubElement(channelcolors, 'anatomyColor').text = '#0080ff'
        SubElement(channelcolors, 'spikeColor').text = '#0080ff'
        channeloffset = SubElement(channels, 'channelOffset')
        SubElement(channeloffset, 'channel').text = str(i)
        SubElement(channeloffset, 'defaultOffset').text = "0"
    return ElementTree(parameters)


def main():
    import argparse
    p = argparse.ArgumentParser(description="""
    Open raw binary file in neuroscope.
    """)
    p.add_argument("dat",
            help="Raw binary file to open.")
    args = p.parse_args()
    fname = os.path.splitext(args.dat)[0] + ".xml"
    if not os.path.isfile(fname):
        # load metadata
        meta = read_metadata(args.dat)
        # convert to neuroscope
        xml_tree = meta_to_neuroscope_xml(meta)
        # save to file
        xml_tree.write(fname, xml_declaration=True, short_empty_elements=False)
    # open neuroscope
    try:
        subprocess.run(['neuroscope', args.dat])
    except AttributeError:
        subprocess.call(['neuroscope', args.dat])

if __name__ == "__main__":
    main()

