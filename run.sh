while true
do
    git pull
    poetry update
    poetry install
    python -m bot
done
