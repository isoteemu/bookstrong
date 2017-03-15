#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PIL import Image, ImageOps

from .FaceDetect import face_detect

import logging

def crop_thumb(picture, size):
    im = Image.open(picture)

    w,h = im.size

    if h > w:
        y = int(max(h / 3 - (w/2), 0))
        h = w
        x = 0
    else:
        y = 0
        x = int(max(w/2 - (h/2), 0))
        w = h
    
    im = upscale_if_needed(im, size)

    x,y,w,h = zoom_box((x,y,w,h), img_size=im.size)

    im = im.crop((x, y, x+w, y+h))

    im.thumbnail(size)
    return im


def crop_face(picture, size):
    im = Image.open(picture)

    im = upscale_if_needed(im, size)

    box = find_face(picture)

    box = zoom_box(box, img_size=im.size)

    x, y, w, h = box

    im = im.crop((x, y, x+w, y+h))
    im.thumbnail(size)

    '''
    im = ImageOps.fit(im, (64,64), Image.ANTIALIAS, 0.2, centering=(left,top))
    #image = ImageOps.fit(image, thumbnail_size, Image.ANTIALIAS)
    im = im.transform((64, 64), im.EXTENT, (x, y, x+w, y+h))
    '''
    return im


def upscale_if_needed(im, size):
    # TODO: Käytä numeroita, älä Imagea
    ''' Upscale image, if thumb is going to be smaller than @param size
    '''
    w,h = im.size

    if w < size[0] or h < size[1]:
        factor = max(1, size[0] / w, size[1] / h)

        im = im.resize((int(w * factor),int(h * factor)),  Image.ANTIALIAS)

        logging.debug('Scaled image with factor %f' % factor)

    return im


def zoom_box(box, img_size, scale=0.6):
    ''' Dummy function for zooming cropbox outwards
    
        :param box:         Current box from where to scale outwards
        :param img_size:    Current image dimenssions.
        :param scale:       Maximum scale to zoom outwars, if possible.
    '''
    x, y, w, h = box
    
    # zoomed width and height
    z_w = z_h = 0

    width, height = img_size
    
    scale = max(scale, w / width, h / height)

    z_w = w / scale
    z_h = h / scale

    # Move box according scaling.
    x = x - ((z_w - w) / 2)
    y = y - ((z_h - h) / 2)
    
    ''' Sanity check that we are inside image dimenssions. '''
    if x < 0:
        x = 0
    elif x + z_w > width:
        x = width - z_w

    if y < 0:
        y = 0
    elif y + z_h > height:
        y = height - z_h

    return (int(x),int(y),int(z_w),int(z_h))


def find_face(picture):

    faces = face_detect(picture)

    max_idx = None
    max_size = 0
    for i, face in enumerate(faces):
        face_size = face[2] * face[3]
        if face_size > max_size:
            max_size = face_size
            max_idx = i

#    print('Biggest face', max_idx, faces[max_idx])

    return faces[max_idx]


