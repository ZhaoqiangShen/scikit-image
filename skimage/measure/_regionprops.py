# coding: utf-8
import warnings
from math import sqrt, atan2, pi as PI
import numpy as np
from scipy import ndimage

from skimage.morphology import convex_hull_image
from skimage.measure import _moments


__all__ = ['regionprops']


STREL_4 = np.array([[0, 1, 0],
                    [1, 1, 1],
                    [0, 1, 0]])
STREL_8 = np.ones((3, 3), 'int8')
PROPS = {
    'Area': 'area',
    'BoundingBox': 'bbox',
    'CentralMoments': 'central_moments',
    'Centroid': 'centroid',
    'ConvexArea': 'convex_area',
#    'ConvexHull',
    'ConvexImage': 'convex_image',
    'Coordinates': 'coords',
    'Eccentricity': 'eccentricity',
    'EquivDiameter': 'equivalent_diameter',
    'EulerNumber': 'euler_number',
    'Extent': 'extent',
#    'Extrema',
    'FilledArea': 'filled_area',
    'FilledImage': 'filled_image',
    'HuMoments': 'hu_moments',
    'Image': 'image',
    'MajorAxisLength': 'major_axis_length',
    'MaxIntensity': 'max_intensity',
    'MeanIntensity': 'mean_intensity',
    'MinIntensity': 'min_intensity',
    'MinorAxisLength': 'minor_axis_length',
    'Moments': 'moments',
    'NormalizedMoments': 'normalized_moments',
    'Orientation': 'orientation',
    'Perimeter': 'perimeter',
#    'PixelIdxList',
#    'PixelList',
    'Solidity': 'solidity',
#    'SubarrayIdx'
    'WeightedCentralMoments': 'weighted_central_moments',
    'WeightedCentroid': 'weighted_centroid',
    'WeightedHuMoments': 'weighted_hu_moments',
    'WeightedMoments': 'weighted_moments',
    'WeightedNormalizedMoments': 'weighted_normalized_moments'
}


class _cached_property(object):
    """Decorator to use a function as a cached property.

    The function is only called the first time and each successive call returns
    the cached result of the first call.

        class Foo(object):

            @_cached_property
            def foo(self):
                return "Cached"

        class Foo(object):

            def __init__(self):
                self._cache_active = False

            @_cached_property
            def foo(self):
                return "Not cached"

    Adapted from <http://wiki.python.org/moin/PythonDecoratorLibrary>.

    """

    def __init__(self, func, name=None, doc=None):
        self.__name__ = name or func.__name__
        self.__module__ = func.__module__
        self.__doc__ = doc or func.__doc__
        self.func = func

    def __get__(self, obj, type=None):
        if obj is None:
            return self

        # call every time, if cache is not active
        if not obj.__dict__.get('_cache_active', True):
            return self.func(obj)

        # try to retrieve from cache or call and store result in cache
        try:
            value = obj.__dict__[self.__name__]
        except KeyError:
            value = self.func(obj)
            obj.__dict__[self.__name__] = value
        return value


