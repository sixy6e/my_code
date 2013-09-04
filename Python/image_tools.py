#! /usr/bin/env python

import numpy
import scipy
from scipy import ndimage
from osgeo import gdal

#Author: Josh Sixsmith; joshua.sixsmith@ga.gov.au

def img2map(geoTransform, pixel):
    """
    Converts a pixel (image) co-ordinate into a map co-ordinate.

    :param geoTransform:
        A list or tuple containing the upper left co-ordinate of the image.
        This info can be retrieved from gdal. Otherwise create your own using
        the following as a guide. Must have 6 elements.
        geoT = (350415.0, 30.0, 0.0, -3718695.0, 0.0, -30.0)
        geoT[0] is top left x co-ordinate.
        geoT[1] is west to east pixel size.
        geoT[2] is image rotation (0 if image is north up).
        geoT[3] is to left y co-ordinate.
        geoT[4] is image rotation (0 if image is north up).
        geoT[5] is north to south pixel size.


    :param pixel:
        A tuple containing the image index of a pixel (row,column).
        This can contain a series of co-ordinates, eg a tuple containing 2
        numpy.array's of pixel co-ordinates.

    :return:
        A tuple containing the (x,y) location co-ordinate.

    :author: 
        Josh Sixsmith; joshua.sixsmith@ga.gov.au
    """

    if len(geoTransform) != 6:
        raise Exception('Need 6 parameters for the geoTransform variable')

    if len(pixel) != 2:
        raise Exception('Need 2 dimensions for the pixel variable')

    if type(pixel[0]) == numpy.ndarray:
        mapx = []
        mapy = []
        for i in range(len(location[0])):
            mapx.append(pixel[1][i] * geoTransform[1] + geoTransform[0])
            mapy.append(geoTransform[3] - (pixel[0][i] * (numpy.abs(geoTransform[5]))))

            mapx = numpy.array(mapx)
            mapy = numpy.array(mapy)
    else:
        mapx = pixel[1] * geoTransform[1] + geoTransform[0]
        mapy = geoTransform[3] - (pixel[0] * (numpy.abs(geoTransform[5])))

    return (mapx,mapy)


def map2img(geoTransform, location):
    """
    Converts a map co-ordinate into a pixel (image) co-ordinate.

    :param geoTransform:
        A list or tuple containing the upper left co-ordinate of the image. 
	This info can be retrieved from gdal. Otherwise create your own using 
	the following as a guide. Must have 6 elements.
        geoT = (350415.0, 30.0, 0.0, -3718695.0, 0.0, -30.0)
        geoT[0] is top left x co-ordinate.
        geoT[1] is west to east pixel size.
        geoT[2] is image rotation (0 if image is north up).
        geoT[3] is to left y co-ordinate.
        geoT[4] is image rotation (0 if image is north up).
        geoT[5] is north to south pixel size.

    :param location:
        A tuple containing the location co-ordinate (x,y).
        This can contain a series of co-ordinates, eg a tuple containing 2
        numpy.array's of location co-ordinates.

    :return:
        A tuple containing the (row,column) pixel co-ordinate.

    :author:
        Josh Sixsmith; joshua.sixsmith@ga.gov.au
    """

    if len(geoTransform) != 6:
        raise Exception('Need 6 parameters for the geoTransform variable')

    if len(location) != 2:
        raise Exception('Need 2 dimensions for the location variable')

    if type(location[0]) == numpy.ndarray:
        imgx = []
        imgy = []
        for i in range(len(location[0])):
            imgx.append(int(numpy.round((location[0][i] - geoTransform[0])/geoTransform[1])))
            imgy.append(int(numpy.round((geoTransform[3] - location[1][i])/numpy.abs(geoTransform[5]))))

            imgx = numpy.array(imgx)
            imgy = numpy.array(imgy)
    else:
        imgx = int(numpy.round((location[0] - geoTransform[0])/geoTransform[1]))
        imgy = int(numpy.round((geoTransform[3] - location[1])/numpy.abs(geoTransform[5])))

    return (imgy,imgx)


