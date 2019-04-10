import numpy as np
import bark
import shutil
BUF = bark.BUFFER_SIZE
#COEF_EST_MAX_SIZE = BUF * 500

def datref(datfile, outfile):
    shutil.copyfile(datfile, outfile)
    shutil.copyfile(datfile + '.meta.yaml', outfile + '.meta.yaml')
    outdset = bark.read_sampled(outfile, 'r+')
    out = outdset.data
    # determine reference coefficient
    n_samples, n_channels = out.shape
    coefs = np.zeros((n_channels, len(range(0, n_samples, BUF))))
    power = np.zeros_like(coefs)
    for ith, i in enumerate(range(0, n_samples, BUF)):
        total_mean = np.mean(out[i:i + BUF, :], axis=1)
        for c in range(n_channels):
            x = out[i:i + BUF, c]
            # this way we avoid re-calculating the entire mean for each channel
            ref = (total_mean * n_channels - x) / (n_channels - 1)
            coefs[c, ith] = np.dot(x, ref) / np.dot(ref, ref)
    best_C = np.zeros(n_channels)
    for c in range(n_channels):
        c_coefs = coefs[c, :]
        c_power = power[c, :]
        mask = c_power >= np.percentile(c_power, 90)
        best_C[c] = np.nanmean(c_coefs[mask])
    print("best reference coefficients: {}".format(best_C))
    for i, c in enumerate(best_C):
        outdset.attrs['columns'][i]['reference_coefficient'] = float(c)
    # we want to avoid re-calculating the median from scratch for each channel
    # unfortunately, the "new median after removing an element" calculation
    # is less succinct than for the mean
    if n_channels % 2 == 0:
        median_idx = [int(n_channels / 2) - 1, int(n_channels / 2)]
        idx_smaller = [median_idx[0] + 1] # new median if elt removed < median
        idx_equal = [median_idx[0]] # new median if elt removed == median
        idx_greater = [median_idx[0]] # new median if elt removed > median
    else:
        median_idx = [int(n_channels / 2)]
        idx_smaller = [median_idx[0], median_idx[0] + 1]
        idx_equal = [median_idx[0] - 1, median_idx[0] + 1]
        idx_greater = [median_idx[0] - 1, median_idx[0]]
    for i in range(0, n_samples, BUF):
        sorted_buffer = np.sort(out[i:i + BUF, :], axis=1)
        total_medians = np.mean(sorted_buffer[:, median_idx], axis=1)
        new_med_smaller = np.mean(sorted_buffer[:, idx_smaller], axis=1)
        new_med_equal = np.mean(sorted_buffer[:, idx_equal], axis=1)
        new_med_greater = np.mean(sorted_buffer[:, idx_greater], axis=1)
        for c in range(n_channels):
            less = np.less(out[i:i + BUF, c], total_medians)
            equal = np.equal(out[i:i + BUF, c], total_medians)
            greater = np.greater(out[i:i + BUF, c], total_medians)
            out[i:i + BUF, c][less] = out[i:i + BUF, c][less] - best_C[c] * new_med_smaller[less]
            out[i:i + BUF, c][equal] = out[i:i + BUF, c][equal] - best_C[c] * new_med_equal[equal]
            out[i:i + BUF, c][greater] = out[i:i + BUF, c][greater] - best_C[c] * new_med_greater[greater]
    bark.write_metadata(outfile, **outdset.attrs)


def main():
    import argparse
    p = argparse.ArgumentParser(description="""
    References each channel from the median of all the others
    """)
    p.add_argument("dat", help="dat file")
    p.add_argument("-o", "--out", help="name of output dat file", required=True)
    opt = p.parse_args()
    datref(opt.dat, opt.out)


if __name__ == "__main__":
    main()
