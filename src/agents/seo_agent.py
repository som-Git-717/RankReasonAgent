import pandas as pd
import json
import os
import re
from google.oauth2 import service_account
from googleapiclient.discovery import build
from src.llm_client import llm_client

class SEOAgent:
    def __init__(self):
        self.spreadsheet_id = "1zzf4ax_H2WiTBVrJigGjF2Q3Yz-qy2qMCbAMKvl6VEE"
        self.credentials_path = os.path.join(os.getcwd(), 'credentials.json')
        self._df_cache = None

    def _get_authenticated_service(self):
        if not os.path.exists(self.credentials_path):
            raise FileNotFoundError(f"Credentials file not found at {self.credentials_path}")
        
        scopes = ['https://www.googleapis.com/auth/spreadsheets.readonly']
        creds = service_account.Credentials.from_service_account_file(
            self.credentials_path, scopes=scopes
        )
        return build('sheets', 'v4', credentials=creds)

    def _sheet_values_to_df(self, values):
        if not values:
            return pd.DataFrame()
        header = values[0]
        data = values[1:]
        max_len = len(header)
        data = [row + [None]*(max_len-len(row)) for row in data]
        df = pd.DataFrame(data, columns=header)
        
        for col in df.columns:
            if any(key in col for key in ['Length', 'Width', 'Count', 'Violations', 'Score', 'Size', 'Bytes', 'Code']):
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        return df

    def _get_data(self):
        try:
            service = self._get_authenticated_service()
            
            ranges = ['internal_all!A:ZZ', 'accessibility_all!A:ZZ']
            
            result = service.spreadsheets().values().batchGet(
                spreadsheetId=self.spreadsheet_id, 
                ranges=ranges
            ).execute()
            
            value_ranges = result.get('valueRanges', [])
            
            df_main = pd.DataFrame()
            if value_ranges and 'values' in value_ranges[0]:
                df_main = self._sheet_values_to_df(value_ranges[0]['values'])
            
            df_access = pd.DataFrame()
            if len(value_ranges) > 1 and 'values' in value_ranges[1]:
                 df_access = self._sheet_values_to_df(value_ranges[1]['values'])

            if df_main.empty:
                spreadsheet_meta = service.spreadsheets().get(spreadsheetId=self.spreadsheet_id).execute()
                first_sheet_title = spreadsheet_meta['sheets'][0]['properties']['title']
                
                result_fallback = service.spreadsheets().values().get(
                    spreadsheetId=self.spreadsheet_id, range=f"'{first_sheet_title}'!A:ZZ"
                ).execute()
                return self._sheet_values_to_df(result_fallback.get('values', []))

            if not df_access.empty:
                common_cols = ['Address', 'Content Type', 'Status Code', 'Status']
                access_cols = [c for c in df_access.columns if c not in df_main.columns and c not in common_cols]
                
                if access_cols:
                    if 'Address' in df_main.columns and 'Address' in df_access.columns:
                        cols_to_merge = ['Address'] + access_cols
                        df_main = pd.merge(df_main, df_access[cols_to_merge], on='Address', how='left')
            
            return df_main

        except Exception as e:
            print(f"Error fetching SEO data via Google Sheets API: {e}")
            raise e

    def run(self, query: str) -> dict:
        try:
            df = self._get_data()
            
            columns = df.columns.tolist()
            print(f"DEBUG: DataFrame Columns: {columns}")
            dtypes = df.dtypes.to_dict()
            sample_data = df.head(3).to_markdown(index=False)
            
            system_prompt = f"""
            You are an expert Python Data Scientist and SEO Analyst.
            You have a pandas DataFrame 'df' containing Screaming Frog SEO audit data.
            
            Schema (Columns): {columns}
            Sample Data:
            {sample_data}
            
            User Question: "{query}"
            
            Your goal is to write a valid Python code snippet that analyzes 'df' to answer the question.
            
            Requirements:
            - The code must be a valid Python script.
            - Assume 'df' is already defined.
            - The final result/answer must be assigned to a variable named 'result'.
            - 'result' can be a DataFrame, a number, a string, or a list.
            - Use pandas operations (filtering, groupby, aggregation).
            - Do NOT use input(), print() or external libraries other than pandas.
            - Handle potential missing values (NaN) gracefully.
            - Return ONLY the code, no markdown markers.
            """
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Generate the code."}
            ]
            
            code = llm_client.get_completion(messages)
            code = code.replace("```python", "").replace("```", "").strip()
            
            code = "import pandas as pd\n" + code
            
            local_vars = {"df": df, "pd": pd}
            try:
                exec(code, local_vars, local_vars) 
                result = local_vars.get("result", "No result variable found.")
            except Exception as exec_error:
                error_str = str(exec_error)
                if "KeyError" in str(type(exec_error)) or "'" in error_str:
                    return {
                        "answer": f"I cannot answer that because the dataset is missing a required column (KeyError: {error_str}). The available columns are: {', '.join(columns[:5])}...",
                        "code_used": code
                    }
                return {"answer": f"Error executing analysis code: {exec_error}", "code_used": code}
            
            return self._generate_nl_response(query, result)
            
        except Exception as e:
            return {"answer": f"Error in SEO Agent: {str(e)}"}

    def _generate_nl_response(self, query, result):
        if isinstance(result, pd.DataFrame):
            pd.set_option('display.max_colwidth', None)
            result_str = result.to_markdown(index=False)
        else:
            result_str = str(result)
            
        system_prompt = f"""
        You are an SEO Consultant.
        User Question: "{query}"
        
        Analysis Result:
        {result_str}
        
        Provide a clear, natural language answer based on this result.
        """
        
        messages = [{"role": "system", "content": system_prompt}]
        return {"answer": llm_client.get_completion(messages)}

seo_agent = SEOAgent()
