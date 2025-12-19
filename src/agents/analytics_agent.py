import json
import os
from typing import Dict, Any, List, Optional
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    RunReportRequest,
    DateRange,
    Metric,
    Dimension,
)
from src.llm_client import llm_client

class AnalyticsAgent:
    def __init__(self):
        self.credentials_path = os.path.join(os.getcwd(), 'credentials.json')
        
    def _get_client(self):
        if not os.path.exists(self.credentials_path):
            raise FileNotFoundError(f"Credentials file not found at {self.credentials_path}")
            
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = self.credentials_path
        return BetaAnalyticsDataClient()

    def run(self, query: str, property_id: str) -> Dict[str, Any]:
        if not property_id:
             return {"error": "Property ID is required for GA4 queries."}

        plan = self._parse_query_to_plan(query)
        if "error" in plan:
            return {"answer": f"I could not understand the query: {plan['error']}"}
        
        try:
            report_response = self._fetch_ga4_data(property_id, plan)
        except Exception as e:
            return {"answer": f"Error fetching data from GA4: {str(e)}"}

        answer = self._generate_natural_language_response(query, plan, report_response)
        
        return {"answer": answer}

    def _parse_query_to_plan(self, query: str) -> Dict[str, Any]:
        system_prompt = """
        You are an expert Google Analytics 4 (GA4) Query Generator.
        Your task is to convert a natural language question into a structured JSON object for the GA4 Data API.
        
        Output strictly valid JSON. No markdown, no explanations.
        
        The JSON must have this structure:
        {
            "date_ranges": [{"start_date": "...", "end_date": "..."}],
            "metrics": [{"name": "..."}],
            "dimensions": [{"name": "..."}] (optional)
        }
        
        Rules for Date Ranges:
        - "today": start_date="today", end_date="today"
        - "yesterday": start_date="yesterday", end_date="yesterday"
        - "last X days": start_date="XdaysAgo", end_date="today" (e.g. "7daysAgo")
        - Default to "last 28 days" if not specified.
        
        Common Metrics:
        - activeUsers, sessions, screenPageViews, eventCount, totalUsers
        
        Common Dimensions:
        - date, city, country, pagePath, deviceCategory, source, medium
        
        Example:
        User: "How many users and views did we get in the last 7 days?"
        JSON: {
            "date_ranges": [{"start_date": "7daysAgo", "end_date": "today"}],
            "metrics": [{"name": "activeUsers"}, {"name": "screenPageViews"}],
            "dimensions": []
        }
        """
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ]
        
        response_text = llm_client.get_completion(messages)
        
        response_text = response_text.replace("```json", "").replace("```", "").strip()
        
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            return {"error": "Failed to parse LLM response as JSON"}

    def _fetch_ga4_data(self, property_id: str, plan: Dict[str, Any]):
        client = self._get_client()
        
        request = RunReportRequest(
            property=f"properties/{property_id}",
            date_ranges=[DateRange(**dr) for dr in plan.get("date_ranges", [])],
            metrics=[Metric(**m) for m in plan.get("metrics", [])],
            dimensions=[Dimension(**d) for d in plan.get("dimensions", [])],
        )
        
        response = client.run_report(request)
        
        if not response.rows:
             return {"data": [], "summary": "No data returned from GA4 for this query."}

        result_data = []
        for row in response.rows:
            item = {}
            for i, dimension_value in enumerate(row.dimension_values):
                dim_name = plan["dimensions"][i]["name"]
                item[dim_name] = dimension_value.value
            
            for i, metric_value in enumerate(row.metric_values):
                metric_name = plan["metrics"][i]["name"]
                item[metric_name] = metric_value.value
            
            result_data.append(item)
            
        return {"data": result_data}

    def _generate_natural_language_response(self, query: str, plan: Dict[str, Any], data_response: Dict[str, Any]) -> str:
        data_str = json.dumps(data_response.get("data", []), indent=2)
        summary = data_response.get("summary", "")
        
        system_prompt = f"""
        You are a Data Analyst. Answer the user's question based STRICTLY on the provided data.
        
        User Question: {query}
        
        Data Retrieved from GA4:
        {data_str}
        {summary}
        
        Plan used: {json.dumps(plan)}
        
        If the data is empty, state that no data was found for the specified period/conditions.
        If the data is present, summarize the key findings directly. Do not explain the API call.
        """
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Please provide the answer."}
        ]
        
        return llm_client.get_completion(messages)

analytics_agent = AnalyticsAgent()
