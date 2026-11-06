"""Offline check of the RCGP environment.

1. imports and versions of the pinned stack (TensorFlow 2.13.0, GPflow 2.9.1, ...)
2. the four UCI files in data/cache read with the same readers the UCI experiments use
3. a small GPflow GPR fit on the yacht data
4. if ../RCGP-main is present: RCGPR (IMQ weighting) fit on data with outliers,
   and the experiment modules import with vendor/benchmark on sys.path

Usage:  python scripts/test_offline.py        (exit code 0 = all checks passed)
"""
import importlib
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT.parent
RCGP_DIR = BASE / "RCGP-main"
CACHE = ROOT / "data" / "cache" / "data"

EXPECTED = {
    "tensorflow": "2.13.0",
    "tensorflow_probability": "0.21.0",
    "gpflow": "2.9.1",
    "numpy": "1.24.3",
}

results = []


def check(name, fn):
    t0 = time.perf_counter()
    try:
        detail = fn()
        results.append((name, True, detail))
        print(f"PASS  {name}  {detail or ''}  ({time.perf_counter() - t0:.1f}s)")
    except Exception as exc:  # noqa: BLE001
        results.append((name, False, repr(exc)))
        print(f"FAIL  {name}  {exc!r}")


def versions():
    out = []
    for mod, want in EXPECTED.items():
        got = importlib.import_module(mod).__version__
        if got != want:
            raise RuntimeError(f"{mod} {got} != {want}")
        out.append(f"{mod}={got}")
    for mod in ("scipy", "pandas", "matplotlib", "sklearn", "check_shapes", "xlrd", "openpyxl", "tabulate", "tueplots"):
        importlib.import_module(mod)
    return ", ".join(out)


def read_uci():
    import numpy as np
    import pandas as pd

    shapes = {
        "boston/housing.data": pd.read_fwf(CACHE / "boston" / "housing.data", header=None).values.shape,
        "concrete/Concrete_Data.xls": pd.read_excel(CACHE / "concrete" / "Concrete_Data.xls").values.shape,
        "energy/ENB2012_data.xlsx": pd.read_excel(
            CACHE / "energy" / "ENB2012_data.xlsx", engine="openpyxl", usecols=np.arange(9)
        ).dropna().values.shape,
        "yacht/yacht_hydrodynamics.data": np.loadtxt(CACHE / "yacht" / "yacht_hydrodynamics.data").shape,
    }
    want = {
        "boston/housing.data": (506, 14),
        "concrete/Concrete_Data.xls": (1030, 9),
        "energy/ENB2012_data.xlsx": (768, 9),
        "yacht/yacht_hydrodynamics.data": (308, 7),
    }
    if shapes != want:
        raise RuntimeError(f"shapes {shapes}")
    return "; ".join(f"{k} {v}" for k, v in shapes.items())


def yacht_xy():
    import numpy as np

    data = np.loadtxt(CACHE / "yacht" / "yacht_hydrodynamics.data")
    X, Y = data[:, :-1], data[:, -1:]
    X = (X - X.mean(0)) / X.std(0)
    Y = (Y - Y.mean()) / Y.std()
    return X, Y


def gpflow_gpr():
    import gpflow
    import numpy as np

    X, Y = yacht_xy()
    m = gpflow.models.GPR((X, Y), kernel=gpflow.kernels.SquaredExponential(lengthscales=np.ones(X.shape[1])))
    gpflow.optimizers.Scipy().minimize(m.training_loss, m.trainable_variables, options={"maxiter": 100})
    mu, var = m.predict_f(X[:5])
    nlml = float(m.training_loss())
    if not np.isfinite(nlml) or not np.all(np.isfinite(mu.numpy())):
        raise RuntimeError("non-finite result")
    return f"yacht GPR -log marginal likelihood {nlml:.2f}"


def rcgp_fit():
    import gpflow
    import numpy as np

    sys.path[:0] = [str(RCGP_DIR), str(ROOT / "vendor")]
    from rcgp import w
    from rcgp.rcgp import RCGPR

    rng = np.random.default_rng(0)
    X = np.linspace(0, 10, 120)[:, None]
    Y = np.sin(X) + 0.1 * rng.standard_normal(X.shape)
    idx = rng.choice(len(X), 12, replace=False)
    Y[idx] += 6.0  # outliers
    clean = np.setdiff1d(np.arange(len(X)), idx)

    def rmse(model):
        gpflow.optimizers.Scipy().minimize(model.training_loss, model.trainable_variables, options={"maxiter": 500})
        mu, _ = model.predict_f(X)
        return float(np.sqrt(np.mean((mu.numpy()[clean] - np.sin(X[clean])) ** 2)))

    r_gpr = rmse(gpflow.models.GPR((X, Y), kernel=gpflow.kernels.SquaredExponential(), noise_variance=0.1))
    r_rcgp = rmse(RCGPR(
        (X, Y),
        kernel=gpflow.kernels.SquaredExponential(),
        weighting_function=w.IMQ(C=np.quantile(np.abs(Y), 0.9)),
        noise_variance=0.1,
    ))
    if not np.isfinite(r_rcgp) or r_rcgp >= r_gpr:
        raise RuntimeError(f"RCGPR RMSE {r_rcgp:.3f} not below GPR RMSE {r_gpr:.3f}")
    return f"10% outliers, RMSE vs sin(x) on clean points: RCGPR {r_rcgp:.3f} < GPR {r_gpr:.3f}"


def rcgp_experiment_modules():
    sys.path[:0] = [str(RCGP_DIR), str(ROOT / "vendor")]
    for mod in ("benchmark.model_api", "benchmark.metrics", "benchmark.paths",
                "experiments.uci.datasets", "experiments.uci.models", "experiments.uci.benchmarks"):
        importlib.import_module(mod)
    from experiments.uci.dataset_api import DATASET_FACTORIES

    ds = DATASET_FACTORIES.get("yacht").create_dataset(CACHE)
    return f"UCI experiment modules import; yacht dataset {ds.train.X.shape[0]}+{ds.test.X.shape[0]} rows from cache"


def main() -> int:
    if not (CACHE / "yacht" / "yacht_hydrodynamics.data").is_file():
        import runpy

        runpy.run_path(str(ROOT / "scripts" / "prepare_data.py"), run_name="__main__")
    print(f"Python {sys.version.split()[0]} on {sys.platform}")
    check("versions", versions)
    check("uci data", read_uci)
    check("gpflow GPR", gpflow_gpr)
    if (RCGP_DIR / "rcgp" / "rcgp.py").is_file():
        check("RCGPR", rcgp_fit)
        check("RCGP experiment modules", rcgp_experiment_modules)
    else:
        print("SKIP  RCGP checks: RCGP-main not downloaded (python scripts/fetch_url_files.py RCGP-main)")
    failed = [r for r in results if not r[1]]
    print(f"{len(results) - len(failed)}/{len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
