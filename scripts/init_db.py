"""Create the paper_stats table (idempotent). Run once per environment."""

from paperlm.db import init_db


def main() -> None:
    init_db()
    print("Initialized database schema.")


if __name__ == "__main__":
    main()
