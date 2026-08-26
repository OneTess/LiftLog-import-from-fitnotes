#!/usr/bin/env python3
"""Pack an iOS .app bundle into an unsigned .ipa (zip with Payload/*.app)."""
from __future__ import annotations

import argparse
import zipfile
from pathlib import Path


def pack_app_to_ipa(app_path: Path, ipa_path: Path) -> Path:
    """Write ipa_path as a zip containing Payload/<App>.app.

    LiveContainer (JIT-less) re-signs this payload with the imported AltStore
    certificate. The zip must look like a normal IPA: Payload/*.app/...
    """
    app_path = Path(app_path)
    ipa_path = Path(ipa_path)
    if not app_path.is_dir():
        raise FileNotFoundError(f".app bundle not found: {app_path}")
    if app_path.suffix != ".app":
        raise ValueError(f"expected a .app directory, got {app_path}")

    ipa_path.parent.mkdir(parents=True, exist_ok=True)
    bundle_name = app_path.name

    with zipfile.ZipFile(ipa_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("Payload/", "")
        zf.writestr(f"Payload/{bundle_name}/", "")
        for file in sorted(app_path.rglob("*")):
            if not file.is_file():
                continue
            rel = file.relative_to(app_path).as_posix()
            arcname = f"Payload/{bundle_name}/{rel}"
            zf.write(file, arcname=arcname)

    return ipa_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Zip a .app into an unsigned IPA")
    parser.add_argument("app", type=Path, help="Path to Foo.app")
    parser.add_argument("ipa", type=Path, help="Output path, e.g. dist/LiftLog.ipa")
    args = parser.parse_args()
    out = pack_app_to_ipa(args.app, args.ipa)
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
