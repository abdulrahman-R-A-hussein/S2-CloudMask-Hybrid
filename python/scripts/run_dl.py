"""Deep-learning reference masks on the validation patches (R1), cached for run_r1.py.

OmniCloudMask (Wright et al. 2025; pip ``omnicloudmask``) takes Red, Green, NIR at 10-50 m and
normalises internally, so the CloudSEN12+ L1C digital numbers (B4, B3, B8) are passed as they
are. Output classes 0 clear, 1 thick, 2 thin, 3 shadow (the CloudSEN12 schema).

CloudS2Mask is not run: its API takes only full .SAFE scenes, and its authors list it as
superseded by OmniCloudMask (DECISIONS D-18).

The 509x509 patch is reflect-padded to 512 (a size the network accepts) and cropped back.
Writes data/cache/dl_omnicloudmask_<tid>.npz and appends a line to results/<run>/run.log.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from cloudbench import data  # noqa: E402

L1C_RGN = (4, 3, 8)  # 1-based rasterio band numbers of B4, B3, B8 in cloudsen12-l1c


def read_rgn(l1, pos: int) -> np.ndarray:
    tid = l1.loc[pos, "tortilla:id"]
    f = data.CACHE / f"l1c_rgn_{tid}.npz"
    if f.exists():
        with np.load(f) as z:
            return z["rgn"]
    s1 = data.retry(lambda: l1.read(int(pos)))
    path = data.retry(lambda: s1.read(0))
    rgn = np.stack([data.retry(lambda b=b: data._read_band(path, b)) for b in L1C_RGN]).astype(np.uint16)
    np.savez_compressed(f, rgn=rgn)
    return rgn


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default=f"r1_{time.strftime('%Y-%m-%d')}")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    import omnicloudmask
    import torch
    from omnicloudmask import predict_from_array
    from omnicloudmask.download_models import get_latest_model_version

    l1, *_ = data.load_tables()
    sel = data.select(l1, "validation")
    if args.limit:
        sel = sel.head(args.limit)
    t0, n_done, n_skip, infer_s = time.time(), 0, 0, 0.0
    for i, pos in enumerate(sel.index, 1):
        tid = l1.loc[pos, "tortilla:id"]
        out = data.CACHE / f"dl_omnicloudmask_{tid}.npz"
        if out.exists():
            n_skip += 1
            continue
        rgn = read_rgn(l1, int(pos)).astype(np.float32)
        pad = np.pad(rgn, ((0, 0), (0, 3), (0, 3)), mode="reflect")
        t1 = time.time()
        pred = predict_from_array(pad, patch_size=512, patch_overlap=0, inference_device="cuda",
                                  no_data_value=0, apply_no_data_mask=True)
        infer_s += time.time() - t1
        np.savez_compressed(out, mask=pred[0, : data.PATCH, : data.PATCH].astype(np.uint8))
        n_done += 1
        if i % 25 == 0:
            print(f"{i}/{len(sel)} patches, {time.time() - t0:.0f}s", flush=True)
    msg = (f"run_dl: OmniCloudMask package {omnicloudmask.__version__}, model v{get_latest_model_version()}, "
           f"torch {torch.__version__}, device {torch.cuda.get_device_name(0)}; input CloudSEN12+ L1C B4/B3/B8 "
           f"reflect-padded to 512; predicted={n_done} already cached={n_skip}; "
           f"GPU inference seconds={infer_s:.0f} (includes model load; first call also downloads weights)")
    res = ROOT.parent / "results" / args.run
    res.mkdir(parents=True, exist_ok=True)
    with open(res / "run.log", "a", encoding="utf-8") as f:
        f.write(msg + "\n")
    print(msg)


if __name__ == "__main__":
    main()
