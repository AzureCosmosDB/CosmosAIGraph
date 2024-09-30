# CosmosAIGraph : Code Generation

A relatively new addition to this codebase is code generation,
which currently can be used to:

- Generate an OWL ontology file
- Fully generate a standalone class RdflibTriplesBuilder, called by GraphBuilder

Both of the above generators use **metadata** that can be mined
from your source input data for your graph.  The format of this
input data will obviously vary by customer.  It is assumed that
your input data contains the relationships and attributes of
your intended graph.

### Example Metadata

This repository contains two example files, for the simple **IMDb**
movies graph, as shown below.
One file identifies the metadata for the **verticies** 
(or entities) in your graph, while the other file identifes the **edges**
(or relationships).

```
impl/data/graph_input_metadata/edge_signatures_imdb.json
impl/data/graph_input_metadata/vertex_signatures_imdb.json
```

#### Edge Signatures Example

```
{
  "Movie|has_principal|Person": 10000,
  "Person|in_movie|Movie": 10000
}
```

This metadata file captures the relationships in your data.
For example, the key in the above dictionary with this value:

```
Movie|has_principal|Person
```

indicates that there is a relationship called **has_principal**
that connects an instance of class **Movie** to a **Person** instance.

The values in this metadata (i.e. - 10000) is informational only;
it indicates the number of times the relationship was observed
in the input data.

#### Vertex Signatures Example

```
{
  "Movie|title|<class 'str'>": 10000,
  "Movie|year|<class 'int'>": 10000,
  "Movie|rating|<class 'int'>": 10000,
  "Movie|genre|<class 'str'>": 10000,
  "Person|name|<class 'str'>": 10000,
  "Person|born|<class 'int'>": 10000,
  "Person|died|<class 'str'>": 10000
}
```

The structure of the Vertex data is similar to the Edges data.

For example this key:
```
Person|born|<class 'int'>
```

indicates that the **Person** class has an **born** attribute,
which is an **integer**.

### Data Wrangling

A simple python program can be created to read your input files,
observe its structure, and produce two metadata files similarly
structured to the above files.

Since the input data for each user of CosmosAIGraph is apt to 
vary widely from one application to the next, there is no standard
metadata-creation python script in this reference application.

### Execute the Generators

Once your metadata files exist, you can generate code as follows:

```
> .\venv\Scripts\Activate.ps1

> python main_console.py generate_owl meta/vertex_signatures_imdb.json meta/edge_signatures_imdb.json http://cosmosdb.com/imdb

...
file written: tmp/generated.owl

> python main_console.py generate_rdflib_triples_builder meta/vertex_signatures_imdb.json

...
file written: tmp/rdflib_triples_builder.py
```
