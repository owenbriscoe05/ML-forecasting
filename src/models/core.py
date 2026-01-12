import sklearn
import pytest
import numpy as np
import pandas as pd

class Classifier:
    X = []
    y = []
    def __init__():
        X = np.zeros()
        y = np.zeros()
    

class kNeighborsClassifier(Classifier):
    def fit(self, X, y):
        dim = np.shape(X)
        dim_y = np.shape(y)
        out = np.zeros(dim, dim_y)
        return out
    def predict(self, X, y):
        output = []
        for x in range(np.shape(X)):
            if x["precip_type"] == y:
                output.append(True)
            else: output.append(False)

    def predictHelper(X, y):
        ...

    