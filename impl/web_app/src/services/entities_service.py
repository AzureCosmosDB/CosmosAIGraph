import logging
import traceback

from src.services.config_service import ConfigService
from src.services.cosmos_nosql_service import CosmosNoSQLService
from src.util.counter import Counter

# Instances of this class are used to:
# - dynamically build entity catalog from source documents in Cosmos DB
# - identify known entities in given text data
# - support multiple entity types (pypi libraries, npm packages, etc.)
#
# Chris Joakim, Microsoft, 2025


class EntitiesService:

    # Class variables
    static_entities_by_name = dict()  # entity_name -> entity_type (e.g., "flask" -> "pypi")
    static_entities_by_type = dict()  # entity_type -> [entity_names] (e.g., "pypi" -> ["flask", "django", ...])
    static_entity_names = set()       # set of all entity names for fast lookup

    @classmethod
    async def initialize(cls, force_reinitialize=False):
        """
        Initialize the entities service by querying the source container in Cosmos DB
        and extracting all entities (documents with 'name' and 'libtype' fields).
        """
        logging.warning(
            "EntitiesService#initialize - force_reinitialize: {}".format(
                force_reinitialize
            )
        )

        # If already initialized, don't reinitialize unless forced
        if len(EntitiesService.static_entity_names) > 0:
            if force_reinitialize == False:
                return

        # Query Cosmos DB source container to build entity catalog
        try:
            container_name = ConfigService.graph_source_container()
            nosql_svc = CosmosNoSQLService()
            await nosql_svc.initialize()
            nosql_svc.set_db(ConfigService.graph_source_db())

            # If the configured container is not present, skip building the entity catalog gracefully
            existing_containers = await nosql_svc.list_containers()
            if container_name not in existing_containers:
                logging.warning(
                    "EntitiesService#initialize - graph source container '{}' not found; skipping entity catalog build".format(
                        container_name
                    )
                )
                await nosql_svc.close()
                return

            nosql_svc.set_container(container_name)
            
            # Query for all documents that have 'name' and 'libtype' fields
            # This makes the service generic - works with any entity type
            query = "SELECT c.name, c.libtype FROM c WHERE IS_DEFINED(c.name) AND IS_DEFINED(c.libtype)"
            
            entities_by_name = dict()
            entities_by_type = dict()
            entity_names = set()
            docs_count = 0
            
            # Execute query and process results
            query_results = nosql_svc._ctrproxy.query_items(query=query)
            async for doc in query_results:
                docs_count += 1
                name = doc.get("name")
                entity_type = doc.get("libtype")
                
                if name and entity_type:
                    # Store entity name -> type mapping
                    entities_by_name[name] = entity_type
                    entity_names.add(name)
                    
                    # Store entity type -> names mapping
                    if entity_type not in entities_by_type:
                        entities_by_type[entity_type] = []
                    entities_by_type[entity_type].append(name)
            
            # Update class variables
            cls.static_entities_by_name = entities_by_name
            cls.static_entities_by_type = entities_by_type
            cls.static_entity_names = entity_names
            
            entity_types_summary = {
                entity_type: len(names) 
                for entity_type, names in entities_by_type.items()
            }
            
            logging.warning(
                "EntitiesService#initialize - processed {} documents, found {} unique entities across {} types: {}".format(
                    docs_count, len(entity_names), len(entities_by_type), entity_types_summary
                )
            )
            
            await nosql_svc.close()
            
        except Exception as e:
            logging.critical("EntitiesService#initialize - exception: {}".format(str(e)))
            print(traceback.format_exc())

    @classmethod
    def entities_count(cls):
        """Return the total number of entities"""
        try:
            return len(cls.static_entity_names)
        except Exception as e:
            return -1

    @classmethod
    def entities_by_type_count(cls, entity_type):
        """Return the count of entities for a specific type (e.g., 'pypi')"""
        try:
            return len(cls.static_entities_by_type.get(entity_type, []))
        except Exception as e:
            return -1

    @classmethod
    def get_entity_types(cls):
        """Return list of all entity types"""
        try:
            return list(cls.static_entities_by_type.keys())
        except Exception as e:
            return []

    @classmethod
    def entity_present(cls, name):
        """Check if an entity name exists"""
        try:
            if name is not None:
                return name in cls.static_entity_names
        except Exception as e:
            pass
        return False

    @classmethod
    def get_entity_type(cls, name):
        """Get the type of an entity by name"""
        try:
            return cls.static_entities_by_name.get(name)
        except Exception as e:
            return None

    @classmethod
    def identify(cls, text) -> Counter:
        """Identify known entities in the given text data, return a Counter"""
        c = Counter()
        if text is not None:
            words = text.lower().replace(",", " ").replace(".", " ").strip().split()
            for word in words:
                if len(word) > 1:
                    if word in cls.static_entity_names:
                        c.increment(word)
        return c

    # Backward compatibility methods for existing code that uses library-specific names
    @classmethod
    def libraries_count(cls):
        """Backward compatibility: return count of 'pypi' entities"""
        return cls.entities_by_type_count("pypi")

    @classmethod
    def library_present(cls, name):
        """Backward compatibility: check if entity exists and is of type 'pypi'"""
        entity_type = cls.get_entity_type(name)
        return entity_type == "pypi" if entity_type else False
