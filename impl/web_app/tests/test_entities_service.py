import os

import pytest

from src.services.config_service import ConfigService
from src.services.entities_service import EntitiesService
from src.util.counter import Counter

# pytest -v tests/test_entities_service.py


@pytest.mark.asyncio
async def test_with_nosql():
    ConfigService.set_standard_unit_test_env_vars()
    os.environ["CAIG_GRAPH_SOURCE_TYPE"] = "cosmos_nosql"

    await EntitiesService.initialize()

    assert EntitiesService.libraries_count() > 10000  # 10760 is expected
    assert EntitiesService.libraries_count() < 20000

    assert EntitiesService.library_present("flask") == True
    assert EntitiesService.library_present("pydantic-core") == True
    assert EntitiesService.library_present("pypi") == False

    # identify case 1
    counter: Counter = EntitiesService.identify(None)
    assert counter is not None
    print(counter.get_data())
    assert counter.most_frequent() == None

    # identify case 2
    counter: Counter = EntitiesService.identify("")
    assert counter is not None
    print(counter.get_data())
    assert counter.most_frequent() == None

    # identify case 3
    counter: Counter = EntitiesService.identify("Chris, Aleksey, Luciano")
    assert counter is not None
    print(counter.get_data())
    assert counter.most_frequent() == None

    # identify case 4
    counter: Counter = EntitiesService.identify("i have a flask of water")
    assert counter is not None
    print(counter.get_data())
    assert counter.most_frequent() == "flask"

    # identify case 5
    counter: Counter = EntitiesService.identify(
        "I want to express how much I like Fastapi, pydantic, you, and fastapi"
    )
    assert counter is not None
    print(counter.get_data())  # {'express': 1, 'fastapi': 2, 'pydantic': 1}
    assert counter.most_frequent() == "fastapi"
    assert counter.get_data()["pydantic"] == 1
    assert counter.get_data()["fastapi"] == 2
