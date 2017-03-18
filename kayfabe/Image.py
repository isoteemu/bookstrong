#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PIL import Image, ImageOps, ImageChops, ImageDraw

from .FaceDetect import face_detect

import os
import logging

logger = logging.getLogger(__name__)


def get_thumb(picture, thumb_path='ass/img/t', thumb_size=(100, 100), force_regen=False):
    """Get thumb picture. Create one if missing.

    :param picture:     Original image
    :param thumb_path:  Thumbnail folder.
    :param thumb_size:  Thumbnail target size.
    :param force_regen: Force thumbnail regeneration
    """
    basename = os.path.basename(picture)
    filename, ext = os.path.splitext(basename)

    size = '%dx%d' % thumb_size

    thumb = os.path.join(thumb_path, size, filename)
    thumb += ext

    if not force_regen and os.path.exists(thumb):
        return thumb

    logger.debug('Creating new thumbnail %s -> %s', picture, thumb)

    # Create new.
    _make_dir(thumb)

    im = crop_thumb(picture, thumb_size)
    im.save(thumb, im.format, quality=85)

    return thumb


def crop_thumb(picture, thumb_size=(100, 100), **kwargs):
    """Crop thumbnail.

    :param picture:     Picture file to generate thumbnail
    :param thumb_size:  (tuple) Target thumbnail size 

    :return:            Image object.
    """
    scale = kwargs.get('scale', 1)

    im = Image.open(picture)

    logger.debug("Image dimenssions: %s", im.size)

    try:
        ''' Search for face '''
        face_box = find_face(picture)

        scale = 0.35
        crop = zoom_box(im, face_box, scale)

        aspect_ratio = thumb_size[0] / thumb_size[1]

        x, y, w, h = crop_to_aspectratio(im, crop, aspect_ratio=aspect_ratio)

        if y > 0:
            face_offset = h * 0.13
        else:
            face_offset = 0

        crop = _check_bounds(im, (x, y + face_offset, w, h))

        im = _crop(im, crop)
        im = upscale_if_needed(im, thumb_size)

    except AttributeError:
        logger.debug('Could not find face, using dummy cropping.')

        im = trim_borders(im)
        im = upscale_if_needed(im, thumb_size)

        crop = _dummy_crop_box(im, size=thumb_size)

        logger.debug("Crop box: %s, thumb: %s", crop, thumb_size)
        im = _crop(im, crop)

    im.thumbnail(thumb_size, Image.ANTIALIAS)

    return im


def _crop(im, box):
    """Wrapper for Image.crop(), but uses box instead of area."""
    x, y, w, h = box

    left = x
    top = y
    right = x + w
    bottom = y + h

    im = im.crop((left, top, right, bottom))
    return im

def _check_bounds(im, box):
    """Check box agains image dimenssions, reposition if necessary."""
    width, height = im.size
    x, y, w, h = box

    if x < 0:
        x = 0
    elif x + w > width:
        x = width - w

    if y < 0:
        y = 0
    elif y + h > height:
        y = height - h

    return (x, y, w, h)


def _dummy_crop_box(im, size):
    """ Dummy image cropping.

    Center on horizontal crop, and from top on vertical crop.
    :param im:          Image object.
    :param thumb_size:  tuple of requested size()
    :return:            tuple(x, y, w, h)
    """
    target_width, target_height = size
    target_aspect_ratio = target_width / target_height

    width, height = im.size
    source_aspect_ratio = width / height

    logger.debug("Rations: %s, %s",source_aspect_ratio, target_aspect_ratio)
    logger.debug("Dimenssion: %s", im.size)
    if source_aspect_ratio > target_aspect_ratio:
        # Crop on horizontal axis, using center point
        y = 0
        width = width /  (source_aspect_ratio / target_aspect_ratio)
        x = (width / 2) - (width / 4)

    elif source_aspect_ratio < target_aspect_ratio:
        ## TODO: If more closer to panorama, start moving Y point.
        x = y = 0
        height = height * (source_aspect_ratio / target_aspect_ratio)
    else:
        x = y = 0

    return _check_bounds(im, (x, y, width, height))


