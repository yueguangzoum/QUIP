# HQ XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
# HQ X
# HQ X   quippy: Python interface to QUIP atomistic simulation library
# HQ X
# HQ X   Copyright James Kermode 2010
# HQ X
# HQ X   These portions of the source code are released under the GNU General
# HQ X   Public License, version 2, http://www.gnu.org/copyleft/gpl.html
# HQ X
# HQ X   If you would like to license the source code under different terms,
# HQ X   please contact James Kermode, james.kermode@gmail.com
# HQ X
# HQ X   When using this software, please cite the following reference:
# HQ X
# HQ X   http://www.jrkermode.co.uk/quippy
# HQ X
# HQ XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

"""Contains :class:`FortranArray` class and utility functions for handling one-based
array indexing."""

import sys
import numpy as np 
import weakref
import logging

__all__ = ['FortranArray', 'frange', 'fenumerate', 'fzeros', 'farray',
           'fidentity', 'fvar', 'f2n', 'n2f', 'unravel_index', 's2a',
           'a2s', 'loadtxt', 'loadcsv', 'tilevec', 'gcd']

major, minor = sys.version_info[0:2]
assert (major, minor) >= (2, 4)
if (major, minor) < (2, 5):
    all = lambda seq: not False in seq
    any = lambda seq: True in seq
    __all__.extend(['all', 'any'])

del major, minor

TABLE_STRING_LENGTH = 10

def frange(min,max=None,step=1):
    """Fortran equivalent of :func:`range` builtin.

    Returns an iterator for integers from ``min`` to ``max`` **inclusive**, increasing by
    ``step`` each time.

    >>> list(frange(3))
    [1, 2, 3]
    >>> list(frange(3,6,2))
    [3, 5]
    """
    if max is None:
        return xrange(1,min+1,step)
    else:
        return xrange(min,max+1,step)

def fenumerate(seq):
    """One-based equivalent of enumerate"""
    i = 1
    for s in seq:
        yield (i, s)
        i += 1

def fzeros(shape,dtype=float):
    """Create an empty :class:`FortranArray` with Fortran ordering."""
    return FortranArray(np.zeros(shape,dtype,order='F'))

def farray(seq, dtype=None):
    """Convert ``seq`` to a :class:`FortranArray` with Fortran ordering.

    >>> fa = farray([1,2,3])

    A copy of the data in seq will be made if necessary."""
    na = np.array(seq,order='F', dtype=dtype)
    return FortranArray(na)

def fidentity(n):
    """Return the ``n`` dimensional identity matrix as a :class:`FortranArray`."""

    return farray(np.identity(n))

def fvar(seq):
    """
    Create one or more rank-0 instances of :class:`FortranArray` and
    inject them into the global namespace.

    This is a convenience function useful for making arrays to use
    as intent(in,out) arguments to a Fortran function. A single
    string argument causes variables with one-letter names to be
    created. The new arrays are also returned.

    The following examples are equivalent::

       >>> fvar("abc")
       (FortranArray(0.0), FortranArray(0.0), FortranArray(0.0))
       >>> a, b, c = fvar(['a','b','c'])
    """

    import inspect
    frame = inspect.currentframe().f_back
    try:
        res = tuple([farray(0.0) for s in seq])
        for s, t in zip(seq, res):
            frame.f_globals[s] = t
        return res
    finally:
        del frame

