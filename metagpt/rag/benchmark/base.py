import evaluate
import jieba
import asyncio
import os
import json

from typing import List
from pydantic import BaseModel

from llama_index.core.evaluation import SemanticSimilarityEvaluator
from llama_index.core.embeddings import BaseEmbedding
from llama_index.core.schema import NodeWithScore

from metagpt.rag.factories import get_rag_embedding
from metagpt.const import EXAMPLE_BENCHMARK_PATH


class DatasetInfo(BaseModel):
    name: str
    document_files: List[str]
    gt_info: List[dict]

class DatasetConfig(BaseModel):
    datasets: List[DatasetInfo]


class RAGBenchMark:

    def __init__(self,
        embed_model: BaseEmbedding = None,
         ):

        self.evaluator = SemanticSimilarityEvaluator(
            embed_model=embed_model or get_rag_embedding(),
        )


    def bleu_score(
        self,
        response: str,
        reference: str,
        with_penalty=False
    ) -> float:
        f = lambda text: list(jieba.cut(text))
        bleu = evaluate.load(path = './metrics/bleu')
        results = bleu.compute(predictions=[response], references=[[reference]], tokenizer=f)

        bleu_avg = results['bleu']
        bleu1 = results['precisions'][0]
        bleu2 = results['precisions'][1]
        bleu3 = results['precisions'][2]
        bleu4 = results['precisions'][3]
        brevity_penalty = results['brevity_penalty']

        if with_penalty:
            return bleu_avg, bleu1, bleu2, bleu3, bleu4
        else:
            return 0.0 if brevity_penalty == 0 else bleu_avg / brevity_penalty, bleu1, bleu2, bleu3, bleu4

    def rougeL_score(
        self,
        response: str,
        reference: str
    ) -> float:
        # pip install rouge_score
        f = lambda text: list(jieba.cut(text))
        rouge = evaluate.load(path = './metrics/rouge')

        results = rouge.compute(predictions=[response], references=[[reference]], tokenizer=f, rouge_types=['rougeL'])
        score = results['rougeL']
        return score

    def recall(
        self,
        nodes: list[NodeWithScore],
        reference_doc: list[str]
    ) -> float:
        # 目前只考虑reference_doc 为 1 的情况

        if nodes:
            for node in nodes:
                if reference_doc == node.text:
                    return 1.0
                else:
                    continue
        else:
            return 0.0

    async def SemanticSimilarity(
            self,
            response: str,
            reference: str
    ) -> float:

        result = await self.evaluator.aevaluate(
            response=response,
            reference=reference,
        )

        return result.score

    @staticmethod
    def load_dataset():
        with open(os.path.join(EXAMPLE_BENCHMARK_PATH,"dataset_info.json"),'r',encoding='utf-8')as f:
            infos = json.load(f)
            dataset_config = DatasetConfig(datasets=[
                DatasetInfo(
                    name=name,
                    document_files=[os.path.join(EXAMPLE_BENCHMARK_PATH,name,file) for file in info['document_file'].split(',')],
                    gt_info=json.load(open(os.path.join(EXAMPLE_BENCHMARK_PATH,name,info['gt_file']),'r',encoding='utf-8'))
                )
                for dataset_info in infos
                for name,info in dataset_info.items()
            ])
        return dataset_config

if __name__=='__main__':
    benchmark = RAGBenchMark()
    answer = '是的，根据提供的信息，2023年7月20日，应急管理部和财政部确实联合发布了《因灾倒塌、损坏住房恢复重建救助工作规范》的通知。这份《规范》旨在进一步规范因灾倒塌、损坏住房的恢复重建救助相关工作。它明确了地方各级政府负责实施救助工作，应急管理部和财政部则负责统筹指导。地方财政应安排足够的资金，中央财政也会提供适当的补助。救助资金将通过专账管理，并采取特定的管理方式。救助对象是那些因自然灾害导致住房倒塌或损坏，并向政府提出申请且符合条件的受灾家庭。相关部门将组织调查统计救助对象信息，并建立档案。此外，《规范》还强调了资金发放的具体方式和公开透明的要求。'
    ground_truth = '“启明行动”是为了防控儿童青少年的近视问题，并发布了《防控儿童青少年近视核心知识十条》。'
    bleu_avg, bleu1, bleu2, bleu3, bleu4 = benchmark.bleu_score(answer, ground_truth)
    print(bleu_avg)
    print(bleu1)
    print(bleu2)
    print(bleu3)
    print(bleu4)

    rougeL_score = benchmark.rougeL_score(answer, ground_truth)
    print(rougeL_score)

    similarity = asyncio.run(benchmark.SemanticSimilarity(answer, ground_truth))
    print('==========similarity==========')
    print(similarity)

