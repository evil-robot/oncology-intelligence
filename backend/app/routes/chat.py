"""
Chat endpoint for conversational AI interface.
Allows researchers, doctors, and parents to ask questions about the pediatric oncology search data.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import json
from openai import OpenAI
from ..database import get_db_connection
from ..config import get_settings

router = APIRouter(prefix="/api/chat", tags=["chat"])

settings = get_settings()

# Only initialize OpenAI client if API key is configured
client = None
if settings.openai_api_key:
    try:
        client = OpenAI(api_key=settings.openai_api_key)
    except Exception as e:
        print(f"Warning: Could not initialize OpenAI client: {e}")


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    conversation_history: Optional[List[ChatMessage]] = []
    context_filter: Optional[dict] = None  # Optional filters like category, geo, etc.


class ChatResponse(BaseModel):
    response: str
    sources: Optional[List[dict]] = None
    suggested_questions: Optional[List[str]] = None


def get_data_context(filters: Optional[dict] = None) -> dict:
    """Gather relevant data context from the database."""
    conn = get_db_connection()
    cur = conn.cursor()
    context = {}

    try:
        # Get summary stats
        cur.execute("SELECT COUNT(*) FROM search_terms")
        context["total_terms"] = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM clusters")
        context["total_clusters"] = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM trend_data")
        context["total_trend_points"] = cur.fetchone()[0]

        # Get top trending terms (last 30 days)
        cur.execute("""
            SELECT st.term, st.category, AVG(td.interest) as avg_interest
            FROM search_terms st
            JOIN trend_data td ON st.id = td.term_id
            WHERE td.date >= CURRENT_DATE - INTERVAL '30 days'
            GROUP BY st.id, st.term, st.category
            ORDER BY avg_interest DESC
            LIMIT 10
        """)
        context["top_trending"] = [
            {"term": row[0], "category": row[1], "avg_interest": float(row[2]) if row[2] else 0}
            for row in cur.fetchall()
        ]

        # Get clusters with term counts
        cur.execute("""
            SELECT c.name, c.description, COUNT(st.id) as term_count
            FROM clusters c
            LEFT JOIN search_terms st ON st.cluster_id = c.id
            GROUP BY c.id, c.name, c.description
            ORDER BY term_count DESC
        """)
        context["clusters"] = [
            {"name": row[0], "description": row[1], "term_count": row[2]}
            for row in cur.fetchall()
        ]

        # Get categories breakdown
        cur.execute("""
            SELECT category, COUNT(*) as count
            FROM search_terms
            WHERE category IS NOT NULL
            GROUP BY category
            ORDER BY count DESC
        """)
        context["categories"] = [
            {"category": row[0], "count": row[1]}
            for row in cur.fetchall()
        ]

        # Get geographic regions with SDOH data
        cur.execute("""
            SELECT geo_code, name, svi_overall, population
            FROM geographic_regions
            ORDER BY svi_overall DESC NULLS LAST
            LIMIT 10
        """)
        context["high_vulnerability_regions"] = [
            {"geo_code": row[0], "name": row[1], "svi": float(row[2]) if row[2] else None, "population": row[3]}
            for row in cur.fetchall()
        ]

        # Get recent anomalies/spikes (terms with high recent interest)
        cur.execute("""
            SELECT st.term, st.category, td.interest, td.date
            FROM search_terms st
            JOIN trend_data td ON st.id = td.term_id
            WHERE td.interest > 70
            AND td.date >= CURRENT_DATE - INTERVAL '7 days'
            ORDER BY td.interest DESC
            LIMIT 5
        """)
        context["recent_spikes"] = [
            {"term": row[0], "category": row[1], "interest": row[2], "date": str(row[3])}
            for row in cur.fetchall()
        ]

        # Get all terms for reference
        cur.execute("""
            SELECT term, category, subcategory
            FROM search_terms
            ORDER BY category, term
            LIMIT 100
        """)
        context["all_terms"] = [
            {"term": row[0], "category": row[1], "subcategory": row[2]}
            for row in cur.fetchall()
        ]

    except Exception as e:
        print(f"Error fetching context: {e}")
    finally:
        cur.close()
        conn.close()

    return context


SYSTEM_PROMPT = """You are an AI assistant for the Oncology & Rare Disease Intelligence dashboard.
You help researchers, clinicians, patients, caregivers, and advocates understand search trends related to cancer and rare diseases.