class FortranArray(np.ndarray):
    """Subclass of :class:`np.ndarray` which uses Fortran-style one-based indexing.

    The first element is numbered one rather than zero and
    trying to access element zero will raise an :exc:`IndexError`
    exception. Negative indices are unchanged; -1 still refers to the
    highest index along a dimension. Slices are also Fortran-style,
    i.e. inclusive on the second element so 1:2 includes the one-based
    elements 1 and 2, equivalent to a C-style slice of 0:2. The ``self.flat``
    iterator is still indexed from zero."""

    __array_priority__ = 100.0

    def __array_finalize__(self, obj):
        if obj is None:
            return
        logging.debug('in __array_finalize__, self.parent=%r, obj.parent=%r' % (getattr(self, 'parent', None),
                                                                                getattr(obj, 'parent', None)))

        if not self.flags.owndata:
            self.parent = getattr(obj, 'parent', None)

    def __array_prepare__(self, array, context=None):
        logging.debug('in __array_prepare__, self.parent=%r, array.parent=%r' % (getattr(self, 'parent', None),
                                                                                 getattr(array, 'parent', None)))
        if getattr(self, 'parent', None) is not None and self.parent() is None:
            raise RuntimeError("array's parent has gone array of scope!")
        if getattr(array, 'parent', None) is not None and array.parent() is None:
            raise RuntimeError("array's parent has gone array of scope!")
        return np.ndarray.__array_prepare__(self, array, context)
        
    #def __array_wrap__(self, array, context=None):
    #    print 'in __array_wrap__, self.parent=%r, array.parent=%r' % (getattr(self, 'parent', None),
    #                                                                getattr(array, 'parent', None))
    #    if self.parent is not None and self.parent() is None:
    #        raise RuntimeError("array's parent has gone array of scope!")
    #    if getattr(array, 'parent', None) is not None and array.parent() is None:
    #        raise RuntimeError("array's parent has gone array of scope!")
    #    return np.ndarray.__array_wrap__(self, array, context)


    def __new__(cls, input_array=None, doc=None, parent=None):
        """Construct a FortanArray from input_array

        a = FortranArray(input_array=None, doc=None)

        If doc is not None, docstring of new array is set to doc."""

        self = np.asarray(input_array)
        self = self.view(cls)

        if doc is not None:
            self.__doc__ = doc

        self.parent = None
        if parent is not None:
            self.parent = weakref.ref(parent)
        return self

    #def __del__(self):
    #    print 'Freeing array shape %r' % self.shape

    def __eq__(self, other):
        obj = np.ndarray.__eq__(self, other)
        if isinstance(obj, np.ndarray):
            return obj.view(self.__class__)
        else:
            return obj

    def __ne__(self, other):
        obj = np.ndarray.__ne__(self, other)
        if isinstance(obj, np.ndarray):
            return obj.view(self.__class__)
        else:
            return obj

    @staticmethod
    def map_int(idx):
        if idx > 0:
            return idx-1
        elif idx == 0:
            raise IndexError('index 0 not permitted - FortranArrays are one-based')
        else:
            return idx

    def mapindices(self, indx):
        """Transform from Fortran-style one-based to C-style zero based indices.

        indx can be any object that can be used to subscript
        an ndarray - scalar integer or slice, sequence of integers and
        slices or an ndarray of integer or boolean kind."""


        def nested(L):
            return [x for x in L if isinstance(x,list)] != []

        one_dim = False
        if not hasattr(indx, '__iter__'):
            one_dim = True
            indx = (indx,)

        islist = isinstance(indx, list)
        doext = False

        if isinstance(indx, np.ndarray):
            indx = (indx,)

        nindx = []
        for idx in indx:
            if isinstance(idx, int) or isinstance(idx, np.integer):
#                print 'mapping int %d to %d' % (idx, FortranArray.map_int(idx))
                nindx.append(FortranArray.map_int(idx))
            elif isinstance(idx, slice):
                rslice_start = None
                rslice_stop = None
                rslice_step = None
                if idx.start is not None:
                    rslice_start = FortranArray.map_int(idx.start)
                if idx.stop is not None:
                    rslice_stop = idx.stop
                if idx.step is not None:
                    rslice_step = idx.step
                rslice = slice(rslice_start, rslice_stop, rslice_step)
