# Linac - Model

This is the source code for a school project about a linear accelerator model.

## 🧩 Structure and Prerequesites

### 1. RaspberryPi setup.
This project is meant to run on a RaspberryPi. In this case the Pi5 was used.
The only special requirement is to enable the PWM overlay by adding `dtoverlay=pwm-2chan` to `/boot/firmware/config.txt`.

### 2. Backend

The project uses a python [fastapi](https://fastapi.tiangolo.com/) backend, handling the RaspberryPis GPIO and logic of the linac.
The backend can be found inside `/backend`.

Python and all of the necessary dependencies are managed using [pdm](https://pdm-project.org/latest/).

### 3. Frontend
To visualize and controll the model, a frontend was made using nuxt (vue).
The frontend can be found inside `/frontend`.

The javascript project is managed using [bun](https://bun.sh/) as package manager and runtime.


## 💻 Development


For a remote dev environment, it's possible to only start the backend on the Raspberry and run the frontend on the local machine.

To start the frontend dev-server
```sh
cd nuxt
# configure nuxt config to point to ip of py (`hostname -I`)
bun install
bun dev # runs frontend dev-server
```

to start the backend dev-server run the following:
Note: Might need to disable the autostarted linac.service via `sudo systemctl stop linac.service` (see below).

```sh
cd backend
pdm install
pdm dev # runs backend dev-server
```


## 🚀 Building and Running

```sh
cd nuxt
bun install
bun generate

cd ../backend
pdm install
pdm start
```

### ⚙️ Setup Autostart
To make the application start automatically, as the rpi starts, 
copy (and possibly modify) the following contents onto the py at `/etc/systemd/system/linac.service`.

```ini
[Unit]
Description=Starts Linac Model Webserver
After=network.target

[Service]
ExecStart=/home/pi/.local/bin/pdm dev
WorkingDirectory=/home/pi/linac/backend
StandardOutput=inherit
StandardError=inherit
Restart=always
User=pi

[Install]
WantedBy=multi-user.target
```

```sh
# to make it load after system boot
sudo systemctl enable linac.service

# start it now without rebooting
sudo systemctl start linac.service 

# check if everything worked
sudo systemctl status linac.service 
```


#### Making it run on port 80
To expose the application on port 80, install a reverse proxy like nginx or caddy:

```
sudo apt install caddy
```

then (create and) edit `/etc/caddy/Caddyfile` to be:

```caddyfile
:80 {
    reverse_proxy localhost:8080
}
```

```sh
# restart caddy to apply changes
sudo systemctl restart caddy
```

