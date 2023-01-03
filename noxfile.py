import nox

BLACK_SPEC = "black>=22.3.0"
ISORT_SPEC = "isort==5.6.3"
PYLINT_SPEC = "pylint==2.15.9"


@nox.session
def reformat(session):
    session.install(
        BLACK_SPEC,
        ISORT_SPEC,
    )
    session.run("python", "-m", "black", ".")
    session.run("python", "-m", "isort", ".")


@nox.session
def lint(session):
    session.install(
        PYLINT_SPEC,
    )
    session.run(
        "python",
        "-m",
        "pylint",
        "digsim/.",
        "-d",
        "missing-class-docstring",
        "-d",
        "missing-module-docstring",
        "-d",
        "missing-function-docstring",
        "-d",
        "no-member",
        "-d",
        "invalid-name",
    )
