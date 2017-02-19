from timeit import timeit
import numpy as npy
a=npy.array([[1,2,3],[4,5,6]])
def test_time():
    a[0]*a[1]

print(timeit('test_time()','from __main__ import test_time',number=1000)) 