"""transform module depends on openquake and pandas."""

import sys
import unittest
from pathlib import Path

from moto import mock_dynamodb

from toshi_hazard_store import model

try:
    import openquake  # noqa

    HAVE_OQ = True
except ImportError:
    HAVE_OQ = False


class TestWithoutOpenquake(unittest.TestCase):
    def setUp(self):
        self._temp_oq = None
        if sys.modules.get('openquake'):
            self._temp_oq = sys.modules['openquake']
        sys.modules['openquake'] = None

    def tearDown(self):
        if self._temp_oq:
            sys.modules['openquake'] = self._temp_oq
        else:
            del sys.modules['openquake']

    def test_no_openquake(self):
        flag = False
        try:
            import openquake  # noqa
        except ImportError:
            flag = True
        self.assertTrue(flag)

    def test_no_openquake_raises_import_error(self):
        flag = False
        try:
            import toshi_hazard_store.transform  # noqa
        except ImportError:
            flag = True
        self.assertTrue(flag)


@mock_dynamodb
class TestWithOpenquake(unittest.TestCase):
    def setUp(self):
        model.migrate()
        super(TestWithOpenquake, self).setUp()

    def tearDown(self):
        model.drop_tables()
        return super(TestWithOpenquake, self).tearDown()

    @unittest.skipUnless(HAVE_OQ, "requires openquake")
    def test_export_rlzs_v2(self):
        from openquake.commonlib import datastore

        from toshi_hazard_store import transform

        TOSHI_ID = 'ABCBD'

        p = Path(Path(__file__).parent, 'fixtures', 'calc_1818.hdf5')

        dstore = datastore.read(str(p))
        # print(dstore['sitecol'])

        # do the saving....
        transform.export_rlzs_v2(dstore, TOSHI_ID)

        saved = list(model.ToshiOpenquakeHazardCurveRlzsV2.query(TOSHI_ID))

        n_sites, n_rlzs, n_lvls, n_vals = dstore['hcurves-rlzs'].shape
        self.assertEqual(len(saved), (n_sites * n_rlzs) - 5)  # TODO test data has aduplicate site!
        self.assertEqual(saved[0].imtvs[0].imt, 'SA(0.5)')
        self.assertEqual(saved[0].imtvs[0].lvls[0], 0.001)
        self.assertEqual(saved[0].imtvs[0].vals[0], 0.32528311014175415)
        self.assertEqual(round(saved[0].imtvs[0].lvls[-1], 5), 10.0)
        self.assertEqual(saved[0].imtvs[0].vals[-1], 0.0)
