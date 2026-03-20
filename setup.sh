pip install -r requirements.txt
if which apt &> /dev/null; then
    sudo apt install -y ffmpeg curl aria2c
else
    echo "cannot run this program on your system"
    exit
fi
curl -fsSL https://deno.land/install.sh | sh