class _RegionProperties(object):

    def __init__(self, slice, label, label_image, intensity_image,
                 cache_active):
        self.label = label
        self._slice = slice
        self._label_image = label_image
        self._intensity_image = intensity_image
        self._cache_active = cache_active

    @_cached_property
    def area(self):
        return self.moments[0, 0]

    @_cached_property
    def bbox(self):
        return (self._slice[0].start, self._slice[1].start,
                self._slice[0].stop, self._slice[1].stop)

    @_cached_property
    def centroid(self):
        row, col = self.local_centroid
        return row + self._slice[0].start, col + self._slice[1].start

    @_cached_property
    def central_moments(self):
        row, col = self.local_centroid
        return _moments.central_moments(self._image_double, row, col, 3)

    @_cached_property
    def convex_area(self):
        return np.sum(self.convex_image)

    @_cached_property
    def convex_image(self):
        return convex_hull_image(self.image)

    @_cached_property
    def coords(self):
        rr, cc = np.nonzero(self.image)
        return np.vstack((rr + self._slice[0].start,
                          cc + self._slice[1].start)).T

    @_cached_property
    def eccentricity(self):
        l1, l2 = self.inertia_tensor_eigvals
        if l1 == 0:
            return 0
        return sqrt(1 - l2 / l1)

    @_cached_property
    def equivalent_diameter(self):
        return sqrt(4 * self.moments[0, 0] / PI)

    @_cached_property
    def euler_number(self):
        euler_array = self.filled_image != self.image
        _, num = ndimage.label(euler_array, STREL_8)
        return -num

    @_cached_property
    def extent(self):
        rows, cols = self.image.shape
        return self.moments[0, 0] / (rows * cols)

    @_cached_property
    def filled_area(self):
        return np.sum(self.filled_image)

    @_cached_property
    def filled_image(self):
        return ndimage.binary_fill_holes(self.image, STREL_8)

    @_cached_property
    def hu_moments(self):
        return _moments.hu_moments(self.normalized_moments)

    @_cached_property
    def image(self):
        return self._label_image[self._slice] == self.label

    @_cached_property
    def _image_double(self):
        return self.image.astype(np.double)

    @_cached_property
    def inertia_tensor(self):
        mu = self.central_moments
        a = mu[2, 0] / mu[0, 0]
        b = -mu[1, 1] / mu[0, 0]
        c = mu[0, 2] / mu[0, 0]
        return np.array([[a, b], [b, c]])

    @_cached_property
    def inertia_tensor_eigvals(self):
        a, b, b, c = self.inertia_tensor.flat
        # eigen values of inertia tensor
        l1 = (a + c) / 2 + sqrt(4 * b ** 2 + (a - c) ** 2) / 2
        l2 = (a + c) / 2 - sqrt(4 * b ** 2 + (a - c) ** 2) / 2
        return l1, l2

    @_cached_property
    def intensity_image(self):
        if self._intensity_image is None:
            raise AttributeError('No intensity image specified.')
        return self._intensity_image[self._slice] * self.image

    @_cached_property
    def _intensity_image_double(self):
        return self.intensity_image.astype(np.double)

    @_cached_property
    def moments(self):
        return _moments.central_moments(self._image_double, 0, 0, 3)

    @_cached_property
    def local_centroid(self):
        m = self.moments
        row = m[0, 1] / m[0, 0]
        col = m[1, 0] / m[0, 0]
        return row, col

    @_cached_property
    def max_intensity(self):
        return np.max(self.intensity_image[self.image])

    @_cached_property
    def mean_intensity(self):
        return np.mean(self.intensity_image[self.image])

    @_cached_property
    def min_intensity(self):
        return np.min(self.intensity_image[self.image])

    @_cached_property
    def major_axis_length(self):
        l1, _ = self.inertia_tensor_eigvals
        return 4 * sqrt(l1)

    @_cached_property
    def minor_axis_length(self):
        _, l2 = self.inertia_tensor_eigvals
        return 4 * sqrt(l2)

    @_cached_property
    def normalized_moments(self):
        return _moments.normalized_moments(self.central_moments, 3)

    @_cached_property
    def orientation(self):
        a, b, b, c = self.inertia_tensor.flat
        b = -b
        if a - c == 0:
            if b > 0:
                return -PI / 4.
            else:
                return PI / 4.
        else:
            return - 0.5 * atan2(2 * b, (a - c))

    @_cached_property
    def perimeter(self):
        return perimeter(self.image, 4)

    @_cached_property
    def solidity(self):
        return self.moments[0, 0] / np.sum(self.convex_image)

    @_cached_property
    def weighted_central_moments(self):
        row, col = self.weighted_local_centroid
        return _moments.central_moments(self._intensity_image_double,
                                        row, col, 3)

    @_cached_property
    def weighted_centroid(self):
        row, col = self.weighted_local_centroid
        return row + self._slice[0].start, col + self._slice[1].start

    @_cached_property
    def weighted_local_centroid(self):
        m = self.weighted_moments
        row = m[0, 1] / m[0, 0]
        col = m[1, 0] / m[0, 0]
        return row, col

    @_cached_property
    def weighted_hu_moments(self):
        return _moments.hu_moments(self.weighted_normalized_moments)

    @_cached_property
    def weighted_moments(self):
        return _moments.central_moments(self._intensity_image_double, 0, 0, 3)

    @_cached_property
    def weighted_normalized_moments(self):
        return _moments.normalized_moments(self.weighted_central_moments, 3)

    def __getitem__(self, key):
        value = getattr(self, key, None)
        if value is not None:
            return value
        else:  # backwards compatability
            warnings.warn('Usage of deprecated property name.',
                          category=DeprecationWarning)
            return getattr(self, PROPS[key])