#                print 'mapping slice %s to %s' % (idx, rslice)
                nindx.append( rslice )
            elif isinstance(idx, np.ndarray):
                if idx.dtype.kind == 'i':
                    if (idx == 0).any(): raise ValueError('Advanced slicing array must not contain index 0')
                    nindx.append(np.where(idx > 0, idx-1, idx))
                elif idx.dtype.kind == 'b':
                    nindx.append(idx)
                else:
                    raise ValueError('Advanced slicing array must be integer or boolean')
            elif idx is Ellipsis or idx is None:
                nindx.append(idx)
            elif isinstance(idx, list):
                islist = True
                if 0 in idx: raise ValueError('Advanced slicing list must not contain index 0')
                nindx.append([FortranArray.map_int(i) for i in idx])
            else:
                raise ValueError('Unknown index object %r' % (idx,))

        if one_dim and not islist:
            if len(self.shape) > 1:
                if nindx[0] is Ellipsis:
                    res = Ellipsis
                else:
                    res = (Ellipsis,nindx[0])
            else:
                res = nindx[0]
        else:
            if islist:
                #if not Ellipsis in nindx:
                #    if doext:
                #        pass
                #    elif nested(nindx):
                #        res = [Ellipsis] + nindx
                #    else:
                #        res = [Ellipsis] + [nindx]
                #else:
                res = nindx
            else:
                if len(self.shape) > len(nindx):
                    if nindx[0] is Ellipsis:
                        res = tuple(nindx)
                    else:
                        res = tuple([Ellipsis] + nindx)
                else:
                    res = tuple(nindx)

        return res

    def __getitem__(self, indx):
        "Overloaded __getitem__ which accepts one-based indices."
        if getattr(self, 'parent', None) and self.parent() is None:
            raise RuntimeError("array's parent has gone out of scope!")
        # logic moved from __getslice__ which is no longer called
        # from numpy 1.13 and Python 3
        if isinstance(indx, slice):
            if indx.start != 0:
                indx = slice(FortranArray.map_int(indx.start), indx.stop,
                             indx.step)
            obj = np.ndarray.__getitem__(self, indx)
            if isinstance(obj, np.ndarray):
                fa = obj.view(self.__class__)
                return fa

        indx = self.mapindices(indx)
        obj = np.ndarray.__getitem__(self, indx)
        if isinstance(obj, np.ndarray):
            fa = obj.view(self.__class__)
            return fa
        return obj

    def __setitem__(self, indx, value):
        "Overloaded __setitem__ which accepts one-based indices."
        if getattr(self, 'parent', None) and self.parent() is None:
            raise RuntimeError("array's parent has gone out of scope!")

        domap = True
        doext = False
        if isinstance(indx, slice): domap = False
        if indx is Ellipsis: domap = False
        if isinstance(indx, list): doext = True
        if isinstance(indx, np.ndarray): doext = True

        if hasattr(indx, '__iter__'):
            if any([isinstance(x,slice) or x is Ellipsis for x in indx]): domap = False
            if any([isinstance(x,np.ndarray) for x in indx]): doext = True
            if any([isinstance(x,list) for x in indx]): doext = True
            if len(indx) != len(self.shape): domap = False
        elif isinstance(indx, int) or isinstance(indx, np.integer):
            if len(self.shape) != 1:
                domap = False
                indx = (Ellipsis, indx)

        if doext:
            domap = True

        if domap:
#            print 'mapping', indx
            indx = self.mapindices(indx)

        np.ndarray.__setitem__(self, indx, value)

    def __getslice__(self, i, j):
        "Overloaded __getslice__ which accepts one-based indices."
        # Removed in Numpy 1.13 and Python 3
        return self.__getitem__(slice(i, j))

    def __setslice__(self, i, j, value):
        "Overloaded __setslice__ which accepts one-based indices."
        # Removed in Numpy 1.13 and Python 3
        self.__setitem__(slice(i, j), value)

    def nonzero(self):
        """Return the one-based indices of the elements of a which are not zero."""
        return tuple(a + 1 for a in np.ndarray.nonzero(self))

    def argmin(self, axis=None, out=None):
        """Return one-based indices of the minimum values along the given  axis of `a`.

        Refer to `np.ndarray.argmax` for detailed documentation."""
        if axis is not None and axis > 0:
            axis -= 1
        return np.ndarray.argmin(self,axis,out) + 1

    def argmax(self, axis=None, out=None):
        """Return one-based indices of the maximum values along the given axis of `a`.

        Refer to `np.ndarray.argmax` for detailed documentation."""
        if axis is not None and axis > 0:
            axis -= 1
        return np.ndarray.argmax(self,axis,out) + 1

    def argsort(self, axis=None, kind='quicksort', order=None):
        """Returns the indices that would sort this array.

        Refer to `np.argsort` for full documentation."""

        if axis is not None and axis > 0:
            axis -= 1
        return np.ndarray.argsort(self,axis,kind,order) + 1

    def take(self, indices, axis=None, out=None, mode='raise'):
        """Return an array formed from the elements of a at the given
        one-based indices.

        Refer to `np.take` for full documentation."""

        if axis is not None and axis > 0:
            axis -= 1
        return np.ndarray.take(self,self.mapindices(indices),
                                  axis,out,mode)

    def put(self, indices, values, mode='raise'):
        """Set a.flat[n] = values[n] for all n in indices.

        Refer to `np.put` for full documentation."""

        return np.ndarray.put(self, self.mapindices(indices),
                                 values, mode)

    def __repr__(self):
        if getattr(self, 'parent', None) and self.parent() is None:
            raise RuntimeError("array's parent has gone out of scope!")
        s = repr(np.asarray(self).view(np.ndarray))
        s = s.replace('array','FortranArray')
        s = s.replace('\n     ','\n            ')
        return s


    def __str__(self):
        if getattr(self, 'parent', None) and self.parent() is None:
            raise RuntimeError("array's parent has gone out of scope!")        
        return str(np.asarray(self).view(np.ndarray))

    def __iter__(self):
        """Iterate over this :class:`FortranArray` treating first dimension as fastest varying.

        Calls fast :meth:`ndarray.__iter__` for a 1D array."""
        if getattr(self, 'parent', None) and self.parent() is None:
            raise RuntimeError("array's parent has gone out of scope!")
        if len(self.shape) > 1:
            return self.col_iter()
        else:
            return np.ndarray.__iter__(np.asarray(self).view(np.ndarray))


    def row_iter(self):
        """Iterate over this :class:`FortranArray` treating first dimension as fastest varying"""
        if self.shape == ():
            yield self.item()
        else:
            for i in frange(self.shape[0]):
                obj = np.ndarray.__getitem__(self, i-1)
                if (isinstance(obj, np.ndarray) and obj.dtype.isbuiltin):
                    fa = obj.view(self.__class__)
                    yield fa
                else:
                    yield obj

    rows = property(row_iter)

    def norm2(self):
        """Squared norm of a 1D or 2D array.

        For a 1D array, returns dot(self,self)
        For a 2D array, must have shape (3,n). Returns array a where a[i] = dot(self[:,i],self[:,i])"""
        if len(self.shape) == 2:
            n, m = self.shape
            if n != 3:
                raise ValueError('first array dimension should be of size 3')
            out = fzeros(m)
            for i in frange(m):
                out[i] = np.dot(self[:,i],self[:,i])
            return out
        elif len(self.shape) == 1:
            return np.dot(self,self)
        elif len(self.shape) == 0:
            return self.item()
        else:
            raise ValueError("Don't know how to take norm2 of array with shape %s" % str(self.shape))


    def norm(self):
        "Return ``sqrt(norm2(self))``"
        return np.sqrt(self.norm2())

    def normalised(self):
        "Return a normalised copy of this array"
        return self.copy()/self.norm()

    hat = normalised

    def col_iter(self):
        """Iterator for ``MxN`` arrays to return ``cols [...,i]`` for ``i=1,N`` one by one as ``Mx1`` arrays."""
        if self.shape == ():
            yield self.item()
        else:
            for i in frange(self.shape[-1]):
                obj = np.ndarray.__getitem__(self, (Ellipsis, i-1)).view(self.__class__)
                yield obj

    cols = property(col_iter)

    def all(self, axis=None, out=None):
        """One-based analogue of :meth:`np.ndarray.all`"""

        if axis is not None and axis > 0:
            axis -= 1
        obj = np.ndarray.all(self, axis, out)
        if isinstance(obj, np.ndarray):
            obj = obj.view(self.__class__)
        return obj

    def any(self, axis=None, out=None):
        """One-based analogue of :meth:`np.ndarray.any`"""

        if axis is not None and axis > 0:
            axis -= 1
        obj = np.ndarray.any(self, axis, out).view(self.__class__)
        if isinstance(obj, np.ndarray):
            obj = obj.view(self.__class__)
        return obj

    def sum(self, axis=None, dtype=None, out=None):
        """One-based analogue of :meth:`np.ndarray.sum`"""
        if axis is not None and axis > 0:
            axis -= 1
        obj = np.ndarray.sum(self, axis, out).view(self.__class__)
        if isinstance(obj, np.ndarray):
            obj = obj.view(self.__class__)
        return obj

    def mean(self, axis=None, dtype=None, out=None):
        """One-based analogue of :meth:`np.ndarray.mean`"""
        if axis is not None and axis > 0:
            axis -= 1
        obj = np.ndarray.mean(self, axis, out).view(self.__class__)
        if isinstance(obj, np.ndarray):
            obj = obj.view(self.__class__)
        return obj


    def stripstrings(self):
        """Return contents as string (0- and 1-dimensional arrays) or array of strings with
        trailing spaces removed (2-dimensional arrays).

        Raises :exc:`ValueError` if this :class:`FortranArray` does not have a string datatype.
        """

        if self.dtype.kind != 'S': raise ValueError('dtype.kind must be "S"')
        if len(self.shape) == 0:
            return self.item()
        elif len(self.shape) == 1:
            return ''.join(self).strip()
        else:
            return farray([''.join(x).strip() for x in self])


