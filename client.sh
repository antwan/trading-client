#!/bin/bash

DOCKER_SHELL="docker run --rm -it -v "$(pwd)"/logs:/app/logs app bash"
[ $# -lt 1 ] && echo "Usage: $0 command args" && exit 1
cmd="$1"; shift

# Installs container if required
[ $( docker images -q app ) ] && [ $cmd != "rebuild" ] || docker build -t app .

# Runs command in container
if [ $cmd = "run" ] ; then
    $DOCKER_SHELL -c "python -m src.app $*"

elif [ $cmd = "test" ] ; then
    $DOCKER_SHELL -c "python -m unittest tests"

elif [ $cmd = "shell" ] ; then
    $DOCKER_SHELL -c "python"

elif [ $cmd = "clean" ] ; then
    docker image rm app

elif [ $cmd != "rebuild" ] ; then
    echo "$cmd: invalid command"
    exit 1
fi