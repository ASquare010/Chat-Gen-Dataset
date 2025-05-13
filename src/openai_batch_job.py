from abc import ABC, abstractmethod
from openai import OpenAI
import json, io
import pandas as pd


class OpenAiBatchJob(ABC):
    """Base class for OpenAI batch jobs. Subclasses override task-building and parsing hooks."""

    job_id:str | None = None
    batch_file:io.BytesIO | None = None
    output_file_id:str | None = None


    def __init__(self,
        key:str,
        read_csv_path: str,
        output_path: str,
        sys_prompt_path: str,
        completion_window: str = "24h",
        model:str = "gpt-4o-mini",
    ):  
        self.client = OpenAI(api_key=key)
        self.output_path = output_path
        self.read_csv_path = read_csv_path
        self.completion_window = completion_window
        self.sys_prompt_path = sys_prompt_path
        self.model = model
        

    @abstractmethod
    def build_tasks(self, df: pd.DataFrame, sys_prompt: str) -> list:
        """
        Hook: build and return a list of full batch-task dicts,
        each having custom_id, method, url, body.
        """
        raise NotImplementedError
    

    @abstractmethod
    def parse_return_json(self, content:str) -> list:
        """Hook: must be overridden in subclasses."""
        raise NotImplementedError
    

    @abstractmethod
    def post_process(self, df:pd.DataFrame) -> pd.DataFrame:
        """Hook: must be overridden in subclasses."""
        raise NotImplementedError


    def make_batch_task(self, idx, prompt, sys_prompt, temp:float = 0.85):
        return {
                "custom_id": str(idx),
                "method": "POST",
                "url": "/v1/chat/completions",
                "body": {
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": sys_prompt},
                        {"role": "user", "content":prompt}
                    ],
                    "temperature": temp
                }
            }
    

    def invoke_job(self):
        if self.job_id is None:
            self.__build_task__()
        else:
            self.__check_job_status__(self.job_id)

        return self.job_id


    def __build_task__(self):
        df = pd.read_csv(self.read_csv_path)
        sys_prompt = self.__read_file__(self.sys_prompt_path)
        tasks =  self.build_tasks(df, sys_prompt)

        batch_content = "\n".join(json.dumps(task) for task in tasks)
        self.batch_file = io.BytesIO(batch_content.encode('utf-8'))

        batch_file = self.client.files.create(
            file=self.batch_file,
            purpose="batch"
        )

        response = self.client.batches.create(
            input_file_id=batch_file.id,
            endpoint="/v1/chat/completions",
            completion_window=self.completion_window
        )

        self.job_id = response.id
        print("posted batch_file->",response)


    def __check_job_status__(self,job_id):    
        batch_job = self.client.batches.retrieve(job_id)

        if batch_job.status == "completed" or batch_job.status == "expired":
            self.output_file_id = batch_job.output_file_id
            self.__downloading_and_save__()
        elif batch_job.status == "in_progress":
            print("Job In Progress", self.job_id)
            return
        else:
            print(batch_job.status)
            return
        

    def __downloading_and_save__(self):
        print('Downloading File',self.output_file_id)
        raw = self.client.files.content(self.output_file_id).content.decode("utf-8").strip().splitlines()
        parsed = [json.loads(line) for line in raw]
        rows = []
        for entry in parsed:
            content = str(entry["response"]["body"]["choices"][0]["message"]["content"])
            content = content.replace("```json","").replace("```","")
            data = self.parse_return_json(content)
            if isinstance(data, list):
                rows.extend(data)
            else:
                rows.append(data)

        new_df = self.post_process(pd.DataFrame(rows))
        new_df.to_csv(self.output_path, index=False)


    def __read_file__(self,file_path:str):
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        return content