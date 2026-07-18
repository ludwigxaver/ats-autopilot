"""Command-line interface for ats-autopilot."""
from __future__ import annotations
import argparse
from pathlib import Path

from .profile import Profile
from .answers import AnswerBook
from .engine import Engine
from .tracker import Tracker
from .resume import FactBase, GroundingVerifier, tailor, read_resume, audit_resume
from .resume.render import render

CONFIG = Path("config")
DB = "state/applications.db"


def _engine(resume_path: str = "") -> Engine:
    return Engine(Profile.load(CONFIG / "profile.yaml"),
                  AnswerBook.load(CONFIG / "answers.yaml"),
                  resume_path=resume_path)


def cmd_prep(args):
    boards = [(b.split(":")[0] if ":" in b else "greenhouse", b.split(":")[-1])
              for b in args.boards.split(",")]
    eng = _engine()
    tracker = Tracker(DB)
    bundles = eng.prepare(boards, limit=args.limit)
    print(f"Prepared {len(bundles)} applications (DRY-RUN — nothing submitted):\n")
    for b in bundles:
        tag = "★CROWN" if b.crown_jewel else "      "
        status = "READY ✅" if b.ready else f"NEEDS {len(b.unmapped_required)} ⚠️"
        print(f"{tag} [{status}] {b.key}  {b.schema.job.title}")
        for n, lab, ft in b.unmapped_required[:3]:
            print(f"        ↳ unmapped ({ft}): {lab[:60]}")
        tracker.record(b.key, b.schema.job.company, b.schema.job.title,
                       b.schema.job.url, "prepared", b.crown_jewel)
    print(f"\nLedger: {DB}")


def cmd_review(args):
    for key, company, title, status, crown, updated in Tracker(DB).all():
        print(f"  [{status:9}] {'★' if crown else ' '} {key}  {title}  ({updated})")


def cmd_resume(args):
    fb = FactBase.load(CONFIG / "facts.yaml")
    resume = tailor(fb, args.title, args.description or "")
    report = GroundingVerifier(fb).verify(resume.render_text())
    if not report.ok:
        print(report.summary())
        raise SystemExit(1)
    profile = Profile.load(CONFIG / "profile.yaml")
    out = render(resume, profile, args.out)
    print(f"✅ {report.summary()}")
    print(f"Wrote grounded résumé → {out}")


def cmd_audit(args):
    """Audit an externally-generated résumé (e.g. from apt.ai) against the verified facts."""
    fb = FactBase.load(CONFIG / "facts.yaml")
    report = audit_resume(fb, read_resume(args.resume))
    print(report.summary())
    if args.clean:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report.clean_text(), encoding="utf-8")
        print(f"\nWrote grounded (fabrications removed) résumé → {out}")
    raise SystemExit(0 if report.ok else 2)


def cmd_submit(args):
    print("Submit is a guarded, human-reviewed action.")
    print(f"  job={args.job}  reviewed={args.i_have_reviewed}")
    print("Crown-jewel employers are refused by design; live send is enabled per-deployment.")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="ats-autopilot",
                                 description="Schema-driven job-application engine with grounded résumés.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("prep", help="discover + prepare applications (dry-run)")
    p.add_argument("--boards", required=True, help="comma list, e.g. coinbase,gemini,lever:aavelabs")
    p.add_argument("--limit", type=int, default=10)
    p.set_defaults(func=cmd_prep)

    p = sub.add_parser("review", help="show the application ledger")
    p.set_defaults(func=cmd_review)

    p = sub.add_parser("resume", help="generate a grounded, tailored résumé")
    p.add_argument("--title", required=True)
    p.add_argument("--description", default="")
    p.add_argument("--out", default="out/resume.html")
    p.set_defaults(func=cmd_resume)

    p = sub.add_parser("audit", help="audit an external (e.g. apt.ai) résumé against verified facts")
    p.add_argument("--resume", required=True, help="path to .txt/.md/.html/.pdf résumé")
    p.add_argument("--clean", action="store_true", help="write a copy with fabricated lines removed")
    p.add_argument("--out", default="out/resume.grounded.txt")
    p.set_defaults(func=cmd_audit)

    p = sub.add_parser("submit", help="submit one reviewed application (guarded)")
    p.add_argument("--job", required=True)
    p.add_argument("--i-have-reviewed", action="store_true")
    p.set_defaults(func=cmd_submit)

    args = ap.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
