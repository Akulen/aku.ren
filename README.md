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

## Initialize the database

```bash
flask shell
```
```python
from app import *
db.drop_all()
db.create_all()
```

## Update the database structure

Use this when the database structure was changed

```bash
flask db migrate -m "<Migration message>"
```

And this to apply the changes

```bash
flask db upgrade
```

## Add an element to the database

```bash
flask shell
```
```python
from app import *
cookie = Algo(name="ccgarden", short_title="Cookie Clicker Garden", title="Maximal number of unmarked cells with at least 3 marked neighboring cells in the n X n kings' graph", content='''{{ code('cookie.py') }}

<p>
Time complexity: \(O(m 2^{3n})\)<br />
There is a solution in \(O(nm 2^{2n+3})\)
The resulting sequences for \(N\\times N\) grids and \(N\\times(N+1)\) grids can be found at ??? and ???
</p>''')
db.session.add(cookie)
db.session.commit()
```

## Running the server for development

```bash
flask run
```