def regionprops(label_image, properties=None,
                intensity_image=None, cache=True):
    """Measure properties of labelled image regions.

    Parameters
    ----------
    label_image : (N, M) ndarray
        Labelled input image.
    properties : {'all', list}
        **Deprecated parameter**

        This parameter is not needed any more since all properties are
        determined dynamically.

    intensity_image : (N, M) ndarray, optional
        Intensity image with same size as labelled image. Default is None.
    cache : bool, optional
        Determine whether to cache calculated properties. The computation is
        much faster for cached properties, whereas the memory consumption
        increases.

    Returns
    -------
    properties : list
        List containing a properties for each region. The properties of each
        region can be accessed as attributes and keys.

    Notes
    -----
    The following properties can be accessed as attributes or keys:

    **area** : int
        Number of pixels of region.
    **bbox** : tuple
       Bounding box `(min_row, min_col, max_row, max_col)`
    **central_moments** : (3, 3) ndarray
        Central moments (translation invariant) up to 3rd order::

            mu_ji = sum{ array(x, y) * (x - x_c)^j * (y - y_c)^i }

        where the sum is over the `x`, `y` coordinates of the region,
        and `x_c` and `y_c` are the coordinates of the region's centroid.
    **centroid** : array
        Centroid coordinate tuple `(row, col)`.
    **convex_area** : int
        Number of pixels of convex hull image.
    **convex_image** : (H, J) ndarray
        Binary convex hull image which has the same size as bounding box.
    **coords** : (N, 2) ndarray
        Coordinate list `(row, col)` of the region.
    **eccentricity** : float
        Eccentricity of the ellipse that has the same second-moments as the
        region. The eccentricity is the ratio of the distance between its
        minor and major axis length. The value is between 0 and 1.
    **equivalent_diameter** : float
        The diameter of a circle with the same area as the region.
    **euler_number** : int
        Euler number of region. Computed as number of objects (= 1)
        subtracted by number of holes (8-connectivity).
    **extent** : float
        Ratio of pixels in the region to pixels in the total bounding box.
        Computed as `Area / (rows*cols)`
    **filled_area** : int
        Number of pixels of filled region.
    **filled_image** : (H, J) ndarray
        Binary region image with filled holes which has the same size as
        bounding box.
    **hu_moments** : tuple
        Hu moments (translation, scale and rotation invariant).
    **image** : (H, J) ndarray
        Sliced binary region image which has the same size as bounding box.
    **inertia_tensor** : (2, 2) ndarray
        Inertia tensor of the region for the rotation around its masss.
    **inertia_tensor_eigvals** : tuple
        The two eigen values of the inertia tensor in decreasing order.
    **major_axis_length** : float
        The length of the major axis of the ellipse that has the same
        normalized second central moments as the region.
    **min_intensity** : float
        Value with the greatest intensity in the region.
    **mean_intensity** : float
        Value with the mean intensity in the region.
    **min_intensity** : float
        Value with the least intensity in the region.
    **minor_axis_length** : float
        The length of the minor axis of the ellipse that has the same
        normalized second central moments as the region.
    **moments** : (3, 3) ndarray
        Spatial moments up to 3rd order::

            m_ji = sum{ array(x, y) * x^j * y^i }

        where the sum is over the `x`, `y` coordinates of the region.
    **normalized_moments** : (3, 3) ndarray
        Normalized moments (translation and scale invariant) up to 3rd order::

            nu_ji = mu_ji / m_00^[(i+j)/2 + 1]

        where `m_00` is the zeroth spatial moment.
    **orientation** : float
        Angle between the X-axis and the major axis of the ellipse that has
        the same second-moments as the region. Ranging from `-pi/2` to
        `pi/2` in counter-clockwise direction.
    **perimeter** : float
        Perimeter of object which approximates the contour as a line
        through the centers of border pixels using a 4-connectivity.
    **solidity** : float
        Ratio of pixels in the region to pixels of the convex hull image.
    **weighted_central_moments** : (3, 3) ndarray
        Central moments (translation invariant) of intensity image up to
        3rd order::

            wmu_ji = sum{ array(x, y) * (x - x_c)^j * (y - y_c)^i }

        where the sum is over the `x`, `y` coordinates of the region,
        and `x_c` and `y_c` are the coordinates of the region's centroid.
    **weighted_centroid** : array
        Centroid coordinate tuple `(row, col)` weighted with intensity
        image.
    **weighted_hu_moments** : tuple
        Hu moments (translation, scale and rotation invariant) of intensity
        image.
    **weighted_moments** : (3, 3) ndarray
        Spatial moments of intensity image up to 3rd order::

            wm_ji = sum{ array(x, y) * x^j * y^i }

        where the sum is over the `x`, `y` coordinates of the region.
    **weighted_normalized_moments** : (3, 3) ndarray
        Normalized moments (translation and scale invariant) of intensity
        image up to 3rd order::

            wnu_ji = wmu_ji / wm_00^[(i+j)/2 + 1]

        where `wm_00` is the zeroth spatial moment (intensity-weighted area).

    References
    ----------
    .. [1] Wilhelm Burger, Mark Burge. Principles of Digital Image Processing:
           Core Algorithms. Springer-Verlag, London, 2009.
    .. [2] B. Jähne. Digital Image Processing. Springer-Verlag,
           Berlin-Heidelberg, 6. edition, 2005.
    .. [3] T. H. Reiss. Recognizing Planar Objects Using Invariant Image
           Features, from Lecture notes in computer science, p. 676. Springer,
           Berlin, 1993.
    .. [4] http://en.wikipedia.org/wiki/Image_moment

    Examples
    --------
    >>> from skimage.data import coins
    >>> from skimage.morphology import label
    >>> img = coins() > 110
    >>> label_img = label(img)
    >>> props = regionprops(label_img)
    >>> props[0].centroid # centroid of first labelled object
    >>> props[0]['centroid'] # centroid of first labelled object
    """
    if not np.issubdtype(label_image.dtype, 'int'):
        raise TypeError('Labelled image must be of integer dtype.')

    if properties is not None:
        warnings.warn('The ``properties`` argument is deprecated and is '
                      'not needed any more as properties are '
                      'determined dynamically.',
                      category=DeprecationWarning)

    regions = []

    objects = ndimage.find_objects(label_image)
    for i, sl in enumerate(objects):
        label = i + 1

        props = _RegionProperties(sl, label, label_image,
                                  intensity_image, cache)
        regions.append(props)

    return regions


