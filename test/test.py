from timeit import timeit
import numpy as npy
a=npy.array([[1,2,3],[4,5,6]])
def test_time():
    a[0]*a[1]

print(timeit('test_time()','from __main__ import test_time',number=1000)) 

import numpy
a=numpy.array([
    [
        [1,2,3],
        [4,5,6]
    ],
    
    [
        [11,12,13],
        [14,15,16]
    ]
])
d,e=numpy.vsplit(a,2)
a[1:,:,:]=numpy.array([[[14, 0, 13],[14, 15, 15]]])
c = numpy.array([[[]]])
a = numpy.array([[1,2,3],[4,5,6]])
b = numpy.array([[11,12,13],[14,15,16]])
numpy.vstack((a,b))
image=[
    [100,100,50],
    [255,0,0],
    [0,0,255]

    [255,255,255]
    [0,0,0]
]