"""RAG benchmark pipeline"""

import asyncio
import json
import os

from metagpt.const import (
    DATA_PATH,
    EXAMPLE_DATA_PATH,
    EXAMPLE_BENCHMARK_PATH
)
from metagpt.logs import logger
from metagpt.rag.engines import SimpleEngine
from metagpt.rag.factories import get_rag_embedding
from metagpt.rag.benchmark import RAGBenchMark
from metagpt.rag.schema import (
    FAISSRetrieverConfig,
    LLMRankerConfig,
    FAISSIndexConfig,
)

from llama_index.core.schema import NodeWithScore


DOC_PATH = EXAMPLE_DATA_PATH / "rag_bm/summary_writer.txt"
QUESTION = "2023年7月20日，应急管理部、财政部联合下发《因灾倒塌、损坏住房恢复重建救助工作规范》的通知，规范倒损住房恢复重建救助相关工作。"

TRAVEL_DOC_PATH = EXAMPLE_DATA_PATH / "rag_bm/documents.txt"
TRAVEL_QUESTION = "国家卫生健康委在2023年7月28日开展的“启明行动”是为了防控哪个群体的哪种健康问题，并请列出活动发布的指导性文件名称。"

DATASET_PATH = EXAMPLE_DATA_PATH / "rag_bm/test.json"
SAVE_PATH = EXAMPLE_DATA_PATH / "rag_bm/result.json"
GROUND_TRUTH_TRANVEL = "2023-07-28 10:14:27作者：白剑峰来源：人民日报    ，正文：为在全社会形成重视儿童眼健康的良好氛围，持续推进综合防控儿童青少年近视工作落实，国家卫生健康委决定在全国持续开展“启明行动”——防控儿童青少年近视健康促进活动，并发布了《防控儿童青少年近视核心知识十条》。本次活动的主题为：重视儿童眼保健，守护孩子明眸“视”界。强调预防为主，推动关口前移，倡导和推动家庭及全社会共同行动起来，营造爱眼护眼的视觉友好环境，共同呵护好孩子的眼睛，让他们拥有一个光明的未来。国家卫生健康委要求，开展社会宣传和健康教育。充分利用网络、广播电视、报纸杂志、海报墙报、培训讲座等多种形式，广泛开展宣传倡导，向社会公众传播开展儿童眼保健、保护儿童视力健康的重要意义，以《防控儿童青少年近视核心知识十条》为重点普及预防近视科学知识。创新健康教育方式和载体，开发制作群众喜闻乐见的健康教育科普作品，利用互联网媒体扩大传播效果，提高健康教育的针对性、精准性和实效性。指导相关医疗机构将儿童眼保健和近视防控等科学知识纳入孕妇学校、家长课堂内容。开展儿童眼保健及视力检查咨询指导。医疗机构要以儿童家长和养育人为重点，结合眼保健和眼科临床服务，开展个性化咨询指导。要针对儿童常见眼病和近视防控等重点问题，通过面对面咨询指导，引导儿童家长树立近视防控意识，改变不良生活方式，加强户外活动，养成爱眼护眼健康行为习惯。提高儿童眼保健专科服务能力。各地要积极推进儿童眼保健专科建设，扎实组织好妇幼健康职业技能竞赛“儿童眼保健”项目，推动各层级开展比武练兵，提升业务能力。"
GROUND_TRUTH_ANSWER = "“启明行动”是为了防控儿童青少年的近视问题，并发布了《防控儿童青少年近视核心知识十条》。"

LLM_TIP = "If you not sure, just answer I don't know."


