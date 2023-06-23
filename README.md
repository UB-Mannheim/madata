# madata

[![PyPI version](https://badge.fury.io/py/madata.svg)](https://badge.fury.io/py/madata)

`madata` syncs the metadata of datasets between [MADATA](https://madata.bib.uni-mannheim.de) (Mannheim Data Repository) and [Wikidata](https://www.wikidata.org). It provides access to the MADATA metadata records directly in Python.

## Table of contents
* [Installation](#installation)
* [Initialization](#initialization)
* [Syncing](#syncing)
* [SPARQL queries](#sparql-queries)

## Installation

```
pip install madata
```

or

```
git clone https://github.com/UB-Mannheim/madata
cd madata/
pip install .
```

## Initialization

By initialization `madata` harvests the MADATA OAI-PMH interface, stores the Dublin Core metadata records in `records.OAI_DC` and queries the Wikidata SPARQL endpoint for the list of metadata records published at MADATA.
 Example:

```python
from madata import Metadata
records = Metadata()
print(records)
[('OAI', 'https://madata.bib.uni-mannheim.de/cgi/oai2'),
 ('MADATA records from OAI-PMH', 163),
 ('MADATA records at Wikidata', 1),
 ('In sync?', False)]
```

Every record `rec` in the the list `records.OAI_DC`has the following attributes: `rec.metadata` (structured metadata record), `rec.header` (structured header for a metadata record) and `rec.raw` (raw DC metadata record). The raw header is available via `rec.header.raw`. Additionally, a pandas-dataframe with metadata records is stored in `records.OAI_DC_df`.

## Syncing

In order to upload the MADATA metadata records to Wikidata, you need an account at Wikidata. If you have an account, use
```python
from madata import Metadata
records = Metadata()
records._sync()
>>> Wikidata username: 
>>> Wikidata password: 
```

Type your username and password, then `madata` starts to sync the metadata records at MADATA and Wikidata.

## SPARQL queries

The MADATA-subset at Wikidata: https://w.wiki/6s7R.
