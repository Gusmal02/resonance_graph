from pathlib import Path
import sys
import unittest
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from resonance_graph.projection import GalleryProjection


class Projection(unittest.TestCase):
    def test_queries_do_not_refit_projection(self):
        rng = np.random.default_rng(3)
        gallery = rng.normal(size=(8, 5))
        projection = GalleryProjection(2).fit(gallery)
        before_mean, before_components = projection.mean.copy(), projection.components.copy()
        first = projection.transform(gallery[:2])
        projection.transform(np.full((3, 5), 1e6))
        np.testing.assert_array_equal(projection.mean, before_mean)
        np.testing.assert_array_equal(projection.components, before_components)
        np.testing.assert_array_equal(first, projection.transform(gallery[:2]))

    def test_gallery_not_mutated_and_dimension_validated(self):
        gallery = np.arange(40.).reshape(8, 5)
        before = gallery.copy()
        GalleryProjection(2).fit(gallery)
        np.testing.assert_array_equal(gallery, before)
        with self.assertRaises(ValueError):
            GalleryProjection(8).fit(gallery)
        with self.assertRaises(ValueError):
            GalleryProjection(2).fit(np.ones((8, 5)))


if __name__ == "__main__":
    unittest.main()
