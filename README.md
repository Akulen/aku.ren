# Aku.Ren

My personal website, available at [aku.ren](https://aku.ren/)

## Installing

After cloning this repo, run these commands to install the venv
```bash
python -m venv venv
. venv/bin/activate
pip install -r requirements.txt
```

You should probably also run the CV submodule to populate the publications and CV pages
```bash
cd CV
make pdf
make html
make clean
```

## Configuring the server

For an apache2 server on debian, mod_wsgi is required.

The VirtualHost must be setup to use a WSGI Daemon, and that daemon must use
the previously created venv, and point to `./app.wsgi`

Then, edit `./app.wsgi` and change the path and secret key.

## Running the server for development

```bash
flask run
```
