# CosmosAIGraph : Cosmos DB Document Design and Modeling

## How is this data modeled, or structured, for graph purposes?

One nice feature of this solution is that **there is no required structure**
for your JSON documents in Cosmos DB.  They can be structured as if
it is a non-graph application, per general NoSQL/Mongo design best practices.

This is because **the graph**, in the CosmosAIGraph solution, only
exists in-memory within the Python rdflib process.

However, one suggestion is to use an **edges attribute** in your
documents, and populate it with the list of **outgoing** relationships
from the given entity/vertex document.

In the case of the CosmosAIGraph reference dataset of python libraries,
however, an edges attribute is not used.  Instead, the **developers**
and **dependency_ids** are used at runtime to construct the in-memory
RDF graph.

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
**https://pypi.org/pypi/{libname}/json**, and their HTML contents were tranformed into JSON.

Subsequent data wrangling fetched referenced HTML documentation, produced 
**text summarization with Azure OpenAI and semantic-kernel** and produced
a **vectorized embedding value** from several concatinated text attributes
within each library JSON document.  A full description of this data wrangling
process is beyond the scope of this documentation, but the process itself
is in file 'impl/app/wrangle.py' in the repo.

## Next Steps: Load Cosmos DB with Library Documents

- See [Load Azure Cosmos DB vCore](load_cosmos_vcore.md)
- See [Load Azure Cosmos DB NoSQL](load_cosmos_nosql.md)
