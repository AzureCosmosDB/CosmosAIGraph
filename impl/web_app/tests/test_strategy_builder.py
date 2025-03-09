import pytest

from src.services.ai_service import AiService
from src.services.entities_service import EntitiesService
from src.services.strategy_builder import StrategyBuilder
from src.util.fs import FS

# pytest -v tests/test_strategy_builder.py

test_fixture_file = "../../data/testdata/strategy_builder_examples.json"
# examples in the test_fixture_file looks like this:
#   {
#     "natural_language": "lookup Flask",
#     "strategy": "db",
#     "name": "flask",
#     "algorithm": ""
#   }


@pytest.mark.asyncio
async def test_determine_with_simple_text_cases():
    await EntitiesService.initialize()
    ai_svc = AiService()
    sb = StrategyBuilder(ai_svc)
    examples_list = FS.read_json(test_fixture_file)

    tested_examples_count, success_count = 0, 0
    for example in examples_list:
        if example["algorithm"] == "text":
            tested_examples_count = tested_examples_count + 1
            natural_language = example["natural_language"]
            expected_strategy = example["strategy"]
            strategy_obj = sb.determine(natural_language)
            print("example: {}\nstrategy_obj: {}".format(example, strategy_obj))
            if strategy_obj["strategy"] == expected_strategy:
                success_count = success_count + 1

    assert len(examples_list) > 10
    assert tested_examples_count > 0
    assert tested_examples_count == success_count


@pytest.mark.asyncio
async def test_determine_with_llm_cases():
    await EntitiesService.initialize()
    ai_svc = AiService()
    sb = StrategyBuilder(ai_svc)
    examples_list = FS.read_json(test_fixture_file)

    tested_examples_count, success_count = 0, 0
    for example in examples_list:
        if example["algorithm"] != "text":
            tested_examples_count = tested_examples_count + 1
            natural_language = example["natural_language"]
            expected_strategy = example["strategy"]
            strategy_obj = sb.determine(natural_language)
            print("example: {}\nstrategy_obj: {}".format(example, strategy_obj))
            if strategy_obj["strategy"] == expected_strategy:
                success_count = success_count + 1

    assert len(examples_list) > 10
    assert tested_examples_count > 0
    assert tested_examples_count == success_count
