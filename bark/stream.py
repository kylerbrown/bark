from itertools import chain
import numpy as np
import bark


class Stream():
    def __init__(self, data, sr=None, attrs=None, chunksize=1e6, ):
        self.data = data
        if sr is None and attrs and "sampling_rate" in attrs:
            self.sr = attrs["sampling_rate"]
        elif sr is None:
            self.sr = 1
        else:
            self.sr = sr
        if attrs:
            self.attrs = attrs.copy()
        else:
            self.attrs = {}
        self.chunksize = int(chunksize)
        self.index = 0

    def __iter__(self):
        return self

    def __next__(self):
        if hasattr(self.data, "__next__"):
            return next(self.data)
        try:
            result = self.data[self.index:self.index + self.chunksize]
        except IndexError:
            raise StopIteration
        if result.shape[0] == 0:
            raise StopIteration
        self.index += self.chunksize
        return result

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
        next(self)

    def write(self, filename, dtype=None):
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
            dtype = data.dtype.name
        attrs["dtype"] = dtype
        attrs["n_channels"] = data.shape[1]
        bark.write_metadata(filename + ".meta", **attrs)

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

    def __getitem__(self, key):
        """ use python syntax for splitting columns out of the stream """
        return self.new_stream((x[:, key]) for x in self)

    def vector_map(self, func):
        """
        Calls func on overlapping chunks of data
        useful for timeseries functions like filters.

        function should return values the same shape as
        the input data

        algorithm:
        Run function over two consecutive buffers.
        return result in 1/3 sections, ensuring that
        there is always a extra 1/3 on either side if possible.
        """
        return self.new_stream(self._vector_map(func)).rechunk()

    def _vector_map(self, func):
        """ helper function """
        C = self.chunksize
        N = C // 3
        prev = None
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
                        yield y[2 * N: C]
                    if len(y) > C:
                        yield y[C: C + N]
                    if len(y) >C + N:
                        yield y[C + N: C + 2 * N]
                prev = x
            if len(y) > C + 2 * N:
                yield y[C + 2 * N:]
        except IndexError:
            raise StopIteration

    def split(self, *args):
        return self.new_stream((x[:, args] for x in self))

    def merge(*streams):
        "Concatenate columns from streams"
        return streams[0].new_stream((np.hstack(data) for data in zip(*streams)
                                      ))

    def chain(*streams):
        self = streams[0]
        return self.new_stream((data
                                for data in rechunk(
                                    chain(*streams), self.chunksize)))

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

    def convolve(self, win):
        " Convolves each channel with window win."
        from scipy.signal import fftconvolve
        def conv_func(x):
            return np.column_stack([fftconvolve(x[:, i], win) for i in range(x.shape[1])]) 
        return self.new_stream(self.vector_map(conv_func))

    def decimate(self, factor):
        return self.new_stream(decimate(self, factor)).rechunk()

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


class FileStream(Stream):
    def __next__(self):
        try:
            result = self.data[self.index:self.index + self.chunksize]
        except IndexError:
            raise StopIteration
        if result.shape[0] == 0:
            raise StopIteration
        self.index += self.chunksize
        return result


def read(fname, **kwargs):
    """ input: the filename of a raw binary file
        should have an associated .meta file
        returns FileStream
        """
    bark_obj = bark.read_sampled(fname)
    data = bark_obj.data
    sr = bark_obj.attrs["sampling_rate"]
    kwargs.update(bark_obj.attrs)
    return FileStream(data, sr=sr, attrs=kwargs)
