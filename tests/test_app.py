import unittest

import os,sys,inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)
import app, nanoapi
import os, json, requests

dataBase = app.mongo.db

baseURL = "http://localhost:5000/api/v1"

class TestApp(unittest.TestCase):

    def testIndex(self):
        res = request.get(url = baseURL)
        assert json.loads(res.data)
