from __future__ import annotations

import json
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.job_digest import run_job_digest


def main() -> None:
    result = run_job_digest(
        careers_config_path=BASE_DIR / "data" / "company_careers.yml",
        search_config_path=BASE_DIR / "data" / "job_search_config.yml",
        experience_library_path=BASE_DIR / "data" / "experience_library.md",
        project_library_path=BASE_DIR / "data" / "project_library.md",
        output_dir=BASE_DIR / "outputs" / "job_digest",
    )
    print(
        json.dumps(
            {
                "generated_at": result.generated_at,
                "discovered_links": len(result.discovered_links),
                "top_matches": len(result.top_matches),
                "warnings": result.warnings,
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
