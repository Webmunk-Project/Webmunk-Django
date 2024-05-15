# Webmunk Data Collection Server

This repository contains the *data collection server component* used in Webmunk projects.

*Webmunk* is a platform conducting browser-based research studies that allows investigators to passively gather user behavior on the web, as well as implement interventions that change participants' web experience to test research hypotheses.

Full Webmunk deployments consist of three main technical components:

* A web browser extension that installs on the participant's local browser.  ([Webmunk-Extension](https://github.com/Webmunk-Project/Webmunk-Extension))
* An enrollment server that manages participant sign-ups, assignments to experimental arms or configurations, and communicates with the data collection server or servers. ([Webmunk-Enrollment-App](https://github.com/Webmunk-Project/Webmunk-Enrollment-App))
* A data collection server that receives de-identified data from Webmunk extensions and provides tools for monitoring and exporting the gathered observations.

This repository contains this last component in the Webmunk architecture, which is likely the first one you will install when you set up your first Webmunk project. For more information and specifics about the other components, visit the respective repositories linked above.


## Data Collection Server Design

The Webmunk data collection server (DCS) is designed to receive de-identified data from Webmunk browser extensions to separate study data from personally-identifiable information in the interests of overall information security and preserving participant privacy.

When a participant begins a Webmunk study, their browser extension may request personal information to identify the participant, and the enrollment server either creates a new random identifier for the participant or retrieves an existing one if the participant has already enrolled. (This allows participants to reinstall a Webmunk extension and continue participating, or to participate across devices by installing the extension on all of their web browsing devices.)

When the extension transmits data to the DCS, only the participant identifier is sent to identify the source of the transmission - the extension itself discards the personal information used for lookup as soon as it retrieves a participant identifier.

The DCS is built on [the Passive Data Kit Django platform](https://github.com/audacious-software/PassiveDataKit-Django/) (PDK) to use existing data collection and processing infrastructure that has powered observational and experimental studies for many years. Investigative teams seeking to deploy Webmunk for their studies are **strongly** encouraged to review the PDK documentation and [the Django web application framework](https://www.djangoproject.com/start/) used by PDK. The Webmunk DCS builds heavily on both platforms and uses conventions, techniques, and tools native to both.

## Prerequisites

A Unix-like OS with access to root/sudo: 
* CRON
* Python 3.6+
* Apache2 web server with [mod_wsgi](https://modwsgi.readthedocs.io/)
* A domain name with an SSL certificate that is pointed to a publicly-addressable IP address (or suitable web application firewall that forwards traffic to the DCS)
* Postgres database 9.5+ with PostGIS extensions

Typically, the bundled Apache server and mod_wsgi module that comes with your Unix distribution will support Django.

In addition to the standard background jobs provided by PDK ([more details here](https://github.com/audacious-software/PassiveDataKit-Django/#background-jobs-setup)), the DCS adds several additional jobs for tasks such as extracting Amazon ASIN identifiers from the data sent by browsers and generating nightly data export jobs that bundle the past day's data collection into a form suitable for study monitoring and analysis.

*Note that many of these tasks (such as compiling a large data report) will often run longer than the typical request timeout window web servers or clients will tolerate, so chaining these requests to HTTP endpoints that are triggered by an outside polling service **will not** be sufficient for these purposes as a CRON substitute.*


## Installation

1. Verify that your system meets the requirements above and install any needed components. *This example provides commands for a Debian-Ubuntu based OS*. Any Linux-based OS will be conceptually similar, but will require different syntax.
   * Make sure you have sudo access `sudo echo "Sudo access confirmed"`
   * Verify your public IP or Domain: `curl ifconfig.me`
   * Update your OS package manager, e.g. `sudo apt update`
   * Verify Cron access `sudo systemctl status cron`
   * Check your Python version `python3 --version`
   * The following are basic utilities you will need that may not be included in a fresh installation.
     ```
     sudo apt install python3-pip
     sudo apt-get install dialog
     sudo apt-get install apt-utils
     sudo apt install git
     sudo apt install python3-venv
     ```
   * Verify that you have Postgres 9.5+ and the PostGIS extension (this extension is needed to setup Webmunk, whether or not you plan to collect geographic information).
     ```
     psql --version
     sudo -u postgres psql -c "SELECT PostGIS_Version();" # change postgres to your database user if different
     ```
   * Verify that you have Apache2 with [mod_wsgi](https://modwsgi.readthedocs.io/)
     ```
     apache2 -v
     sudo apachectl -M | grep wsgi
     ```

1. **(Strongly Recommended)** Before installing the DCS, [create a Python virtual environment](https://docs.python.org/3/library/venv.html) that will contain the local Python environment and all of the relevant dependencies separate from your host platform's own Python installation. *Do not put this virtual environment in your home directory, which is not accessible to Apache*, a suggestion is to create a directory such as `/var/www/venvs/dcs` to put it in. then create it once you are in the appropriate directory `python3 -m venv myvenv`  Don't forget to activate your virtual environment before continuing (and every time you make changes)! e.g. `source /var/www/venvs/dcs/myvenv/bin/activate`

2. Clone this repository to a suitable location on your server:

    ```
    $ git clone https://github.com/Webmunk-Project/Webmunk-Django.git /var/www/webmunk
    $ cd /var/www/webmunk
    ```

    Initialize the Git submodules:

    ```
    git submodule init
    git submodule update
    ```

3. Create a suitable Postgres database as the local `postgres` (or equivalent) user:

    ```
    $ sudo su - postgres
    $ psql
    postgres=# CREATE USER webmunk WITH PASSWORD 'XXX' LOGIN;
    postgres=# CREATE DATABASE webmunk_data WITH OWNER webmunk;
    postgres=# exit
    ```

    (Replace `XXX` with a strong password.)

    After the database has been created, enable the PostGIS extension:

    ```
    $ psql webmunk_data
    postgres=# CREATE EXTENSION postgis;
    postgres=# exit
    ```

    After the PostGIS extension has been enabled, you may log out as the local `postgres` user.

4. Back in the DCS directory, install the Python dependencies:

    ```
    $ pip install wheel
    $ pip install -r requirements.txt
    ```

    Installing the `wheel` package before the rest of the Python dependencies allow the system to use pre-compiled packages, which may save signicant time spent building Python modules and tracking down all of the system-level dependencies and development libraries needed.

5. Install and configure the `local_settings.py` file:

    ```
    $ cp webmunk/local_settings.py-template webmunk/local_settings.py
    ```

    Open the new `local_settings.py` file and [follow the configuration instructions within the file](/webmunk/local_settings.py-template) to configure the server.
    
6. Once the server has been configured, initialize the database:

    ```$ ./manage.py migrate```

    Copy the static resource files to the appropriate location:

    ```$ ./manage.py collectstatic```

    Create a new superuser account to login to the server:

    ```$ ./manage.py createsuperuser```

7. If  you are not familiar with setting up an Apache2 website, see [this basic tutorial](https://ubuntu.com/tutorials/install-and-configure-apache#1-overview), if you are not using Ubuntu, there are similar tutorials for different Linux distributions. Make sure Apache is running properly by using `systemctl status apache2`
8. Next, [configure your local Apache HTTP server](https://docs.djangoproject.com/en/3.2/howto/deployment/wsgi/modwsgi/) to connect to Django.

    Your must configure Django to be served over HTTPS ([obtain a Let's Encrypt certificate if needed](https://letsencrypt.org/)) and to forward any unencrypted HTTP requests to the HTTPS port using a `VirtualHost` definition like:

    ````
    <VirtualHost *:80>
        ServerName myserver.example.com

        RewriteEngine on
        RewriteRule    ^(.*)$    https://myserver.example.com$1    [R=301,L]
    </VirtualHost>
    ````

9. Change the postgres configuration to allow for password-based access by Django:
```
sudo nano /etc/postgresql/14/main/pg_hba.conf
```

Change the line from something like this:
```
# TYPE DATABASE USER ADDRESS METHOD 
local all all peer
```
to:
```
# TYPE DATABASE USER ADDRESS METHOD 
local all all md5
```
Then restart postgres
```
sudo systemctl restart postgresql
```
10. Once Apache is configured and running, login to the Django administrative backend using the user credentials created above: 

    `https://myserver.example.com/admin/` (Replace `myserver.example.com` with your own host's name.) 
    
Congratulations, you are almost finished installing the Webmunk data collection server.


## Background Jobs Setup

Before your site is ready for use by clients, we have one more **very** important step to complete: setting up the background CRON jobs. Before continuing here, follow [the instructions for Passive Data Kit](https://github.com/audacious-software/PassiveDataKit-Django/#background-jobs-setup). Once you have completed those steps, you will be ready to install the Webmunk-specific processing jobs.

On to the Webmunk-specific background jobs...


### webmunk_fetch_amazon_asin_items

`*/5 * * * *    source /var/www/venv/bin/activate && python /var/www/myproject/manage.py webmunk_fetch_amazon_asin_items`

This job inspects new data received every 5 minutes and creates new `AmazonASINItem` objects for ASIN identifiers not yet logged. This job scans both Amzon order data points (`webmunk-amazon-order`) and logged HTML content (`element-content` fields located in the various webmunk data points) to identify Amazon items both ordered and observed by the web browser extension on the page.


### webmunk_populate_amazon_asin_items_keepa

`* * * * *    source /var/www/venv/bin/activate && python /var/www/myproject/manage.py webmunk_populate_amazon_asin_items_keepa`

This job attempts to populate the Amazon metadata (product name, price, brand, etc.) of `AmazonASINItem` objects by using [the Keepa API](https://keepa.com/). This job stores the full metadata retrieved (including price histories) as part of the `AmazonASINItem` objects for future export and analysis.  


### webmunk_create_nightly_export_job

`30 5 * * *    source /var/www/venv/bin/activate && python /var/www/myproject/manage.py webmunk_create_nightly_export_job`

This job generates a nightly PDK report job that is uploaded to cloud storage for additional analysis. This report job includes the following exported data types:

* `pdk-external-amazon-item`
* `webmunk-extension-class-added`
* `webmunk-extension-element-click`
* `webmunk-extension-matched-rule`
* `webmunk-extension-element-show`
* `webmunk-extension-element-hide`
* `webmunk-extension-log-elements`
* `webmunk-extension-scroll-position`
* `webmunk-visibility-export`
* `webmunk-extension-action`
* `webmunk-amazon-order`
* `webmunk-local-tasks`

A full example of the CRON file is available here: [Example Crontab](support/documentation/example.crontab).

## License and Other Project Information

Copyright 2022-2024 The Fradkin Foundation and the President & Fellows of Harvard College

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
