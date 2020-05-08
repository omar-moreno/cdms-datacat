#!/usr/bin/env python3

import unittest
import tempfile
from CDMSDataCatalog import CDMSDataCatalog


class FetchTestCase(unittest.TestCase):
    def setUp(self):
        self.dc = CDMSDataCatalog()
        # should do tempdir in setup and teardown?

    def test_fetchorder(self):
        basepath = "/CDMS/CUTE/R10/Processed/Releases/Prodv5.9.0/Unmerged/23191101_1235/"
        dataset_paths = [basepath+'Prodv5.9.0_23191101_1235_F0002.root',
                         basepath+'calib_Prodv5.9.0_23191101_1235_F0002.root',
                         ]

        with tempfile.TemporaryDirectory() as tmpdirname:
            fetched = self.dc.fetch(dataset_paths, dest=tmpdirname, 
                                    checkonly=350)
            for pth, dset in zip(dataset_paths, fetched):
                self.assertEqual(pth, dset.relativePath)


if __name__ == '__main__':
    unittest.main()
