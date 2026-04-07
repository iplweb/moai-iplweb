# MOAI — Open Access Server Platform for Institutional Repositories

[![Tests](https://github.com/iplweb/moai-iplweb/actions/workflows/test.yml/badge.svg)](https://github.com/iplweb/moai-iplweb/actions/workflows/test.yml)

MOAI is a platform for aggregating content from different sources and publishing it through the [Open Archive Initiative Protocol for Metadata Harvesting](http://www.openarchives.org/pmh/) (OAI-PMH). It can harvest data from various sources — OAI feeds, SQL databases, XML files, Fedora Commons, EPrints, DSpace — and serve multiple OAI feeds from a single server, each with independent configuration.

<p align="center">
  <b>Support graciously provided by</b><br><br>
  <a href="https://www.iplweb.pl"><img src="https://www.iplweb.pl/images/ipl-logo-large.png" width="150" alt="IPL Web"></a>
</p>

## About this fork

This is a maintained fork of [MOAI by Infrae](https://github.com/infrae/moai/), adding Python 3 support, modern packaging (`pyproject.toml`, `uv`), and GitHub Actions CI. Changes were offered upstream via [PR #5](https://github.com/infrae/moai/pull/5).

> **Note:** Other than modernizing the tooling, there are no major functional changes. Some parts of the documentation below may be outdated. Patches welcome.

## Installation

MOAI is a normal Python package. It is tested with Python 3.9, 3.10, 3.11, 3.12, 3.13.
We recommend using [uv](https://docs.astral.sh/uv/) for dependency management.

Instructions below are for Unix, but MOAI should also work on Windows.

Install MOAI using uv:

```bash
cd moai
uv sync
```

To run tests:

```bash
uv sync --extra test
uv run pytest
```

## Running in development mode

The development server should never be used in production. It is convenient for testing and development.

```bash
cd moai
uv run paster serve settings.ini
```

This will print something like:

```
Starting server in PID 7306.
Starting HTTP server on http://127.0.0.1:8080
```

You can now visit `localhost:8080/oai` to view the MOAI OAI-PMH feed.

## Configuring MOAI

Configuration is done in the `settings.ini` file. The default settings file uses the `Paste#urlmap` application to map WSGI applications to a URL.

In the `[composite:main]` section there is a line:

```
/oai = moai_example
```

Which maps the `/oai` URL to a MOAI instance. This makes it easy to run many MOAI instances in one server, each with its own configuration.

The `[app:moai_example]` configuration lets you specify the following options:

| Option | Description |
|--------|-------------|
| `name` | The name of the OAI feed (returned in Identify verb) |
| `url` | The URL of the OAI feed (returned in OAI-PMH XML output) |
| `admin_email` | The email address of the admin (returned in Identify verb) |
| `formats` | Available metadata formats |
| `disallow_sets` | List of setspecs that are not allowed in the output of this feed |
| `allow_sets` | If used, only sets listed here will be returned |
| `database` | SQLAlchemy URI to identify the database used for storage |
| `provider` | Provider identifier where MOAI retrieves content from |
| `content` | Class that maps metadata from provider format to MOAI format |

## Adding content

The MOAI system is designed to periodically fetch content from a *provider*, and convert it to MOAI's internal format, which can then be translated to the different metadata formats for the OAI-PMH feed.

MOAI comes with an example that shows this principle:

In the `moai/moai` directory there are two XML files. Let's pretend these files are from a remote system, and we want to publish them with MOAI.

In the `settings.ini` file, the following option is specified:

```
provider = file://moai/example-*.xml
```

This tells MOAI that we want to use a file provider, with some files located in `moai/example-*.xml`.

The following option points to the class that we want to use for converting the example content XML data to MOAI's internal format:

```
content = moai_example
```

The last option tells MOAI where to store its data, this is usually a SQLite database:

```
database = sqlite:///moai-example.db
```

Now let's try to add these two XML files. First visit the OAI-PMH feed to make sure nothing is already being served:

```
http://localhost:8080/oai?verb=ListRecords&metadataPrefix=oai_dc
```

This should return a `noRecordsMatch` error.

To add the content, run the `update_moai` script with the section name from the `settings.ini` as argument:

```bash
uv run update_moai moai_example
```

This will produce the following output:

```
/ Updating content provider: example-2345.xml
Content provider returned 2 new/modified objects

100.0%[====================================================================>] 2
Updating database with 2 objects took 0 seconds
```

Now when you visit the OAI-PMH feed again you should see the two records:

```
http://localhost:8080/oai?verb=ListRecords&metadataPrefix=oai_dc
```

When you run the `update_moai` script again, it will create a new database with all the records. It is also possible to specify a date with the `--date` switch. When a date is specified, only records that were modified after this date will be added. The `update_moai` script can be run from a daily or hourly cron job to update the database.

## Adding your own Provider / Content and Metadata classes

It's possible — and most of the time, needed — to extend MOAI for your use-cases. The Provider and Content classes from the example might be a good starting point. All your customizations should be registered with MOAI through `entry_points`. Have a look at MOAI's `pyproject.toml` for more information.

The best approach would be to create your own Python package with `pyproject.toml` and install it in the same environment as MOAI. This will let MOAI find your customizations. Note that when you change something in your package metadata, you have to reinstall the package for MOAI to pick up the changes.

The `moai.interfaces` file contains documentation about the different classes that you can implement.

## Adding your own database

Instead of writing your own provider/content classes, you can also register your own custom database. Implementing a replacement for `moai.database.SQLDatabase` can be more complicated than writing a provider/content class, but it has the advantage that MOAI is always up to date and you don't need a second SQLite database.

Have a look at the `pyproject.toml` file — it registers several databases. You could use this mechanism to register your own database from your own Python package.

In the `settings.ini` configuration you can then reference your database (`mydb://some+config+variables`).

For the database, have a look at the generic database provider in `database.py`. The only methods that you need to implement are: `oai_sets`, `oai_earliest_datestamp` and `oai_query`.

The `oai_query` method returns dictionaries with record data. The keys of these dictionaries are defined in the metadata files (for example `metadata.py`) — have a look at the source.

For `oai_dc` there are the following names:

`title`, `creator`, `subject`, `description`, `publisher`, `contributor`, `type`, `format`, `identifier`, `source`, `language`, `date`, `relation`, `coverage`, `rights`

So a return value would look like:

```python
{'id': '<oai record id>',
 'deleted': '<bool>',
 'modified': '<utc datetime>',
 'sets': ['<list of setspecs>'],
 'metadata': {
   'title': ['<list with publication title>'],
   'creator': ['<list of creator names>'],
   ...}
}
```
