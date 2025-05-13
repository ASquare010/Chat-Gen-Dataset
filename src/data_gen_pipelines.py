import pandas as pd
import ast, re, json
import unicodedata
from openai_batch_job import OpenAiBatchJob


class CharGenBatchJob(OpenAiBatchJob):
    """Batch job for generating initial Character-Environment-Context rows."""

    def build_tasks(self, df: pd.DataFrame, sys_prompt: str) -> list:
        tasks = []
        for idx, row in df.iterrows():
            name = row.iloc[0]
            prompt = (
                f"Generate city, rural, natural, fantasy, futuristic, historical contexts "
                f"for Character Name: {name}" 
            )
            tasks.append(self.make_batch_task(idx, prompt, sys_prompt))
        return tasks

    def parse_return_json(self, content: str) -> list:
        try:
            data = json.loads(content)
            tasks = []
            for char_obj in data.get("Characters", []):
                tasks.append({
                    "Character": char_obj.get("Character", ""),
                    "Environment": char_obj.get("Environment", ""),
                    "Context": char_obj.get("Context", "")
                })
            return tasks
        except Exception as e:
            return [{"Character": content, "Environment": "" ,"Context": ""}]
        
    def post_process(self, df):
        return df


class CharEnvBatchJob(OpenAiBatchJob):

    def build_tasks(self, df: pd.DataFrame, sys_prompt: str) -> list:
        tasks = []
        for idx, row in df.iterrows():
            prompt = (
                f"Generate the dataset of:\n"
                f"- Role play of `{row['Character']}`\n"
                f"- Environment `{row['Environment']}`\n"
                f"- Context `{row['Context']}`"
            )
            tasks.append(self.make_batch_task(idx, prompt, sys_prompt))
        return tasks

    def parse_return_json(self, content: str) -> list:

        try:
            data = json.loads(content)
            return [{"character": json.dumps(data['Character']),
                    "environments": json.dumps(data['Environments']),
                    "contexts": json.dumps(data['Contexts'])}]
        except Exception as e:
            return [{"character": content,
                    "environments": [],
                    "contexts": []}]
        
    def post_process(self,df: pd.DataFrame) -> pd.DataFrame:

        for col in ('environments','contexts'):
            df[col] = df[col].apply(lambda x: ast.literal_eval(x) if isinstance(x, str) else x)

        well_mask = (
            df['environments'].apply(lambda x: isinstance(x, list) and len(x) > 0)
            & df['contexts'].apply(lambda x: isinstance(x, list) and len(x) > 0)
        )
        
        good_df = df[well_mask].reset_index(drop=True)
        bad_df  = df[~well_mask].reset_index(drop=True)

        print(f"Good rows: {len(good_df)}")
        print(f"Bad  rows: {len(bad_df)}") 

        repaired_rows = []

        for _, row in bad_df.iterrows():
            try:
                raw = str(row['character'])
                norm = raw.replace('“', '"').replace('”', '"').replace('‘', "'").replace('’', "'")
                norm = re.sub(r',\s*(?=[\]\}])', '', norm)

                try:
                    j = json.loads(norm)
                except Exception:
                    m = re.search(r'(\{.*\})', norm, flags=re.DOTALL)
                    if m:
                        block = re.sub(r',\s*(?=[\]\}])', '', m.group(1))
                        try:
                            j = json.loads(block)
                        except Exception:
                            j = {}
                    else:
                        j = {}

                new_char = j.get('Character', row['character'])
                new_env  = j.get('Environments', row['environments'])
                new_ctx  = j.get('Contexts',     row['contexts'])

                if isinstance(new_env, list) and new_env and isinstance(new_ctx, list) and new_ctx:
                    repaired_rows.append({
                        'character':    new_char,
                        'environments': new_env,
                        'contexts':     new_ctx
                    })
            except:
                pass
                
        if repaired_rows:
            repaired_df = pd.DataFrame(repaired_rows, columns=['character','environments','contexts'])
            fixed_df = pd.concat([good_df, repaired_df], ignore_index=True)
        else:
            fixed_df = good_df

        fixed_df = fixed_df.sample(frac=1, random_state=42).reset_index(drop=True)
        return fixed_df
 

