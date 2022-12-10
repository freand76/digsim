import nox

BLACK_SPEC = "black>=22.3.0"
ISORT_SPEC = "isort==5.6.3"


@nox.session
def reformat(session):
    session.install(
        BLACK_SPEC,
        ISORT_SPEC,
    )
    session.run("python", "-m", "black", ".")
    session.run("python", "-m", "isort", ".")
