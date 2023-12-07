SCRIPT_DIR=$(dirname $0)
VENV_DIR=$SCRIPT_DIR/.venv/digsim_app

if [ ! -f $VENV_DIR/digsim_installed ]; then
    echo "Creating virtual environment"
    python3 -m venv $VENV_DIR
    source $VENV_DIR/bin/activate
    pip3 install pip --upgrade
    pip3 install .
    touch $VENV_DIR/digsim_installed
else
    echo "Virtual environment already created"
    source $VENV_DIR/bin/activate
fi

echo "Starting DigSim application"
python3 -m digsim.app $@
