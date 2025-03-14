# CosmosAIGraph : Cosmos DB Document Design and Modeling

## Modeling the data for graph purposes

This solution does not have a **pre-defined data structure**.  The JSON documents in Cosmos DB can be structured as per general NoSQL design best practices.

This is because **the graph**, in the CosmosAIGraph solution, only
exists in-memory within the Apache Jena process, while all of the source data for it comes from Cosmos DB during initialization.

For example, one way to model this source data is to use an **edges attribute** in JSON
documents, and populate it with the list of **outgoing** edges (relationships)
from the given a node (entity) document.

In the case of the CosmosAIGraph reference dataset of python libraries,
however, more specifically-named **developers**
and **dependency_ids** JSON fields are used to construct the in-memory
RDF graph:

```
  ...
  "developers": [
    "contact@palletsprojects.com"
  ],
  ...
  "dependency_ids": [
    "pypi_asgiref",
    "pypi_blinker",
    "pypi_click",
    "pypi_importlib_metadata",
    "pypi_itsdangerous",
    "pypi_jinja2",
    "pypi_python_dotenv",
    "pypi_werkzeug"
  ],
  ...
```

## The Data - Python Libraries at PyPi

The **impl\data** directory in this repo contains a curated set of
[PyPi (Python)](https://pypi.org/) library JSON documents.

This domain of software libraries was chosen because it should be **relatable** 
to most customers, and it also suitable for **Bill-of-Materials** graphs.

The PyPi JSON files were obtained with HTTP requests to public URLs such as 
**https://pypi.org/pypi/{libname}/json**, and their HTML contents were transformed into JSON.

Subsequent data wrangling fetched referenced HTML documentation, produced 
**text summarization with Azure OpenAI and semantic-kernel** and produced
a **vectorized embedding value** from several concatenated text attributes
within each library JSON document.  A full description of this data wrangling
process is beyond the scope of this documentation, but the process itself
is in file 'impl/app/wrangle.py'.

## Next Steps: Load Cosmos DB with Library Documents

- See [Load Azure Cosmos DB NoSQL](load_cosmos_nosql.md)