Your knowledge includes:
- Google Trends data showing what people search for related to:
  * Pediatric oncology (childhood cancers, leukemia, brain tumors, etc.)
  * Adult oncology (breast, lung, colorectal, prostate cancers, melanoma, lymphoma, etc.)
  * Rare genetic diseases (Gaucher, Fabry, muscular dystrophy, cystic fibrosis, etc.)
  * Rare neurological conditions (Huntington's, ALS, MS, ataxias, etc.)
  * Rare autoimmune and metabolic disorders
  * Cancer treatments (immunotherapy, CAR-T, targeted therapy, clinical trials)
- Semantic clusters grouping similar search terms together
- Social Determinants of Health (SDOH) data from CDC's Social Vulnerability Index
- Geographic patterns in search behavior across US states and metro areas

When answering questions:
1. Be empathetic - remember that users may be patients, caregivers, or family members dealing with serious diagnoses
2. Be precise - cite specific data points when available
3. Be helpful - suggest actionable insights when relevant
4. Be clear about limitations - this is search data, not medical data or diagnosis

You can help with questions like:
- "What are people searching for about triple negative breast cancer?"
- "Are there regional differences in rare disease searches?"
- "What immunotherapy topics are trending?"
- "How do searches differ in high-vulnerability communities?"
- "What's the search interest in gene therapy for muscular dystrophy?"
- "Compare search patterns for different cancer types"

Always maintain a supportive, informative tone. If asked medical questions, remind users to consult healthcare professionals.

Current data context will be provided with each query."""


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Process a chat message and return an AI-generated response."""

    # Gather data context (needed for both AI and fallback responses)
    context = get_data_context(request.context_filter)

    # If OpenAI is not configured, return a helpful fallback response
    if not client or not settings.openai_api_key:
        return generate_fallback_response(request.message, context)

    # Build messages for OpenAI
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": f"Current data context:\n{json.dumps(context, indent=2)}"}
    ]

    # Add conversation history
    for msg in request.conversation_history[-10:]:  # Limit history to last 10 messages
        messages.append({"role": msg.role, "content": msg.content})

    # Add current user message
    messages.append({"role": "user", "content": request.message})

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Cost-effective for this use case
            messages=messages,
            temperature=0.7,
            max_tokens=1000
        )

        assistant_message = response.choices[0].message.content

        # Generate suggested follow-up questions
        suggested_questions = generate_suggestions(request.message, context)

        return ChatResponse(
            response=assistant_message,
            sources=[
                {"type": "terms", "count": context.get("total_terms", 0)},
                {"type": "trend_points", "count": context.get("total_trend_points", 0)},
                {"type": "clusters", "count": context.get("total_clusters", 0)}
            ],
            suggested_questions=suggested_questions
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating response: {str(e)}")


def generate_fallback_response(query: str, context: dict) -> ChatResponse:
    """Generate a helpful response without OpenAI by analyzing the query and context."""
    query_lower = query.lower()

    response_parts = []

    # Check for trending/popular questions
    if any(word in query_lower for word in ['trending', 'popular', 'top', 'most']):
        if context.get('top_trending'):
            trending = context['top_trending'][:5]
            terms_list = ', '.join([f"**{t['term']}** ({t['category']})" for t in trending])
            response_parts.append(f"📈 **Top Trending Terms:**\n{terms_list}")

    # Check for category questions
    if any(word in query_lower for word in ['category', 'categories', 'types', 'breakdown']):
        if context.get('categories'):
            cats = context['categories'][:5]
            cat_list = '\n'.join([f"• {c['category'].replace('_', ' ').title()}: {c['count']} terms" for c in cats])
            response_parts.append(f"📊 **Categories:**\n{cat_list}")

    # Check for cluster questions
    if any(word in query_lower for word in ['cluster', 'group', 'semantic']):
        if context.get('clusters'):
            clusters = context['clusters'][:5]
            cluster_list = '\n'.join([f"• {c['name']}: {c['term_count']} terms" for c in clusters])
            response_parts.append(f"🔮 **Semantic Clusters:**\n{cluster_list}")

    # Check for regional/geographic questions
    if any(word in query_lower for word in ['region', 'geographic', 'state', 'area', 'sdoh', 'vulnerability']):
        if context.get('high_vulnerability_regions'):
            regions = context['high_vulnerability_regions'][:5]
            region_list = '\n'.join([f"• {r['name']}: SVI {r['svi']:.2f}" for r in regions if r['svi']])
            response_parts.append(f"🗺️ **High Vulnerability Regions (by SDOH):**\n{region_list}")

    # Check for spike/anomaly questions
    if any(word in query_lower for word in ['spike', 'anomaly', 'unusual', 'sudden']):
        if context.get('recent_spikes'):
            spikes = context['recent_spikes']
            spike_list = '\n'.join([f"• {s['term']}: {s['interest']}% interest on {s['date']}" for s in spikes])
            response_parts.append(f"⚡ **Recent Spikes:**\n{spike_list}")

    # Default: show summary stats
    if not response_parts:
        stats = f"""📊 **Dashboard Overview:**
• Total search terms tracked: {context.get('total_terms', 0)}
• Semantic clusters: {context.get('total_clusters', 0)}
• Trend data points: {context.get('total_trend_points', 0)}

💡 **Try asking about:**
• "What terms are trending?"
• "Show me the categories"
• "Which regions have high vulnerability?"
• "Any recent spikes in search activity?"

*Note: Full AI chat requires OpenAI API key configuration.*"""
        response_parts.append(stats)

    # Add note about limited mode
    response_parts.append("\n\n*ℹ️ Running in data-only mode. For conversational AI, configure OPENAI_API_KEY.*")

    return ChatResponse(
        response='\n\n'.join(response_parts),
        sources=[
            {"type": "terms", "count": context.get("total_terms", 0)},
            {"type": "trend_points", "count": context.get("total_trend_points", 0)},
            {"type": "clusters", "count": context.get("total_clusters", 0)}
        ],
        suggested_questions=[
            "What terms are trending?",
            "Show me the categories breakdown",
            "Which regions have high SDOH vulnerability?",
            "Any recent spikes in activity?"
        ]
    )


def generate_suggestions(query: str, context: dict) -> List[str]:
    """Generate relevant follow-up questions based on the query and context."""
    suggestions = []

    # Base suggestions
    base_suggestions = [
        "What search terms are trending this week?",
        "How do searches vary by region?",
        "What support resources are people looking for?",
        "Are there any unusual spikes in search activity?",
    ]

    # Context-aware suggestions
    if context.get("top_trending"):
        top_term = context["top_trending"][0]["term"]
        suggestions.append(f"Tell me more about searches for '{top_term}'")

    if context.get("clusters"):
        cluster = context["clusters"][0]["name"]
        suggestions.append(f"What terms are in the '{cluster}' cluster?")

    if context.get("high_vulnerability_regions"):
        region = context["high_vulnerability_regions"][0]["name"]
        suggestions.append(f"What are people searching for in {region}?")

    # Combine and limit
    all_suggestions = suggestions + base_suggestions
    return all_suggestions[:4]


@router.get("/suggestions")
async def get_suggestions():
    """Get initial suggested questions for the chat interface."""
    return {
        "suggestions": [
            "What cancer types have the highest search interest?",
            "Show me trends for immunotherapy searches",
            "Which rare diseases are trending?",
            "What support resources are people looking for?",
            "How do searches differ by region?",
            "Compare pediatric vs adult cancer search patterns",
            "What gene therapy topics are emerging?",
            "Which conditions show regional disparities?"
        ]
    }
