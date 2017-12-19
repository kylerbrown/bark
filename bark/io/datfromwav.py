from scipy.io import wavfile
import bark, os


def dat_from_wav(wav, barkname, **attrs):
    rate, data = wavfile.read(wav)
    return bark.write_sampled(barkname, data, rate,**attrs)


def _main():
    ''' Function for getting commandline args.'''

    import argparse

    p = argparse.ArgumentParser(description='''
    converts wav file to bark format
        ''')
    p.add_argument('wav', help='path to wav file')
    p.add_argument('out', help="path to bark file")
    p.add_argument("-a",
        "--attributes",
        action='append',
        type=lambda kv: kv.split("="),
        dest='keyvalues',
        help="extra metadata in the form of KEY=VALUE")

    args = p.parse_args()

    if args.keyvalues:
        dat_from_wav(args.wav,
               args.out,
               **dict(args.keyvalues))
    else:
        dat_from_wav(args.wav, args.out)

   


if __name__ == '__main__':
    _main()
