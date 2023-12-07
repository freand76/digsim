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
        "typing-extensions==4.8.0",
        "pylint==3.0.2",
        "flake8-pyproject==1.2.3",
        "flake8==6.1.0",
    )
    session.run(
        "python",
        "-m",
        "pylint",
        "src",
        "tests",
        "examples",
    )
    session.run("python", "-m", "flake8")


@nox.session
def test(session):
    session.install(
        "pytest==7.2.0",
    )
    session.run(
        "python",
        "-m",
        "pip",
        "install",
        ".",
    )
    session.run("pytest", "tests/")
