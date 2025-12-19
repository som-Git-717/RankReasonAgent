from src.llm_client import llm_client
from src.agents.analytics_agent import analytics_agent
from src.agents.seo_agent import seo_agent
import json

class Orchestrator:
    def route_request(self, query: str, property_id: str = None) -> dict:
        
        intent = self._detect_intent(query)
        
        if intent == "ANALYTICS":
            if not property_id:
                return {"answer": "This looks like an analytics question, but no propertyId was provided."}
            return analytics_agent.run(query, property_id)
            
        elif intent == "SEO":
            return seo_agent.run(query)
            
        elif intent == "MULTI_AGENT":
            return self._run_multi_agent_flow(query, property_id)
            
        else:
            return {"answer": "I'm not sure how to handle that query. I support Web Analytics (GA4) and SEO Audits."}

    def _detect_intent(self, query: str) -> str:
        system_prompt = """
        You are an Intent Classifier.
        Classify the user's query into one of these categories:
        
        1. ANALYTICS: Questions about traffic, users, sessions, pageviews, bounce rate, events, sources, mediums. (Requires GA4)
        2. SEO: Questions about title tags, meta descriptions, status codes (404, 200), indexability, canoncials, word counts, crawl depth. (Requires Screaming Frog)
        3. MULTI_AGENT: Questions that explicitly require matching metrics (views, users) with SEO attributes (title tags, meta descriptions) for the SAME pages.
        
        Output ONLY the category name: ANALYTICS, SEO, or MULTI_AGENT.
        """
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ]
        
        intent = llm_client.get_completion(messages).strip().upper()
        if intent not in ["ANALYTICS", "SEO", "MULTI_AGENT"]:
            return "UNKNOWN"
        return intent

    def _run_multi_agent_flow(self, query: str, property_id: str) -> dict:
        if not property_id:
             return {"answer": "Multi-agent queries involving traffic data require a propertyId."}

        plan_prompt = f"""
        You are a Task Planner. The user has asked a complex question requiring both Analytics and SEO data.
        Query: "{query}"
        
        Identify:
        1. What data to get from GA4 (e.g. "top 10 pages by screenPageViews")
        2. What data to get from SEO (e.g. "title tags for those pages")
        
        Output a JSON:
        {{
            "ga4_query": "...",
            "seo_query": "..."
        }}
        """
        messages = [{"role": "system", "content": plan_prompt}]
        try:
            plan_str = llm_client.get_completion(messages).replace("```json", "").replace("```", "").strip()
            plan = json.loads(plan_str)
        except:
            plan = {"ga4_query": query, "seo_query": query}

        ga4_result = analytics_agent.run(plan["ga4_query"], property_id)
        
        seo_lookup_query = "Get a list of all URLs and their " + ("title tags" if "title" in query else "meta descriptions")
        seo_result = seo_agent.run(seo_lookup_query)
        
        fusion_prompt = f"""
        You are a Data Fusion Expert.
        
        User Query: {query}
        
        GA4 Data:
        {ga4_result.get('answer', 'No GA4 data')}
        
        SEO Data:
        {seo_result.get('answer', 'No SEO data')}
        
        Combine these insights into a single answer. 
        If the user asked for a JSON output, provide strictly JSON.
        """
        
        messages = [{"role": "system", "content": fusion_prompt}]
        return {"answer": llm_client.get_completion(messages)}

orchestrator = Orchestrator()
