import json
import faker

from src.services.ai_service import AiService
from src.util.fs import FS
from src.util.prompt_optimizer import PromptOptimizer


# pytest -v tests/test_prompt_optimizer.py

# test results on 6/7:
# test case: 0, initial_tokens: 333, pruned_tokens: 333, iteration_count: 1, ratio: -1.0
# test case: 1, initial_tokens: 1893, pruned_tokens: 1893, iteration_count: 1, ratio: -1.0
# test case: 2, initial_tokens: 3899, pruned_tokens: 3899, iteration_count: 1, ratio: -1.0
# test case: 3, initial_tokens: 7767, pruned_tokens: 2420, iteration_count: 2, ratio: 0.47735934080082404
# test case: 4, initial_tokens: 15334, pruned_tokens: 3864, iteration_count: 3, ratio: 0.21711882092082951
# test case: 5, initial_tokens: 39834, pruned_tokens: 3277, iteration_count: 7, ratio: 0.05282673093337349

def test_generate_and_truncate():
    ai_svc = AiService()
    pu = PromptOptimizer()
    test_cases = list()
    prev_actual_tokens = -1
    for idx, n in enumerate([3, 20, 42, 84, 160, 400]):  # relative sizes - 30, 80, 200 should be truncated
        test_case = dict()
        template = ai_svc.generic_prompt_template()
        context = generate_context(n)
        history = generate_history(n)
        user_query = "what is the capital of France"
        result_obj = pu.generate_and_truncate(
            template,
            context,
            history,
            user_query,
            4096)

        test_case['template_lines'] = list()
        for line in template.split("\n"):
            test_case['template_lines'].append(line)

        test_case['context_lines'] = list()
        for line in context.split("\n"):
            test_case['context_lines'].append(line)

        test_cases.append(result_obj)
        FS.write_json(test_cases, "tmp/test_prompt_util_test_cases.json")

        print("test case: {}, initial_tokens: {}, pruned_tokens: {}, iteration_count: {}, ratio: {}".format(
            idx,
            result_obj['initial_tokens'],
            result_obj['pruned_tokens'],
            result_obj['iteration_count'],
            result_obj['initial_context_words_ratio']))

        if result_obj['iteration_count'] == 1:
            assert result_obj['initial_tokens'] == result_obj['pruned_tokens']
        else:
            assert result_obj['initial_tokens'] > result_obj['pruned_tokens']
        assert result_obj['exception'] == ""

# private methods below

def generate_context(count: int) -> str:
    lines = list()
    word_idx = 0
    for n in range(count):
        sentence = list()
        for w in range(10):
            word_idx += 1
            sentence.append(str(word_idx))
        lines.append(" ".join(sentence) + ".")
    return "\n".join(lines)

def generate_history(count: int) -> str:
    messages = list()
    history = dict()
    history['messages'] = messages
    fake = faker.Faker()
    for n in range(count):
        msg = {
            "inner_content": "",
            "ai_model_id": "",
            "metadata": {},
            "role": "user",
            "content": "",
            "encoding": ""
        }
        msg['inner_content'] = str(n)
        msg['content'] = fake.paragraph()
        messages.append(msg)
    return json.dumps(history, sort_keys=False, indent=2)