def region_grow(array, seed, stdv_multiplier=None, ROI=None, All_Neighbours=True):
    """
    Grows a single pixel or a group of pixels into a region.

    Similar to IDL's REGION_GROW function. 
    For the single pixel case, the seed and its neighbours
    are used to generate statistical thresholds by which to grow
    connected pixels. If the keyword 'ROI' is set to anything but None, then
    the seed will be assumed to be a region of neighbouring pixels. Otherwise       the region grow function will iterate through the seed points and treat
    them individually.

    :param array:
        A single 2D numpy array.

    :param seed:
        A tuple containing a the location of a single pixel, or multiple pixel locations.

    :param stdv_multiplier:
        A value containing the standard deviation multiplier that defines the 
	upper and lower threshold limits. Defaulted to None, in which case the 
	min and max will be used as defining threshold limits.

    :param ROI:
        The seed will be assumed to be a region of neighbouring pixels, and 
	gather stats from the ROI to perform the threholding. Defaults to
        None; eg pixels are not neighbouring and will iterate through all
        pixels contained in the seed.

    :param All_Neighbours:
        If set to True, then all 8 neighbours will be used to search for connectivity.    
 
    :return:
        A mask containing the grown locations.

    :author:
        Josh Sixsmith; joshua.sixsmith@ga.gov.au
    """

    if len(array.shape) != 2:
        raise Exception('Input array needs to be 2D in shape')

    if type(seed) != tuple:
        raise Exception('Seed must be a tuple')
    
    if len(seed) != 2:
        raise Exception('Seed must be of length 2')

    if type(All_Neighbours) != bool:
        raise Exception('All_Neighbours keyword must be of type bool')

    # Create the structure for the labeling procedure
    if All_Neighbours == True: 
        s = [[1,1,1],[1,1,1],[1,1,1]]
    else:
        s = [[0,1,0],[1,1,1],[0,1,0]]

    dims = array.shape
    # Create the array that will hold the grown region
    grown_regions = numpy.zeros(dims, dtype='byte').flatten()

    if (type(seed[0]) == numpy.ndarray) & ROI == None:
       loop = range(len(seed[0]))
    else:
       loop = range(1)

    for i in loop:

        if ROI == None:
            # Find the seed's neighbours
            x   = numpy.arange(9) % 3 + (seed[1][i] - 1)
            y   = numpy.arange(9) / 3 + (seed[0][i] - 1)
            roi = (y,x)

            # Check if any parts of the roi are outside the image
            bxmin = numpy.where(roi[1] < 0)
            bymin = numpy.where(roi[0] < 0)
            bxmax = numpy.where(roi[1] >= dims[1])
            bymax = numpy.where(roi[0] >= dims[0])

            # Change if roi co-ordinates exist outside the image domain.
            roi[1][bxmin] = 0
            roi[0][bymin] = 0
            roi[1][bxmax] = dims[1]-1
            roi[0][bymax] = dims[0]-1
        else:
            roi = seed

        if stdv_multiplier == None:
            upper = numpy.max(array[roi])
            lower = numpy.min(array[roi])
        else:
            stdv  = numpy.std(array[roi], ddof=1)
            limit = stdv_multiplier * stdv
            mean  = numpy.mean(array[roi])
            upper = mean + limit
            lower = mean - limit

        # Create the mask via the thresholds
        mask = (array >= lower) & (array <= upper)

        # The label function segments the image into contiguous blobs
        label_array, num_labels = ndimage.label(mask, structure=s)

        # Find the labels associated with the roi
        labels  = label_array[roi]
        ulabels = numpy.unique(labels[labels > 0])

        # The in1d search method is slow for when there are only a few labels.
        # When there are heaps of labels it is more effiecient.
        if ulabels.shape[0] < 50:
            for label in ulabels:
                grown_regions |= label_array.flatten() == label
        else:
            find_labels = numpy.in1d(label_array.flatten(), ulabels)
            grown_regions |= find_labels

    return grown_regions.reshape(dims)


def linear_percent(array, percent=2):
    """
    Image contrast enhancement.

    A 2D image is ehanced via a specifed percentage (Default 2%).

    :param array:
        A single 2D array of any data type.
	
    :param perecent:
        A value in the range of 0-100. Default is 2.

    :return:
        A 2D array of the same dimensions as the input array, with values scaled by the specified percentage.

    :author:
        Josh Sixsmith; joshua.sixsmith@ga.gov.au
    """

    if len(array.shape) != 2:
        raise Exception('Only 2D arrays are supported.')

    if (percent <= 0) or (percent >= 100):
        raise Exception('Percent must be between 0 and 100')

    low  = (percent/100.)
    high = (1 - (percent/100.))
    nbins = 256.
    imgmin = numpy.min(array).astype('float')
    imgmax = numpy.max(array).astype('float')
    if array.dtype == 'uint8':
        hist, bedge = numpy.histogram(array, bins=nbins, range=(0,255))
        binsize = 1.
        imgmin = 0
        imgmax = 255
    else:
        hist, bedge = numpy.histogram(array, bins=nbins)
        binsize = (imgmax - imgmin)/(nbins - 1)

    #hist, bedge = numpy.histogram(array, bins=nbins)
    cumu = numpy.cumsum(hist, dtype='float')
    n = cumu[-1]
    
    x1 = numpy.searchsorted(cumu, n * low)
    while cumu[x1] == cumu[x1 + 1]:
        x1 = x1 + 1

    x2 = numpy.searchsorted(cumu, n * high)
    while cumu[x2] == cumu[x2 - 1]:
        x2 = x2 - 1

    minDN = x1 * binsize + imgmin
    maxDN = x2 * binsize + imgmin
        
    # Scaling in the range 0-255.
    y1 = 0
    y2 = 255
    m = float(y2 - y1)/(maxDN - minDN)
    b = m*(-minDN)
    scl_img = array*m + b
    scl_img[scl_img > 255] = 255
    scl_img[scl_img < 0] = 0
    # Could floor the result before converting to uint8 ?
    scl_img = scl_img.astype('uint8')

    return scl_img
    