def perimeter(image, neighbourhood=4):
    """Calculate total perimeter of all objects in binary image.

    Parameters
    ----------
    image : array
        binary image
    neighbourhood : 4 or 8, optional
        neighbourhood connectivity for border pixel determination, default 4

    Returns
    -------
    perimeter : float
        total perimeter of all objects in binary image

    References
    ----------
    .. [1] K. Benkrid, D. Crookes. Design and FPGA Implementation of
           a Perimeter Estimator. The Queen's University of Belfast.
           http://www.cs.qub.ac.uk/~d.crookes/webpubs/papers/perimeter.doc
    """
    if neighbourhood == 4:
        strel = STREL_4
    else:
        strel = STREL_8
    eroded_image = ndimage.binary_erosion(image, strel, border_value=0)
    border_image = image - eroded_image

    # perimeter contribution: corresponding values in convolved image
    perimeter_weights = {
        1:                 (5, 7, 15, 17, 25, 27),
        sqrt(2):           (21, 33),
        (1 + sqrt(2)) / 2: (13, 23)
    }
    perimeter_image = ndimage.convolve(border_image, np.array([[10, 2, 10],
                                                               [ 2, 1,  2],
                                                               [10, 2, 10]]),
                                       mode='constant', cval=0)
    total_perimeter = 0
    for weight, values in perimeter_weights.items():
        num_values = 0
        for value in values:
            num_values += np.sum(perimeter_image == value)
        total_perimeter += num_values * weight

    return total_perimeter
