"""Entry point so that ``python -m gnome_windeploy`` works."""

from gnome_windeploy.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