def write_img(array, name='', format='ENVI', projection=None, geotransform=None):
    """
    Write a 2D/3D image to disk using GDAL.

    :param array:
        A 2D/3D Numpy array.

    :param name:
        A string containing the output file name.

    :param format:
        A string containing a GDAL compliant image format.

    :param projection:
        A variable containing the projection information of the array.

    :param geotransform:
        A variable containing the geotransform information for the array.

    :author:
        Josh Sixsmith, joshua.sixsmith@ga.gov.au

    :history:
        * 04/09/2013--Created
    """
    dims   = array.shape
    if (len(dims) == 2):
        samples = dims[1]
        lines   = dims[0]
        bands   = 1
    elif (len(dims) == 3):
        samples = dims[2]
        lines   = dims[1]
        bands   = dims[0]
    else:
        print 'Input array is not of 2 or 3 dimensions!!!'
        print 'Array dimensions: ', len(dims)
        return

    dtype  = datatype(data.dtype.name)
    driver = gdal.GetDriverByName(format)
    outds  = driver.Create(name, samples, lines, bands, dtype)

    if (projection != None):
        outds.SetProjection(projection)

    if (geotransform != None):
        outds.SetGeoTransform(geotransform)

    if (bands > 1):
        for i in range(bands):
            band   = outds.GetRasteraBand(i+1)
            band.WriteArray(array[i])
            band.FlushCache()
    else:
        band   = outds.GetRasteraBand(1)
        band.WriteArray(array)
        band.FlushCache()

    outds = None

def get_tiles(samples, lines, xtile=100,ytile=100):
    """
    A function that pre-calculates tile indices for a 2D array.

    :param samples:
        An integer expressing the total number of samples in an array.

    :param lines:
        An integer expressing the total number of lines in an array.

    :param xtile:
        (Optional) The desired size of the tile in the x-direction. Default is 100.

    :param ytile:
        (Optional) The desired size of the tile in the y-direction. Default is 1
00.

    :return:
        A list of tuples containing the precalculated tiles used for indexing a larger array. Each tuple contains (ystart,yend,xstart,xend)

    Example:

        >>> tiles = get_tile3(8624, 7567, xtile=1000,ytile=400)
        >>>
        >>> for tile in tiles:
        >>>     ystart = int(tile[0])
        >>>     yend   = int(tile[1])
        >>>     xstart = int(tile[2])
        >>>     xend   = int(tile[3])
        >>>     xsize  = int(xend - xstart)
        >>>     ysize  = int(yend - ystart)
        >>>
        >>>     # When used to read data from disk
        >>>     subset = gdal_indataset.ReadAsArray(xstart, ystart, xsize, ysize)
        >>>
        >>>     # The same method can be used to write to disk.
        >>>     gdal_outdataset.WriteArray(array, xstart, ystart)
        >>>
        >>>     # Or simply move the tile window across an array
        >>>     subset = array[ystart:yend,xstart:xend] # 2D
        >>>     subset = array[:,ystart:yend,xstart:xend] # 3D

    :author:
        Josh Sixsmith, joshua.sixsmith@ga.gov.au

    :history:
        * 01/08/2012: Created

    """
    ncols = samples
    nrows = lines
    tiles = []
    xstart = numpy.arange(0,ncols,xtile)
    ystart = numpy.arange(0,nrows,ytile)
    for ystep in ystart:
        if ystep + ytile < nrows:
            yend = ystep + ytile
        else:
            yend = nrows
        for xstep in xstart:
            if xstep + xtile < ncols:
                xend = xstep + xtile
            else:
                xend = ncols
            tiles.append((ystep,yend,xstep, xend))
    return tiles


def indices_2d(array, indices):
    """
    Converts 1D indices into their 2D counterparts.

    :param array:
         2D array on which the indices were derived. Can accept a 3D array but indices are assumed to be in 2D.

    :param indices:
         The 1D array containing the indices. Can accept the tuple returned from a 'where' statement.

    :return:
        A tuple containing the 2D indices.

    :author:
        Josh Sixsmith, joshua.sixsmith@ga.gov.au

    :history:
        * 03/03/2013: Created

    """

    dims = array.shape
    if (len(dims) == 3):
        rows = dims[1]
        cols = dims[2]
    elif (len(dims) == 2):
        rows = dims[0]
        cols = dims[1]
    elif (len(dims) == 1):
        return indices
    else:
        print 'Error. Array not of correct shape!'
        return

    if (type(indices) == tuple):
        if (len(indices) == 1):
            indices = indices[0]
        else:
            print 'Error. Indices is not a 1 dimensional array!'
            return

    sz = cols * rows
    min = numpy.min(indices)
    max = numpy.max(indices)

    if ((min < 0) | (max >= sz)):
        print 'Error. Index out of bounds!'
        return

    r = indices / cols
    c = indices % cols
    ind = (r,c)

    return ind


