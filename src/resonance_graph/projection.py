"""PCA ajustada únicamente con los embeddings de la galería."""
import numpy as np


class GalleryProjection:
    def __init__(self, dimensions):
        if not isinstance(dimensions, int) or isinstance(dimensions, bool) or dimensions < 1:
            raise ValueError("Dimensión inválida")
        self.dimensions = dimensions
        self.mean = self.components = None

    def fit(self, gallery):
        x = np.array(gallery, dtype=np.float64, copy=True)
        if x.ndim != 2 or not np.isfinite(x).all() or self.dimensions > min(x.shape[0]-1, x.shape[1]):
            raise ValueError("Galería o dimensión de PCA inválida")
        mean = x.mean(0)
        _, s, vt = np.linalg.svd(x-mean, full_matrices=False)
        if (s*s).sum() <= 1e-20:
            raise ValueError("Galería sin varianza")
        self.mean, self.components = mean, vt[:self.dimensions].copy()
        self.mean.flags.writeable = self.components.flags.writeable = False
        self.variance_retained = float((s[:self.dimensions]**2).sum() / (s*s).sum())
        return self

    def transform(self, vectors):
        if self.mean is None:
            raise ValueError("PCA no ajustada")
        x = np.asarray(vectors, dtype=np.float64)
        if x.ndim != 2 or x.shape[1] != len(self.mean) or not np.isfinite(x).all():
            raise ValueError("Datos incompatibles con PCA")
        return (x - self.mean) @ self.components.T
