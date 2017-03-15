#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import cv2
import sys
import json

cascPath = '/usr/share/OpenCV/haarcascades/haarcascade_frontalface_alt2.xml'

def face_detect(imagePath, cascPath):
    faceCascade = cv2.CascadeClassifier(cascPath)

    # Read the image
    image = cv2.imread(imagePath)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Detect faces in the image
    faces = faceCascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(30, 30)
    )
    return faces.tolist()


if __name__ == '__main__':
    
    import argparse
    
    cmdline = argparse.ArgumentParser(description='Detect face from image.')
    cmdline.add_argument('--cascpath', default=cascPath,
                         help='haar cascade to use.')
    cmdline.add_argument('image', help='File to detect faces.')

    args = cmdline.parse_args()

    print(json.dumps(face_detect(args.image, args.cascpath)))
