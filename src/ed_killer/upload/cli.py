"""Interactive CLI composition for the optional ClearML upload workflow."""

import argparse
from collections.abc import Sequence
from pathlib import Path

from loguru import logger

from ed_killer.upload.models import UploadCancelled, UploadError, UploadRequest
from ed_killer.upload.ports import UploadServices


class ConsoleInteraction:
    def tell(self, message: str) -> None:
        print(message)

    def text(self, question: str, default: str | None = None) -> str:
        suffix = f" [{default}]" if default is not None else ""
        try:
            answer = input(f"{question}{suffix}: ").strip()
        except (EOFError, KeyboardInterrupt) as error:
            raise UploadCancelled("Input closed; upload cancelled.") from error
        return answer or default or ""

    def confirm(self, question: str, default: bool = False) -> bool:
        while True:
            answer = self.text(question + (" [Y/n]" if default else " [y/N]")).casefold()
            if not answer:
                return default
            if answer in {"y", "yes"}:
                return True
            if answer in {"n", "no"}:
                return False
            self.tell("Please answer yes or no.")


def _services() -> UploadServices:
    # Optional dependencies load only when executing the upload command, so the
    # base validator and upload --help remain usable without the upload extra.
    from ed_killer.upload.files import LocalFiles
    from ed_killer.upload.paths import LocalRoots
    from ed_killer.upload.remote import ClearMLStore, HttpClassApi, S3Roots

    return UploadServices(
        HttpClassApi(), ClearMLStore(), S3Roots(), LocalRoots(), LocalFiles(), ConsoleInteraction()
    )


def run_upload(request: UploadRequest, services: UploadServices) -> None:
    from ed_killer.upload.workflow import run_upload as execute

    execute(request, services)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ed-killer-upload",
        description="Validate full cveta2 fetch output and upload a new finalized ClearML dataset version.",
    )
    parser.add_argument("fetch_dir", type=Path, help="Directory with all four cveta2 fetch CSV files")
    parser.add_argument("--project", required=True, help="ClearML project name")
    parser.add_argument("--dataset-name", help="Dataset name; otherwise choose interactively")
    parser.add_argument("--api-url", help="Unauthenticated class API URL; otherwise inherit or prompt")
    parser.add_argument(
        "--local-root", action="append", default=[], help="Approved local directory; repeatable"
    )
    parser.add_argument(
        "--s3-root", action="append", default=[], help="Approved S3 bucket/prefix; repeatable"
    )
    parser.add_argument(
        "--output-dir", type=Path, help="New local report directory; existing paths are refused"
    )
    args = parser.parse_args(argv)
    try:
        request = UploadRequest(
            source=args.fetch_dir.expanduser().resolve(),
            project=args.project,
            dataset_name=args.dataset_name,
            api_url=args.api_url,
            local_roots=tuple(args.local_root),
            s3_roots=tuple(args.s3_root),
            output_dir=args.output_dir.expanduser().resolve() if args.output_dir else None,
        )
        run_upload(request, _services())
        return 0
    except (UploadCancelled, KeyboardInterrupt) as error:
        logger.info("Cancelled: {}", error)
        return 1
    except ImportError as error:
        logger.error("Upload dependencies unavailable; install ed-killer[clearml]: {}", error)
        return 2
    except (UploadError, ValueError, OSError) as error:
        logger.error("Upload blocked: {}", error)
        return 2
    except Exception:
        logger.exception("Unexpected upload failure")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