class ConversationBatchJob(OpenAiBatchJob):
    
    def build_tasks(self, df: pd.DataFrame, sys_prompt: str) -> list:
        tasks = []
        for idx, row in df.iterrows():
            envs = ast.literal_eval(row['environments'])
            ctxs = ast.literal_eval(row['contexts'])
            for i, (env, ctx) in enumerate(zip(envs, ctxs)):
                prompt = (
                    f"Generate conversation for:\n"
                    f"- Role play of `{row['character']}`\n"
                    f"- Environment `{env}`\n"
                    f"- Context `{ctx}`"
                )
                tasks.append(self.make_batch_task(f"{idx}-{i}", prompt, sys_prompt))
        return tasks

    def parse_return_json(self, content: str) -> dict:
        return {"conversation": content.strip()}
 
    def post_process(self,df: pd.DataFrame, col: str = 'conversation') -> pd.DataFrame: 
        valid_rows = []
        for raw in df[col].astype(str):
            if self.__is_well_formed__(raw):
                valid_rows.append(raw)
            else:
                ok, fixed = self.__repair__(raw)
                if ok and self.__is_well_formed__(fixed):
                    valid_rows.append(fixed)

        fixed_df = pd.DataFrame({col: valid_rows}).reset_index(drop=True)
    
        try: 
            old_df = pd.read_csv(self.output_path)
            combine = pd.concat([old_df, fixed_df], ignore_index=True)
            return combine.drop_duplicates().reset_index(drop=True)
        except:
            print('No old dataset')
            return df

    def __is_well_formed__(self,s: str) -> bool:
        try:
            obj = json.loads(s)
        except json.JSONDecodeError:
            return False
        if not isinstance(obj, dict) or 'conversation' not in obj:
            return False
        convo = obj['conversation']
        if not isinstance(convo, list) or not convo:
            return False
        for turn in convo:
            if (
                not isinstance(turn, dict) or
                'role' not in turn or 'content' not in turn or
                not isinstance(turn['role'], str) or
                not isinstance(turn['content'], str)
            ):
                return False
        return True

    def __repair__(self,raw: str) -> (bool, str):
        _MISSING_OBJ_COMMAS = re.compile(r'}\s*{')
        _MISSING_OBJ_QUOTE = re.compile(r'}\s*"')
        _TR_LING_COMMA = re.compile(r',\s*(?=[}\]])')
        _BARE_KEY = re.compile(r'(?P<pre>[\{\[,]\s*)(?P<key>[A-Za-z_][A-Za-z0-9_]*)\s*:(?P<post>)')
        _ARRAY_ERR = re.compile(r'([}\]"])(?=[{\[\"])')
        _DUP_QUOTES = re.compile(r'""+')

        dQUOTE_MAP = {
            '“': '"', '”': '"', '―': '-', '–': '-', '—': '-',
            '‘': "'", '’': "'",
        }
        text = raw
        
        if not text.strip().startswith('{'):
            return False, text 
        
        text = ''.join(dQUOTE_MAP.get(c, c) for c in text) 
        text = ''.join(ch for ch in text if (ch in '\n\r\t') or not unicodedata.category(ch).startswith('C')) 
        text = re.sub(r'"content": "(.*?)"',
                    lambda m: '"content": "' + m.group(1).replace('"', r'\\"') + '"',
                    text, flags=re.DOTALL) 
        text = _MISSING_OBJ_COMMAS.sub('},\n{', text)
        text = _MISSING_OBJ_QUOTE.sub('},\n"', text) 
        text = _TR_LING_COMMA.sub('', text) 
        text = _BARE_KEY.sub(lambda m: f"{m.group('pre')}\"{m.group('key')}\":", text) 
        text = _ARRAY_ERR.sub(r"\1, ", text) 
        text = _DUP_QUOTES.sub('"', text) 
        if text.count('"') % 2:
            text += '"' 
        try:
            obj = json.loads(text)
        except json.JSONDecodeError:
            return False, text
        if not isinstance(obj, dict) or 'conversation' not in obj or not isinstance(obj['conversation'], list):
            return False, text
        return True, text


class RawBatchJob(OpenAiBatchJob):

    def build_tasks(self, df: pd.DataFrame, sys_prompt: str) -> list:
        tasks = []
        for idx, row in df.iterrows():
            conv_list = []
            turn = True
            for line in ast.literal_eval(row['chat']):
                role = "user" if turn else "assistant"
                conv_list.append({"role": role, "content": line})
                turn = not turn
            
            prompt = {'conversation': conv_list} 
            tasks.append(self.make_batch_task(idx, str(prompt), sys_prompt))
        return tasks

    def parse_return_json(self, content: str) -> list:
        try:
            data = json.loads(content)
            return [{"chat": json.dumps(data['chat'])}]
        except Exception as e:
            return [{"chat": content}]
       
    def post_process(self,df: pd.DataFrame, col: str = 'chat') -> pd.DataFrame: 
        
        conv_df = []
        input_df = pd.read_csv(self.read_csv_path)

        # make sure the two dataframes have the same length
        if len(input_df) == len(df):
            for i, row in input_df.iterrows():
                try:
                    # 1) parse the metadata JSON from add_df
                    add_meta = json.loads(df.at[i, col])
                    system_msg = add_meta['System']
                    new_msgs   = add_meta['new_messages']

                    # start the conversation with the System prompt
                    temp = [{"role": "system", "content": system_msg}]

                    # 2) parse your existing chat turns
                    data = ast.literal_eval(row[col])

                    # 3) walk through each turn, alternating roles
                    turn_user = True
                    for chat_item in data:
                        role = "user" if turn_user else "assistant"
                        temp.append({"role": role, "content": chat_item})
                        turn_user = not turn_user

                    # 4) append the new messages from add_df
                    for chat_item in new_msgs:
                        role = "user" if turn_user else "assistant"
                        temp.append({"role": role, "content": chat_item['content']})
                        turn_user = not turn_user
                    
                    # 5) serialize and collect
                    conv_df.append(json.dumps({"conversation": temp}, indent=4))


                except Exception as e:
                    pass
            
            try: 
                old_df = pd.read_csv(self.output_path)
                combine = pd.concat([old_df, pd.DataFrame({'conversation': conv_df})], ignore_index=True)
                return combine.drop_duplicates().reset_index(drop=True)
            except:
                print('No old dataset')
                return pd.DataFrame({'conversation': conv_df})

