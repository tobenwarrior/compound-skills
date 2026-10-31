"""Fetch pinned sources and build the fixtures, reference trees, mutants and judge context the benchmark grades with.

Fixtures (work/fixtures/<name>) are git repositories with no remote, no tags, no reflog and only the refs a task
needs. Each is rebuilt from pinned inputs and checked against the commit it had when the benchmark was frozen,
so results stay comparable. Reference trees (work/refs/<name>) are copies of the invoicekit sources with exactly
one change: a bug fix, the refactor done right, or the naive refactor that changes tax rounding.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from common import BENCH, DATA, FIXTURES, JUDGE_CONTEXT, PYENVS, REFS, SOURCES, git, sha256_bytes

# Upstream repositories at fixed commits. "full" keeps history (fixtures, retrieval); "shallow" is one commit.
PINS = {
    "flask": ("https://github.com/pallets/flask", "49943b5a94413a530761350f04e896f76e8d620e", "full"),
    "django": ("https://github.com/django/django", "a05e16a7230fe33d3f43f4a3aaed103cebb42efc", "shallow"),
    "click": ("https://github.com/pallets/click", "2247b35ea1c47c727d7a06e51fa280e12a863ff6", "full"),
    "hono": ("https://github.com/honojs/hono", "17ad0e21f5a91c939eeafa3df05793a8ea60f016", "full"),
    "vue-core": ("https://github.com/vuejs/core", "24c9d0bffb2299635b8112a978d74a38723aaa10", "shallow"),
    "gin": ("https://github.com/gin-gonic/gin", "0f09c3a9b4626d9fe9979cf4d0521d6ae32ab646", "shallow"),
    "ripgrep": ("https://github.com/BurntSushi/ripgrep", "91f5d22ef48bde459d90a8c7dbeab416e97d0f2b", "shallow"),
    "werkzeug": ("https://github.com/pallets/werkzeug", "2adaad1ab68312fa46efb07ff072b15b720e2444", "full"),
    "attrs": ("https://github.com/python-attrs/attrs", "c8bb9bfaa2843e7844b5bb13bed4370b51feec4f", "full"),
    "packaging": ("https://github.com/pypa/packaging", "78d8673da4d275bb7aee0126a5edc3cf90976af1", "full"),
    "marshmallow": ("https://github.com/marshmallow-code/marshmallow", "b762ea2d59ca52fe5df76b90de14bed7e5ec5607", "full"),
}
TASK_SOURCES = ("flask", "django", "click", "werkzeug", "attrs", "packaging", "marshmallow")
MAP_SOURCES = ("flask", "click", "hono", "django", "vue-core", "gin", "ripgrep")

# The frozen fixtures were signed commits; rebuilt ones are unsigned, so a rebuild must match tree, parent,
# people, dates and message rather than the commit id.
INVOICEKIT = {"tree": "fa4f767dab83d25e53185e476b9b53831bad4e95", "parent": "", "message": "invoicekit 0.4.0\n",
              "who": ("Billing Team", "billing@example.invalid"), "date": "1793424106 +0000"}
REVIEW = {"base": "49943b5a94413a530761350f04e896f76e8d620e", "tree": "719747b4621bddad647f0fbe89325ee1443b12d7",
          "frozen": "7edd825a749148d92e1c630db4aa3ff3917077eb", "branch": "feature/static-folders",
          "who": ("Sam Rivera", "sam.rivera@example.invalid"), "date": "1793423656 +0000",
          "message": "Add App.add_static_folders for serving extra static folders\n"}
DJANGO_HEAD = PINS["django"][1]

# Judge context, rebuilt from the fixtures instead of committing third-party source excerpts.
REVIEW_HELPERS = ("src/flask/helpers.py", 543, 587)
DJANGO_EXCERPTS = [
    ("django/middleware/csrf.py", "CsrfViewMiddleware.process_view", [(420, 432)]),
    ("django/views/decorators/http.py", None, [(70, 80), (118, 135)]),
    ("django/utils/cache.py", "get_conditional_response", [(185, 215)]),
    ("django/middleware/http.py", "ConditionalGetMiddleware", [(1, 30)]),
    ("django/views/generic/base.py", "View", [(40, 56), (135, 145)]),
    ("django/middleware/common.py", "CommonMiddleware.get_full_path_with_slash", [(77, 100)]),
    ("django/contrib/admin/options.py", None, [(2060, 2066), (2503, 2509)]),
    ("django/contrib/auth/admin.py", None, [(113, 119)]),
    ("django/test/client.py", "RequestFactory.query, Client.query, AsyncClient.query", [(638, 660), (1385, 1395), (1778, 1788)]),
    ("django/middleware/cache.py", None, [(20, 35), (165, 180)]),
    ("django/http/request.py", "_load_post_and_files", [(445, 458)]),
]
CONTEXT_SHA256 = {"review-diff.txt": "3e79aaeb5add957d927928aeb675f38a054036f83986c682172fefbf5b5e8225",
                  "django-excerpts.txt": "d99b1d1763fb3feabc3752a8cdbad433b50c6144cd4b967524da3f9d7a004b2c"}

# Real bugs fixed upstream in July to September 2026. Each fixture is the project at the fix's parent, with
# history up to there; the fix's own new tests are the hidden tests.
REAL_BUGS = {
    "flask-ipv6-run": ("flask", "7203feabf723edae0286ae5dc64fec8ac4c91735"),
    "flask-ipv6-session": ("flask", "de8429ffda8cfb54db175529e2bae72a24e1fa7e"),
    "click-pickle-option": ("click", "f58ca3e81424a35626c8a475eb59ab95589008ce"),
    "click-progress-final": ("click", "f316d5cb3aa89b57c14aee54da6ac9062ac5bec4"),
    # Frozen on 31 October 2026, before any run: fixes merged August to October 2026 whose new tests fail before the fix.
    "werkzeug-float-sign": ("werkzeug", "594452f6a4fe4de38a544962fbf04bfc9d37fbc2"),
    "attrs-evolve-name": ("attrs", "f53fc5440d7f86aac4328aec7a563eb48634177f"),
    "packaging-empty-platforms": ("packaging", "4e79787a31c99348649bb0dafee2a5078d3595be"),
    "packaging-licenseref-case": ("packaging", "2c87a33f665828b7aa0f650b1b50243b3ab95695"),
    "packaging-pylock-separators": ("packaging", "fa52d7237a74effdadd4ad2627d4ca413234cac2"),
    "packaging-group-errors": ("packaging", "959bb79c06cb883bf1ecd1ddc94a079294907e0f"),
    "marshmallow-timedelta-nan": ("marshmallow", "7dff08fcb7fb40d2772728bb8d8a76b5beff3200"),
    "marshmallow-url-fragment": ("marshmallow", "902f99c4151d1f0c4c3b8e8dfbafc7b6a76aeaa6"),
    "marshmallow-pluck-data-key": ("marshmallow", "5761beab3985d654d712f9326e08bfb2e2ec9c4c"),
}
# Test dependencies at the versions each project's uv.lock pinned, installed as wheels only.
PYENV_PACKAGES = {
    "flask": ["pytest==9.1.1", "iniconfig==2.3.0", "pluggy==1.6.0", "packaging==26.2", "pygments==2.20.0", "werkzeug==3.1.8",
              "jinja2==3.1.6", "itsdangerous==2.2.0", "click==8.4.2", "blinker==1.9.0", "markupsafe==3.0.3",
              "asgiref==3.12.1", "python-dotenv==1.2.2"],
    "click": ["pytest==9.0.2", "iniconfig==2.3.0", "pluggy==1.6.0", "packaging==26.0", "pygments==2.20.0"],
    # Resolved with pip on 31 October 2026 from each project's test dependency group, wheels only.
    "werkzeug": ["markupsafe==3.0.4", "cffi==2.1.1", "cryptography==50.0.2", "ephemeral-port-reserve==1.1.4", "pytest==9.2.0",
                 "pytest-timeout==2.4.0", "watchdog==7.0.0", "iniconfig==2.3.1", "packaging==26.3", "pluggy==1.7.0",
                 "pycparser==3.12", "pygments==2.21.0"],
    "attrs": ["cloudpickle==3.1.2", "hypothesis==6.170.14", "pympler==1.1", "sortedcontainers==2.4.0", "pytest==9.2.0",
              "iniconfig==2.3.1", "packaging==26.3", "pluggy==1.7.0", "pygments==2.21.0"],
    # Not packaging itself: pytest imports it, and an installed copy would shadow the project's src/.
    "packaging": ["hypothesis==6.170.14", "pip==26.2.2", "pretend==1.0.9", "tomli-w==1.2.0", "sortedcontainers==2.4.0",
                  "pytest==9.2.0", "iniconfig==2.3.1", "pluggy==1.7.0", "pygments==2.21.0"],
    "marshmallow": ["pytest==9.2.0", "simplejson==4.2.0", "iniconfig==2.3.1", "packaging==26.3", "pluggy==1.7.0",
                    "pygments==2.21.0"],
}
# Package metadata for the project itself, as an editable install would provide it.
PYENV_PROJECT = {"flask": ("Flask", "3.2.0.dev"), "click": ("click", "8.5.0.dev0"), "werkzeug": ("Werkzeug", "3.2.0.dev"),
                 "attrs": ("attrs", "26.2.0.dev0"), "packaging": ("packaging", "26.4.dev0"), "marshmallow": ("marshmallow", "4.3.1")}

QUIET_GIT = ["-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false", "-c", "core.autocrlf=false",
             "-c", "init.defaultBranch=main"]


def _git(repo: Path, *args: str, env: dict | None = None) -> str:
    out = subprocess.run(["git", *QUIET_GIT, "-C", str(repo), *args], capture_output=True, text=True,
                         env={**os.environ, **(env or {})})
    if out.returncode:
        raise RuntimeError(f"git {' '.join(args)}: {out.stderr.strip()}")
    return out.stdout.strip()


def _identity(who: tuple[str, str], date: str) -> dict:
    return {"GIT_AUTHOR_NAME": who[0], "GIT_AUTHOR_EMAIL": who[1], "GIT_AUTHOR_DATE": date,
            "GIT_COMMITTER_NAME": who[0], "GIT_COMMITTER_EMAIL": who[1], "GIT_COMMITTER_DATE": date}


def fetch(name: str) -> dict:
    """Clone one pinned source into work/sources/<name>, once."""
    url, sha, depth = PINS[name]
    dest = SOURCES / name
    if dest.is_dir() and git(dest, "rev-parse", "HEAD").strip() == sha:
        return {"source": name, "head": sha, "cached": True}
    shutil.rmtree(dest, ignore_errors=True)
    dest.mkdir(parents=True)
    _git(dest, "init", "-q")
    _git(dest, "remote", "add", "origin", url)
    _git(dest, "fetch", "-q", *(["--depth", "1"] if depth == "shallow" else []), "origin", sha)
    _git(dest, "checkout", "-q", "-B", "main", sha)
    return {"source": name, "head": _git(dest, "rev-parse", "HEAD"), "cached": False}


def scrub(repo: Path, keep: set[str]) -> None:
    """Remove every ref outside keep, the remote, tags, reflogs and unreachable objects."""
    if "origin" in git(repo, "remote").split():
        _git(repo, "remote", "remove", "origin")
    for tag in git(repo, "tag", "-l").splitlines():
        _git(repo, "tag", "-d", tag)
    for ref in git(repo, "for-each-ref", "--format=%(refname)").splitlines():
        if ref not in keep:
            _git(repo, "update-ref", "-d", ref)
    for name in ("FETCH_HEAD", "ORIG_HEAD", "packed-refs.lock"):
        (repo / ".git" / name).unlink(missing_ok=True)
    shutil.rmtree(repo / ".git" / "refs" / "original", ignore_errors=True)
    shutil.rmtree(repo / ".git" / "logs", ignore_errors=True)
    _git(repo, "reflog", "expire", "--expire=now", "--all")
    _git(repo, "gc", "-q", "--prune=now")


def leak_checks(repo: Path, keep: set[str]) -> dict:
    refs = set(git(repo, "for-each-ref", "--format=%(refname)").splitlines())
    return {
        "only_expected_refs": refs == keep,
        "no_remote": git(repo, "remote").strip() == "",
        "clean_status": git(repo, "status", "--porcelain").strip() == "",
        "no_stash": git(repo, "stash", "list").strip() == "",
        "no_orig_head": not (repo / ".git" / "ORIG_HEAD").exists(),
        "no_reflog": not (repo / ".git" / "logs").exists() or not any((repo / ".git" / "logs").rglob("*")),
        "head": git(repo, "rev-parse", "HEAD").strip(),
        "branch": git(repo, "rev-parse", "--abbrev-ref", "HEAD").strip(),
    }


def same_commit(repo: Path, frozen: dict, parent: str) -> bool:
    who, date = frozen["who"], frozen["date"]
    fields = git(repo, "log", "-1", "--date=raw", "--format=%T%n%P%n%an%n%ae%n%ad%n%cn%n%ce%n%cd%n%B", "HEAD")
    expected = "\n".join([frozen["tree"], parent, who[0], who[1], date, who[0], who[1], date, frozen["message"]])
    return fields.rstrip("\n") == expected.rstrip("\n")


def build_invoicekit() -> dict:
    dest = FIXTURES / "invoicekit"
    shutil.rmtree(dest, ignore_errors=True)
    shutil.copytree(DATA / "invoicekit", dest, ignore=shutil.ignore_patterns("__pycache__"))
    _git(dest, "init", "-q", "-b", "main")
    _git(dest, "add", "-A")
    message = dest / ".git" / "COMMIT_MESSAGE"
    message.write_text(INVOICEKIT["message"])
    _git(dest, "commit", "-q", "-F", str(message), env=_identity(INVOICEKIT["who"], INVOICEKIT["date"]))
    message.unlink()
    keep = {"refs/heads/main"}
    scrub(dest, keep)
    checks = leak_checks(dest, keep)
    checks["matches_frozen_commit"] = same_commit(dest, INVOICEKIT, "")
    return checks


def build_flask_review() -> dict:
    dest = FIXTURES / "flask-review"
    shutil.rmtree(dest, ignore_errors=True)
    shutil.copytree(SOURCES / "flask", dest, symlinks=True)
    _git(dest, "checkout", "-q", "-B", REVIEW["branch"], REVIEW["base"])
    who = REVIEW["who"]
    _git(dest, "am", "-q", str(DATA / "flask-review.patch"),
         env={"GIT_COMMITTER_NAME": who[0], "GIT_COMMITTER_EMAIL": who[1], "GIT_COMMITTER_DATE": REVIEW["date"]})
    _git(dest, "branch", "-f", "main", REVIEW["base"])
    keep = {"refs/heads/main", f"refs/heads/{REVIEW['branch']}"}
    scrub(dest, keep)
    checks = leak_checks(dest, keep)
    checks["ahead_of_main"] = git(dest, "rev-list", "--count", "main..HEAD").strip()
    checks["matches_frozen_commit"] = same_commit(dest, REVIEW, REVIEW["base"])
    return checks


def build_django() -> dict:
    dest = FIXTURES / "django"
    shutil.rmtree(dest, ignore_errors=True)
    shutil.copytree(SOURCES / "django", dest, symlinks=True)
    keep = {"refs/heads/main"}
    scrub(dest, keep)
    checks = leak_checks(dest, keep)
    checks["matches_frozen_commit"] = checks["head"] == DJANGO_HEAD
    return checks


def build_judge_context() -> dict:
    JUDGE_CONTEXT.mkdir(parents=True, exist_ok=True)
    review = FIXTURES / "flask-review"
    path, first, last = REVIEW_HELPERS
    helpers = (review / path).read_text().splitlines()[first - 1:last]
    show = subprocess.run(["git", "-C", str(review), "-c", "diff.noprefix=false", "show", "--no-color", "--no-ext-diff", "HEAD"],
                          capture_output=True, text=True).stdout
    # The judge must see the commit id the agent sees; the frozen text is checked with the frozen id put back.
    head = git(review, "rev-parse", "HEAD").strip()
    texts = {"review-diff.txt": show + "# git show HEAD of the reviewed commit is above. Relevant helpers:\n" + "\n".join(helpers) + "\n"}
    lines = []
    for name, about, segments in DJANGO_EXCERPTS:
        source = (FIXTURES / "django" / name).read_text().splitlines()
        lines.append(f"== {name}" + (f" ({about})" if about else ""))
        for first, last in segments:
            lines.extend(source[first - 1:last])
    texts["django-excerpts.txt"] = "\n".join(lines) + "\n"
    report = {}
    for name, text in texts.items():
        (JUDGE_CONTEXT / name).write_text(text)
        frozen = text.replace(f"commit {head}\n", f"commit {REVIEW['frozen']}\n", 1)
        report[name] = sha256_bytes(frozen.encode()) == CONTEXT_SHA256[name]
    return report


REFERENCE_EDITS = {
    # One change per tree, applied to the fixture sources only.
    "refund": ("money.py", [(
        "        unit = self.currency.minor_unit\n"
        "        units = int(self.amount / unit)\n"
        "        total = sum(ratios)\n"
        "        shares = [int(units * ratio / total) for ratio in ratios]\n"
        "        remainder = units - sum(shares)\n"
        "        for index in range(remainder):\n"
        "            shares[index] += 1\n"
        "        return [Money(Decimal(share) * unit, self.currency) for share in shares]\n",
        "        unit = self.currency.minor_unit\n"
        "        units = int(self.amount / unit)\n"
        "        sign = -1 if units < 0 else 1\n"
        "        units = abs(units)\n"
        "        total = sum(ratios)\n"
        "        shares = [units * ratio // total for ratio in ratios]\n"
        "        remainder = units - sum(shares)\n"
        "        for index in range(remainder):\n"
        "            shares[index] += 1\n"
        "        return [Money(Decimal(sign * share) * unit, self.currency) for share in shares]\n",
    )]),
    "leap": ("proration.py", [(
        "    return _DAYS_IN_MONTH[month - 1]\n",
        "    if month == 2 and year % 4 == 0 and (year % 100 != 0 or year % 400 == 0):\n"
        "        return 29\n"
        "    return _DAYS_IN_MONTH[month - 1]\n",
    )]),
    "december": ("terms.py", [(
        "    first_of_next = date(day.year, day.month % 12 + 1, 1)\n",
        "    first_of_next = date(day.year + day.month // 12, day.month % 12 + 1, 1)\n",
    )]),
    # The refactor done right keeps half-up rounding for tax by passing it through money.quantize.
    "refactor": ("", []),
    # The naive refactor routes tax through banker's rounding and changes tax amounts.
    "refactor-naive": ("tax.py", [(
        "    return amount.quantize(currency.minor_unit, rounding=ROUND_HALF_UP)\n",
        "    from .money import quantize\n"
        "    return quantize(amount, currency)\n",
    )]),
}


def _replace_once(text: str, old: str, new: str, where: str) -> str:
    if text.count(old) != 1:
        raise RuntimeError(f"{where}: edit anchor not found exactly once")
    return text.replace(old, new)


def _refactor_right(package: Path) -> None:
    money = package / "money.py"
    money.write_text(_replace_once(
        money.read_text(),
        'def quantize(amount: Decimal, currency: Currency) -> Decimal:\n    """Round to the currency\'s minor unit with banker\'s rounding."""\n    return amount.quantize(currency.minor_unit, rounding=ROUND_HALF_EVEN)\n',
        'def quantize(amount: Decimal, currency: Currency, rounding: str = ROUND_HALF_EVEN) -> Decimal:\n    """Round to the currency\'s minor unit, with banker\'s rounding unless told otherwise."""\n    return amount.quantize(currency.minor_unit, rounding=rounding)\n',
        "refactor money.py"))
    tax = package / "tax.py"
    text = tax.read_text()
    text = _replace_once(text, "from .money import Money\n", "from .money import Money, quantize\n", "refactor tax.py import")
    text = _replace_once(text, 'def _round_tax(amount: Decimal, currency: Currency) -> Decimal:\n    """Round a tax amount to the currency\'s minor unit."""\n    return amount.quantize(currency.minor_unit, rounding=ROUND_HALF_UP)\n\n\n', "", "refactor tax.py helper")
    text = _replace_once(text, "_round_tax(net.amount * rate, net.currency)", "quantize(net.amount * rate, net.currency, ROUND_HALF_UP)", "refactor tax.py net")
    text = _replace_once(text, "_round_tax(gross.amount / (1 + rate), gross.currency)", "quantize(gross.amount / (1 + rate), gross.currency, ROUND_HALF_UP)", "refactor tax.py gross")
    text = _replace_once(text, "from .currency import Currency\n", "", "refactor tax.py currency")
    tax.write_text(text)
    invoice = package / "invoice.py"
    text = invoice.read_text()
    text = _replace_once(text, 'def _round_money(amount: Decimal, currency: Currency) -> Decimal:\n    """Round a line amount to the currency\'s minor unit."""\n    return amount.quantize(currency.minor_unit, rounding=ROUND_HALF_EVEN)\n\n\n', "", "refactor invoice.py helper")
    text = _replace_once(text, "_round_money(self.unit_price.amount * self.quantity, self.unit_price.currency)", "quantize(self.unit_price.amount * self.quantity, self.unit_price.currency)", "refactor invoice.py line")
    text = _replace_once(text, "from .money import Money\n", "from .money import Money, quantize\n", "refactor invoice.py import")
    text = _replace_once(text, "from decimal import ROUND_HALF_EVEN, Decimal\n", "from decimal import Decimal\n", "refactor invoice.py decimal")
    text = _replace_once(text, "from .currency import Currency\n", "", "refactor invoice.py currency")
    invoice.write_text(text)