def upscale_if_needed(im, size):
    """Upscale image, if thumb is going to be smaller than :param size:

    :param size:    Minimum image size allowed.
    """
    w, h = im.size

    min_width, min_height = size

    logger.debug("Width, height: %s x %s", w, h)

    if w < size[0] or h < size[1]:
        factor = max(1, min_width / w, min_height / h)

        new_width = int(w * factor)
        new_height = int(h * factor)
        im = im.resize((new_width, new_height),  Image.ANTIALIAS)

        logger.debug('Upscaled image with factor %f -> (%d, %d)',
                     factor, new_width, new_height)

    return im


def zoom_box(im, box, scale, target_size=None):
    """Dummy function for zooming cropbox outwards.

    :param box:         Current box from where to scale outwards
    :param img_size:    Current image dimenssions.
    :param scale:       Maximum scale to zoom outwars, if possible.
    :param target_size: Target size. Keep inside thease bounds.
    """
    x, y, w, h = box

    # zoomed width and height
    z_w = z_h = 0

    width, height = im.size

    scale = max(scale, w / width, h / height)

    max_width = max(scale * w, width)
    max_height = max(scale * h, height)

    #im = upscale_if_needed(im, (max_width, max_height))

    z_w = w / scale
    z_h = h / scale

    # Move box according scaling.
    x = x - ((z_w - w) / 2)
    y = y - ((z_h - h) / 2)

    ''' Sanity check that we are inside image dimenssions. '''

    return _check_bounds(im, (int(x), int(y), int(z_w), int(z_h)))


def crop_to_aspectratio(im, box, aspect_ratio):
    """Crops image to fit inside defined aspect ration.
    Enlarge if possible, crop if necessary.
    """
    width, height = im.size
    x, y, box_width, box_height = box

    center = (x + box_width/2) / width
    middle = (y + box_height/2) / height

    target_width = box_width * aspect_ratio
    target_height = box_height

    diff_width = width / target_width
    diff_height = height / target_height

    scale = min(diff_width, diff_height)

    logger.debug("Scale: %s (%s, %s)", scale, diff_height, diff_width)

    if scale < 1:
        logger.debug('New bounding box too big, scaling down.')
        target_width = target_width * scale
        target_height = target_height * scale

        new_x = (width * scale) * center - (target_width/2)
        new_y = (height * scale) * middle - (target_height/2)

    else:
        new_x = width * center - (target_width/2)
        new_y = height * middle - (target_height/2)

    logger.debug("Targets: %s x %s", target_width, target_height)


    bounds = (new_x, new_y, target_width, target_height)

    return _check_bounds(im, bounds)


def trim_borders(im):
    ''' Trim image borders.
    From: http://stackoverflow.com/questions/10615901/trim-whitespace-using-pil
    '''

    bg = Image.new(im.mode, im.size, im.getpixel((0,0)))
    diff = ImageChops.difference(im, bg)
    diff = ImageChops.add(diff, diff, 1.1, -100)
    bbox = diff.getbbox()
    if bbox:
        return im.crop(bbox)
    return im

def find_face(picture):

    faces = face_detect(picture)

    logger.debug("Found %d faces for picture %s", len(faces), picture)

    max_idx = None
    max_size = 0
    for i, face in enumerate(faces):
        face_size = face[2] * face[3]
        if face_size > max_size:
            max_size = face_size
            max_idx = i

#    print('Biggest face', max_idx, faces[max_idx])

    return faces[max_idx]


def _make_dir(name, dirmode=0o0755):
    ''' Create directory for file
        :param name: Filename.
    '''

    try:
        os.makedirs(os.path.dirname(name), dirmode)
    except (IOError, OSError):
        pass