class RAGExample:
    """Show how to use RAG for evaluation."""

    def __init__(self):

        self.benchmark = RAGBenchMark()
        self.embedding = get_rag_embedding()

    async def rag_evaluate_pipeline(self,dataset_name=['all']):

        dataset_config = self.benchmark.load_dataset()

        for dataset in dataset_config.datasets:
            if 'all' in dataset_name or dataset.name in dataset_name:
                output_dir = DATA_PATH / f"rag_faiss_{dataset.name}"
                self.engine = SimpleEngine.from_docs(
                    input_files=dataset.document_files,
                    retriever_configs=[FAISSRetrieverConfig(persist_path=output_dir)],
                    ranker_configs=[LLMRankerConfig()],
                )
                results = []
                for gt_info in dataset.gt_info:
                    result = await self.rag_evaluate_single(
                        question=gt_info['question'],
                        reference=gt_info['gt_reference'],
                        ground_truth=gt_info['gt_answer']
                    )
                    results.append(result)
                logger.info(f"=====The {dataset.name} BenchMark dataset assessment is complete!=====")
                self._print_bm_result(results)

                with open(os.path.join(EXAMPLE_BENCHMARK_PATH,dataset.name,'bm_result.json'),'w',encoding='utf-8')as f:
                    json.dump(results,f,ensure_ascii=False,indent=4)


    async def rag_evaluate_single(self, question,reference,ground_truth,print_title=True):
        """This example run rag pipeline, use faiss&bm25 retriever and llm ranker, will print something like:

        Retrieve Result:
        0. Productivi..., 10.0
        1. I wrote cu..., 7.0
        2. I highly r..., 5.0

        Query Result:
        Passion, adaptability, open-mindedness, creativity, discipline, and empathy are key qualities to be a good writer.

        RAG BenchMark result:
        {
        'metrics':
         {
         'bleu-avg': 0.48318624982047,
         'bleu-1': 0.5609756097560976,
         'bleu-2': 0.5,
         'bleu-3': 0.46153846153846156,
         'bleu-4': 0.42105263157894735,
         'rouge-L': 0.6865671641791045,
         'semantic similarity': 0.9487444961487591,
         'length': 74
         },
         'log': {
         'generated_text':
         '国家卫生健康委在2023年7月28日开展的“启明行动”是为了防控儿童青少年的近视问题。活动发布的指导性文件名称为《防控儿童青少年近视核心知识十条》。',
         'ground_truth_text':
         '“启明行动”是为了防控儿童青少年的近视问题，并发布了《防控儿童青少年近视核心知识十条》。'
            }
         }
        """
        if print_title:
            self._print_title("RAG Pipeline")
        try:
            nodes = await self.engine.aretrieve(question)
            self._print_result(nodes, state="Retrieve")

            answer = await self.engine.aquery(question)
            self._print_result(answer, state="Query")

        except:
            return {
                'metrics':
                 {
                 'bleu-avg': 0.0,
                 'bleu-1': 0.0,
                 'bleu-2': 0.0,
                 'bleu-3': 0.0,
                 'bleu-4': 0.0,
                 'rouge-L': 0.0,
                 'semantic similarity': 0.0,
                 'length': 0
                 },
                 'log': {
                 'generated_text':"Retrieve failed due to LLM wasn't follow instruction",
                 'ground_truth_text':ground_truth,
                 'question':question,
                    }
                }


        result = await self.evaluate_result(answer.response, ground_truth, nodes, [reference])
        result['log']['question'] = question

        logger.info("==========RAG BenchMark result demo as follows==========")
        logger.info(result)

        return result

    async def rag_faissdb(self):
        """This example show how to use FAISS. how to save and load index. will print something like:

        Query Result:
        Bob likes traveling.
        """
        self._print_title("RAG FAISS")

        # save index
        output_dir = DATA_PATH / "rag_faiss"
        # 在这里会重新计算Embedding,与init中的from_docs重复
        SimpleEngine.from_docs(
            input_files=[TRAVEL_DOC_PATH],
            retriever_configs=[FAISSRetrieverConfig(dimensions = 512,persist_path=output_dir)],
        )

        # load index
        engine = SimpleEngine.from_index(
            index_config=FAISSIndexConfig(persist_path=output_dir),
        )

        # query
        nodes = engine.retrieve(QUESTION)
        self._print_result(nodes,state='Retrieve')

        answer = engine.query(TRAVEL_QUESTION)
        self._print_result(answer, state="Query")

    async def evaluate_result(
        self,
        response: str = None,
        reference: str = None,
        nodes : list[NodeWithScore] = None,
        reference_doc: list[str] = None
    ):
        recall = self.benchmark.recall(nodes, reference_doc)
        bleu_avg, bleu1, bleu2, bleu3, bleu4 = self.benchmark.bleu_score(response, reference)
        rouge_l = self.benchmark.rougeL_score(response, reference)

        result = {
            'metrics': {
                'bleu-avg': bleu_avg or 0.0,
                'bleu-1': bleu1 or 0.0,
                'bleu-2': bleu2 or 0.0,
                'bleu-3': bleu3 or 0.0,
                'bleu-4': bleu4 or 0.0,
                'rouge-L': rouge_l,
                'semantic similarity': await self.benchmark.SemanticSimilarity(response, reference),
                'recall': recall,
                'length': len(response)
            },
            'log': {
                'generated_text': response,
                'ground_truth_text': reference,
            }
        }
        return result

    @staticmethod
    def _print_title(title):
        logger.info(f"{'#'*30} {title} {'#'*30}")

    @staticmethod
    def _print_result(result, state="Retrieve"):
        """print retrieve or query result"""
        logger.info(f"{state} Result:")

        if state == "Retrieve":
            for i, node in enumerate(result):
                logger.info(f"{i}. {node.text[:10]}..., {node.score}")
            logger.info("======Retrieve Finished======")
            return

        logger.info(f"{result}\n")

    @staticmethod
    def _print_bm_result(result):
        import pandas as pd
        metrics = [item['metrics'] for item in result]

        data = pd.DataFrame(metrics)
        logger.info(f"\n {data.mean()}")

        llm_errors =  [item for item in result
                       if item['log']['generated_text'] =="Retrieve failed due to LLM wasn't follow instruction"]
        retrieve_errors = [item for item in result
                        if item['log']['generated_text'] == "Empty Response"]
        logger.info(f"Percentage of retrieval failures due to incorrect LLM instruction following:"
                    f" {100.0 * len(llm_errors) / len(result)}%")
        logger.info(f"Percentage of retrieval failures due to retriever not recalling any documents is:"
                    f" {100.0 * len(retrieve_errors) / len(result)}%")

    async def _retrieve_and_print(self, question):
        nodes = await self.engine.aretrieve(question)
        self._print_result(nodes, state="Retrieve")
        return nodes


async def main():
    """RAG pipeline"""
    e = RAGExample()
    await e.rag_evaluate_pipeline()


if __name__ == "__main__":
    asyncio.run(main())