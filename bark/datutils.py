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

    def write(self, filename, dtype=None):
        """ Saves to disk as raw binary """
        attrs = self.attrs.copy()
        attrs["sampling_rate"] = self.sr
        with open(filename, "wb") as fp:
            for data in self:
                fp.write(data.tobytes())
        if not dtype:
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
        """
        return self.new_stream(self._vector_map(func))

    def _vector_map(self, func):
        """ helper function """
        N = self.chunksize // 3
        prev = None
        try:
            for x in self:
                if not prev:
                    y = func(x)
                    yield y[:N, :]
                    if len(y) > N:
                        yield y[N:2 * N]
                else:
                    y = func(np.vstack((prev, x)))
                    if len(y) > 2 * N:
                        yield y[2 * N:3 * N]
                    if len(y) > 3 * N:
                        yield y[3 * N:4 * N]
                    if len(y) > 4 * N:
                        yield y[4 * N:5 * N]
                prev = x
            if len(y) > 5 * N:
                yield y[5 * N:]
        except IndexError:
            raise StopIteration

    def _vector_map_old(self, func):
        """ helper function """
        x, x2, x3 = None, None, None
        try:
            x1 = next(self)
            x = x1
            x2 = next(self)
            x = np.vstack((x1, x2))
            x3 = next(self)
            x = np.vstack((x1, x2, x3))
        except StopIteration:
            pass
        if x1:
            yield func(x)[:len(x1), :]
        if x2:
            yield fun(x)[len(x1):len(x1) + len(x2), :]

        for data in self:
            x1 = x2
            x2 = x3
            x3 = data
            x = np.vstack(x1, x2, x3)
            yield func(x)[len(x1):len(x) - len(x3), :]
        if x3:
            yield func(x)[len(x) - len(x3):, :]

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

    def rechunk(self, chunksize):
        " calls the function rechunk and returns a Stream object."
        self.chunksize = chunksize
        return self.new_stream(rechunk(self, self.chunksize))


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
        
        (should be a method of the SampledData object
        eventually)
        """
    bark_obj = bark.read_sampled(fname)
    data = bark_obj.data
    sr = bark_obj.attrs["sampling_rate"]
    kwargs.update(bark_obj.attrs)
    return FileStream(data, sr=sr, attrs=kwargs)
