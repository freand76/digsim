import os

import nox


@nox.session
def reformat(session):
    session.install(
        "black==22.12.0",
        "isort==5.6.3",
    )
    session.run("python", "-m", "black", ".")
    session.run("python", "-m", "isort", ".")


@nox.session
def lint(session):
    session.install(
        "typing-extensions==4.4.0",
        "pylint==2.15.9",
    )
    session.run(
        "python",
        "-m",
        "pylint",
        "digsim/.",
    )