def build_refs() -> list[str]:
    fixture = FIXTURES / "invoicekit"
    for name, (filename, edits) in REFERENCE_EDITS.items():
        dest = REFS / name
        shutil.rmtree(dest, ignore_errors=True)
        shutil.copytree(fixture, dest, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        package = dest / "src" / "invoicekit"
        if name == "refactor":
            _refactor_right(package)
        for old, new in edits:
            target = package / filename
            target.write_text(_replace_once(target.read_text(), old, new, f"reference {name}"))
    return sorted(REFERENCE_EDITS)


MUTANTS = {
    # Plausible wrong or partial fixes, applied to the task's reference tree. Each must survive the original
    # suite; the tests an agent leaves behind are scored by how many they catch.
    "refund": {
        "revert": ("money.py", None),
        "remainder-on-first-part": ("money.py", [(
            "        sign = -1 if units < 0 else 1\n"
            "        units = abs(units)\n"
            "        total = sum(ratios)\n"
            "        shares = [units * ratio // total for ratio in ratios]\n"
            "        remainder = units - sum(shares)\n"
            "        for index in range(remainder):\n"
            "            shares[index] += 1\n"
            "        return [Money(Decimal(sign * share) * unit, self.currency) for share in shares]\n",
            "        total = sum(ratios)\n"
            "        shares = [int(units * ratio / total) for ratio in ratios]\n"
            "        remainder = units - sum(shares)\n"
            "        if remainder < 0:\n"
            "            shares[0] += remainder\n"
            "        for index in range(max(remainder, 0)):\n"
            "            shares[index] += 1\n"
            "        return [Money(Decimal(share) * unit, self.currency) for share in shares]\n")]),
        "sign-dropped": ("money.py", [(
            "        return [Money(Decimal(sign * share) * unit, self.currency) for share in shares]\n",
            "        return [Money(Decimal(share) * unit, self.currency) for share in shares]\n")]),
    },
    "leap": {
        "revert": ("proration.py", None),
        "every-fourth-year": ("proration.py", [(
            "    if month == 2 and year % 4 == 0 and (year % 100 != 0 or year % 400 == 0):\n",
            "    if month == 2 and year % 4 == 0:\n")]),
        "no-400-rule": ("proration.py", [(
            "    if month == 2 and year % 4 == 0 and (year % 100 != 0 or year % 400 == 0):\n",
            "    if month == 2 and year % 4 == 0 and year % 100 != 0:\n")]),
    },
    "december": {
        "revert": ("terms.py", None),
        "net-eom-path-unfixed": ("terms.py", [(
            "            return end_of_month(issued) + timedelta(days=days)\n",
            "            return date(issued.year, issued.month % 12 + 1, 1) - timedelta(days=1) + timedelta(days=days)\n")]),
        "eom-path-unfixed": ("terms.py", [(
            "        return end_of_month(issued)\n",
            "        return date(issued.year, issued.month % 12 + 1, 1) - timedelta(days=1)\n")]),
    },
    "refactor": {
        "tax-half-even": ("tax.py", [(
            "    return Money(quantize(net.amount * rate, net.currency, ROUND_HALF_UP), net.currency)\n",
            "    return Money(quantize(net.amount * rate, net.currency), net.currency)\n")]),
        "line-gross-half-up": ("invoice.py", [(
            "        amount = quantize(self.unit_price.amount * self.quantity, self.unit_price.currency)\n",
            "        amount = quantize(self.unit_price.amount * self.quantity, self.unit_price.currency, \"ROUND_HALF_UP\")\n")]),
    },
}
# The one mutant the hidden test does not catch: the remainder lands on the first part, so totals still add up.
HIDDEN_MISSES = {"refund/remainder-on-first-part"}


def unittest_run(tree: Path, *args: str) -> bool:
    env = {"PATH": "/usr/bin:/bin", "PYTHONPATH": str(tree / "src"), "PYTHONDONTWRITEBYTECODE": "1", "LANG": "C.UTF-8"}
    out = subprocess.run([sys.executable, "-B", "-m", "unittest", *args], cwd=tree, env=env, capture_output=True, text=True, timeout=300)
    return out.returncode == 0


def _with_hidden(tree: Path, test: Path, scratch: Path) -> Path:
    shutil.rmtree(scratch, ignore_errors=True)
    shutil.copytree(tree, scratch, ignore=shutil.ignore_patterns(".git", "__pycache__"))
    shutil.copy(test, scratch / test.name)
    return scratch


def build_mutants() -> dict:
    report = {}
    scratch = REFS / ".scratch"
    for task, mutants in MUTANTS.items():
        for name, (filename, edits) in mutants.items():
            dest = REFS / "mutants" / task / name
            shutil.rmtree(dest, ignore_errors=True)
            shutil.copytree(REFS / task, dest)
            target = dest / "src" / "invoicekit" / filename
            if edits is None:
                shutil.copy(FIXTURES / "invoicekit" / "src" / "invoicekit" / filename, target)
            else:
                text = target.read_text()
                for old, new in edits:
                    text = _replace_once(text, old, new, f"mutant {task}/{name}")
                target.write_text(text)
            survives = unittest_run(dest, "discover", "-s", "tests")
            caught = not unittest_run(_with_hidden(dest, DATA / "hidden" / f"hidden_{task}.py", scratch), f"hidden_{task}")
            expected_caught = f"{task}/{name}" not in HIDDEN_MISSES
            report[f"{task}/{name}"] = {"survives_original_suite": survives, "hidden_test_catches": caught,
                                        "as_frozen": survives and caught == expected_caught}
    shutil.rmtree(scratch, ignore_errors=True)
    return report


def hidden_matrix() -> dict:
    """Each bug's hidden test fails on the fixture and passes only on its own fix; the refactor test catches only the naive refactor."""
    trees = {"fixture": FIXTURES / "invoicekit", **{name: REFS / name for name in REFERENCE_EDITS}}
    scratch = REFS / ".scratch"
    matrix = {"suite_passes_everywhere": all(unittest_run(tree, "discover", "-s", "tests") for tree in trees.values())}
    for test in sorted((DATA / "hidden").glob("hidden_*.py")):
        name = test.stem.removeprefix("hidden_")
        row = {label: unittest_run(_with_hidden(tree, test, scratch), test.stem) for label, tree in trees.items()}
        if name == "refactor":
            expected = {label: label != "refactor-naive" for label in trees}
        else:
            expected = {label: label == name for label in trees}
        matrix[test.stem] = {"passes_on": sorted(label for label, ok in row.items() if ok), "as_frozen": row == expected}
    shutil.rmtree(scratch, ignore_errors=True)
    return matrix


def build(map_sources: bool = False) -> dict:
    """Everything the tasks need; with map_sources, also the repositories the map benchmarks read."""
    for folder in (SOURCES, FIXTURES, REFS):
        folder.mkdir(parents=True, exist_ok=True)
    report: dict = {"sources": [fetch(name) for name in (MAP_SOURCES if map_sources else TASK_SOURCES)]}
    report["fixtures"] = {"invoicekit": build_invoicekit(), "flask-review": build_flask_review(), "django": build_django()}
    report["judge_context"] = build_judge_context()
    report["refs"] = build_refs()
    report["hidden"] = hidden_matrix()
    report["mutants"] = build_mutants()
    try:
        report["real_bugs"] = build_real_bugs()
        report["warnings"] = []
    except (RuntimeError, OSError, subprocess.CalledProcessError) as error:
        report["real_bugs"] = {}
        report["warnings"] = [f"real-bug tasks unavailable: {error}"]
    problems = [f"fixture {name} {key}" for name, checks in report["fixtures"].items() for key, value in checks.items()
                if value is False]
    problems += [f"judge context {name} differs from the frozen text" for name, ok in report["judge_context"].items() if not ok]
    problems += [f"hidden test {name} behaves differently" for name, row in report["hidden"].items() if isinstance(row, dict) and not row["as_frozen"]]
    if not report["hidden"]["suite_passes_everywhere"]:
        problems.append("the fixture suite fails on a reference tree")
    problems += [f"mutant {name} behaves differently" for name, row in report["mutants"].items() if not row["as_frozen"]]
    problems += [f"real bug {name} {key}" for name, checks in report["real_bugs"].items() if isinstance(checks, dict)
                 for key in ("matches_frozen_commit", "fix_not_reachable", "as_frozen", "only_expected_refs", "no_remote")
                 if checks.get(key) is False]
    report["problems"] = problems
    (FIXTURES / "build.json").write_text(json.dumps(report, indent=1))
    return report


def build_pyenv(name: str) -> dict:
    dest = PYENVS / name
    stamp = dest / ".packages"
    wanted = "\n".join(PYENV_PACKAGES[name])
    if not (stamp.exists() and stamp.read_text() == wanted):
        shutil.rmtree(dest, ignore_errors=True)
        dest.mkdir(parents=True)
        out = subprocess.run([sys.executable, "-m", "pip", "install", "-q", "--disable-pip-version-check", "--no-input",
                              "--no-deps", "--only-binary=:all:", "--target", str(dest), *PYENV_PACKAGES[name]],
                             capture_output=True, text=True)
        if out.returncode:
            raise RuntimeError(f"pip could not install the {name} test dependencies: {out.stderr.strip()[-400:]}")
        project, version = PYENV_PROJECT[name]
        meta = dest / f"{project}-{version}.dist-info"
        meta.mkdir()
        (meta / "METADATA").write_text(f"Metadata-Version: 2.1\nName: {project}\nVersion: {version}\n")
        stamp.write_text(wanted)
    return {"pyenv": name, "packages": len(PYENV_PACKAGES[name])}


def pytest_env(tree: Path, pyenv: str) -> dict:
    return {"PATH": "/usr/bin:/bin", "PYTHONPATH": f"{PYENVS / pyenv}:{tree / 'src'}", "PYTHONDONTWRITEBYTECODE": "1",
            "LANG": "C.UTF-8", "HOME": str(tree)}


def pytest_probe(tree: Path, pyenv: str, *args: str) -> dict:
    out = subprocess.run([sys.executable, "-B", str(BENCH / "probe_pytest.py"), *args], cwd=tree, env=pytest_env(tree, pyenv),
                         capture_output=True, text=True, timeout=900)
    try:
        return json.loads(out.stdout.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError):
        return {"probe_error": (out.stderr or out.stdout)[-500:]}


def pytest_suite(tree: Path, pyenv: str) -> dict:
    out = subprocess.run([sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider"], cwd=tree,
                         env=pytest_env(tree, pyenv), capture_output=True, text=True, timeout=1200)
    lines = out.stdout.strip().splitlines()
    return {"ok": out.returncode == 0, "summary": lines[-1] if lines else (out.stderr or "")[-300:]}


def compose(base: Path, src_from: Path, tests_from: Path, dest: Path) -> Path:
    """The base project with src/ from one tree and tests/ from another."""
    shutil.rmtree(dest, ignore_errors=True)
    top = lambda folder, names: [n for n in names if n in (".git", "__pycache__") or Path(folder) == base and n in ("src", "tests")]  # noqa: E731
    shutil.copytree(base, dest, symlinks=True, ignore=top)
    for part, origin in (("src", src_from), ("tests", tests_from)):
        shutil.copytree(origin / part, dest / part, symlinks=True, ignore=shutil.ignore_patterns("__pycache__"))
    return dest


def build_real(name: str) -> dict:
    source, fix = REAL_BUGS[name]
    dest = FIXTURES / name
    shutil.rmtree(dest, ignore_errors=True)
    shutil.copytree(SOURCES / source, dest, symlinks=True)
    parent = _git(dest, "rev-parse", f"{fix}^")
    _git(dest, "checkout", "-q", "-B", "main", parent)
    keep = {"refs/heads/main"}
    scrub(dest, keep)
    checks = leak_checks(dest, keep)
    checks["matches_frozen_commit"] = checks["head"] == parent
    checks["fix_not_reachable"] = subprocess.run(["git", "-C", str(dest), "cat-file", "-e", f"{fix}^{{commit}}"],
                                                 capture_output=True).returncode != 0
    ref = REFS / "real" / name
    shutil.rmtree(ref, ignore_errors=True)
    (ref / "fix").mkdir(parents=True)
    archive = subprocess.run(["git", "-C", str(SOURCES / source), "archive", "--format=tar", fix, "src", "tests"],
                             capture_output=True, check=True).stdout
    subprocess.run(["tar", "-x", "-C", str(ref / "fix")], input=archive, check=True)
    pyenv = source
    scratch = ref / ".scratch"
    before = pytest_probe(compose(dest, dest, dest, scratch / "fixture"), pyenv, "list")
    after = pytest_probe(compose(dest, dest, ref / "fix", scratch / "fix-tests"), pyenv, "list")
    hidden = [i for i in after.get("ids", []) if i not in before.get("ids", [])]
    on_parent = pytest_probe(compose(dest, dest, ref / "fix", scratch / "parent"), pyenv, "run", *hidden)
    on_fix = pytest_probe(compose(dest, ref / "fix", ref / "fix", scratch / "fixed"), pyenv, "run", *hidden)
    suite = pytest_suite(scratch / "fixture", pyenv)
    shutil.rmtree(scratch, ignore_errors=True)
    (ref / "hidden.json").write_text(json.dumps({"ids": hidden, "fixture_info": before}, indent=1))
    checks.update({
        "hidden_tests": len(hidden), "fixture_suite_passes": suite["ok"], "fixture_suite": suite["summary"],
        "hidden_fail_on_parent": sum(1 for status in on_parent.values() if status != "pass"),
        "hidden_pass_on_fix": all(status == "pass" for status in on_fix.values()) and bool(hidden),
    })
    checks["as_frozen"] = bool(checks["hidden_fail_on_parent"] and checks["hidden_pass_on_fix"] and suite["ok"])
    return checks


def build_real_subset(names: list[str]) -> dict:
    """Fetch, install and check only the named real bugs; for adding bugs while other fixtures are in use."""
    unknown = [name for name in names if name not in REAL_BUGS]
    if unknown:
        raise SystemExit(f"unknown real bugs: {', '.join(unknown)}")
    sources = sorted({REAL_BUGS[name][0] for name in names})
    for folder in (SOURCES, FIXTURES, REFS):
        folder.mkdir(parents=True, exist_ok=True)
    for source in sources:
        fetch(source)
        build_pyenv(source)
    return {name: build_real(name) for name in names}


def build_real_bugs() -> dict:
    report = {"pyenvs": [build_pyenv(name) for name in PYENV_PACKAGES]}
    for name in REAL_BUGS:
        report[name] = build_real(name)
    return report

