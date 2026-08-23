import requests
import json

MANIFEST = {
    "name": "autonomousselfupgrade",
    "description": "Initiates a comprehensive autonomous self-upgrade process by identifying new APIs, training modules, and relevant GitHub repositories.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "upgrade_focus": {
                "type": "string",
                "description": "Specifies the area of focus for the upgrade. Options: 'api_discovery', 'training_modules', 'github_research', or 'all'. Defaults to 'all'.",
                "enum": ["api_discovery", "training_modules", "github_research", "all"],
                "default": "all"
            },
            "search_query": {
                "type": "string",
                "description": "An optional specific keyword to refine the discovery process for all categories."
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of discovery results to report per category. Defaults to 3.",
                "default": 3
            }
        },
        "required": []
    }
}

def _github_search(query: str, max_results: int) -> list:
    """Helper function to search GitHub repositories, handling network and parsing errors."""
    base_url = "https://api.github.com/search/repositories"
    headers = {"Accept": "application/vnd.github.v3+json", "User-Agent": "J.A.R.V.I.S.SelfUpgradeSkill/1.0"}
    # GitHub's per_page max is 100, but we limit to prevent excessive data transfer for a skill call.
    params = {"q": query, "per_page": min(max_results, 10)} 
    
    try:
        response = requests.get(base_url, headers=headers, params=params, timeout=10)
        response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
        data = response.json()
        
        results = []
        for item in data.get("items", [])[:max_results]:
            results.append({
                "name": item.get("full_name"),
                "description": item.get("description", "No description provided."),
                "url": item.get("html_url"),
                "stars": item.get("stargazers_count", 0)
            })
        return results
    except requests.exceptions.Timeout:
        # Request timed out, return empty list to indicate no results from this attempt
        return []
    except requests.exceptions.RequestException:
        # Other request-related errors (e.g., network issues, bad URL, HTTP status)
        return []
    except json.JSONDecodeError:
        # Response was not valid JSON
        return []

def run(parameters=None, player=None, speak=None) -> str:
    """
    Implements a continuous autonomous self-upgrade mechanism by discovering and reporting
    potential resources for new APIs, self-training modules, and GitHub repositories
    for continuous improvement.
    """
    if parameters is None:
        parameters = {}

    upgrade_focus = parameters.get("upgrade_focus", "all").lower()
    custom_query = parameters.get("search_query")
    max_results = parameters.get("max_results", 3)
    
    # Validate and sanitize max_results
    if not isinstance(max_results, int) or max_results <= 0:
        max_results = 3 # Default to 3 if invalid

    discovered_resources_report = []
    
    try:
        # Autonomous API Discovery and Integration
        if upgrade_focus in ["api_discovery", "all"]:
            api_search_terms = ["public API list", "free API examples", "RESTful API services", "open source API"]
            if custom_query:
                api_search_terms.insert(0, custom_query + " API")
            
            api_results_combined = []
            for term in api_search_terms:
                if len(api_results_combined) >= max_results:
                    break
                api_results_combined.extend(_github_search(term, max_results))
            
            if api_results_combined:
                discovered_resources_report.append("\n**Potential API Integrations:**")
                # Remove duplicates based on URL and limit to max_results
                unique_api_results = []
                seen_urls = set()
                for res in api_results_combined:
                    if res['url'] not in seen_urls:
                        unique_api_results.append(res)
                        seen_urls.add(res['url'])
                
                for res in unique_api_results[:max_results]:
                    discovered_resources_report.append(f"- **{res['name']}** (Stars: {res['stars']}) - {res['url']}")
            else:
                discovered_resources_report.append("\n**Potential API Integrations:** No new public APIs identified at this time.")

        # Autonomous Self-Training Modules (AI, ML, Data Sites)
        if upgrade_focus in ["training_modules", "all"]:
            training_search_terms = ["AI training datasets", "machine learning tutorials", "deep learning resources", "data science learning paths"]
            if custom_query:
                training_search_terms.insert(0, custom_query + " AI/ML training")

            training_results_combined = []
            for term in training_search_terms:
                if len(training_results_combined) >= max_results:
                    break
                training_results_combined.extend(_github_search(term, max_results))

            if training_results_combined:
                discovered_resources_report.append("\n**Autonomous Self-Training Modules:**")
                unique_training_results = []
                seen_urls = set()
                for res in training_results_combined:
                    if res['url'] not in seen_urls:
                        unique_training_results.append(res)
                        seen_urls.add(res['url'])

                for res in unique_training_results[:max_results]:
                    discovered_resources_report.append(f"- **{res['name']}** (Stars: {res['stars']}) - {res['url']}")
            else:
                discovered_resources_report.append("\n**Autonomous Self-Training Modules:** No new self-training modules identified at this time.")

        # Utilize GitHub Repositories for Continuous Improvement and Self-Healing
        if upgrade_focus in ["github_research", "all"]:
            github_search_terms = ["autonomous agent framework", "self-healing systems code", "AI assistant improvement", "intelligent automation tools"]
            if custom_query:
                github_search_terms.insert(0, custom_query + " GitHub repository")

            github_results_combined = []
            for term in github_search_terms:
                if len(github_results_combined) >= max_results:
                    break
                github_results_combined.extend(_github_search(term, max_results))

            if github_results_combined:
                discovered_resources_report.append("\n**GitHub Repositories for Improvement/Self-Healing:**")
                unique_github_results = []
                seen_urls = set()
                for res in github_results_combined:
                    if res['url'] not in seen_urls:
                        unique_github_results.append(res)
                        seen_urls.add(res['url'])
                
                for res in unique_github_results[:max_results]:
                    discovered_resources_report.append(f"- **{res['name']}** (Stars: {res['stars']}) - {res['url']}")
            else:
                discovered_resources_report.append("\n**GitHub Repositories for Improvement/Self-Healing:** No new GitHub repositories identified for direct integration at this time.")

        if not discovered_resources_report:
            return "Analysis complete. No specific upgrade resources were identified based on the current parameters. Standing by for further instructions."
            
        return "Initiating autonomous self-upgrade resource discovery. Analysis complete. Discovered the following potential resources:\n" + "\n".join(discovered_resources_report)

    except Exception as e:
        # Catch any unexpected errors that might have bypassed specific handlers
        return f"An unexpected error occurred during autonomous upgrade resource discovery: {str(e)}. Please check system connectivity and try again."