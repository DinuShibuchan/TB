import httpx
from typing import Optional

class LLMService:
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url
        self.model = model
        self.ollama_online = None

    async def check_connection(self) -> bool:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.base_url, timeout=2.0)
                self.ollama_online = (response.status_code == 200)
                return self.ollama_online
        except Exception:
            self.ollama_online = False
            return False
        
    async def generate_response(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.0  # Zero temperature helps enforce strictly context-bound, realistic answers
            }
        }
        if system_prompt:
            payload["system"] = system_prompt
            
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=60.0)
                if response.status_code == 200:
                    self.ollama_online = True
                    result = response.json()
                    return result.get("response", "").strip()
                self.ollama_online = False
                return f"Error: Ollama returned status code {response.status_code}"
        except Exception as e:
            self.ollama_online = False
            return self._generate_mock_response(prompt)

    def _generate_mock_response(self, prompt: str) -> str:
        # Fallback Mock Generator if Ollama is offline
        import json
        import re
        
        # Determine if it's a chat or a trip plan request
        is_plan = "OUTPUT FORMAT (raw JSON only" in prompt
        
        # Extract Database Context
        db_context = ""
        if "Database Context:" in prompt:
            parts = prompt.split("Database Context:")
            if len(parts) > 1:
                db_part = parts[1]
                if "Wikipedia Context:" in db_part:
                    db_context = db_part.split("Wikipedia Context:")[0].strip()
                else:
                    db_context = db_part.strip()
                    
        # Extract Wikipedia Context
        wiki_context = ""
        if "Wikipedia Context:" in prompt:
            parts = prompt.split("Wikipedia Context:")
            if len(parts) > 1:
                wiki_part = parts[1]
                if "Weather at" in wiki_part:
                    wiki_context = wiki_part.split("Weather at")[0].strip()
                elif "User Query:" in wiki_part:
                    wiki_context = wiki_part.split("User Query:")[0].strip()
                else:
                    wiki_context = wiki_part.strip()

        no_db = not db_context or db_context == "None available"
        no_wiki = not wiki_context or wiki_context == "None available"
        
        if no_db and no_wiki:
            if is_plan:
                return '{"error": "Data not available"}'
            else:
                return "Data not available"
                
        if not is_plan:
            # Chat fallback: Intelligent context sentence matcher and synthesizer
            query = ""
            if "User Query:" in prompt:
                query = prompt.split("User Query:")[1].strip().lower()
            
            # Clean punctuation from query to prevent matching failures (e.g. "tokyo?" vs "tokyo")
            clean_query = re.sub(r"[^\w\s]", "", query)
            query_words = [w for w in clean_query.split() if len(w) > 2]
            
            # Define common stopwords to ignore for matching
            stopwords = {
                "what", "where", "when", "how", "who", "why", "which",
                "about", "would", "could", "should", "there", "their", "these", "those",
                "tell", "show", "give", "find", "need", "want", "like", "best", "good",
                "some", "more", "most", "have", "with", "from", "that", "this", "your",
                "places", "place", "food", "stay", "hotels", "hotel"
            }
            keywords = [w for w in query_words if w not in stopwords]
            if not keywords:
                keywords = query_words  # Fallback to all words if all are stopwords
                
            # Determine category intent from query
            category_intent = None
            if any(w in query for w in ["food", "eat", "restaurant", "restaurants", "dish", "dishes", "dine", "dining", "cuisine", "ramen", "gelato", "croissant", "bistro", "sadya"]):
                category_intent = "FOOD"
            elif any(w in query for w in ["stay", "hotel", "hotels", "hostel", "hostels", "accommodation", "accommodations", "lodge", "lodging"]):
                category_intent = "STAY"
            elif any(w in query for w in ["place", "places", "sight", "sights", "temple", "temples", "park", "parks", "waterfall", "crossing", "tower", "museum", "colosseum"]):
                category_intent = "PLACE"
                
            # Determine destination intent
            dest_intent = None
            for dest in ["tokyo", "paris", "rome", "munnar"]:
                if dest in query:
                    dest_intent = dest
                    break

            # Parse sentences from db_context and wiki_context with metadata
            candidate_sentences = []
            
            # 1. Parse Database Context
            if db_context and db_context != "None available":
                lines = db_context.split("\n")
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    # Check for category prefix e.g. "- [PLACE] Tokyo: Senso-ji is..."
                    category = None
                    dest_name = None
                    text_content = line
                    
                    match = re.match(r"^-\s*\[(PLACE|FOOD|STAY)\]\s*([^:]+):\s*(.*)$", line, re.IGNORECASE)
                    if match:
                        category = match.group(1).upper()
                        dest_name = match.group(2).strip().lower()
                        text_content = match.group(3).strip()
                    
                    # Split line into sentences
                    parts = [p.strip() for p in re.split(r"\.\s+", text_content) if p.strip()]
                    for part in parts:
                        if not part.endswith("."):
                            part += "."
                        candidate_sentences.append({
                            "text": part,
                            "category": category,
                            "destination": dest_name,
                            "source": "db"
                        })
            
            # 2. Parse Wikipedia Context
            if wiki_context and wiki_context != "None available":
                parts = [p.strip() for p in re.split(r"\.\s+", wiki_context) if p.strip()]
                for part in parts:
                    if not part.endswith("."):
                        part += "."
                    # Guess destination from first word of wiki context
                    dest_guess = None
                    first_words = wiki_context.strip().lower()
                    for dest in ["tokyo", "paris", "rome", "munnar"]:
                        if dest in first_words[:30]:
                            dest_guess = dest
                            break
                    candidate_sentences.append({
                        "text": part,
                        "category": None,
                        "destination": dest_guess,
                        "source": "wiki"
                    })

            # Score each sentence based on relevance
            scored_sentences = []
            for item in candidate_sentences:
                score = 0
                sentence_lower = item["text"].lower()
                
                # Check keyword matches
                for kw in keywords:
                    if kw in sentence_lower:
                        score += 5
                
                # Boost if destination matches query intent
                if dest_intent and item["destination"] == dest_intent:
                    score += 10
                    
                # Boost if category matches query intent
                if category_intent and item["category"] == category_intent:
                    score += 8
                    
                # Boost if the sentence actually contains specific keywords (e.g. food/stay words)
                if category_intent == "FOOD" and any(w in sentence_lower for w in ["food", "eat", "restaurant", "dish", "cuisine", "ramen", "gelato", "croissant", "bistro", "sadya"]):
                    score += 3
                if category_intent == "STAY" and any(w in sentence_lower for w in ["stay", "hotel", "hostel", "accommodation", "lodging"]):
                    score += 3
                    
                if score > 0:
                    scored_sentences.append((score, item["text"]))

            # Sort by score descending
            scored_sentences.sort(key=lambda x: x[0], reverse=True)
            
            # Select unique matching sentences up to a reasonable limit (3-4 sentences)
            selected = []
            seen = set()
            for score, text in scored_sentences:
                if text not in seen:
                    selected.append(text)
                    seen.add(text)
                if len(selected) >= 3:
                    break
                    
            if selected:
                return " ".join(selected)
                
            # Fallback 1: If no keyword matched but a destination was specified, return its sentences
            if dest_intent:
                dest_fallback = []
                for item in candidate_sentences:
                    if item["destination"] == dest_intent:
                        dest_fallback.append(item["text"])
                        if len(dest_fallback) >= 3:
                            break
                if dest_fallback:
                    return " ".join(dest_fallback)
                    
            # Fallback 2: Return first 2 sentences of combined context
            fallback_sentences = [item["text"] for item in candidate_sentences[:2]]
            if fallback_sentences:
                return " ".join(fallback_sentences)
                
            return "Data not available"
            
        else:
            # Trip Plan fallback
            dest = "Unknown"
            match = re.search(r"itinerary for (.*?) with a", prompt)
            if match:
                dest = match.group(1).strip()
            
            days = 1
            match = re.search(r"Generate a (\d+)-day travel itinerary", prompt)
            if match:
                days = int(match.group(1))
                
            budget = "Moderate"
            match = re.search(r"with a (.*?) budget", prompt)
            if match:
                budget = match.group(1).strip()

            places, foods, stays = [], [], []
            for line in db_context.split("\n"):
                line = line.strip()
                if line.startswith("- [PLACE]"):
                    places.append(line[len("- [PLACE]"):].strip())
                elif line.startswith("- [FOOD]"):
                    foods.append(line[len("- [FOOD]"):].strip())
                elif line.startswith("- [STAY]"):
                    stays.append(line[len("- [STAY]"):].strip())
                    
            if not places and not no_wiki:
                places.append(wiki_context[:200])
                
            itinerary = []
            for d in range(1, days + 1):
                place = places[(d - 1) % len(places)] if places else f"Explore {dest}"
                food = foods[(d - 1) % len(foods)] if foods else f"Local dining in {dest}"
                stay = stays[0] if stays else f"Standard accommodation in {dest}"
                
                activities = [s.strip() + "." for s in place.split(". ") if s.strip()][:2]
                if not activities:
                    activities = [f"Enjoy sightseeing in {dest}"]
                    
                itinerary.append({
                    "day": d,
                    "theme": f"Discovering {dest}",
                    "activities": activities,
                    "recommended_food": [food],
                    "recommended_stay": stay,
                    "estimated_cost": "$50-$100 per day" if budget == "Moderate" else ("$20-$40 per day" if budget == "Budget" else "$150-$300 per day")
                })
                
            return json.dumps({
                "destination": dest,
                "budget": budget,
                "days": days,
                "itinerary": itinerary
            })