def padded_str_array(d, length):
    """Return :class:`FortranArray` with shape ``(length, len(d))``,
       filled with rows from ``d`` padded with spaces"""
    res = fzeros((length, len(d)), 'S')
    res[...] = ' '
    for i, line in fenumerate(d):
        res[1:len(line),i] = list(line)
    return res


def convert_farray_to_ndarray(func):
    """Decorator to convert all occurences of farray in arguments to ndarray.
       If result contains ndarray, they will be converted back to farray."""
    from functools import wraps
    @wraps(func)

    def nfunc(*args, **kwargs):
        from numpy  import ndarray
        from farray import FortranArray

        nargs = []
        for a in args:
            if isinstance(a, FortranArray):
                nargs.append(a.view(ndarray))
            else:
                nargs.append(a)

        nkwargs = {}
        for k, v in kwargs.iteritems():
            if isinstance(v, FortranArray):
                nkwargs[k] = v.view(ndarray)
            else:
                nkwargs[k] = v

        nargs = tuple(nargs)
        res = func(*nargs, **nkwargs)
        if res is None: return

        one_result = not isinstance(res, tuple)
        if one_result:
            res = (res,)

        nres = []
        for r in res:
            if isinstance(r, ndarray):
                nres.append(r.view(self.__class__))
            else:
                nres.append(r)

        if one_result:
            return nres[0]
        else:
            return tuple(nres)


    return nfunc


def convert_ndarray_to_farray(func):
    """Decorator to convert all occurences of ndarray in arguments to farray.
    If results contains farray, they will be converted back to ndarray. """
    from functools import wraps
    @wraps(func)

    def nfunc(*args, **kwargs):
        from numpy  import ndarray
        from farray import FortranArray

        nargs = []
        for a in args:
            if isinstance(a, ndarray):
                nargs.append(a.view(FortranArray))
            else:
                nargs.append(a)

        nkwargs = {}
        for k, v in kwargs.iteritems():
            if isinstance(v, ndarray):
                nkwargs[k] = v.view(FortranArray)
            else:
                nkwargs[k] = v

        nargs = tuple(nargs)
        res = func(*nargs, **nkwargs)
        if res is None: return

        one_result = not isinstance(res, tuple)
        if one_result:
            res = (res,)

        nres = []
        for r in res:
            if isinstance(r, FortranArray):
                nres.append(r.view(ndarray))
            else:
                nres.append(r)

        if one_result:
            return nres[0]
        else:
            return tuple(nres)

    return nfunc

def f2n(x):
    """Return ``x.view(np.ndarray)``"""
    return x.view(np.ndarray)

def n2f(x):
    """Return ``x.view(FortranArray)``"""
    return x.view(FortranArray)

def unravel_index(x, dims):
    """1-based version of np.unravel_index"""

    return tuple([n+1 for n in np.unravel_index(x-1, dims)])


def s2a(d, pad=TABLE_STRING_LENGTH):
    """Convert from list of strings to array of shape (pad, len(d)).
    If pad is not specified, we use the length of longest string in d"""
    if pad is None:
        pad = max([len(s) for s in d])
    res = fzeros((pad, len(d)), 'S')
    res[...] = ' '
    for i, line in fenumerate(d):
        res[1:len(line),i] = list(line)
    return res

def a2s(a):
    """Convert from array of shape (pad, len(d)) to list of strings d"""
    return [ ''.join(a[:,i]).strip() for i in frange(a.shape[1]) ]

def loadtxt(filename):
    return farray(np.loadtxt(filename))

def loadcsv(filename):
    """Read CSV formatted data file and return dictionary of farrays, using first
       row in file as column labels for dictionary keys."""
    data = np.loadtxt(filename,delimiter=',',skiprows=1)
    cols = open(filename,'rU').readline().strip().split(',')
    data = dict(zip(cols, (farray(data[:,i]) for i in range(data.shape[1]))))
    return data

def tilevec(vec, n):
    """repeat 3-vector `vec` n times to give an array with shape (3,N)"""
    return np.tile(array(vec)[:,np.newaxis], n)

def gcd(a, b):
    """Calculate the greatest common divisor of a and b"""
    while b:
        a, b = b, a%b
    return a

