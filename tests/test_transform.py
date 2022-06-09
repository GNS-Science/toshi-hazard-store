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
    def test_export_aggs_v2(self):
        from openquake.commonlib import datastore

        from toshi_hazard_store import transform

        TOSHI_ID = 'ABCBD'

        p = Path(Path(__file__).parent, 'fixtures', 'calc_1822.hdf5')

        dstore = datastore.read(str(p))
        # print(dstore['sitecol'])

        # do the saving....
        transform.export_rlzs_v2(dstore, TOSHI_ID)

        saved = list(model.ToshiOpenquakeHazardCurveRlzsV2.query(TOSHI_ID))

        n_sites, n_rlzs, n_lvls, n_vals = dstore['hcurves-rlzs'].shape
        self.assertEqual(len(saved), (n_sites * n_rlzs))  # TODO test data has aduplicate site!
        self.assertEqual(saved[0].values[0].imt, 'PGA')
        self.assertEqual(saved[0].values[0].lvls[0], 0.01)
        self.assertEqual(saved[0].values[0].vals[0], 0.07746574282646179)
        self.assertEqual(round(saved[0].values[0].lvls[-1], 5), 5.0)
        self.assertEqual(saved[0].values[0].vals[-1], 0.0)

    @unittest.skipUnless(HAVE_OQ, "requires openquake")
    def test_export_stats_v2(self):
        from openquake.commonlib import datastore

        from toshi_hazard_store import transform

        TOSHI_ID = 'ABCBD'

        p = Path(Path(__file__).parent, 'fixtures', 'calc_1822.hdf5')

        dstore = datastore.read(str(p))
        # print(dstore['sitecol'])

        # do the saving....
        transform.export_stats_v2(dstore, TOSHI_ID)

        saved = list(model.ToshiOpenquakeHazardCurveStatsV2.query(TOSHI_ID))

        n_sites, n_aggs, n_lvls, n_vals = dstore['hcurves-stats'].shape
        self.assertEqual(len(saved), (n_sites * n_aggs))
        self.assertEqual(saved[0].agg, '0.1')
        self.assertEqual(saved[1].agg, '0.5')
        self.assertEqual(saved[2].agg, '0.9')
        self.assertEqual(saved[3].agg, 'mean')

        # check we have the quantiles ordered OK
        q_01 = saved[0].values[0].vals[12]
        q_05 = saved[1].values[0].vals[12]
        q_09 = saved[2].values[0].vals[12]
        mean = saved[3].values[0].vals[12]

        self.assertTrue(q_09 > q_05 > q_01)
        self.assertTrue(q_09 > q_05)
        self.assertTrue(q_09 > mean > q_01)

        self.assertEqual(saved[0].values[0].imt, 'PGA')
        self.assertEqual(saved[0].values[0].lvls[0], 0.01)
        self.assertEqual(saved[0].values[0].vals[0], 0.03890583664178848)
        self.assertEqual(round(saved[0].values[0].lvls[-1], 5), 5.0)
        self.assertEqual(saved[0].values[0].vals[-1], 0.0)
