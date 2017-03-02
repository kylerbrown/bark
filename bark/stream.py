from itertools import chain
import numpy as np
import bark

def array_iterator(data, chunksize):
    index = 0
    while True:
        try:
            result = data[index:index + chunksize]
        except IndexError:
            raise StopIteration
        if result.shape[0] == 0:
            raise StopIteration
        yield result
        index += chunksize


class Stream():
    def __init__(self, data, sr=None, attrs=None, chunksize=2e6):
        """
        chunksize: 1e6 is about 1 minute of data
        and 64 mb per channel. Therefore each addition stream operation
        will use and additional 64*N mb of memory.
        If this becomes burdensome, lower the chunksize,
        however any operations that span time (filters, resampling)
        may be compromized by having too low of chunksize.
        """
        self.chunksize = int(chunksize)
        if isinstance(data, np.ndarray):  # note: memmap is an ndarray subclass too
            self.data = array_iterator(data, self.chunksize)
        else:
            self.data = data
        if sr is None and attrs and "sampling_rate" in attrs:
            self.sr = attrs["sampling_rate"]
        elif sr is None:
            self.sr = 1
        else:
            self.sr = sr
        if attrs:
            self.attrs = attrs.copy()
            attrs['columns']
        else:
            self.attrs = {}
        if 'columns' not in self.attrs:
            self.attrs['columns'] = bark.template_columns(range(self.peek().shape[1]))

    def __iter__(self):
        return self

    def __next__(self):
        return next(self.data)

    def peek(self):
        "Returns the first buffer without removing it from the stream"
        x = next(self)
        self.data = chain((x,), self.data)
        return x


    def __add__(self, other):
        return self._binary_operator(other, lambda x, y: x + y)

    def __sub__(self, other):
        return self._binary_operator(other, lambda x, y: x - y)

    def __mul__(self, other):
        return self._binary_operator(other, lambda x, y: x * y)

    def __truediv__(self, other):
        return self._binary_operator(other, lambda x, y: x / y)

    def __floordiv__(self, other):
        return self._binary_operator(other, lambda x, y: x // y)

    def new_stream(self, newdata):
        " Creates a new stream with new data"
        return Stream(newdata,
                      sr=self.sr,
                      attrs=self.attrs,
                      chunksize=self.chunksize)

    def _binary_operator(self, other, func):
        if isinstance(other, Stream):
            return self.new_stream((func(x, y) for x, y in zip(self, other)))
        else:
            return self.new_stream((func(x, other) for x in self))

    def call(self):
        "Returns the data as a numpy array."
        return np.vstack(self)

    def pop(self):
        "Returns the first buffer of the stream."
        return next(self)

    def write(self, filename, dtype=None, **new_attrs):
        """ Saves to disk as raw binary """
        attrs = self.attrs.copy()
        attrs["sampling_rate"] = self.sr
        if dtype:
            with open(filename, "wb") as fp:
                for data in self:
                    fp.write(data.astype(dtype).tobytes())
        else:
            # we don't know the datatype until we stream
            with open(filename, "wb") as fp:
                for data in self:
                    fp.write(data.tobytes())
            dtype = data.dtype.str
        attrs["dtype"] = dtype
        try:
            bark.sampled_columns(data, attrs['columns'])
        except (ValueError, KeyError):
            print('warning, column attribute was mangled ... reseting')
            attrs['columns'] = bark.sampled_columns(data)
        attrs.update(new_attrs)
        bark.write_metadata(filename, **attrs)

    def map(self, func, vectorize=False):
        """ Maps a function to data,
        intended for scalar operators like
        numpy.abs
        or
        lambda x : x ** 2

        make sure your custom function returns a two dimensional array
        """
        if vectorize:
            func = np.vectorize(func)
        newdata = (func(x) for x in self)
        return self.new_stream(newdata)
    
    def padded_chunks(self, pad_len, edge_val=0):
        """
        returns overlapping chunks of the array.

        each chunk is pad_len + self.chunksize + pad_len

        first chunk's first pad is filled with edge_val
        last chunk's last pad is filled with edge_val
        """
        peek = self.peek()
        n_columns = peek.shape[1]
        dtype = peek.dtype
        edge_pad = np.array(np.ones((pad_len, n_columns)) * edge_val, dtype=dtype)
        left_pad = edge_pad[:]
        cur_x = None
        for next_x in self:
            if cur_x is None:  # first chunk
                cur_x = next_x
            else:
                right_pad = next_x[:pad_len, :]
                yield np.vstack((left_pad, cur_x, right_pad))
                left_pad = cur_x[-pad_len:, :]
                cur_x = next_x
        # last chunk
        yield np.vstack((left_pad, cur_x, edge_pad))

    def vector_map(self, func):
        """
        Calls func on overlapping chunks of data
        useful for timeseries functions like filters.

        func MUST return values the same shape as
        the it's input, ie don't use this function for resampling!
        """
        return self.new_stream(self._vector_map(func)).rechunk()

    def _vector_map(self, func):
        """ helper function 
        
        Run function over two consecutive buffers.
        return result in 1/3 sections, ensuring that
        there is always a extra 1/3 on either side if possible.
        """
        C = self.chunksize
        N = C // 3
        prev = None
        y = []
        try:
            for x in self:
                if prev is None:
                    y = func(x)
                    yield y[:N, :]
                    if len(y) > N:
                        yield y[N:2 * N]
                else:
                    y = func(np.vstack((prev, x)))
                    if len(y) > 2 * N:
                        yield y[2 * N:C]
                    if len(y) > C:
                        yield y[C:C + N]
                    if len(y) > C + N:
                        yield y[C + N:C + 2 * N]
                prev = x
            if len(y) > C + 2 * N:
                yield y[C + 2 * N:]
        except IndexError:
            raise StopIteration

    def __getitem__(self, ix):
        """ use python syntax for splitting columns out of the stream """
        n_cols = self.peek().shape[1]
        if isinstance(ix, slice):
            #  convert a slice object to indices
            return self.split(*list(range(*ix.indices(n_cols))))
        if hasattr(ix, '__iter__'):
            return self.split(*[i % n_cols for i in ix])
        return self.split(ix % n_cols)

    def split(self, *args):
        if 'columns' in self.attrs:
            self.attrs['columns'] = {i: self.attrs['columns'][x] for i, x in enumerate(args)}
        return self.new_stream((x[:, args]) for x in self)

    def merge(*streams):
        "Concatenate columns from streams"
        s = streams[0].new_stream((np.hstack(data) for data in zip(*streams)
                                      ))
        i = 0
        newcols = {}
        if 'columns' in s.attrs:
            for oldstream in streams:
                oldcols = oldstream.attrs['columns']
                for oldi in range(len(oldcols)):
                    newcols[i] = oldcols[oldi]
                    i += 1
            s.attrs['columns'] = newcols
        return s 


        
    def chain(*streams):
        self = streams[0]
        return self.new_stream((data
                                for data in rechunk(
                                    chain(*streams), self.chunksize)))

    def medfilt(self, kernel_size):
        ' Performed median filtering on each channel, casts dtype to float32'
        from scipy.signal import medfilt2d  # oddly faster than medfilt

        def medfilt_func(x):
            return np.column_stack([medfilt2d(
                x[:, i].astype(np.float32)
                .reshape(-1, 1), (kernel_size, 1)) for i in range(x.shape[1])])

        return self.new_stream(self.vector_map(medfilt_func))

    def _analog_filter(self,
                       ftype,
                       highpass=None,
                       lowpass=None,
                       order=3,
                       zerophase=True):
        ' Use a classic analog filter on the data, currently butter or bessel'
        from scipy.signal import butter, bessel
        filter_types = {'butter': butter, 'bessel': bessel}
        afilter = filter_types[ftype]
        if highpass is None and lowpass is not None:
            b, a = afilter(order, lowpass / (self.sr / 2), btype='lowpass')
        elif highpass is not None and lowpass is None:
            b, a = afilter(order, highpass / (self.sr / 2), btype='highpass')
        elif highpass is not None and lowpass is not None:
            if highpass < lowpass:
                b, a = afilter(order,
                               (highpass / (self.sr / 2),
                                lowpass / (self.sr / 2)),
                               btype='bandpass')
            else:
                b, a = afilter(order,
                               (lowpass / (self.sr / 2),
                                highpass / (self.sr / 2)),
                               btype='bandstop')
        if zerophase:
            return self.filtfilt(b, a)
        else:
            return self.lfilter(b, a)

    def butter(self, highpass=None, lowpass=None, order=3, zerophase=True):
        ' Buttworth filter the data'
        return self._analog_filter('butter', highpass, lowpass, order,
                                   zerophase)

    def bessel(self, highpass=None, lowpass=None, order=3, zerophase=True):
        ' Bessel filter the data'
        return self._analog_filter('bessel', highpass, lowpass, order,
                                   zerophase)

    def rechunk(self, chunksize=None):
        " calls the function rechunk and returns a Stream object."
        if chunksize is not None:
            self.chunksize = chunksize
        return self.new_stream(rechunk(self, self.chunksize))

    def filtfilt(self, b, a):
        " Performs forward backward filtering on the stream."
        from scipy.signal import filtfilt
        filter_func = lambda x: filtfilt(b, a, x, axis=0)
        return self.new_stream(self.vector_map(filter_func))

    def lfilter(self, b, a):
        " Forward only filtering"
        from scipy.signal import lfilter
        filter_func = lambda x: lfilter(b, a, x, axis=0)
        return self.new_stream(self.vector_map(filter_func))

    def convolve(self, win):
        " Convolves each channel with window win."
        from scipy.signal import fftconvolve

        def conv_func(x):
            return np.column_stack([fftconvolve(x[:, i], win)
                                    for i in range(x.shape[1])])

        return self.new_stream(self.vector_map(conv_func))

    def decimate(self, factor):
        s = self.new_stream(decimate(self, factor)).rechunk()
        s.sr = self.sr / factor
        if 'n_samples' in s.attrs:
            del s.attrs['n_samples']
        return s

    def demean(self):
        ' Subtracts the mean across channels for each sample.'
        func = lambda x: x - np.mean(x, axis=1).reshape(-1, 1)
        return self.map(func)

    def demedian(self):
        ' Subtracts the median across channels for each sample.'
        func = lambda x: x - np.median(x, axis=1).reshape(-1, 1)
        return self.map(func)


def decimate(stream, factor):
    " Downsample signals by factor. Remember to filter first!"
    remainder = 0
    for data in stream:
        yield data[remainder::factor, :]
        remainder = (remainder + data.shape[0]) % factor


def rechunk(stream, chunksize):
    "New iterator with correct chunksize."
    buffer = None
    for x in stream:
        if buffer is None:
            buffer = x
        else:
            buffer = np.vstack((buffer, x))
        while len(buffer) > chunksize:
            yield buffer[:chunksize, :]
            buffer = buffer[chunksize:, :]
    yield buffer  # leftover samples at end of stream


def read(fname, chunksize=2e6, **kwargs):
    """ input: the filename of a raw binary file
        should have an associated meta file
        returns FileStream
        """
    bark_obj = bark.read_sampled(fname)
    data = bark_obj.data
    sr = bark_obj.attrs["sampling_rate"]
    kwargs.update(bark_obj.attrs)
    return Stream(data, sr=sr, chunksize=chunksize, attrs=kwargs)

def to_wav(stream, filename):
    import ewave
    data = stream.peek()
    dtype = data.dtype.str,
    nchannels = data.size[1]
    with ewave.open(wavfile,
                    "w+",
                    sampling_rate=stream.sr,
                    dtype=dtype,
                    nchannels=nchannels) as wavfp:
        for x in stream:
            wavfp.write(x)

