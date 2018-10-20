import json
import logging
import unittest
import os

import arrow
import bson
import dryable
import mock
import mongomock

from mongo_interface.util.mongo_utils import DbConnection
from mongo_interface.mongo_api import FLM

dryable.set(True)

logger = logging.getLogger(__name__)

BASE_ID = 3
BASE_FACILITY_ID = 'smpte-' + str(BASE_ID)


class TestMongo(unittest.TestCase):
    @staticmethod
    def mock_client():
        with open('test/mock/mock_data.json', encoding='utf-8') as f:
            test_data = json.load(f)

        return_client = mongomock.MongoClient().flm

        test_data["_id"] = bson.ObjectId(test_data["_id"])
        return_client.flm.insert_one(test_data)

        init_seq = {'_id': 'flm', 'seq': 0}
        return_client.sequences.insert_one(init_seq)

        print('return_client')
        print(return_client)

        return return_client

    @staticmethod
    def mock_init():
        return None

    @mock.patch.object(DbConnection, 'conn', mock_client)
    @mock.patch.object(FLM, '_initialize_collections', mock_init)
    def setUp(self):
        config = {
            'flm-db': {'port': 27017,
                       'host': 'localhost'}
        }
        self.flm = FLM(config=config)

    @mock.patch.object(DbConnection, 'conn', mock_client)
    def test_delete(self):
        with open("test/json/" + BASE_FACILITY_ID + ".json", "r") as insert_data:
            insert_data = json.load(insert_data)
            insert_data['FacilityID'] = None
        self.flm._insert_smpte_flm(insert_data)

        self.flm.delete_one_smpte_flm(facility_id=BASE_ID)
        flm = self.flm.extract_smpte_flm(facility_id=BASE_ID)
        self.assertEqual(flm, [])
