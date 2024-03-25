/bin/sleep 5

source $HOME/.bashrc
source $HOME/.profile

tmux kill-session -t vrcp
/usr/bin/tmux new-session -d -s vrcp 

cd $HOME/vrcPosterSystemv2

# /usr/bin/tmux send-keys -t vrcp "cd ./vrcp" C-m
/usr/bin/tmux send-keys -t vrcp "docker container stop vrcp" C-m
/usr/bin/tmux send-keys -t vrcp "docker container rm vrcp" C-m
/usr/bin/tmux send-keys -t vrcp "docker run -it --user "$(id -u):$(id -g)" --name vrcp --workdir /app -v "$(pwd)":/app vrcp:latest python3 src/discord.py" C-m

