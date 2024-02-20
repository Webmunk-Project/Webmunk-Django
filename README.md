# Webmunk Data Collection Server

This repository contains the *data collection server component* used in Webmunk projects.

*Webmunk* is a platform conducting browser-based research studies that allow investigators to passively gather user bahavior on the web, as well as implement interventions that change participants' web experience to test research hypotheses.

Full Webmunk deployments consist of three main technical components:

* A web browser extension that the installs in their local browser.  ([Webmunk-Extension](https://github.com/Webmunk-Project/Webmunk-Extension))
* An enrollment server that manages participant sign-ups and assignments to experimental arms or configurations. ([Webmunk-Enrollment-App](https://github.com/Webmunk-Project/Webmunk-Enrollment-App))
* A data collection server that receives de-identified data from Webmunk extensions and provides tools for monitoring and exporting the gathered observations.

This repository contains this last component in the Webmunk architecture. For more information and specifics about the other components, visit the respective repositories linked above.


## Data Collection Server Design

The Webmunk data collection server (DCS) is designed to receive de-identitified data from Webmunk browser extensions in order to separate study data from personally-identifiable information in the interests of overall information security and preserving participant privacy.

When a partipant begins a Webmunk study, their browser extension may request personal information to identify the participant, and the enrollment server either creates a new random identifier for the participant or retrieves an existing one if the participant has already enrolled. (This allows participants to reinstall a Webmunk extension and continue participating, as well as participate across devices by installing the extension on all of their web browsing devices.)

When the extension transmits data to the DCS, only the participant identifier is sent to identify the source of the transmission - the extension itself discards the personal information used for lookup as soon as it retrieves a participant identifier.

The DCS is built on [the Passive Data Kit Django platform](https://github.com/audacious-software/PassiveDataKit-Django/) (PDK) in order to leverage the existing data collection and processing infrastructure that has been deployed across observational and experimental studies for almost a decade. Investigators seeking to deploy Webmunk for their own studies are **strongly** encouraged to review the PDK documentation and [the Django web application framework](https://www.djangoproject.com/start/) used by PDK. The Webmunk DCS builds heavily on both platforms and uses conventions, techniques, and tools native to both.


## Prerequisites

The DCS has been developed primarily on Unix-like platforms and assumes the existence of tools such as CRON ob scheduling and the Apache web server. DCS instances expose publicly-facing web interfaces for management and data collection, so a server with a publicly-addressable IP address (or suitable web application firewall that forwards traffic to the DCS) is required. 

The DCS targets currently-supportred LTS releases of Django (3.2.X, 4.2.X). It requires Python 3.6 and newer.

In addition to Django, the DCS relies extensively on the Postgres database support included with Django, including the PostGIS extensions needed to enable spatial data types within Postgres. The DCS requires Postgres 9.5 and newer.

To make your DCS server accessible to outside Webmunk clients, we typically configure Django with the Apache 2 webserver, using [mod_wsgi](https://modwsgi.readthedocs.io/) to facilitate communication between the front-end Apache web server and the Python application server. Typically, the bundled Apache server and mod_wsgi module that comes with your Unix distribution is more than sufficient to support Django.

The DCS server assumes that local users are able to set up and run CRON jobs. In addition to the standard background jobs provided by PDK ([more details here](https://github.com/audacious-software/PassiveDataKit-Django/#background-jobs-setup)), the DCS adds several additional jobs for tasks such as extracting Amazon ASIN identifiers from the data sent by browsers and generating nightly data export jobs that bundle the past day's data collection into a form suitable for study monitoring and analysis.

*Note that many of these tasks (such as compiling a large data report) will often run longer than the typical request timeout window web servers or clients will tolerate, so chaining these requests to HTTP endpoints that are triggered by an outside polling service **will not** be sufficient for these purposes as a CRON substitute.*


## Installation

If you are operating in an environment that fulfills all of the requirements above, the first step to get started is to install the Django web application framework with Postgres and PostGIS enabled by cloning repository:

1. **(Strongly Recommended)** Before installing the DCS, [create a Python virtual environment](https://docs.python.org/3/library/venv.html) that will contain the local Python environment and all of the relevant dependencies separate from your host platform's own Python installation. Don't forget to activate your virtual environment before continuing!

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
    $ psql webmunk_study
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

    Open the new `local_settings.py` file and [follow the configuration instructions](/support/documentation/settings.md) to configure the server.
    
6. Once the server has been configured, initialize the database:

    ```$ ./manage.py migrate```

    Copy the static resource files to the appropriate location:

    ```$ ./manage.py collectstatic```

    Create a new superuser account to login to the server:

    ```$ ./manage.py createsuperuser```

7. Next, [configure your local Apache HTTP server](https://docs.djangoproject.com/en/3.2/howto/deployment/wsgi/modwsgi/) to connect to Django.

    We **strongly recommend** that your configure Django to be served over HTTPS ([obtain a Let's Encrypt certificate if needed](https://letsencrypt.org/)) and to forward any unencrypted HTTP requests to the HTTPS port using a `VirtualHost` definition like:

    ````
    <VirtualHost *:80>
        ServerName myserver.example.com

        RewriteEngine on
        RewriteRule    ^(.*)$    https://myserver.example.com$1    [R=301,L]
    </VirtualHost>
    ````

8. Once Apache is configured and running, login to the Django administrative backend using the user credentials created above: 

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

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

[http://www.apache.org/licenses/LICENSE-2.0](http://www.apache.org/licenses/LICENSE-2.0)

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
